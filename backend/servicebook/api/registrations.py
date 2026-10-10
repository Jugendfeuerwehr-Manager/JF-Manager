"""Registrations of a planned service inside the servicebook (PART-02.1)."""

from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework import serializers

from members.models import Member
from participation import service as participation_service
from participation.models import Registration
from participation.staff_views import can_read_notes, display_state
from participation.views import MAX_TARGET, target_members
from servicebook.models import Attendance

from ..linked_people import CountedAsOther
from .attendance_board import set_attendance

ATTENDING = ("expected", "registered", "assigned")
OVERVIEW_UPCOMING_DAYS = 14
OVERVIEW_OPEN_DAYS = 60
OVERVIEW_LIMIT = 20


def build_people(service, user=None):
    """``(session payload | None, people)`` for one servicebook entry; ``user`` decides reason-note visibility."""
    attendance = dict(Attendance.objects.filter(service=service).values_list("person_id", "state"))
    session = service.training_session
    members = {}
    in_target = set()
    registrations = {}
    session_body = None
    mode = None
    if session is not None:
        participation, _ = participation_service.participation_for(session)
        mode = participation.mode
        due = participation_service.deadlines(session, participation)
        session_body = {
            "id": session.pk,
            "mode": mode,
            "max_participants": participation.max_participants,
            "deadlines": {
                "registration_closes_at": due.registration_closes_at,
                "cancellation_closes_at": due.cancellation_closes_at,
            },
        }
        target = target_members(session)
        for member in list(target)[:MAX_TARGET] if target is not None else []:
            members[member.pk] = member
            in_target.add(member.pk)
        registrations = {r.member_id: r for r in Registration.objects.filter(session=session)}
    extra = (set(registrations) | set(attendance)) - set(members)
    if extra:
        for member in Member.objects.filter(pk__in=extra).only("pk", "name", "lastname"):
            members[member.pk] = member
    groups = dict(Member.objects.filter(pk__in=members, group__isnull=False).values_list("pk", "group__name"))
    waiting = sorted(
        (r for r in registrations.values() if r.state == Registration.State.WAITLISTED),
        key=lambda r: (r.state_changed_at, r.pk),
    )
    positions = {r.member_id: i for i, r in enumerate(waiting, start=1)}
    notes = session is not None and user is not None and can_read_notes(user, session)
    people = []
    for member in sorted(members.values(), key=lambda m: (m.lastname.lower(), m.name.lower(), m.pk)):
        registration = registrations.get(member.pk)
        row = {
            "member_id": member.pk,
            "name": member.get_full_name(),
            "group": groups.get(member.pk),
            "state": display_state(mode, registration) if session is not None else None,
            "waitlist_position": positions.get(member.pk),
            "reason_category": registration.reason_category if registration else "",
            "reason_note": (registration.reason_note if notes else None) if registration else None,
            "source": registration.source if registration else None,
            "at": registration.state_changed_at if registration else None,
            "late": bool(registration and registration.late),
            "conflict": bool(registration and registration.conflict),
            "in_target": member.pk in in_target if session is not None else True,
            "attendance": attendance.get(member.pk),
        }
        people.append(row)
    return session_body, people


def build_counts(people):
    counts = dict.fromkeys(
        ("expected", "registered", "cancelled", "waitlisted", "applied", "assigned", "no_response"), 0
    )
    counts.update(conflicts=0, recorded=0, guests=0)
    for row in people:
        if row["state"] in counts:
            counts[row["state"]] += 1
        counts["conflicts"] += row["conflict"]
        counts["recorded"] += row["attendance"] is not None
        counts["guests"] += not row["in_target"]
    return counts


def registrations_payload(service, user):
    session_body, people = build_people(service, user)
    return {"session": session_body, "counts": build_counts(people), "people": people}


class ApplyExcusedSerializer(serializers.Serializer):
    dry_run = serializers.BooleanField(required=False, default=False)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, allow_null=True, max_length=2000
    )


def apply_excused(service, *, dry_run, member_ids=None):
    """Take cancellations over as "excused" through the attendance compare-and-set (never automatic)."""
    _session, people = build_people(service)
    wanted = None if member_ids is None else set(member_ids)
    apply, skipped = [], []
    for row in people:
        if wanted is not None and row["member_id"] not in wanted:
            continue
        entry = {"member_id": row["member_id"], "name": row["name"]}
        if row["state"] != "cancelled":
            if wanted is not None:
                skipped.append({**entry, "reason": "not_cancelled"})
        elif row["attendance"] is not None:
            skipped.append({**entry, "reason": "has_attendance"})
        else:
            apply.append(entry)
    if wanted is not None:
        known = {row["member_id"] for row in people}
        for pk in sorted(wanted - known):
            skipped.append({"member_id": pk, "name": "", "reason": "not_cancelled"})
    applied = 0
    if not dry_run:
        done = []
        for entry in apply:
            try:
                ok, _current = set_attendance(service, Attendance, entry["member_id"], "E", None)
            except CountedAsOther:  # recorded as staff for this service (PORTAL-04.4)
                skipped.append({**entry, "reason": "counted_as_staff"})
                continue
            if ok:
                applied += 1
                done.append(entry)
            else:  # somebody recorded this person in the meantime: their value wins
                skipped.append({**entry, "reason": "has_attendance"})
        apply = done
    return {"apply": apply, "skipped": skipped, "applied": applied}


def overview_card(service):
    session_body, people = build_people(service)
    counts = build_counts(people)
    session = service.training_session
    groups = [g.name for g in session.groups.all()] if session is not None else []
    local = timezone.localtime
    return {
        "id": service.pk,
        "date": local(service.start).date(),
        "start": local(service.start),
        "end": local(service.end),
        "topic": service.topic,
        "groups": groups,
        "session_id": session.pk if session is not None else None,
        "mode": session_body["mode"] if session_body else None,
        "counts": {
            "expected": sum(counts[key] for key in ATTENDING),
            "cancelled": counts["cancelled"],
            "recorded": counts["recorded"],
            "total": len(people),
        },
    }


def overview_payload(services):
    now = timezone.localtime()
    today = now.date()
    day = timedelta(days=1)

    def start_of(date):
        return timezone.make_aware(datetime.combine(date, time.min))

    services = services.select_related("training_session").prefetch_related("training_session__groups")
    todays = services.filter(start__gte=start_of(today), start__lt=start_of(today + day)).order_by("start")
    upcoming = services.filter(
        start__gte=start_of(today + day), start__lt=start_of(today + day * (OVERVIEW_UPCOMING_DAYS + 1))
    ).order_by("start")[:OVERVIEW_LIMIT]
    past = services.filter(start__gte=start_of(today - day * OVERVIEW_OPEN_DAYS), start__lt=start_of(today)).order_by(
        "-start"
    )
    open_cards = []
    for service in past:
        card = overview_card(service)
        counts = card["counts"]
        incomplete = counts["recorded"] < counts["expected"] if counts["expected"] else counts["recorded"] == 0
        if incomplete:
            open_cards.append(card)
            if len(open_cards) >= OVERVIEW_LIMIT:
                break
    return {
        "today": [overview_card(s) for s in todays],
        "upcoming": [overview_card(s) for s in upcoming],
        "open": open_cards,
    }
