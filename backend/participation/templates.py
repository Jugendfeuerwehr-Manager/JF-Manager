"""Staffing templates (PART-04.5, concept 4.7): snapshot, validate, clean and apply.

A body is a plain copy of the staffing part of a configuration::

    {"mode", "eligibility", "max_participants", "min_participants", "extra_places",
     "waitlist_mode", "slots": [{"label", "min", "max", "rule"}]}

Applying copies it into a service (independent copy as in TRAIN-03). Rules reference
qualification and other ids; ids that no longer exist are dropped with a warning.
"""

from __future__ import annotations

import copy

from django.db import transaction

from . import changes, slots
from .models import Mode, Registration, Slot, WaitlistMode
from .rules import KIND_LABELS, _collect_ids, _model_for, validate_rule
from .service import SEATED, ParticipationError, participation_for

BODY_KEYS = ("mode", "eligibility", "max_participants", "min_participants", "extra_places", "waitlist_mode", "slots")
MAX_SLOTS = 30


def snapshot(participation):
    """Body of a (possibly unsaved) configuration."""
    return {
        "mode": participation.mode,
        "eligibility": copy.deepcopy(participation.eligibility or {}),
        "max_participants": None if slots.slots_for(participation) else participation.max_participants,
        "min_participants": participation.min_participants,
        "extra_places": participation.extra_places,
        "waitlist_mode": participation.waitlist_mode,
        "slots": [
            {"label": s.label, "min": s.min_count, "max": s.max_count, "rule": copy.deepcopy(s.rule or {})}
            for s in slots.slots_for(participation)
        ],
    }


def _number(value, low, path, errors, *, allow_none=True):
    if value is None and allow_none:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value < low or value > 10000:
        errors[path] = "Ungültige Zahl."


def validate_body(body):
    """``{path: message}`` for a body (structure only; ids are cleaned when applying)."""
    errors = {}
    if not isinstance(body, dict):
        return {"body": "Die Vorlage muss ein Objekt sein."}
    for key in body:
        if key not in BODY_KEYS:
            errors[key] = "Unbekanntes Feld"
    if body.get("mode", Mode.OPT_IN) not in Mode.values:
        errors["mode"] = "Unbekannter Teilnahmemodus."
    if body.get("waitlist_mode", WaitlistMode.AUTO) not in WaitlistMode.values:
        errors["waitlist_mode"] = "Unbekannte Wartelisten-Einstellung."
    for key, low in (("max_participants", 1), ("min_participants", 0), ("extra_places", 0)):
        _number(body.get(key), low, key, errors)
    if body.get("eligibility"):
        for path, message in validate_rule(body["eligibility"]).items():
            if "nicht gefunden" not in message:
                errors[f"eligibility.{path}"] = message
    items = body.get("slots", [])
    if not isinstance(items, list) or len(items) > MAX_SLOTS:
        errors["slots"] = f"Höchstens {MAX_SLOTS} Positionen."
        return errors
    if items and body.get("mode") == Mode.OPT_OUT:
        errors["slots"] = "Im Modus „Abmeldung“ gibt es keine Positionen."
    seen = set()
    for i, item in enumerate(items):
        path = f"slots[{i}]"
        if not isinstance(item, dict):
            errors[path] = "Position muss ein Objekt sein."
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label.strip() or len(label) > 80:
            errors[f"{path}.label"] = "Bezeichnung fehlt oder ist zu lang."
        elif label.casefold() in seen:
            errors[f"{path}.label"] = "Doppelte Position."
        else:
            seen.add(label.casefold())
        _number(item.get("min"), 0, f"{path}.min", errors, allow_none=False)
        _number(item.get("max"), 1, f"{path}.max", errors, allow_none=False)
        if f"{path}.min" not in errors and f"{path}.max" not in errors and item["min"] > item["max"]:
            errors[f"{path}.min"] = "Mindestens darf nicht größer als die Zahl der Plätze sein."
        if item.get("rule"):
            for rpath, message in validate_rule(item["rule"]).items():
                if "nicht gefunden" not in message:
                    errors[f"{path}.rule.{rpath}"] = message
    return errors


def _clean_rule(rule, where, warnings):
    """Drop ids that no longer exist (deleted qualification types etc.) and empty conditions."""
    if not rule or not rule.get("rules"):
        return rule or {}
    wanted = _collect_ids(rule)
    existing = {
        kind: set(_model_for(kind).objects.filter(pk__in=ids).values_list("pk", flat=True))
        for kind, ids in wanted.items()
    }
    missing = {kind: ids - existing[kind] for kind, ids in wanted.items() if ids - existing[kind]}
    if not missing:
        return rule
    for kind, ids in missing.items():
        warnings.append(
            f"{where}: {KIND_LABELS[kind]} {', '.join(f'#{i}' for i in sorted(ids))} gibt es nicht mehr und wurde entfernt."
        )

    def clean(cond):
        if cond.get("kind") not in missing:
            return cond
        values = [v for v in cond["values"] if v not in missing[cond["kind"]]]
        return {**cond, "values": values} if values else None

    out = []
    for item in rule["rules"]:
        if "kind" in item:
            kept = clean(item)
            if kept:
                out.append(kept)
        else:
            sub = [c for c in (clean(c) for c in item["rules"]) if c]
            if sub:
                out.append({**item, "rules": sub})
    return {**rule, "rules": out} if out else {}


def clean_body(body):
    """``(body, warnings)`` with ids that no longer exist removed."""
    body = copy.deepcopy(body)
    warnings = []
    body["eligibility"] = _clean_rule(body.get("eligibility") or {}, "Allgemeine Voraussetzungen", warnings)
    for item in body.get("slots", []):
        item["rule"] = _clean_rule(item.get("rule") or {}, f"Position ‚{item.get('label')}‘", warnings)
    return body, warnings


def apply_to_session(session, body, *, template=None):
    """Copy ``body`` into the configuration of ``session`` (caller holds the session lock).

    Positions are replaced; positions that people hold are refused (``ParticipationError``).
    Returns ``(participation, warnings)``.
    """
    body, warnings = clean_body(body)
    participation, _ = participation_for(session)
    previous_mode = participation.mode
    held = slots.held_by_slot(Registration.objects.filter(session=session, state__in=SEATED).only("slot_id"))
    taken = [s.label for s in slots.slots_for(participation) if held.get(s.pk)]
    if taken:
        raise ParticipationError(
            "positions_taken",
            "Positionen sind bereits besetzt; erst umbesetzen oder abmelden.",
            reasons=[f"„{label}“ ist besetzt." for label in taken],
        )
    participation.mode = body.get("mode", participation.mode)
    participation.eligibility = body.get("eligibility") or {}
    participation.min_participants = body.get("min_participants")
    participation.extra_places = body.get("extra_places")
    participation.waitlist_mode = body.get("waitlist_mode", participation.waitlist_mode)
    participation.max_participants = None if participation.mode == Mode.OPT_OUT else body.get("max_participants")
    participation.template_source = template
    participation.revision = (participation.revision or 0) + 1
    with transaction.atomic():
        participation.save()
        Slot.objects.filter(participation=participation).delete()
        items = [] if participation.mode == Mode.OPT_OUT else body.get("slots", [])
        for index, item in enumerate(items):
            Slot.objects.create(
                participation=participation,
                label=item["label"].strip(),
                min_count=item["min"],
                max_count=item["max"],
                rule=item.get("rule") or {},
                position=index,
            )
        positions = slots.slots_for(participation)
        if positions:
            participation.max_participants = slots.capacity(participation, positions)
        else:
            participation.extra_places = None
        participation.save(update_fields=["max_participants", "extra_places", "updated_at"])
        changes.apply_mode_change(session, previous_mode, participation)
    return participation, warnings


def apply_body_quietly(session, body):
    """For copies into a new draft service (no registrations exist): apply and ignore warnings."""
    if not body:
        return None
    return apply_to_session(session, body)[0]


def copy_slots(source, target):
    """Positions of ``source`` copied to ``target`` (both ``SessionParticipation``)."""
    Slot.objects.filter(participation=target).delete()
    Slot.objects.bulk_create(
        Slot(
            participation=target,
            label=s.label,
            min_count=s.min_count,
            max_count=s.max_count,
            rule=copy.deepcopy(s.rule or {}),
            position=s.position,
        )
        for s in source.slots.all()
    )


# ---------------------------------------------------------------- exercise templates (TRAIN-03)


def session_to_template_participation(session, template):
    """Saving a service as exercise template keeps an independent copy of its staffing configuration."""
    from .models import SessionParticipation, TemplateParticipation

    row = SessionParticipation.objects.filter(session=session).first()
    if row is None:
        return None
    return TemplateParticipation.objects.create(
        template=template, body=snapshot(row), staffing_template=row.template_source
    )


def template_participation_to_session(template, session):
    """A service made from an exercise template gets its own copy of the staffing configuration."""
    from .models import TemplateParticipation

    row = TemplateParticipation.objects.filter(template=template).first()
    if row is None or not row.body:
        return None
    participation, _ = apply_to_session(session, row.body, template=row.staffing_template)
    return participation
