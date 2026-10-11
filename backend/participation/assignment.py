"""Assignment mode (PART-04.4, concept 4.7): applications, board draft, publication.

The board works on a draft ``{"entries": {member_id: slot_id | "extra"}}`` stored on the configuration. Saving
and publishing are bound to ``SessionParticipation.revision`` (409 with the current board when
stale). Publishing turns drafted applicants into ``assigned`` (with their position) and the other
applicants into ``not_selected`` - or leaves them ``applied`` when applications stay open.
Every change writes a ``RegistrationEvent`` and the ``registration_changed`` signal (E16 mails).
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from training.models import TrainingSession

from . import service, slots
from .eligibility import load_facts
from .models import Mode, Registration
from .service import ParticipationError

EXTRA = slots.EXTRA
APPLICANT_STATES = (Registration.State.APPLIED, Registration.State.ASSIGNED, Registration.State.NOT_SELECTED)
FAIRNESS_DAYS = 90


def _key(value):
    """Draft value as stored: slot id (int) or ``"extra"``."""
    return EXTRA if value == EXTRA else int(value)


def applicants(session):
    return list(
        Registration.objects.filter(session=session, state__in=APPLICANT_STATES)
        .select_related("member")
        .order_by("created_at", "pk")
    )


def current_draft(participation, rows):
    """Stored draft limited to people who still apply; without a draft the published state."""
    ids = {r.member_id for r in rows}
    stored = participation.assignment_draft or {}
    if "entries" in stored:
        return {int(k): _key(v) for k, v in stored["entries"].items() if int(k) in ids}
    return {
        r.member_id: (r.slot_id if r.slot_id is not None else EXTRA)
        for r in rows
        if r.state == Registration.State.ASSIGNED
    }


def published_state(rows):
    return {
        r.member_id: (r.slot_id if r.slot_id is not None else EXTRA)
        for r in rows
        if r.state == Registration.State.ASSIGNED
    }


def check_draft(participation, positions, fits, draft):
    """Reasons why ``draft`` cannot be used (empty list: fine)."""
    by_id = {slot.pk: slot for slot in positions}
    counts = Counter(draft.values())
    problems = []
    for member_id, target in draft.items():
        fit = fits.get(member_id)
        if fit is None:
            problems.append(f"Person {member_id} hat sich nicht beworben.")
            continue
        if target == EXTRA:
            if not fit.general_ok:
                problems.append(f"Person {member_id} erfüllt die allgemeinen Voraussetzungen nicht.")
            continue
        slot = by_id.get(target)
        if slot is None:
            problems.append("Unbekannte Position.")
        elif not fit.suits(slot):
            problems.append(f"Person {member_id} passt nicht zur Position ‚{slot.label}‘.")
    for target, count in counts.items():
        if target == EXTRA:
            limit = participation.extra_places or 0
            if not positions:
                limit = participation.max_participants if participation.max_participants is not None else count
            if count > limit:
                problems.append(f"Ohne Position sind höchstens {limit} Plätze frei.")
        elif target in by_id and count > by_id[target].max_count:
            problems.append(f"‚{by_id[target].label}‘ hat nur {by_id[target].max_count} Plätze.")
    return problems


def _names(rows):
    return {r.member_id: (r.member.name, r.member.lastname) for r in rows}


def board(session, participation):
    """Everything the board shows: positions, applicants with fit and fairness hints, draft, staffing."""
    positions = slots.slots_for(participation)
    rows = applicants(session)
    ids = [r.member_id for r in rows]
    fits = slots.fits(participation, positions, ids, session.date)
    draft = current_draft(participation, rows)
    published = published_state(rows)
    facts = load_facts(ids) if ids else {}
    from qualifications.models import QualificationType

    valid = {}
    for pk, person in facts.items():
        valid[pk] = sorted(
            type_id
            for type_id, entries in person.qualifications.items()
            if any(start <= session.date and (end is None or end >= session.date) for start, end in entries)
        )
    type_names = dict(
        QualificationType.objects.filter(pk__in={t for v in valid.values() for t in v}).values_list("pk", "name")
    )
    since = session.date - timedelta(days=FAIRNESS_DAYS)
    recent = dict(
        Registration.objects.filter(
            member_id__in=ids,
            state=Registration.State.ASSIGNED,
            session__date__gte=since,
            session__date__lt=session.date,
        )
        .exclude(session=session)
        .values_list("member_id")
        .annotate(n=Count("pk"))
        .values_list("member_id", "n")
    )
    held = Counter(v for v in draft.values())
    people = []
    for row in rows:
        fit = fits.get(row.member_id, slots.Fit())
        people.append(
            {
                "member_id": row.member_id,
                "name": row.member.name,
                "lastname": row.member.lastname,
                "state": row.state,
                "version": row.version,
                "applied_at": row.created_at,
                "preferred_slot": row.preferred_slot_id,
                "general_ok": fit.general_ok,
                "general_reasons": [] if fit.general_ok else list(fit.general.reasons),
                "fits": slots.suitable_ids(positions, fit),
                "reasons": {str(slot.pk): fit.reasons_for(slot) for slot in positions if not fit.suits(slot)},
                "notes": sorted({n for slot in positions if fit.suits(slot) for n in fit.notes_for(slot)}),
                "qualifications": [type_names.get(t, f"#{t}") for t in valid.get(row.member_id, [])],
                "recent_assignments": recent.get(row.member_id, 0),
                "draft": draft.get(row.member_id),
                "published": published.get(row.member_id),
                "conflict": row.conflict,
            }
        )
    staffing = slots.staffing(participation, positions, {(None if k == EXTRA else k): v for k, v in held.items()})
    return {
        "session": session.pk,
        "mode": participation.mode,
        "revision": participation.revision,
        "published_at": participation.assignment_published_at,
        "keep_open": participation.assignment_keep_open,
        "dirty": draft != published,
        "slots": [
            {
                "id": slot.pk,
                "label": slot.label,
                "min": slot.min_count,
                "max": slot.max_count,
                "drafted": held.get(slot.pk, 0),
            }
            for slot in positions
        ],
        "extra_places": participation.extra_places if positions else participation.max_participants,
        "extra_drafted": held.get(EXTRA, 0),
        "staffing": staffing,
        "applicants": people,
        "draft": {str(k): v for k, v in draft.items()},
    }


def _locked(session_id):
    session = TrainingSession.objects.select_for_update(of=("self",)).get(pk=session_id)
    participation, persisted = service.participation_for(session)
    if not persisted or participation.mode != Mode.ASSIGNMENT:
        raise ParticipationError("mode_forbidden", "Zuteilen ist nur im Modus „Zuteilung“ möglich.")
    return session, participation


def _stale(session, participation, revision):
    if revision != participation.revision:
        raise ParticipationError(
            "stale",
            "Die Zuteilung wurde inzwischen von jemand anderem geändert.",
            status=409,
            current=board(session, participation),
        )


def _parse(items):
    draft = {}
    for member_id, target in (items or {}).items():
        try:
            draft[int(member_id)] = _key(target)
        except (TypeError, ValueError) as exc:
            raise ParticipationError("invalid", "Ungültiger Zuteilungsentwurf.", status=400) from exc
    return draft


def save_draft(session_id, items, revision, *, now=None):
    """Store the board draft; returns the new board."""
    with transaction.atomic():
        session, participation = _locked(session_id)
        _stale(session, participation, revision)
        draft = _parse(items)
        positions = slots.slots_for(participation)
        rows = applicants(session)
        fits = slots.fits(participation, positions, [r.member_id for r in rows], session.date)
        problems = check_draft(participation, positions, fits, draft)
        if problems:
            raise ParticipationError("invalid_assignment", "Der Entwurf ist nicht gültig.", reasons=problems)
        participation.assignment_draft = {"entries": {str(k): v for k, v in draft.items()}}
        participation.revision += 1
        participation.save(update_fields=["assignment_draft", "revision", "updated_at"])
        return board(session, participation)


def publish(session_id, revision, *, actor, keep_open=False, now=None):
    """Apply the draft: assigned with position, others not selected (or still applied). Returns the board."""
    now = now or timezone.now()
    with transaction.atomic():
        session, participation = _locked(session_id)
        _stale(session, participation, revision)
        if session.status != TrainingSession.Status.PUBLISHED:
            raise ParticipationError("not_open", "Der Dienst ist nicht veröffentlicht.")
        if now >= service.session_start(session):
            raise ParticipationError("deadline_passed", "Der Dienst hat bereits begonnen; Meldungen sind eingefroren.")
        positions = slots.slots_for(participation)
        rows = list(
            Registration.objects.select_for_update()
            .filter(session=session, state__in=APPLICANT_STATES)
            .order_by("created_at", "pk")
        )
        draft = current_draft(participation, rows)
        fits = slots.fits(participation, positions, [r.member_id for r in rows], session.date)
        problems = check_draft(participation, positions, fits, draft)
        if problems:
            raise ParticipationError("invalid_assignment", "Der Entwurf ist nicht gültig.", reasons=problems)
        S = Registration.State
        for row in rows:
            target = draft.get(row.member_id)
            if target is not None:
                state, slot_id = S.ASSIGNED, (None if target == EXTRA else target)
            elif keep_open and row.state != S.NOT_SELECTED:
                state, slot_id = S.APPLIED, None
            elif keep_open:
                continue  # already not selected; stays so
            else:
                state, slot_id = S.NOT_SELECTED, None
            if (row.state, row.slot_id) == (state, slot_id):
                continue
            previous = row.state
            row.state, row.slot_id, row.state_changed_at = state, slot_id, now
            row.version += 1
            row.save(update_fields=["state", "slot", "state_changed_at", "version", "updated_at"])
            service.record_event(row, previous, state, actor, Registration.Source.STAFF, now)
        participation.assignment_draft = {"entries": {str(k): v for k, v in draft.items()}}
        participation.assignment_published_at = now
        participation.assignment_keep_open = keep_open
        participation.revision += 1
        participation.save(
            update_fields=[
                "assignment_draft",
                "assignment_published_at",
                "assignment_keep_open",
                "revision",
                "updated_at",
            ]
        )
        return board(session, participation)
