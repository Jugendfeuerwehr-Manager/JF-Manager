"""Rules for registering, cancelling and applying (PART-01.2, concept 4.5).

Everything that changes a ``Registration`` goes through ``set_registration``: one transaction
that locks the ``TrainingSession`` row (capacity decisions are serialised per session on
PostgreSQL; SQLite ignores row locks but serialises writers anyway), applies the state machine,
the deadlines and the eligibility rule, and writes a ``RegistrationEvent``.

Deadline semantics: an action is allowed *until and including* the deadline instant. The three
deadlines are derived from ``ParticipationDefaults`` (department, then organisation, then the hard
defaults) unless set on the session, and are capped at the session start. All arithmetic runs on
the UTC timeline so an offset of 48 hours really is 48 hours across a daylight-saving change.
From the start of the session every change is frozen, also for staff (D8).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from members.models import Member
from training.models import TrainingSession

from . import slots, states
from .eligibility import NEUTRAL_AUDIENCE_NOTICE, Result, evaluate_members
from .models import Mode, ParticipationDefaults, Registration, RegistrationEvent, SessionParticipation, WaitlistMode

MAX_ABSENCE_DAYS = 400
HARD_DEFAULTS = {
    "mode": Mode.OPT_OUT,
    "registration_offset_h": 48,
    "cancellation_offset_h": 2,
    "waitlist_mode": WaitlistMode.AUTO,
    "urgent_notice_h": 24,
}
SEATED = (Registration.State.REGISTERED, Registration.State.ASSIGNED)
REASON_NOTE_MAX = 200

MESSAGES = {
    states.MODE_FORBIDDEN: "Diese Aktion ist in diesem Teilnahmemodus nicht möglich.",
    states.INVALID_TRANSITION: "Diese Änderung ist im aktuellen Status nicht möglich.",
}


class ParticipationError(Exception):
    """A refused change. ``code`` is part of the API contract (422 unless ``status`` says otherwise)."""

    def __init__(self, code, message="", *, reasons=None, status=422, current=None):
        super().__init__(message or code)
        self.code, self.message, self.status = code, message or code, status
        self.reasons = list(reasons or [])
        self.current = current

    def payload(self):
        body = {"code": self.code, "detail": self.message, "reasons": self.reasons}
        if self.current is not None:
            body["current"] = self.current
        return body


# ---------------------------------------------------------------- configuration and time


def effective_defaults(department_id):
    """Defaults of the department, else of the organisation, else the hard defaults."""
    rows = {
        row.department_id: row
        for row in ParticipationDefaults.objects.filter(Q(department_id=department_id) | Q(department__isnull=True))
    }
    row = rows.get(department_id) if department_id else None
    row = row or rows.get(None)
    if row is None:
        return dict(HARD_DEFAULTS)
    return {key: getattr(row, key) for key in HARD_DEFAULTS}


def participation_for(session):
    """``(SessionParticipation, persisted)``; an unsaved instance carries the defaults when no row exists."""
    row = SessionParticipation.objects.filter(session=session).first()
    if row is not None:
        return row, True
    defaults = effective_defaults(session.department_id)
    return SessionParticipation(
        session=session, mode=defaults["mode"], waitlist_mode=defaults["waitlist_mode"], revision=0
    ), False


def session_start(session):
    return timezone.make_aware(datetime.combine(session.date, session.start_time))


def offset_before(start, hours):
    """``start`` minus ``hours`` real hours, expressed in the local zone of ``start``."""
    return (start.astimezone(UTC) - timedelta(hours=hours)).astimezone(start.tzinfo)


@dataclass(frozen=True)
class Deadlines:
    start: datetime
    opens_at: datetime | None
    registration_closes_at: datetime
    cancellation_closes_at: datetime


def deadlines(session, participation, defaults=None):
    start = session_start(session)
    defaults = defaults or effective_defaults(session.department_id)

    def closing(explicit, hours):
        value = explicit if explicit is not None else offset_before(start, hours)
        return min(value, start)

    return Deadlines(
        start=start,
        opens_at=participation.registration_opens_at,
        registration_closes_at=closing(participation.registration_closes_at, defaults["registration_offset_h"]),
        cancellation_closes_at=closing(participation.cancellation_closes_at, defaults["cancellation_offset_h"]),
    )


def is_target_member(session, member_id):
    """Q1: members of the session's groups; without groups all members of its department."""
    members = Member.objects.filter(pk=member_id)
    group_ids = list(session.groups.values_list("pk", flat=True))
    if group_ids:
        return members.filter(group_id__in=group_ids).exists()
    if session.department_id:
        return members.filter(departments=session.department_id).exists()
    return False


def target_sessions_for(member):
    """Sessions whose target group contains ``member`` (queryset, not yet filtered by time or status)."""
    through = TrainingSession.groups.through
    group_link = through.objects.filter(trainingsession_id=OuterRef("pk"))
    condition = Q()
    if member.group_id:
        condition |= Q(Exists(group_link.filter(group_id=member.group_id)))
    department_ids = list(member.departments.values_list("pk", flat=True))
    if department_ids:
        condition |= ~Q(Exists(group_link)) & Q(department_id__in=department_ids)
    if not condition:
        return TrainingSession.objects.none()
    return TrainingSession.objects.filter(condition)


# ---------------------------------------------------------------- eligibility


def has_rule(participation):
    return bool(participation.eligibility)


def eligibility_for(session, participation, member_ids):
    """``{member_id: Result}``; no rule means everybody is eligible (empty dict)."""
    if not has_rule(participation) or not member_ids:
        return {}
    return evaluate_members(participation.eligibility, list(member_ids), session.date)


def neutral_reasons(reasons):
    """Reasons for portal accounts: a gender condition is never spelled out (concept 4.6)."""
    out = []
    for reason in reasons:
        text = NEUTRAL_AUDIENCE_NOTICE if "Geschlecht" in reason else reason
        if text not in out:
            out.append(text)
    return out


# ---------------------------------------------------------------- planning


@dataclass
class Plan:
    state: str | None = None
    noop: bool = False
    late: bool = False
    waitlisted: bool = False
    reasons: list = field(default_factory=list)


def _deadline_kind(mode, target):
    """Cancelling (and, in opt-out, taking a cancellation back) is bound to the cancellation deadline."""
    if target in (states.CANCELLED, states.WITHDRAWN) or (mode == states.OPT_OUT and target == states.REGISTERED):
        return "cancel"
    return "register"


def _local(value):
    return timezone.localtime(value).strftime("%d.%m.%Y %H:%M")


def seated_count(session, exclude_member_id=None):
    queryset = Registration.objects.filter(session=session, state__in=SEATED)
    if exclude_member_id is not None:
        queryset = queryset.exclude(member_id=exclude_member_id)
    return queryset.count()


def plan_change(
    session,
    participation,
    registration,
    target,
    *,
    staff,
    now,
    seated,
    eligibility=None,
    accept_waitlist=True,
    defaults=None,
    full=None,
):
    """Decide what ``target`` does for one person, or raise ``ParticipationError``. Writes nothing.

    ``seated`` is the number of other people holding a place (registered or assigned);
    ``eligibility`` is the ``Result`` of the person (``None``: no rule applies or not checked yet).
    ``full`` overrides the capacity decision (positions decide per position, PART-04.2).
    """
    if session.status != TrainingSession.Status.PUBLISHED:
        text = "Der Dienst wurde abgesagt." if session.status == "cancelled" else "Der Dienst ist nicht meldefähig."
        raise ParticipationError("not_open", text)
    if not staff and not participation.portal_visible:
        raise ParticipationError("not_open", "Der Dienst ist im Portal nicht sichtbar.")
    due = deadlines(session, participation, defaults)
    if now >= due.start:
        raise ParticipationError("deadline_passed", "Der Dienst hat bereits begonnen; Meldungen sind eingefroren.")

    mode = participation.mode
    current = registration.state if registration else None
    if full is None:
        full = (
            mode == Mode.OPT_IN
            and participation.max_participants is not None
            and seated >= participation.max_participants
        )
    outcome = states.next_state(mode, current, target, full=full)
    if staff and current == states.WAITLISTED and target == states.REGISTERED and not full:
        # Staff take a waiting person onto a free place (manual waiting list, E5); people
        # asking again from the portal keep their waiting place.
        outcome = states.Outcome(state=states.REGISTERED)
    if not outcome.ok:
        raise ParticipationError(outcome.code, MESSAGES[outcome.code])
    if outcome.noop:
        return Plan(state=outcome.state, noop=True)

    kind = _deadline_kind(mode, target)
    late = False
    if kind == "register" and not staff and due.opens_at is not None and now < due.opens_at:
        raise ParticipationError("not_open", f"Die Anmeldung beginnt am {_local(due.opens_at)}.")
    closes = due.registration_closes_at if kind == "register" else due.cancellation_closes_at
    if now > closes:
        if not staff:
            text = (
                f"Anmeldeschluss war am {_local(closes)}."
                if kind == "register"
                else "Abmeldung nur noch direkt bei der Dienstleitung."
            )
            raise ParticipationError("deadline_passed", text)
        late = True  # D8: staff may act until the start; flagged "nach Frist durch Betreuende"

    if target in (states.REGISTERED, states.APPLIED) and eligibility is not None and not eligibility.ok:
        raise ParticipationError("not_eligible", "Die Voraussetzungen sind nicht erfüllt.", reasons=eligibility.reasons)
    if outcome.state == states.WAITLISTED and not accept_waitlist:
        raise ParticipationError("full", "Alle Plätze sind vergeben.")
    return Plan(state=outcome.state, late=late, waitlisted=outcome.state == states.WAITLISTED)


# ---------------------------------------------------------------- writing


def _validate_reason(category, note):
    if category and category not in Registration.Reason.values:
        raise ParticipationError("invalid", "Unbekannte Grundkategorie.", status=400)
    if len(note or "") > REASON_NOTE_MAX:
        raise ParticipationError("invalid", f"Der Kurztext darf höchstens {REASON_NOTE_MAX} Zeichen haben.", status=400)


def snapshot(registration):
    if registration is None:
        return {"state": None, "version": 0}
    return {"state": registration.state, "version": registration.version}


def _record(registration, from_state, to_state, actor, via, now):
    RegistrationEvent.objects.create(
        registration=registration, actor=actor, from_state=from_state or "", to_state=to_state, at=now, via=via
    )
    from .signals import registration_changed

    payload = {
        "registration_id": registration.pk,
        "session_id": registration.session_id,
        "member_id": registration.member_id,
        "from_state": from_state or "",
        "to_state": to_state,
        "actor_id": getattr(actor, "pk", None),
        "via": via,
    }
    transaction.on_commit(lambda: registration_changed.send(sender=Registration, **payload))


def _slot_choice(session, participation, positions, member_id, target, slot_id):
    """Position handling for a request with positions (PART-04.2).

    Returns ``(eligibility, full, decision)``: the ``Result`` to check, the capacity decision for
    ``plan_change`` and the ``slots.Decision`` (``None`` unless a place is asked for in opt-in).
    """
    by_id = {slot.pk: slot for slot in positions}
    if slot_id is not None and slot_id not in by_id:
        raise ParticipationError("invalid", "Unbekannte Position.", status=400)
    fit = slots.fits(participation, positions, [member_id], session.date).get(member_id, slots.Fit())
    if slot_id is not None:
        chosen = by_id[slot_id]
        reasons = fit.reasons_for(chosen)
        if fit.general_ok:
            reasons = [f"Position ‚{chosen.label}‘: {reason}" for reason in reasons]
        result = Result(not reasons, reasons)
    elif fit.general_ok and (slots.suitable_ids(positions, fit) or participation.extra_places):
        result = Result(True)
    elif not fit.general_ok:
        result = fit.general
    else:
        result = Result(False, [f"Position ‚{slot.label}‘: {'; '.join(fit.reasons_for(slot))}" for slot in positions])
    if target != states.REGISTERED or participation.mode != Mode.OPT_IN or not result.ok:
        return result, None, None
    seated_rows = Registration.objects.filter(session=session, state__in=SEATED).exclude(member_id=member_id)
    held = slots.held_by_slot(seated_rows.only("slot_id"))
    scarce = None
    if slot_id is None and slots.needs_scarcity(positions, fit, held):
        scarce = _scarcity(session, participation, positions)
    decision = slots.decide(participation, positions, fit, slot_id, held, scarce=scarce)
    return result, decision.waitlist, decision


def _scarcity(session, participation, positions):
    """Number of target people suiting each position (one evaluation of the target group)."""
    from .views import target_members

    members = target_members(session)
    ids = [m.pk for m in members] if members is not None else []
    return slots.scarcity(positions, slots.fits(participation, positions, ids, session.date))


def set_registration(
    session_id,
    member_id,
    target,
    *,
    actor,
    source,
    reason_category="",
    reason_note="",
    version=None,
    accept_waitlist=True,
    now=None,
    via=None,
    slot=None,
):
    """Apply ``target`` for one person atomically. Returns ``(registration or None, changed, plan)``.

    ``slot`` is the position asked for (opt-in) or wished (assignment, Q3); ``None`` = any suitable one.
    """
    now = now or timezone.now()
    reason_category, reason_note = reason_category or "", (reason_note or "").strip()
    _validate_reason(reason_category, reason_note)
    staff = source == Registration.Source.STAFF
    with transaction.atomic():
        session = TrainingSession.objects.select_for_update().get(pk=session_id)
        participation, persisted = participation_for(session)
        registration = Registration.objects.select_for_update().filter(session=session, member_id=member_id).first()
        if version is not None and version != (registration.version if registration else 0):
            raise ParticipationError(
                "stale", "Die Meldung wurde inzwischen geändert.", status=409, current=snapshot(registration)
            )
        if not is_target_member(session, member_id):
            raise ParticipationError("not_target", "Die Person gehört nicht zur Zielgruppe des Dienstes.")
        positions = slots.slots_for(participation)
        if slot is None and registration is not None and registration.state == Registration.State.WAITLISTED:
            slot = registration.preferred_slot_id  # moving up keeps the position asked for
        decision = full = None
        if positions and participation.mode != Mode.OPT_OUT and target in (states.REGISTERED, states.APPLIED):
            eligibility, full, decision = _slot_choice(session, participation, positions, member_id, target, slot)
        else:
            eligibility = eligibility_for(session, participation, [member_id]).get(member_id)
        plan = plan_change(
            session,
            participation,
            registration,
            target,
            staff=staff,
            now=now,
            seated=seated_count(session, member_id),
            eligibility=eligibility,
            accept_waitlist=accept_waitlist,
            full=full,
        )
        cancelling = plan.state == states.CANCELLED
        if plan.noop:
            if (
                registration
                and cancelling
                and (reason_category, reason_note)
                != (
                    registration.reason_category,
                    registration.reason_note,
                )
            ):
                registration.reason_category, registration.reason_note = reason_category, reason_note
                registration.version += 1
                registration.save(update_fields=["reason_category", "reason_note", "version", "updated_at"])
                return registration, True, plan
            return registration, False, plan

        if not persisted:
            participation.revision = 1
            participation.save()
        previous = registration.state if registration else None
        previous_slot = registration.slot_id if registration else None
        seated_slot = None
        if plan.state in SEATED:
            seated_slot = decision.slot_id if decision is not None else previous_slot
        if target in (states.REGISTERED, states.APPLIED):
            preferred = slot if positions else None
        else:
            preferred = registration.preferred_slot_id if registration else None
        values = {
            "state": plan.state,
            "slot_id": seated_slot,
            "preferred_slot_id": preferred,
            "reason_category": reason_category if cancelling else "",
            "reason_note": reason_note if cancelling else "",
            "late": plan.late,
            "conflict": False,
            "conflict_reasons": [],
            "state_changed_at": now,
        }
        if registration is None:
            registration = Registration.objects.create(
                session=session, member_id=member_id, source=source, created_by=actor, **values
            )
        else:
            for key, value in values.items():
                setattr(registration, key, value)
            registration.source, registration.created_by = source, actor
            registration.version += 1
            registration.save()
        _record(registration, previous, plan.state, actor, via or source, now)
        freed = previous in SEATED and plan.state not in SEATED
        if freed and not promote_waitlist(session, participation, now=now):
            announce_free_place(session, participation, previous_slot)
        return registration, True, plan


def announce_free_place(session, participation, slot_id):
    """Manual waiting list or assignment mode: tell the responsible staff a place is free (E5)."""
    if participation.mode == Mode.OPT_OUT:
        return
    if participation.mode == Mode.OPT_IN and participation.waitlist_mode == WaitlistMode.AUTO:
        return
    waiting_state = (
        Registration.State.APPLIED if participation.mode == Mode.ASSIGNMENT else Registration.State.WAITLISTED
    )
    waiting = Registration.objects.filter(session=session, state=waiting_state).count()
    if not waiting:
        return
    label = ""
    if slot_id is not None:
        label = next((slot.label for slot in slots.slots_for(participation) if slot.pk == slot_id), "")
    from .signals import place_freed

    session_id = session.pk
    transaction.on_commit(
        lambda: place_freed.send(sender=Registration, session_id=session_id, slot_label=label, waiting=waiting)
    )


def _promote(registration, slot_id, now):
    registration.state, registration.state_changed_at = Registration.State.REGISTERED, now
    registration.slot_id = slot_id
    registration.version += 1
    registration.save(update_fields=["state", "slot", "state_changed_at", "version", "updated_at"])
    _record(registration, Registration.State.WAITLISTED, Registration.State.REGISTERED, None, "system", now)


def promote_waitlist(session, participation, *, now=None):
    """Fill free places from the waitlist, earliest first, skipping people who no longer qualify.

    Only for opt-in services with ``waitlist_mode=auto`` (E5); the caller holds the session lock.
    With positions the first waiting person who suits a free position moves up: a person waiting
    for a specific position only into that one, "beliebig" into any suitable position or a place
    without position. Returns the promoted registrations.
    """
    now = now or timezone.now()
    if participation.mode != Mode.OPT_IN or participation.waitlist_mode != WaitlistMode.AUTO:
        return []
    if participation.max_participants is None or now >= session_start(session):
        return []
    positions = slots.slots_for(participation)
    if positions:
        return _promote_with_positions(session, participation, positions, now)
    free = participation.max_participants - seated_count(session)
    if free <= 0:
        return []
    waiting = list(
        Registration.objects.select_for_update()
        .filter(session=session, state=Registration.State.WAITLISTED)
        .order_by("state_changed_at", "pk")
    )
    results = eligibility_for(session, participation, [r.member_id for r in waiting])
    promoted = []
    for registration in waiting:
        if free <= 0:
            break
        result = results.get(registration.member_id)
        if result is not None and not result.ok:
            continue
        _promote(registration, None, now)
        promoted.append(registration)
        free -= 1
    return promoted


def _promote_with_positions(session, participation, positions, now):
    held = slots.held_by_slot(Registration.objects.filter(session=session, state__in=SEATED).only("slot_id"))
    if sum(held.values()) >= slots.capacity(participation, positions):
        return []
    waiting = list(
        Registration.objects.select_for_update()
        .filter(session=session, state=Registration.State.WAITLISTED)
        .order_by("state_changed_at", "pk")
    )
    fits = slots.fits(participation, positions, [r.member_id for r in waiting], session.date)
    by_id = {slot.pk: slot for slot in positions}
    promoted = []
    for registration in waiting:
        fit = fits.get(registration.member_id, slots.Fit())
        slot = by_id.get(registration.preferred_slot_id)
        if slot is not None:
            if not fit.suits(slot) or held.get(slot.pk, 0) >= slot.max_count:
                continue
            decision = slots.Decision(slot_id=slot.pk)
        else:
            decision = slots.decide(participation, positions, fit, None, held)
            if decision.waitlist:
                continue
        _promote(registration, decision.slot_id, now)
        held[decision.slot_id] = held.get(decision.slot_id, 0) + 1
        promoted.append(registration)
    return promoted


def waitlist_position(registration):
    if registration is None or registration.state != Registration.State.WAITLISTED:
        return None
    earlier = Registration.objects.filter(
        session_id=registration.session_id, state=Registration.State.WAITLISTED
    ).filter(
        Q(state_changed_at__lt=registration.state_changed_at)
        | Q(state_changed_at=registration.state_changed_at, pk__lt=registration.pk)
    )
    if registration.preferred_slot_id is not None:
        # Waiting for one position competes with those waiting for it and with "beliebig".
        earlier = earlier.filter(Q(preferred_slot_id=registration.preferred_slot_id) | Q(preferred_slot__isnull=True))
    return earlier.count() + 1


# ---------------------------------------------------------------- period cancellation (D7)


def _absence_range(date_from, date_to):
    if date_from > date_to:
        raise ParticipationError("invalid", "Das Ende darf nicht vor dem Beginn liegen.", status=400)
    if (date_to - date_from).days > MAX_ABSENCE_DAYS:
        raise ParticipationError("invalid", "Der Zeitraum ist zu lang.", status=400)


def preview_absence(member, date_from, date_to, *, source, now=None):
    """Sessions in ``[date_from, date_to]`` the person would be cancelled from, and those skipped (with reason).

    Considers published, not yet started sessions of the person's target groups; cancelled
    sessions and sessions hidden from the portal are not listed.
    """
    _absence_range(date_from, date_to)
    now = now or timezone.now()
    staff = source == Registration.Source.STAFF
    sessions = list(
        target_sessions_for(member)
        .filter(status=TrainingSession.Status.PUBLISHED, date__gte=date_from, date__lte=date_to)
        .order_by("date", "start_time", "pk")
        .distinct()
    )
    rows = {p.session_id: p for p in SessionParticipation.objects.filter(session__in=[s.pk for s in sessions])}
    registrations = {
        r.session_id: r for r in Registration.objects.filter(member=member, session__in=[s.pk for s in sessions])
    }
    items, cache = [], {}
    for session in sessions:
        participation = rows.get(session.pk)
        if participation is None:
            participation, _ = participation_for(session)
        if not staff and not participation.portal_visible:
            continue
        registration = registrations.get(session.pk)
        item = {
            "session": session,
            "state": registration.state if registration else None,
            "action": "cancel",
            "skip": None,
        }
        try:
            plan = plan_change(
                session,
                participation,
                registration,
                states.CANCELLED,
                staff=staff,
                now=now,
                seated=0,
                defaults=cache.setdefault(session.department_id, effective_defaults(session.department_id)),
            )
            if plan.noop:
                item.update(action="skip", skip={"code": "already_cancelled", "detail": "Bereits abgemeldet."})
        except ParticipationError as error:
            item.update(action="skip", skip={"code": error.code, "detail": error.message})
        items.append(item)
    return items


def execute_absence(member, date_from, date_to, *, actor, source, reason_category="", reason_note="", now=None):
    """Cancel the person from every session ``preview_absence`` lists as cancellable (re-checked per session)."""
    now = now or timezone.now()
    _validate_reason(reason_category or "", (reason_note or "").strip())
    cancelled, skipped = [], []
    for item in preview_absence(member, date_from, date_to, source=source, now=now):
        session = item["session"]
        if item["action"] != "cancel":
            skipped.append((session, item["skip"]))
            continue
        try:
            set_registration(
                session.pk,
                member.pk,
                states.CANCELLED,
                actor=actor,
                source=source,
                reason_category=reason_category,
                reason_note=reason_note,
                now=now,
            )
            cancelled.append(session)
        except ParticipationError as error:
            skipped.append((session, {"code": error.code, "detail": error.message}))
    return cancelled, skipped
