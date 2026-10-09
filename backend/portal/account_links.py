"""Staff account ↔ member/parent record (PORTAL-04, concept 4.10, E13, Q4).

Account management links a staff account 1:1 to a member record and/or a
parent record. The link stays ``pending`` without any effect until the account
itself confirms it after login; a rejection notifies the linking person.
Portal accounts are never linked here: their links come from invitations and
end through the portal lifecycle. All writes lock the affected rows, so two
parallel requests cannot bind one record twice (the one-to-one columns are the
final guard).
"""

import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from members.models import Member, Parent

from .invitations import departments_with_permission, record_department_ids
from .models import AccountLink, Invitation

User = get_user_model()
security_log = logging.getLogger("security.portal")

LINK_PERMISSION = "users.change_customuser"
CONFIRM_ROUTE = "/konto-bestaetigen"
FIELDS = ("member", "parent")
RELEASE_KIND = "account_link_release"


class LinkError(Exception):
    def __init__(self, code, detail, status=409):
        super().__init__(detail)
        self.code, self.detail, self.status = code, detail, status


# --------------------------------------------------------------------- scope
def linking_departments(user):
    """Departments in which ``user`` may link accounts; None means every department."""
    return departments_with_permission(user, LINK_PERMISSION)


def may_manage_links(user):
    allowed = linking_departments(user)
    return allowed is None or bool(allowed)


def may_link(user, record):
    """Account management in at least one department of the record (parents: of a child)."""
    allowed = linking_departments(user)
    return allowed is None or bool(allowed & record_department_ids(record))


def scoped_links(user):
    links = AccountLink.objects.select_related("user", "member", "parent", "linked_by").filter(
        user__account_kind=User.AccountKind.STAFF
    )
    allowed = linking_departments(user)
    if allowed is None:
        return links
    return (
        links.filter(member__departments__in=allowed) | links.filter(parent__children__departments__in=allowed)
    ).distinct()


# --------------------------------------------------------------------- payloads
def _name(user):
    return (user.get_full_name() or user.username) if user else ""


def _member_card(member):
    if member is None:
        return None
    return {
        "id": member.pk,
        "name": member.get_full_name(),
        "birth_year": member.birthday.year if member.birthday else None,
        "departments": sorted(d.name for d in member.departments.all()),
        "group": member.group.name if member.group_id else None,
    }


def _parent_card(parent):
    if parent is None:
        return None
    return {
        "id": parent.pk,
        "name": parent.get_full_name(),
        "children": [
            {"first_name": child.name, "group": child.group.name if child.group_id else None}
            for child in parent.children.select_related("group").order_by("name")
        ],
    }


def link_payload(link):
    data = {
        "id": link.pk,
        "status": link.status,
        "user": {"id": link.user_id, "username": link.user.username, "name": _name(link.user)},
        "member": _member_card(link.member),
        "parent": _parent_card(link.parent),
        "linked_by": _name(link.linked_by),
        "linked_at": link.linked_at,
        "confirmed_at": link.confirmed_at,
        "rejected_at": link.rejected_at,
    }
    return data


def describe(link):
    """Short, name-only description for notices and mails (no other personal data)."""
    parts = []
    if link.member_id:
        parts.append(f"Mitgliedsdatensatz {link.member.get_full_name()}")
    if link.parent_id:
        parts.append(f"Elterndatensatz {link.parent.get_full_name()}")
    return " und ".join(parts)


# --------------------------------------------------------------------- writes
def _check_record(record, user, transfer, actor):
    """Free ``record`` for ``user`` or raise; returns links that must be released first."""
    field = "parent" if isinstance(record, Parent) else "member"
    existing = AccountLink.objects.select_for_update().select_related("user").filter(**{field: record}).first()
    if existing is not None and existing.user_id != user.pk:
        if existing.status == AccountLink.Status.REJECTED:
            return existing  # a rejected link has no effect; it yields to the new one
        if existing.user.is_portal_account:
            if not (transfer and actor.is_superuser):
                raise LinkError(
                    "record_has_portal_account",
                    "Für diesen Datensatz besteht ein Portalzugang. Umwandeln kann nur die Systemadministration.",
                )
            return existing
        raise LinkError(
            "record_linked",
            "Dieser Datensatz ist bereits mit einem anderen Konto verknüpft.",
        )
    if Invitation.objects.filter(**{field: record}, accepted_at__isnull=True, revoked_at__isnull=True).exists():
        raise LinkError(
            "invitation_open",
            "Für diesen Datensatz ist eine Portaleinladung offen. Bitte die Einladung zuerst widerrufen.",
        )
    return None


def _release(existing, field, actor):
    """Detach ``field`` from a rejected link or end a portal account's access (transfer)."""
    if existing.user.is_portal_account:
        from .lifecycle import end

        end(getattr(existing, field), actor)
        security_log.info("portal account converted to staff link", extra={"user": existing.user_id, "actor": actor.pk})
        return
    other = "parent" if field == "member" else "member"
    if getattr(existing, f"{other}_id") is None:
        existing.delete()
    else:
        setattr(existing, field, None)
        existing.save(update_fields=[field])


@transaction.atomic
def link(actor, user, *, member=None, parent=None, transfer=False):
    """Create or extend the link of a staff account; returns ``(link, changed)``.

    A new or extended link is pending again: the account confirms the complete
    set of records (E13). Records already bound elsewhere answer 409.
    """
    if member is None and parent is None:
        raise LinkError("target_missing", "Bitte ein Mitglied oder einen Elterndatensatz wählen.", 400)
    user = User.objects.select_for_update().get(pk=user.pk)
    if user.is_portal_account:
        raise LinkError("portal_account", "Portalzugänge werden in der Portalverwaltung verknüpft.")
    if not user.is_active:
        raise LinkError("account_inactive", "Das Konto ist deaktiviert.")
    if user.pk == actor.pk and not actor.is_superuser:
        raise LinkError("own_account", "Das eigene Konto verknüpft eine andere Person.", 403)
    current = AccountLink.objects.select_for_update().filter(user=user).first()
    if current is not None and current.status == AccountLink.Status.REJECTED:
        current.delete()  # start over; the rejection was reported to the linking person
        current = None
    targets = {"member": member, "parent": parent}
    for field, record in targets.items():
        if record is None:
            continue
        bound = getattr(current, f"{field}_id", None) if current else None
        if bound is not None and bound != record.pk:
            label = "einem Mitglied" if field == "member" else "einem Elterndatensatz"
            raise LinkError("account_linked", f"Das Konto ist bereits mit {label} verknüpft.")
    releases = []
    for field, record in targets.items():
        if record is not None:
            existing = _check_record(record, user, transfer, actor)
            if existing is not None:
                releases.append((existing, field))
    for existing, field in releases:
        _release(existing, field, actor)
    changed = current is None or any(
        record is not None and getattr(current, f"{field}_id") != record.pk for field, record in targets.items()
    )
    if not changed:
        return current, False
    now = timezone.now()
    try:
        with transaction.atomic():
            if current is None:
                current = AccountLink.objects.create(
                    user=user, member=member, parent=parent, linked_by=actor, status=AccountLink.Status.PENDING
                )
            else:
                for field, record in targets.items():
                    if record is not None:
                        setattr(current, field, record)
                current.status = AccountLink.Status.PENDING
                current.linked_by = actor
                current.linked_at = now
                current.confirmed_at = None
                current.rejected_at = None
                current.save()
    except IntegrityError as error:
        raise LinkError("record_linked", "Dieser Datensatz wurde gerade mit einem anderen Konto verknüpft.") from error
    security_log.info(
        "account link pending",
        extra={"link": current.pk, "user": user.pk, "actor": actor.pk, "member": bool(current.member_id)},
    )
    transaction.on_commit(lambda link_id=current.pk: _notify_account(link_id))
    return current, True


@transaction.atomic
def unlink(actor, link_obj, target=None):
    """Remove one record (``member``/``parent``) or the whole link. Existing registrations stay (4.10)."""
    link_obj = AccountLink.objects.select_for_update().select_related("user").get(pk=link_obj.pk)
    if link_obj.user.is_portal_account:
        raise LinkError("portal_account", "Portalzugänge werden in der Portalverwaltung beendet.")
    fields = [target] if target in FIELDS else list(FIELDS)
    for field in fields:
        setattr(link_obj, field, None)
    from notifications.inbox import complete_tasks

    complete_tasks(object_type="portal.accountlink", object_id=link_obj.pk, kind=RELEASE_KIND, by=actor, via="ui")
    if link_obj.member_id is None and link_obj.parent_id is None:
        link_obj.delete()
        remaining = None
    else:
        link_obj.save(update_fields=fields)
        remaining = link_obj
    security_log.info(
        "account link released", extra={"user": link_obj.user_id, "actor": actor.pk, "target": target or "all"}
    )
    return remaining


def pending_for(user):
    if user.is_portal_account:
        return None
    return (
        AccountLink.objects.select_related("member__group", "parent", "linked_by")
        .filter(user=user, status=AccountLink.Status.PENDING)
        .first()
    )


@transaction.atomic
def decide(user, link_id, accept):
    """The account confirms or rejects its own pending link; deciding again is a no-op."""
    link_obj = AccountLink.objects.select_for_update().filter(pk=link_id, user=user).first()
    if link_obj is None:
        raise LinkError("not_found", "Keine Verknüpfung gefunden.", 404)
    wanted = AccountLink.Status.CONFIRMED if accept else AccountLink.Status.REJECTED
    if link_obj.status == wanted:
        return link_obj
    if link_obj.status != AccountLink.Status.PENDING:
        raise LinkError("decided", "Über diese Verknüpfung wurde bereits entschieden.")
    link_obj.status = wanted
    if accept:
        link_obj.confirmed_at = timezone.now()
    else:
        link_obj.rejected_at = timezone.now()
    link_obj.save(update_fields=["status", "confirmed_at", "rejected_at"])
    security_log.info("account link decided", extra={"link": link_obj.pk, "user": user.pk, "status": wanted})
    transaction.on_commit(lambda: _notify_linker(link_obj.pk))
    return link_obj


def request_release(user):
    """The account asks account management to dissolve its confirmed link (4.10 "Lösen")."""
    from notifications.inbox import notify
    from notifications.models import InboxItem

    link_obj = AccountLink.objects.select_related("member", "parent").filter(user=user).first()
    if link_obj is None or link_obj.status != AccountLink.Status.CONFIRMED:
        raise LinkError("not_linked", "Es besteht keine bestätigte Verknüpfung.", 404)
    record = link_obj.member or link_obj.parent
    departments = sorted(record_department_ids(record))
    open_task = InboxItem.objects.filter(
        kind=RELEASE_KIND,
        task_state=InboxItem.TaskState.OPEN,
        object_type="portal.accountlink",
        object_id=link_obj.pk,
    )
    if open_task.exists():
        return False
    from .account_link_notices import staff_for

    notify(
        kind=RELEASE_KIND,
        category=InboxItem.Category.ACCOUNTS,
        item_type=InboxItem.ItemType.TASK,
        title=f"{_name(user)} bittet, die Verknüpfung mit {describe(link_obj)} zu lösen",
        department=departments[0] if departments else None,
        obj=link_obj,
        permission=LINK_PERMISSION,
        link=f"/members/{link_obj.member_id}" if link_obj.member_id else f"/parents/{link_obj.parent_id}/edit",
        recipients=staff_for(departments),
    )
    security_log.info("account link release requested", extra={"link": link_obj.pk, "user": user.pk})
    return True


def _notify_account(link_id):
    from .account_link_notices import link_pending

    link_pending(link_id)


def _notify_linker(link_id):
    from .account_link_notices import link_decided

    link_decided(link_id)


# --------------------------------------------------------------------- suggestions
def suggestions_for_user(actor, user, limit=10):
    """Member and parent records with the account's e-mail address or name, inside the actor's scope."""
    allowed = linking_departments(actor)
    found = []
    for model in (Member, Parent):
        records = model.objects.all()
        if allowed is not None:
            field = "children__departments__in" if model is Parent else "departments__in"
            records = records.filter(**{field: allowed})
        query = None
        if user.email:
            query = Q(email__iexact=user.email)
        if user.first_name and user.last_name:
            by_name = Q(name__iexact=user.first_name, lastname__iexact=user.last_name)
            query = by_name if query is None else query | by_name
        if query is None:
            continue
        for record in records.filter(query).distinct().order_by("lastname", "name")[:limit]:
            kind = "parent" if model is Parent else "member"
            link_obj = AccountLink.objects.filter(**{kind: record}).select_related("user").first()
            found.append(
                {
                    "kind": kind,
                    "id": record.pk,
                    "name": record.get_full_name(),
                    "reason": "email" if user.email and (record.email or "").lower() == user.email.lower() else "name",
                    "linked": bool(link_obj and link_obj.status != AccountLink.Status.REJECTED),
                }
            )
    return found


def suggestions_for_record(record, limit=10):
    """Active staff accounts with the record's e-mail address or name."""
    from users.people import person_accounts

    query = Q(first_name__iexact=record.name, last_name__iexact=record.lastname)
    if record.email:
        query |= Q(email__iexact=record.email)
    accounts = person_accounts().filter(account_kind=User.AccountKind.STAFF).filter(query).order_by("last_name")
    return [
        {
            "id": account.pk,
            "username": account.username,
            "name": _name(account),
            "reason": "email" if record.email and (account.email or "").lower() == record.email.lower() else "name",
            "linked": AccountLink.objects.filter(user=account).exclude(status=AccountLink.Status.REJECTED).exists(),
        }
        for account in accounts[:limit]
    ]


def search_accounts(text, limit=20):
    """Active staff accounts for the link dialog (account management only)."""
    from users.people import person_accounts

    accounts = person_accounts().filter(account_kind=User.AccountKind.STAFF)
    text = (text or "").strip()
    if text:
        accounts = accounts.filter(
            Q(username__icontains=text)
            | Q(first_name__icontains=text)
            | Q(last_name__icontains=text)
            | Q(email__icontains=text)
        )
    accounts = list(accounts.order_by("last_name", "first_name", "username")[:limit])
    linked = set(
        AccountLink.objects.filter(user__in=accounts)
        .exclude(status=AccountLink.Status.REJECTED)
        .values_list("user_id", flat=True)
    )
    return [
        {"id": a.pk, "username": a.username, "name": _name(a), "reason": "", "linked": a.pk in linked}
        for a in accounts
    ]
