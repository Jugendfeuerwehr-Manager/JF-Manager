"""Account and digest notifications (NOTIF-01.5c).

- Parent access ends in 30 days (E6): one notice and mail to the parent accounts
  and the member's own account, one task for staff who may invite or extend.
- Invitation accepted: notice for the inviting person.
- Daily digest of registrations for responsible staff (``reg_digest``).
All runs are idempotent: repeated daily jobs neither duplicate entries nor
re-open read ones.
"""

from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from .dispatch import common_context, queue_email, queue_push
from .inbox import notify, staff_with_permission
from .models import InboxItem

INVITE = "portal.invite_portal_account"


def _frontend_open(user, route):
    from .actions import make_link

    return make_link(user, "open", {"r": route})


def parent_access_warnings(child_ids, today=None):
    """Warn once per child and account that parent access ends (E6, 30 days ahead)."""
    from members.models import Member
    from portal.lifecycle import eighteenth_birthday
    from portal.models import AccountLink, ParentAccessExtension

    today = today or timezone.localdate()
    created = 0
    for child in Member.objects.filter(pk__in=child_ids).exclude(birthday__isnull=True).prefetch_related("departments"):
        if ParentAccessExtension.objects.filter(member=child, until__gte=today).exists():
            continue  # an extension moves the end; staff decided consciously
        ends_on = eighteenth_birthday(child)
        ends_text = f"{ends_on:%d.%m.%Y}"
        links = AccountLink.objects.select_related("user").filter(
            status=AccountLink.Status.CONFIRMED, user__is_active=True, user__account_kind="portal"
        )
        recipients = [(link.user, "parent") for link in links.filter(parent__children=child).distinct()]
        recipients += [(link.user, "member") for link in links.filter(member=child)]
        for user, kind in recipients:
            key = f"parent_access_end:{user.pk}:{child.pk}:{ends_on:%Y%m%d}"
            if InboxItem.objects.filter(group_key=key).exists():
                continue
            title = (
                f"Elternzugang für {child.name} endet am {ends_text}"
                if kind == "parent"
                else f"Ab {ends_text} sehen deine Eltern deine Daten nicht mehr"
            )
            item = notify(
                kind="parent_access_end",
                category=InboxItem.Category.ACCOUNTS,
                title=title,
                recipients=[user],
                link="/portal",
                group_key=key,
            )
            open_url = _frontend_open(user, "/portal")
            context = {
                **common_context(
                    user, open_url=open_url, actions=[{"label": "Portal öffnen", "url": open_url, "style": "primary"}]
                ),
                "person": {"first_name": child.name},
                "access": {"ends_at": ends_text},
            }
            context["recipient"]["kind"] = kind
            queue_email("parent_access_end", user, context, event_key=key)
            queue_push(user, item, "participation")
            created += 1
        department_ids = [d.pk for d in child.departments.all()]
        if not InboxItem.objects.filter(
            kind="parent_access_end", item_type="task", object_type="members.member", object_id=child.pk
        ).exists():
            staff = set()
            for department_id in department_ids:
                staff |= set(staff_with_permission(INVITE, department_id))
            if staff:
                notify(
                    kind="parent_access_end",
                    category=InboxItem.Category.ACCOUNTS,
                    item_type=InboxItem.ItemType.TASK,
                    title=f"Elternzugriff endet am {ends_text}: {child.get_full_name()} – Mitglied einladen oder verlängern",
                    department=department_ids[0] if department_ids else None,
                    obj=child,
                    permission=INVITE,
                    link="/portal-verwaltung?tab=endet",
                    recipients=staff,
                )
                created += 1
    return created


def invitation_accepted(invitation):
    """Notice for the inviting person (4.9.1 "Einladung angenommen")."""
    from portal.invitations import record_department_ids

    if invitation.created_by_id is None:
        return None
    departments = sorted(record_department_ids(invitation.record))
    return notify(
        kind="invitation_accepted",
        category=InboxItem.Category.ACCOUNTS,
        title=f"{invitation.record.get_full_name()} hat die Portaleinladung angenommen",
        department=departments[0] if departments else None,
        obj=invitation,
        permission=INVITE,
        link="/portal-verwaltung",
        recipients=[invitation.created_by],
    )


def registration_digest(now=None):
    """One mail per responsible person with today's registrations (``reg_digest``)."""
    from participation.models import RegistrationEvent

    from .producers import _date, responsibles

    now = now or timezone.now()
    since = now - timedelta(hours=24)
    events = (
        RegistrationEvent.objects.filter(at__gte=since, registration__session__date__gte=timezone.localdate(now))
        .exclude(via="system")
        .select_related("registration__session")
    )
    per_session = defaultdict(lambda: defaultdict(int))
    sessions = {}
    for event in events:
        session = event.registration.session
        sessions[session.pk] = session
        per_session[session.pk][event.to_state] += 1
    labels = {"registered": "angemeldet", "cancelled": "abgemeldet", "waitlisted": "Warteliste", "applied": "beworben"}
    per_user = defaultdict(list)
    users = {}
    for session_id, counts in per_session.items():
        primary, _everyone = responsibles(sessions[session_id])
        for user in primary:
            users[user.pk] = user
            per_user[user.pk].append(
                {
                    "title": sessions[session_id].title,
                    "date": _date(sessions[session_id].date),
                    "counts": {labels.get(state, state): n for state, n in counts.items()},
                }
            )
    day = timezone.localdate(now)
    queued = 0
    for user_id, rows in per_user.items():
        user = users[user_id]
        open_url = _frontend_open(user, "/eingang")
        context = {
            **common_context(
                user, open_url=open_url, actions=[{"label": "Eingang öffnen", "url": open_url, "style": "primary"}]
            ),
            "sessions": rows,
            "counts": {"total": sum(sum(r["counts"].values()) for r in rows)},
        }
        if queue_email("reg_digest", user, context, event_key=f"reg_digest:{user_id}:{day:%Y%m%d}", explicit=True):
            queued += 1
    return queued
