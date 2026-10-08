"""Evaluation of eligibility rules (PART-03.2, E10, E11).

``evaluate`` is pure: it only looks at preloaded ``PersonFacts``. ``load_facts`` collects the
facts of many members in a constant number of queries (members, departments, confirmed account
links, qualifications, special tasks).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from django.db.models import Q

from .rules import GENDER_LABELS, KIND_LABELS, Names, iter_conditions

PLURALS = {"qualification": "Qualifikationen", "special_task": "Sonderaufgaben"}
NEUTRAL_AUDIENCE_NOTICE = "Dieser Dienst richtet sich an eine bestimmte Teilnehmendengruppe"


@dataclass(frozen=True)
class Result:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    # informational, also on success: a requirement met by a higher qualification names the substitute (E18)
    notes: list[str] = field(default_factory=list)


@dataclass
class PersonFacts:
    member_id: int
    gender: str = ""
    birthday: date | None = None
    group_id: int | None = None
    status_id: int | None = None
    department_ids: frozenset = frozenset()
    # type id -> [(valid_from, valid_until or None)]; member and linked-account entries merged (E10)
    qualifications: dict = field(default_factory=dict)
    special_tasks: dict = field(default_factory=dict)


def age_on(birthday, day):
    """Completed years on ``day``; a 29 Feb birthday counts from 1 March in non-leap years."""
    return day.year - birthday.year - ((day.month, day.day) < (birthday.month, birthday.day))


def _fmt(day):
    return day.strftime("%d.%m.%Y")


def neutral_audience_notice(rule):
    """Neutral wording for the portal when a rule contains a gender condition, else ``None``."""
    if any(c.get("kind") == "gender" for c in iter_conditions(rule)):
        return NEUTRAL_AUDIENCE_NOTICE
    return None


def _entry_state(entries, day):
    """Return ``("valid", None)``, ``("expired", last_end)``, ``("future", first_start)`` or ``("missing", None)``."""
    if not entries:
        return "missing", None
    if any(start <= day and (end is None or end >= day) for start, end in entries):
        return "valid", None
    ended = [end for start, end in entries if end is not None and end < day and start <= day]
    if ended:
        return "expired", max(ended)
    return "future", min(start for start, _ in entries)


def _quoted(names, kind, ids):
    return [f"‚{names.get(kind, i)}‘" for i in ids]


def _list(parts, word):
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} {word} {parts[-1]}"


def _candidates(kind, value, names):
    """Types that satisfy a condition value: for qualifications also all higher ones (E18)."""
    if kind != "qualification":
        return [value]
    others = sorted(names.satisfied_by(value) - {value}, key=lambda pk: names.get(kind, pk))
    return [value, *others]


def _resolve(kind, value, pool, day, names):
    """Return ``(state, when, holder_id)`` for a condition value.

    ``holder_id`` is the valid type that satisfies it (the value itself preferred, else a higher
    type). Without a valid holder the state is the best one over the value and all higher types:
    expired (latest end) before future before missing.
    """
    candidates = _candidates(kind, value, names)
    for pk in candidates:
        if _entry_state(pool.get(pk), day)[0] == "valid":
            return "valid", None, pk
    merged = [entry for pk in candidates for entry in pool.get(pk, ())]
    state, when = _entry_state(merged, day)
    return state, when, None


def _eval_has(cond, facts, day, names):
    kind, op, values = cond["kind"], cond["op"], cond["values"]
    pool = facts.qualifications if kind == "qualification" else facts.special_tasks
    noun = KIND_LABELS[kind]
    states = {v: _resolve(kind, v, pool, day, names) for v in values}
    valid = [v for v, (state, _, _) in states.items() if state == "valid"]
    if op == "has_none":
        # E18: holders of T or of any type that includes T are excluded.
        reasons = []
        for v in valid:
            holder = states[v][2]
            if holder == v:
                reasons.append(f"{noun} ‚{names.get(kind, v)}‘ schließt die Teilnahme aus")
            else:
                reasons.append(
                    f"{noun} ‚{names.get(kind, holder)}‘ schließt ‚{names.get(kind, v)}‘ ein "
                    "und schließt die Teilnahme aus"
                )
        return Result(not valid, reasons)
    if (op == "has_any" and valid) or (op == "has_all" and len(valid) == len(values)):
        return Result(
            True,
            notes=[
                f"{noun} ‚{names.get(kind, v)}‘ erfüllt durch ‚{names.get(kind, states[v][2])}‘"
                for v in valid
                if states[v][2] != v
            ],
        )
    failing = [v for v in values if v not in valid]
    if op == "has_any" and all(states[v][0] == "missing" for v in failing):
        return Result(
            False,
            [
                f"Keine der {PLURALS[kind]} {_list(_quoted(names, kind, failing), 'oder')} vorhanden"
                if len(failing) > 1
                else f"{noun} ‚{names.get(kind, failing[0])}‘ fehlt"
            ],
        )
    reasons = []
    for v in failing:
        state, when, _ = states[v]
        label = f"{noun} ‚{names.get(kind, v)}‘"
        if state == "missing":
            reasons.append(f"{label} fehlt")
        elif state == "expired":
            reasons.append(f"{label}: Gültig nur bis {_fmt(when)}")
        else:
            reasons.append(f"{label}: Gültig erst ab {_fmt(when)}")
    return Result(False, reasons)


def _eval_in(cond, facts, names):
    kind, values = cond["kind"], cond["values"]
    if kind == "gender":
        if not facts.gender:
            return Result(False, ["Geschlecht ist nicht erfasst"])
        if facts.gender in values:
            return Result(True)
        return Result(
            False, [f"Nur für Teilnehmende des Geschlechts {_list([GENDER_LABELS[v] for v in values], 'oder')}"]
        )
    if kind == "department":
        if facts.department_ids & set(values):
            return Result(True)
        if not facts.department_ids:
            return Result(False, ["Keiner Abteilung zugeordnet"])
        return Result(False, [f"Nur für die Abteilung {_list(_quoted(names, kind, values), 'oder')}"])
    current = facts.group_id if kind == "group" else facts.status_id
    if current in values:
        return Result(True)
    label = KIND_LABELS[kind]
    if current is None:
        return Result(False, [f"{label} ist nicht erfasst"])
    return Result(False, [f"Nur für {label} {_list(_quoted(names, kind, values), 'oder')}"])


def _eval_age(cond, facts, day):
    if facts.birthday is None:
        return Result(False, ["Geburtsdatum ist nicht erfasst"])
    age = age_on(facts.birthday, day)
    op = cond["op"]
    low = cond["min"] if op in ("min", "between") else None
    high = cond["max"] if op in ("max", "between") else None
    if (low is None or age >= low) and (high is None or age <= high):
        return Result(True)
    if op == "between":
        text = f"von {low} bis {high} Jahren"
    elif op == "min":
        text = f"ab {low} Jahren"
    else:
        text = f"bis {high} Jahre"
    return Result(False, [f"Nur für Teilnehmende {text}"])


def _eval_condition(cond, facts, day, names):
    kind = cond["kind"]
    if kind in ("qualification", "special_task"):
        return _eval_has(cond, facts, day, names)
    if kind == "age":
        return _eval_age(cond, facts, day)
    return _eval_in(cond, facts, names)


def _combine(results, match):
    if match == "all":
        reasons = [r for res in results for r in res.reasons]
        notes = [n for res in results for n in res.notes]
        return Result(not reasons and all(r.ok for r in results), reasons, notes)
    if not results or any(r.ok for r in results):
        return Result(True, notes=[n for res in results if res.ok for n in res.notes])
    detail = "; ".join(r for res in results for r in res.reasons)
    return Result(False, [f"Keine der Alternativen erfüllt: {detail}"])


def evaluate(rule, facts, on_date, names=None):
    """Evaluate a *valid* rule for one person on ``on_date``. Pure: no database access when ``names`` is given."""
    names = names or Names.for_rule(rule)
    results = []
    for item in rule.get("rules", []):
        if "kind" in item:
            results.append(_eval_condition(item, facts, on_date, names))
        else:
            sub = [_eval_condition(c, facts, on_date, names) for c in item["rules"]]
            results.append(_combine(sub, item["match"]))
    return _combine(results, rule.get("match", "all"))


def load_facts(member_ids):
    """Facts for many members in a constant number of queries (5)."""
    from members.models import Member
    from portal.models import AccountLink
    from qualifications.models import Qualification, SpecialTask

    member_ids = list(member_ids)
    facts = {}
    for pk, gender, birthday, group_id, status_id in Member.objects.filter(pk__in=member_ids).values_list(
        "pk", "gender", "birthday", "group_id", "status_id"
    ):
        facts[pk] = PersonFacts(pk, gender, birthday, group_id, status_id)
    departments = defaultdict(set)
    for member_id, department_id in Member.departments.through.objects.filter(member_id__in=member_ids).values_list(
        "member_id", "department_id"
    ):
        departments[member_id].add(department_id)
    for pk, person in facts.items():
        person.department_ids = frozenset(departments[pk])

    # E10: only confirmed links count; pending or rejected links grant nothing.
    user_to_member = dict(
        AccountLink.objects.filter(member_id__in=member_ids, status=AccountLink.Status.CONFIRMED).values_list(
            "user_id", "member_id"
        )
    )
    scope = Q(member_id__in=member_ids) | Q(user_id__in=list(user_to_member))

    def owner(member_id, user_id):
        return member_id if member_id is not None else user_to_member.get(user_id)

    for type_id, member_id, user_id, start, end in Qualification.objects.filter(scope).values_list(
        "type_id", "member_id", "user_id", "date_acquired", "date_expires"
    ):
        person = facts.get(owner(member_id, user_id))
        if person:
            person.qualifications.setdefault(type_id, []).append((start, end))
    for type_id, member_id, user_id, start, end in SpecialTask.objects.filter(scope).values_list(
        "task_id", "member_id", "user_id", "start_date", "end_date"
    ):
        person = facts.get(owner(member_id, user_id))
        if person:
            person.special_tasks.setdefault(type_id, []).append((start, end))
    return facts


def evaluate_members(rule, member_ids, on_date):
    """``{member_id: Result}`` for many members: facts and names are loaded once."""
    facts = load_facts(member_ids)
    names = Names.for_rule(rule)
    return {pk: evaluate(rule, person, on_date, names) for pk, person in facts.items()}
