"""Portal invitations (PORTAL-01.3): invite, resend, revoke and accept.

Only staff with ``portal.invite_portal_account`` in a department of the record
may invite. Accepting creates a local portal account (username = e-mail) and a
confirmed AccountLink; it never takes over an existing account.
"""

import hashlib
import logging
import secrets
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from dynamic_preferences.registries import global_preferences_registry

from members.models import Member, Parent

from .models import AccountLink, Invitation
from .policy import member_portal_allowed

INVITE_PERMISSION = "portal.invite_portal_account"
security_log = logging.getLogger("security.portal")
User = get_user_model()


class InvitationError(Exception):
    def __init__(self, code, detail, status=400):
        super().__init__(detail)
        self.code, self.detail, self.status = code, detail, status


def hash_token(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


# --------------------------------------------------------------------- scope
def record_department_ids(record):
    if isinstance(record, Parent):
        return set(
            Member.departments.through.objects.filter(member__parent=record).values_list("department_id", flat=True)
        )
    return set(record.departments.values_list("pk", flat=True))


def departments_with_permission(user, permission):
    """Departments where ``user`` holds ``permission``; None means every department."""
    if user.is_superuser:
        return None
    if user.has_perm("departments.can_access_all_departments") and user.has_perm(permission):
        return None
    assigned = set(user.department_roles.values_list("department_id", flat=True))
    if user.has_perm(permission):
        return assigned
    app_label, codename = permission.split(".")
    return set(
        user.department_roles.filter(
            groups__permissions__content_type__app_label=app_label, groups__permissions__codename=codename
        ).values_list("department_id", flat=True)
    )


def inviting_department_ids(user):
    """Departments where ``user`` may invite; None means every department."""
    return departments_with_permission(user, INVITE_PERMISSION)


def may_invite(user, record):
    allowed = inviting_department_ids(user)
    return allowed is None or bool(allowed & record_department_ids(record))


def scoped_invitations(user):
    allowed = inviting_department_ids(user)
    invitations = Invitation.objects.select_related("parent", "member", "created_by")
    if allowed is None:
        return invitations
    return (
        invitations.filter(member__departments__in=allowed)
        | invitations.filter(parent__children__departments__in=allowed)
    ).distinct()


def scoped_records(user, model):
    allowed = inviting_department_ids(user)
    records = model.objects.all()
    if allowed is None:
        return records
    field = "children__departments__in" if model is Parent else "departments__in"
    return records.filter(**{field: allowed}).distinct()


# --------------------------------------------------------------------- mail
def _send(invitation, raw_token):
    record = invitation.record
    prefs = global_preferences_registry.manager()
    context = {
        "org_name": prefs["general__title"],
        "first_name": record.name,
        "kind": invitation.kind,
        "children": [child.name for child in record.children.all()] if invitation.kind == "parent" else [],
        "accept_url": f"{settings.FRONTEND_URL.rstrip('/')}/passwort-festlegen?token={raw_token}",
        "expires_at": timezone.localtime(invitation.expires_at).strftime("%d.%m.%Y, %H:%M Uhr"),
        "site_name": prefs["general__title"],
    }
    from orders.notifications.template_service import TemplateRenderer

    subject, html_message, plain_message = TemplateRenderer.render_email_content("portal_invite", context)
    try:
        send_mail(subject, plain_message, settings.DEFAULT_FROM_EMAIL, [invitation.email], html_message=html_message)
    except (ImproperlyConfigured, OSError, SMTPException) as exc:
        # The surrounding transaction rolls back: no open invitation without a delivered link.
        security_log.warning("portal invitation mail failed", extra={"error": type(exc).__name__})
        raise InvitationError(
            "mail_failed",
            "Die Einladung konnte nicht per E-Mail versendet werden. Bitte den E-Mail-Versand in den Einstellungen prüfen.",
            503,
        ) from exc
    invitation.sent_at = timezone.now()


def _new_token(invitation):
    raw = secrets.token_urlsafe(32)
    invitation.token_hash = hash_token(raw)
    invitation.expires_at = timezone.now() + timedelta(days=Invitation.VALIDITY_DAYS)
    return raw


# --------------------------------------------------------------------- staff actions
def _check_invitable(record):
    email = (record.email or "").strip()
    if not email:
        raise InvitationError("email_missing", "Am Datensatz ist keine E-Mail-Adresse hinterlegt.")
    if isinstance(record, Member) and not member_portal_allowed(record):
        raise InvitationError(
            "member_portal_disabled", "Das Mitgliederportal ist für dieses Mitglied nicht freigegeben.", 422
        )
    if AccountLink.objects.filter(**{"parent" if isinstance(record, Parent) else "member": record}).exists():
        raise InvitationError("already_linked", "Für diesen Datensatz besteht bereits ein Zugang.", 409)
    if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
        # Linking an existing account needs its confirmation (PORTAL-04); never a second account.
        raise InvitationError("account_exists", "Mit dieser E-Mail-Adresse besteht bereits ein Konto.", 409)
    return email


@transaction.atomic
def invite(record, actor):
    email = _check_invitable(record)
    field = "parent" if isinstance(record, Parent) else "member"
    if Invitation.objects.filter(**{field: record}, accepted_at__isnull=True, revoked_at__isnull=True).exists():
        raise InvitationError("invitation_open", "Es besteht bereits eine offene Einladung.", 409)
    invitation = Invitation(**{field: record}, email=email, created_by=actor)
    raw = _new_token(invitation)
    invitation.save()
    _send(invitation, raw)
    invitation.save(update_fields=["sent_at"])
    security_log.info("portal invitation sent", extra={"invitation": invitation.pk, "actor": actor.pk})
    return invitation


@transaction.atomic
def resend(invitation, actor):
    invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
    if invitation.state not in {"open", "expired"}:
        raise InvitationError("not_open", "Die Einladung ist nicht mehr offen.", 409)
    invitation.email = _check_invitable(invitation.record)
    raw = _new_token(invitation)
    _send(invitation, raw)
    invitation.save(update_fields=["email", "token_hash", "expires_at", "sent_at"])
    security_log.info("portal invitation resent", extra={"invitation": invitation.pk, "actor": actor.pk})
    return invitation


@transaction.atomic
def revoke(invitation, actor):
    invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
    if invitation.state not in {"open", "expired"}:
        raise InvitationError("not_open", "Die Einladung ist nicht mehr offen.", 409)
    invitation.revoked_at = timezone.now()
    invitation.save(update_fields=["revoked_at"])
    security_log.info("portal invitation revoked", extra={"invitation": invitation.pk, "actor": actor.pk})
    return invitation


# --------------------------------------------------------------------- acceptance
def open_invitation(raw_token):
    """The open invitation for a token, or InvitationError (no hint whether it ever existed)."""
    invitation = (
        Invitation.objects.select_related("parent", "member").filter(token_hash=hash_token(raw_token or "")).first()
    )
    if invitation is None or invitation.state in {"accepted", "revoked"}:
        raise InvitationError("invalid", "Dieser Einladungslink ist ungültig oder wurde bereits verwendet.", 404)
    if invitation.state == "expired":
        raise InvitationError(
            "expired", "Dieser Einladungslink ist abgelaufen. Bitte die Jugendfeuerwehr um eine neue Einladung.", 410
        )
    return invitation


@transaction.atomic
def accept(raw_token, password):
    invitation = open_invitation(raw_token)
    invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
    if invitation.state != "open":
        raise InvitationError("invalid", "Dieser Einladungslink ist ungültig oder wurde bereits verwendet.", 404)
    record = invitation.record
    if invitation.kind == "member" and not member_portal_allowed(record):
        raise InvitationError("member_portal_disabled", "Das Mitgliederportal ist nicht freigegeben.", 422)
    if (
        AccountLink.objects.filter(**{invitation.kind: record}).exists()
        or User.objects.filter(email__iexact=invitation.email).exists()
    ):
        raise InvitationError("account_exists", "Für diese Einladung besteht bereits ein Zugang.", 409)
    user = User(
        username=invitation.email,
        email=invitation.email,
        first_name=record.name,
        last_name=record.lastname,
        account_kind=User.AccountKind.PORTAL,
        dsgvo_external=True,
    )
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise InvitationError("password", " ".join(exc.messages)) from exc
    user.set_password(password)
    user.save()
    now = timezone.now()
    AccountLink.objects.create(
        user=user,
        status=AccountLink.Status.CONFIRMED,
        linked_by=invitation.created_by,
        confirmed_at=now,
        **{invitation.kind: record},
    )
    invitation.accepted_at, invitation.accepted_user = now, user
    invitation.save(update_fields=["accepted_at", "accepted_user"])
    security_log.info("portal invitation accepted", extra={"invitation": invitation.pk, "user": user.pk})
    return user
