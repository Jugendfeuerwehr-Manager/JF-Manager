"""Portal access lifecycle (PORTAL-01.4): suspend, resume, end, extend, daily check.

States of a record's access: none → invited (expired) → active → suspended | ended.
Suspending or ending revokes every session of the account immediately. Ending
detaches the record; an account without any linked record is deactivated, never
deleted (deletion follows the existing member deletion rules).
"""

import logging
from datetime import date, timedelta

from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone

from members.models import Member, Parent
from users.models import UserSession

from .models import AccountLink, Invitation, ParentAccessExtension
from .people import eighteen_years_before, visible_children

security_log = logging.getLogger("security.portal")
WARNING_DAYS = 30
MAX_EXTENSION_MONTHS = 12


class LifecycleError(Exception):
    def __init__(self, code, detail, status=400):
        super().__init__(detail)
        self.code, self.detail, self.status = code, detail, status


def _field(record):
    return "parent" if isinstance(record, Parent) else "member"


def revoke_sessions(user):
    sessions = UserSession.objects.filter(user=user).values("session_id")
    Session.objects.filter(session_key__in=sessions).delete()


def link_for(record):
    return AccountLink.objects.select_related("user").filter(**{_field(record): record}).first()


def access_state(record):
    """One of none, invited, expired, active, suspended for a parent or member record."""
    return access_states([record])[record.pk]


def access_states(records):
    """Bulk variant for lists: {record.pk: state} with a constant number of queries."""
    if not records:
        return {}
    field = _field(records[0])
    ids = [r.pk for r in records]
    links = {
        getattr(link, f"{field}_id"): link
        for link in AccountLink.objects.select_related("user").filter(**{f"{field}__in": ids})
    }
    invitations = {
        getattr(inv, f"{field}_id"): inv
        for inv in Invitation.objects.filter(**{f"{field}__in": ids}, accepted_at__isnull=True, revoked_at__isnull=True)
    }
    states = {}
    for record in records:
        link, invitation = links.get(record.pk), invitations.get(record.pk)
        if link is not None and link.user.is_portal_account:
            states[record.pk] = "active" if link.user.is_active else "suspended"
        elif invitation is not None:
            states[record.pk] = "expired" if invitation.state == "expired" else "invited"
        else:
            states[record.pk] = "none"
    return states


def _portal_link(record):
    link = link_for(record)
    if link is None or not link.user.is_portal_account:
        raise LifecycleError("no_access", "Für diesen Datensatz besteht kein Portalzugang.", 409)
    return link


@transaction.atomic
def suspend(record, actor):
    link = _portal_link(record)
    user = link.user
    user.is_active = False
    user.save(update_fields=["is_active"])
    revoke_sessions(user)
    security_log.info("portal access suspended", extra={"user": user.pk, "actor": actor.pk})
    return link


@transaction.atomic
def resume(record, actor):
    link = _portal_link(record)
    user = link.user
    user.is_active = True
    user.save(update_fields=["is_active"])
    security_log.info("portal access resumed", extra={"user": user.pk, "actor": actor.pk})
    return link


@transaction.atomic
def end(record, actor):
    """Detach the record from the portal account; an account left without records is deactivated."""
    link = _portal_link(record)
    user, field = link.user, _field(record)
    other = "member" if field == "parent" else "parent"
    revoke_sessions(user)
    if getattr(link, f"{other}_id") is None:
        link.delete()
        user.is_active = False
        user.save(update_fields=["is_active"])
    else:
        setattr(link, field, None)
        link.save(update_fields=[field])
    security_log.info("portal access ended", extra={"user": user.pk, "actor": actor.pk, "target": field})


def eighteenth_birthday(member):
    born = member.birthday
    try:
        return born.replace(year=born.year + 18)
    except ValueError:  # 29 February
        return date(born.year + 18, 3, 1)


def _add_months(day, months):
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    for candidate in (day.day, 30, 29, 28):
        try:
            return date(year, month, candidate)
        except ValueError:
            continue
    raise ValueError(day)


@transaction.atomic
def extend(parent, member, until, reason, actor):
    if not parent.children.filter(pk=member.pk).exists():
        raise LifecycleError("not_a_child", "Das Mitglied ist diesem Elternteil nicht zugeordnet.", 404)
    if member.birthday is None:
        raise LifecycleError("no_birthday", "Ohne Geburtsdatum ist keine Verlängerung nötig.")
    reason = (reason or "").strip()
    if not reason:
        raise LifecycleError("reason_missing", "Bitte eine Begründung angeben.")
    limit = _add_months(eighteenth_birthday(member), MAX_EXTENSION_MONTHS)
    if until > limit:
        raise LifecycleError("too_long", f"Höchstens bis {limit:%d.%m.%Y} (12 Monate nach dem 18. Geburtstag).")
    if until < timezone.localdate():
        raise LifecycleError("in_past", "Das Enddatum liegt in der Vergangenheit.")
    extension = ParentAccessExtension.objects.create(
        parent=parent, member=member, until=until, reason=reason[:500], granted_by=actor
    )
    security_log.info("parent access extended", extra={"extension": extension.pk, "actor": actor.pk})
    return extension


def child_access(parent, today=None):
    """Per child: when the parent access ends (18th birthday or extension), for staff views."""
    today = today or timezone.localdate()
    extensions = {}
    for extension in ParentAccessExtension.objects.filter(parent=parent, until__gte=today):
        extensions[extension.member_id] = max(extensions.get(extension.member_id, extension.until), extension.until)
    rows = []
    for child in parent.children.order_by("name", "pk"):
        birthday_end = eighteenth_birthday(child) if child.birthday else None
        extended_until = extensions.get(child.pk)
        # Access ends at the start of the 18th birthday; an extension includes its last day.
        open_by_age = birthday_end is None or birthday_end > today
        last_day = extended_until or (birthday_end - timedelta(days=1) if birthday_end else None)
        rows.append(
            {
                "member": child.pk,
                "name": child.get_full_name(),
                "access_ends_on": last_day,
                "extended_until": extended_until,
                "ended": not (open_by_age or extended_until is not None),
                "ends_soon": last_day is not None and today <= last_day < today + timedelta(days=WARNING_DAYS),
            }
        )
    return rows


def daily(today=None):
    """Deactivate parent-only portal accounts whose children all aged out; report upcoming ends.

    Visibility per child is already enforced on every request (people.visible_children);
    this job ends accounts that have nothing left to see and revokes their sessions.
    Warnings (30 days ahead) go to the inbox and e-mail once NOTIF-01 exists.
    """
    today = today or timezone.localdate()
    ended, soon = [], []
    links = AccountLink.objects.select_related("user", "parent").filter(
        user__account_kind="portal", user__is_active=True, parent__isnull=False, member__isnull=True
    )
    for link in links:
        if link.parent.children.exists() and not visible_children(link.parent, today).exists():
            user = link.user
            user.is_active = False
            user.save(update_fields=["is_active"])
            revoke_sessions(user)
            security_log.info("parent portal access ended (age)", extra={"user": user.pk})
            ended.append(user.pk)
    warn_from = eighteen_years_before(today + timedelta(days=WARNING_DAYS))
    for child in Member.objects.filter(
        parent__account_link__isnull=False, birthday__gt=eighteen_years_before(today), birthday__lte=warn_from
    ).distinct():
        soon.append(child.pk)
    return {"ended_accounts": ended, "children_ending_soon": soon}
