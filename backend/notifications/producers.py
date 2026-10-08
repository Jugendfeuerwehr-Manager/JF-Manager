"""Turn participation events into inbox entries, e-mails and push (NOTIF-01.5b).

Affected people (E16, E19) are reached through their portal accounts: the own
member account and parent accounts that still see the child (minor or
extended). Responsible staff (D10) are the creator of the planned service and
the leaders of its service-book entry (inbox, e-mail and push); everyone with
the planning right in the department gets the inbox entry only.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.utils import timezone

from participation.signals import eligibility_conflict, registration_changed, session_changed, session_published

from .dispatch import common_context, queue_email, queue_push
from .inbox import notify, staff_with_permission
from .models import InboxItem

User = get_user_model()
PLANNING = "training.can_manage_training"
WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
REASONS = {
    "krankheit": "Krankheit",
    "schule_beruf": "Schule/Beruf",
    "urlaub": "Urlaub",
    "familie": "Familie",
    "sonstiges": "Sonstiges",
}


# ----------------------------------------------------------------------------- formatting
def _date(day):
    return f"{WEEKDAYS[day.weekday()]} {day:%d.%m.%Y}" if day else ""


def _time(session):
    if not session.start_time:
        return ""
    end = f"–{session.end_time:%H:%M}" if session.end_time else ""
    return f"{session.start_time:%H:%M}{end} Uhr"


def _moment(value):
    if not value:
        return ""
    local = timezone.localtime(value)
    return f"{WEEKDAYS[local.weekday()]} {local:%d.%m.}, {local:%H:%M} Uhr"


def _session(session, participation=None):
    return {
        "title": session.title,
        "date": _date(session.date),
        "time": _time(session),
        "place": session.location or "",
        "public_note": participation.public_note if participation else "",
    }


def _frontend(path):
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}"


def _link(user, action, objects, route, expires_at=None):
    """Signed quick-action link (NOTIF-01.4); ``route`` documents the target for readers."""
    from .actions import make_link

    return make_link(user, action, objects, expires_at)


# ----------------------------------------------------------------------------- people
def accounts_for_member(member):
    """[(user, relation)] of active portal accounts acting for ``member``."""
    from portal.models import AccountLink
    from portal.people import visible_children

    result = []
    links = AccountLink.objects.select_related("user", "parent").filter(
        status=AccountLink.Status.CONFIRMED, user__is_active=True, user__account_kind="portal"
    )
    for link in links.filter(member=member):
        result.append((link.user, "self"))
    for link in links.filter(parent__children=member).distinct():
        if visible_children(link.parent).filter(pk=member.pk).exists():
            result.append((link.user, "child"))
    return result


def responsibles(session):
    """(primary, all): primary get e-mail and push, all get the inbox entry (D10)."""
    primary = set()
    if session.created_by_id:
        primary.add(session.created_by_id)
    entry = getattr(session, "servicebook_entry", None)
    if entry is not None:
        primary |= set(entry.operations_manager.values_list("pk", flat=True))
    primary_users = list(User.objects.filter(pk__in=primary, is_active=True, account_kind="staff"))
    everyone = {u.pk for u in primary_users} | set(
        staff_with_permission(PLANNING, session.department_id).values_list("pk", flat=True)
    )
    return primary_users, list(User.objects.filter(pk__in=everyone))


def _person_label(member, relation):
    return member.name if relation == "child" else "dich"


# ----------------------------------------------------------------------------- portal side (E16, E19)
def _participant_mail(
    kind, user, relation, member, session, participation, *, title, extra, withdraw, event_key, bundle_key=""
):
    route = f"/portal/termine/{session.pk}"
    open_url = _link(user, "open", {"r": route}, route)
    withdraw_action, withdraw_label = withdraw
    # Registry keys (NOTIF-01.4): participation actions take session "s" and member "m", unsubscribe the kind "k".
    objects = {"k": kind} if withdraw_action == "unsubscribe" else {"s": session.pk, "m": member.pk}
    withdraw_url = _link(user, withdraw_action, objects, route)
    actions = [{"label": "Termin ansehen", "url": open_url, "style": "secondary"}]
    if withdraw_action != "unsubscribe":
        actions.append({"label": withdraw_label, "url": withdraw_url, "style": "primary"})
    context = {
        **common_context(
            user, open_url=open_url, withdraw_url=withdraw_url, withdraw_label=withdraw_label, actions=actions
        ),
        "person": {"first_name": member.name},
        "session": _session(session, participation),
        **extra,
    }
    group = bundle_key or None
    item = notify(
        kind=kind,
        category=InboxItem.Category.PARTICIPATION,
        title=title,
        recipients=[user],
        link=route,
        group_key=group,
    )
    queue_email(
        kind,
        user,
        context,
        event_key=event_key,
        bundle_key=bundle_key,
        delay=timedelta(minutes=2) if bundle_key else timedelta(0),
    )
    queue_push(user, item, "participation")


def _withdraw_for(state, member, relation):
    name = f"{member.name} abmelden" if relation == "child" else "Abmelden"
    if state == "waitlisted":
        return ("waitlist_leave", "Von der Warteliste abmelden")
    if state == "applied":
        return ("withdraw", "Bewerbung zurückziehen")
    if state in {"registered", "assigned"}:
        return ("cancel", name)
    return None


@receiver(session_published)
def on_session_published(sender, session, **kwargs):
    from participation.eligibility import evaluate_members
    from participation.service import deadlines, has_rule, participation_for
    from participation.views import target_members

    participation, _ = participation_for(session)
    if not participation.portal_visible:
        return
    members = list(target_members(session) or [])
    if has_rule(participation):
        results = evaluate_members(participation.eligibility, [m.pk for m in members], session.date)
        members = [m for m in members if results[m.pk].ok]  # no invitation for people who cannot take part (E19)
    due = deadlines(session, participation)
    series = str(session.series_uuid) if getattr(session, "series_uuid", None) else ""
    extra = {
        "series": {"title": "", "dates": []},
        "deadlines": {
            "registration": _moment(due.registration_closes_at),
            "cancellation": _moment(due.cancellation_closes_at),
        },
        "participation": {"mode": participation.mode},
    }
    for member in members:
        for user, relation in accounts_for_member(member):
            if participation.mode == "opt_out":
                withdraw = ("cancel", f"{member.name} abmelden" if relation == "child" else "Abmelden")
            else:
                withdraw = ("unsubscribe", "Keine Mitteilungen über neue Dienste")
            bundle = f"session_published:{series}:{user.pk}:{member.pk}" if series else ""
            _participant_mail(
                "session_published",
                user,
                relation,
                member,
                session,
                participation,
                title=f"Neuer Termin für {member.name}: {session.title} am {_date(session.date)}",
                extra=extra,
                withdraw=withdraw,
                event_key=f"session_published:{session.pk}:{user.pk}:{member.pk}",
                bundle_key=bundle,
            )


@receiver(session_changed)
def on_session_changed(sender, session, kind, old, new, member_ids, **kwargs):
    from members.models import Member
    from participation.models import Registration
    from participation.service import participation_for

    participation, _ = participation_for(session)
    states = dict(Registration.objects.filter(session=session).values_list("member_id", "state"))

    def describe(values):
        day = values.get("date")
        text = _date(day) if hasattr(day, "weekday") else str(day or "")
        start = values.get("start_time")
        return f"{text}, {start:%H:%M} Uhr" if hasattr(start, "hour") else text

    change = {
        "kind": kind,
        "old": describe(old),
        "new": describe(new) if kind != "changed" else f"Ort: {new.get('place') or '–'}",
    }
    label = "Abgesagt" if kind == "cancelled" else "Geändert"
    stamp = timezone.now().strftime("%Y%m%d%H%M%S")
    for member in Member.objects.filter(pk__in=member_ids):
        for user, relation in accounts_for_member(member):
            withdraw = _withdraw_for(
                states.get(member.pk, "registered" if participation.mode == "opt_out" else ""), member, relation
            )
            if kind == "cancelled" or withdraw is None:
                withdraw = ("unsubscribe", "Keine Mitteilungen über geänderte Dienste")
            _participant_mail(
                "session_changed",
                user,
                relation,
                member,
                session,
                participation,
                title=f"{label}: {session.title} ({_date(session.date)})",
                extra={"change": change},
                withdraw=withdraw,
                event_key=f"session_changed:{session.pk}:{stamp}:{user.pk}:{member.pk}",
            )


# ----------------------------------------------------------------------------- registrations
@receiver(registration_changed)
def on_registration_changed(
    sender, registration_id, session_id, member_id, from_state, to_state, actor_id, via, **kwargs
):
    from participation.models import Registration
    from participation.service import participation_for, waitlist_position

    registration = Registration.objects.select_related("session", "member").filter(pk=registration_id).first()
    if registration is None:
        return
    session, member = registration.session, registration.member
    participation, _ = participation_for(session)
    stamp = registration.state_changed_at.strftime("%Y%m%d%H%M%S%f") if registration.state_changed_at else "0"
    if to_state == "waitlisted" and from_state != "waitlisted":
        for user, relation in accounts_for_member(member):
            _participant_mail(
                "waitlist_placed",
                user,
                relation,
                member,
                session,
                participation,
                title=f"Warteliste: {session.title} ({_date(session.date)})",
                extra={
                    "waitlist": {
                        "position": waitlist_position(registration) or 0,
                        "slot": "",
                        "auto": participation.waitlist_mode == "auto",
                    }
                },
                withdraw=("waitlist_leave", "Von der Warteliste abmelden"),
                event_key=f"waitlist_placed:{registration_id}:{stamp}:{user.pk}",
            )
    elif from_state == "waitlisted" and to_state == "registered" and via == "system":
        from participation.service import deadlines

        due = deadlines(session, participation)
        for user, relation in accounts_for_member(member):
            _participant_mail(
                "waitlist_promoted",
                user,
                relation,
                member,
                session,
                participation,
                title=f"{member.name} ist nachgerückt: {session.title}",
                extra={"deadlines": {"cancellation": _moment(due.cancellation_closes_at)}},
                withdraw=("cancel", f"{member.name} abmelden" if relation == "child" else "Abmelden"),
                event_key=f"waitlist_promoted:{registration_id}:{stamp}:{user.pk}",
            )
    elif to_state == "cancelled" and via != "system":
        _staff_cancellation(registration, session, member, participation, stamp)


def _staff_cancellation(registration, session, member, participation, stamp):
    from participation.models import Registration
    from participation.service import effective_defaults, session_start

    cancelled = Registration.objects.filter(session=session, state="cancelled").count()
    primary, everyone = responsibles(session)
    if not everyone:
        return
    title = f"{cancelled} Abmeldung{'en' if cancelled != 1 else ''} · {session.title}, {_date(session.date)}"
    route = f"/training/sessions/{session.pk}/plan"
    item = notify(
        kind="reg_cancelled",
        category=InboxItem.Category.REGISTRATIONS,
        title=title,
        department=session.department_id,
        obj=session,
        permission=PLANNING,
        link=route,
        recipients=everyone,
        group_key=f"reg_cancelled:session:{session.pk}",
    )
    urgent_hours = effective_defaults(session.department_id).get("urgent_notice_h") or 48
    start = session_start(session)
    if start is None or start - timezone.now() > timedelta(hours=urgent_hours):
        return  # earlier cancellations go into the daily digest (NOTIF-01.5c)
    seated = Registration.objects.filter(session=session).exclude(state="cancelled").count()
    for user in primary:
        open_url = _link(user, "open", {"r": route}, route)
        context = {
            **common_context(
                user, open_url=open_url, actions=[{"label": "Meldungen ansehen", "url": open_url, "style": "primary"}]
            ),
            "session": _session(session, participation),
            "cancellations": [
                {
                    "name": member.get_full_name(),
                    "reason_category": REASONS.get(registration.reason_category, "ohne Angabe"),
                    "at": _moment(registration.state_changed_at),
                }
            ],
            "counts": {"expected": seated, "cancelled": cancelled},
            "staffing": {"missing": []},
        }
        queue_email("reg_cancelled", user, context, event_key=f"reg_cancelled:{registration.pk}:{stamp}:{user.pk}")
        queue_push(user, item, "participation")


@receiver(eligibility_conflict)
def on_eligibility_conflict(sender, session, registration_ids, **kwargs):
    from participation.models import Registration

    registrations = list(Registration.objects.select_related("member").filter(pk__in=registration_ids))
    if not registrations:
        return
    primary, everyone = responsibles(session)
    if not everyone:
        return
    route = f"/training/sessions/{session.pk}/plan"
    item = notify(
        kind="eligibility_conflict",
        category=InboxItem.Category.STAFFING,
        item_type=InboxItem.ItemType.TASK,
        title=f"Voraussetzung nicht mehr erfüllt · {session.title}, {_date(session.date)}",
        department=session.department_id,
        obj=session,
        permission=PLANNING,
        link=route,
        recipients=everyone,
    )
    conflicts = [
        {
            "name": r.member.get_full_name(),
            "reason": "; ".join(r.conflict_reasons or []) or "Voraussetzung nicht erfüllt",
        }
        for r in registrations
    ]
    key = "-".join(str(r.pk) for r in registrations)
    for user in primary:
        open_url = _link(user, "open", {"r": route}, route)
        context = {
            **common_context(
                user, open_url=open_url, actions=[{"label": "Meldungen ansehen", "url": open_url, "style": "primary"}]
            ),
            "session": _session(session),
            "conflicts": conflicts,
        }
        queue_email(
            "eligibility_conflict", user, context, event_key=f"eligibility_conflict:{session.pk}:{key}:{user.pk}"
        )
        queue_push(user, item, "participation")
