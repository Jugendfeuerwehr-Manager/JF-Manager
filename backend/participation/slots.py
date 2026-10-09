"""Positions, places and minimum staffing (PART-04, concept 4.7).

A service with positions (``Slot``) has as many places as the position maxima plus the optional
``extra_places`` ("Weitere Teilnehmende ohne Position"). A person suits a position when the general
requirements of the service and the rule of the position are met on the day of the service.

Everything here is pure or works on preloaded data; the callers hold the session lock when they
decide about places.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .eligibility import Result, evaluate, load_facts
from .rules import Names

EXTRA = "extra"  # key of the places without position
ANY = None  # preferred slot "beliebig"


@dataclass
class Fit:
    """Eligibility of one person: general rule and every position."""

    general: Result | None = None  # None: no general rule
    slots: dict = field(default_factory=dict)  # slot id -> Result (only slots with a rule)

    @property
    def general_ok(self):
        return self.general is None or self.general.ok

    def suits(self, slot):
        if not self.general_ok:
            return False
        result = self.slots.get(slot.pk)
        return result is None or result.ok

    def reasons_for(self, slot):
        reasons = [] if self.general_ok else list(self.general.reasons)
        result = self.slots.get(slot.pk)
        if result is not None and not result.ok:
            reasons += list(result.reasons)
        return reasons

    def notes_for(self, slot):
        notes = list(self.general.notes) if self.general is not None else []
        result = self.slots.get(slot.pk)
        if result is not None:
            notes += list(result.notes)
        return notes


def slots_for(participation):
    """Positions of a configuration in display order; none for an unsaved configuration."""
    if participation is None or participation.pk is None:
        return []
    return list(participation.slots.all())


def capacity(participation, slots):
    """Derived maximum: sum of the position maxima plus extra places (``None`` = unlimited without positions)."""
    if not slots:
        return participation.max_participants
    return sum(slot.max_count for slot in slots) + (participation.extra_places or 0)


def fits(participation, slots, member_ids, on_date):
    """``{member_id: Fit}`` for many people: facts loaded once, names once per rule."""
    member_ids = list(member_ids)
    rules = [participation.eligibility] if participation.eligibility else []
    rules += [slot.rule for slot in slots if slot.rule]
    if not member_ids or not rules:
        return {pk: Fit() for pk in member_ids}
    facts = load_facts(member_ids)
    general_names = Names.for_rule(participation.eligibility) if participation.eligibility else None
    slot_names = {slot.pk: Names.for_rule(slot.rule) for slot in slots if slot.rule}
    out = {}
    for pk in member_ids:
        person = facts.get(pk)
        if person is None:
            continue
        fit = Fit()
        if participation.eligibility:
            fit.general = evaluate(participation.eligibility, person, on_date, general_names)
        for slot in slots:
            if slot.rule:
                fit.slots[slot.pk] = evaluate(slot.rule, person, on_date, slot_names[slot.pk])
        out[pk] = fit
    return out


def held_by_slot(registrations):
    """Counter ``{slot_id or None: seated}`` of the given seated registrations."""
    return Counter(r.slot_id for r in registrations)


@dataclass(frozen=True)
class Decision:
    slot_id: int | None = None  # slot to take (None with ``extra`` for a place without position)
    extra: bool = False
    waitlist: bool = False


def scarcity(slots, candidates):
    """``{slot_id: number of target people suiting the slot}`` (``candidates``: ``{member_id: Fit}``)."""
    return {slot.pk: sum(1 for fit in candidates.values() if fit.suits(slot)) for slot in slots}


def order_for_any(slots, held, scarce):
    """Server order for "beliebig" (concept 4.7): below minimum first, then the scarcest, then position."""
    return sorted(
        slots,
        key=lambda slot: (
            0 if held.get(slot.pk, 0) < slot.min_count else 1,
            scarce.get(slot.pk, 0) if scarce is not None else 0,
            slot.position,
            slot.pk,
        ),
    )


def decide(participation, slots, fit, preferred_id, held, *, scarce=None):
    """Where a person who asks for a place goes: a position, an extra place or the waiting list.

    ``preferred_id`` is a slot id or ``None`` ("beliebig"); ``held`` the seats per slot of the others.
    ``scarce`` (``{slot_id: count}``) breaks ties for "beliebig"; ``None`` skips the scarcity step.
    The caller has checked that the person suits ``preferred_id`` (or at least one position).
    """

    def free(slot):
        return held.get(slot.pk, 0) < slot.max_count

    if preferred_id is not ANY:
        slot = next(s for s in slots if s.pk == preferred_id)
        return Decision(slot_id=slot.pk) if free(slot) else Decision(waitlist=True)
    suitable = [s for s in slots if fit.suits(s) and free(s)]
    if suitable:
        return Decision(slot_id=order_for_any(suitable, held, scarce)[0].pk)
    if fit.general_ok and held.get(None, 0) < (participation.extra_places or 0):
        return Decision(extra=True)
    return Decision(waitlist=True)


def needs_scarcity(slots, fit, held):
    """Whether the scarcity step can change the result of ``decide`` for "beliebig"."""
    suitable = [s for s in slots if fit.suits(s) and held.get(s.pk, 0) < s.max_count]
    if len(suitable) < 2:
        return False
    below = [s for s in suitable if held.get(s.pk, 0) < s.min_count]
    return len(below) != 1


def suitable_ids(slots, fit):
    return [slot.pk for slot in slots if fit.suits(slot)]


def staffing(participation, slots, held, *, seated=None):
    """Minimum staffing (concept 4.7).

    Returns ``None`` when nothing is required, else ``{"met", "required", "fulfilled", "missing",
    "text", "slots"}``. ``held`` counts seats per slot id (``None`` = without position); ``seated`` is
    the total for services without positions.
    """
    if slots:
        rows = []
        for slot in slots:
            taken = held.get(slot.pk, 0)
            rows.append(
                {
                    "id": slot.pk,
                    "label": slot.label,
                    "min": slot.min_count,
                    "max": slot.max_count,
                    "seated": taken,
                    "free": max(slot.max_count - taken, 0),
                    "missing": max(slot.min_count - taken, 0),
                }
            )
        required = [row for row in rows if row["min"] > 0]
        missing = [{"label": row["label"], "count": row["missing"]} for row in required if row["missing"]]
        fulfilled = len(required) - len(missing)
        if not required:
            return {"met": True, "required": 0, "fulfilled": 0, "missing": [], "text": "", "slots": rows}
        text = f"Mindestbesetzung: {fulfilled} von {len(required)} erfüllt"
        if missing:
            text += " – es fehlt " + ", ".join(f"{m['count']}× {m['label']}" for m in missing)
        return {
            "met": not missing,
            "required": len(required),
            "fulfilled": fulfilled,
            "missing": missing,
            "text": text,
            "slots": rows,
        }
    low = participation.min_participants
    if not low:
        return None
    seated = seated if seated is not None else sum(held.values())
    lacking = max(low - seated, 0)
    text = f"Mindestzahl: {min(seated, low)} von {low} erreicht"
    if lacking:
        text += f" – es fehlen {lacking}"
    return {
        "met": not lacking,
        "required": 1,
        "fulfilled": 0 if lacking else 1,
        "missing": [{"label": "Teilnehmende", "count": lacking}] if lacking else [],
        "text": text,
        "slots": [],
    }
