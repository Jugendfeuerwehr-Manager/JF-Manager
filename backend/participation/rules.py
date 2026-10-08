"""Eligibility rule language v1 (PART-03.1): schema, strict validation, plain-German summary.

A rule is JSON::

    {"v": 1, "match": "all" | "any", "rules": [<condition> | <group>, ...]}

A condition is ``{"kind", "op", ...}``; a group is ``{"match", "rules": [<condition>, ...]}``
and may not contain further groups (two levels at most). An empty top-level ``rules`` list is
allowed and means "no special requirements"; empty groups are rejected.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = 1
MAX_CONDITIONS = 50
MAX_VALUES = 100
MAX_AGE = 120

MATCHES = ("all", "any")
GENDERS = ("male", "female", "diverse")
GENDER_LABELS = {"male": "männlich", "female": "weiblich", "diverse": "divers"}

HAS_OPS = ("has_any", "has_all", "has_none")
KIND_OPS = {
    "qualification": HAS_OPS,
    "special_task": HAS_OPS,
    "gender": ("in",),
    "age": ("min", "max", "between"),
    "group": ("in",),
    "status": ("in",),
    "department": ("in",),
}
KIND_LABELS = {
    "qualification": "Qualifikation",
    "special_task": "Sonderaufgabe",
    "gender": "Geschlecht",
    "age": "Alter",
    "group": "Gruppe",
    "status": "Status",
    "department": "Abteilung",
}
AGE_KEYS = {"min": ("min",), "max": ("max",), "between": ("min", "max")}


def _model_for(kind):
    if kind == "qualification":
        from qualifications.models import QualificationType

        return QualificationType
    if kind == "special_task":
        from qualifications.models import SpecialTaskType

        return SpecialTaskType
    if kind == "group":
        from members.models import Group

        return Group
    if kind == "status":
        from members.models import Status

        return Status
    if kind == "department":
        from departments.models import Department

        return Department
    return None


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def iter_conditions(rule):
    """Yield every condition of an (already valid) rule, groups flattened."""
    for item in rule.get("rules", []):
        if "kind" in item:
            yield item
        else:
            yield from item.get("rules", [])


def _collect_ids(rule):
    ids = {}
    for cond in iter_conditions(rule):
        kind = cond.get("kind")
        if _model_for(kind) is not None and isinstance(cond.get("values"), list):
            ids.setdefault(kind, set()).update(v for v in cond["values"] if _is_int(v))
    return ids


class Names:
    """Display names for the ids used in a rule (one query per used kind)."""

    def __init__(self, names=None, satisfying=None):
        self._names = names or {}
        # E18: qualification type id -> ids of all types whose holders satisfy it (incl. itself)
        self.satisfying = satisfying or {}

    @classmethod
    def for_rule(cls, rule):
        names = {}
        collected = _collect_ids(rule)
        for kind, ids in collected.items():
            names[kind] = dict(_model_for(kind).objects.filter(pk__in=ids).values_list("pk", "name"))
        satisfying = {}
        if "qualification" in collected:
            # one more query for the hierarchy closure and one for the names of substitutes
            from qualifications.hierarchy import satisfying_types

            satisfying = satisfying_types()
            extra = {pk for ids in satisfying.values() for pk in ids} - set(names["qualification"])
            if extra:
                from qualifications.models import QualificationType

                names["qualification"].update(QualificationType.objects.filter(pk__in=extra).values_list("pk", "name"))
        return cls(names, satisfying)

    def satisfied_by(self, pk):
        """Qualification type ids that satisfy a requirement on ``pk`` (itself first-class member)."""
        return self.satisfying.get(pk, {pk}) | {pk}

    def get(self, kind, pk):
        return self._names.get(kind, {}).get(pk, f"#{pk}")


def _check_values(cond, path, errors, kind):
    values = cond.get("values")
    if not isinstance(values, list) or not values:
        errors[f"{path}.values"] = "Mindestens ein Wert ist erforderlich"
        return None
    if len(values) > MAX_VALUES:
        errors[f"{path}.values"] = f"Höchstens {MAX_VALUES} Werte erlaubt"
        return None
    if kind == "gender":
        if any(not isinstance(v, str) or v not in GENDERS for v in values):
            errors[f"{path}.values"] = "Ungültiges Geschlecht (erlaubt: männlich, weiblich, divers)"
            return None
        return values
    if any(not _is_int(v) for v in values):
        errors[f"{path}.values"] = "Werte müssen Zahlen (Kennungen) sein"
        return None
    return values


def _check_condition(cond, path, errors):
    kind, op = cond.get("kind"), cond.get("op")
    if not isinstance(kind, str) or kind not in KIND_OPS:
        errors[f"{path}.kind"] = "Unbekannte Art der Bedingung"
        return
    if not isinstance(op, str) or op not in KIND_OPS[kind]:
        errors[f"{path}.op"] = f"Ungültiger Operator für {KIND_LABELS[kind]}"
        return
    allowed = {"kind", "op"} | (set(AGE_KEYS[op]) if kind == "age" else {"values"})
    for key in cond:
        if key not in allowed:
            errors[f"{path}.{key}"] = "Unbekanntes Feld"
    if kind == "age":
        bounds = {}
        for key in AGE_KEYS[op]:
            value = cond.get(key)
            if not _is_int(value) or not 0 <= value <= MAX_AGE:
                errors[f"{path}.{key}"] = f"Alter muss eine ganze Zahl von 0 bis {MAX_AGE} sein"
            else:
                bounds[key] = value
        if len(bounds) == 2 and bounds["min"] > bounds["max"]:
            errors[f"{path}.max"] = "Mindestalter größer als Höchstalter"
        return
    _check_values(cond, path, errors, kind)


def validate_rule(rule):
    """Return ``{path: German message}``; an empty dict means the rule is valid."""
    errors = {}
    if not isinstance(rule, dict):
        return {"": "Die Regel muss ein Objekt sein"}
    for key in rule:
        if key not in ("v", "match", "rules"):
            errors[key] = "Unbekanntes Feld"
    if rule.get("v") != SCHEMA_VERSION or not _is_int(rule.get("v")):
        errors["v"] = f"Nur Regelversion {SCHEMA_VERSION} wird unterstützt"
    if rule.get("match") not in MATCHES:
        errors["match"] = "Verknüpfung muss „alle“ (all) oder „mindestens eine“ (any) sein"
    items = rule.get("rules")
    if not isinstance(items, list):
        errors["rules"] = "Bedingungen müssen als Liste angegeben werden"
        return errors
    count = 0
    for i, item in enumerate(items):
        path = f"rules[{i}]"
        if not isinstance(item, dict):
            errors[path] = "Bedingung muss ein Objekt sein"
        elif "rules" in item or "match" in item:
            if "kind" in item:
                errors[path] = "Eine Bedingung darf keine Untergruppe sein"
                continue
            for key in item:
                if key not in ("match", "rules"):
                    errors[f"{path}.{key}"] = "Unbekanntes Feld"
            if item.get("match") not in MATCHES:
                errors[f"{path}.match"] = "Verknüpfung muss „alle“ (all) oder „mindestens eine“ (any) sein"
            sub = item.get("rules")
            if not isinstance(sub, list) or not sub:
                errors[f"{path}.rules"] = "Eine Bedingungsgruppe braucht mindestens eine Bedingung"
                continue
            for j, cond in enumerate(sub):
                cpath = f"{path}.rules[{j}]"
                count += 1
                if not isinstance(cond, dict):
                    errors[cpath] = "Bedingung muss ein Objekt sein"
                elif "rules" in cond or "match" in cond:
                    errors[cpath] = "Bedingungsgruppen dürfen nicht weiter verschachtelt werden"
                else:
                    _check_condition(cond, cpath, errors)
        else:
            count += 1
            _check_condition(item, path, errors)
    if count > MAX_CONDITIONS:
        errors["rules"] = f"Höchstens {MAX_CONDITIONS} Bedingungen erlaubt"
    if not errors:
        errors.update(_check_ids(rule))
    return errors


def _check_ids(rule):
    """Referenced ids must exist (one query per used kind)."""
    errors = {}
    wanted = _collect_ids(rule)
    existing = {
        kind: set(_model_for(kind).objects.filter(pk__in=ids).values_list("pk", flat=True))
        for kind, ids in wanted.items()
    }
    labels = {
        "qualification": "Qualifikationstyp",
        "special_task": "Sonderaufgabentyp",
        "group": "Gruppe",
        "status": "Status",
        "department": "Abteilung",
    }

    def check(cond, path):
        kind = cond["kind"]
        if kind in existing:
            missing = [v for v in cond["values"] if v not in existing[kind]]
            if missing:
                errors[f"{path}.values"] = f"{labels[kind]} nicht gefunden: {', '.join(str(m) for m in missing)}"

    for i, item in enumerate(rule["rules"]):
        if "kind" in item:
            check(item, f"rules[{i}]")
        else:
            for j, cond in enumerate(item["rules"]):
                check(cond, f"rules[{i}].rules[{j}]")
    return errors


# --- plain-German summary -------------------------------------------------------------


def _join(parts, word):
    if len(parts) <= 1:
        return "".join(parts)
    return f"{', '.join(parts[:-1])} {word} {parts[-1]}"


def _condition_text(cond, names):
    """Return ``(text, inner_joiner)``; the joiner is "und"/"oder" for composite texts."""
    kind, op = cond["kind"], cond["op"]
    if kind == "age":
        if op == "min":
            return f"Alter ab {cond['min']}", None
        if op == "max":
            return f"Alter bis {cond['max']}", None
        return f"Alter von {cond['min']} bis {cond['max']}", None
    if kind == "gender":
        labels = [GENDER_LABELS[v] for v in cond["values"]]
        return f"Geschlecht {_join(labels, 'oder')}", "oder" if len(labels) > 1 else None
    labels = [names.get(kind, v) for v in cond["values"]]
    if kind == "qualification" and op != "has_none":
        # E18: a requirement on T is also met by every type that includes T
        labels = [
            f"{label} (oder höher)" if len(names.satisfied_by(v)) > 1 else label
            for label, v in zip(labels, cond["values"], strict=True)
        ]
    if kind in ("qualification", "special_task"):
        prefix = "" if kind == "qualification" else "Sonderaufgabe "
        if op == "has_none":
            noun = "Qualifikation" if kind == "qualification" else "Sonderaufgabe"
            if len(labels) == 1:
                return f"ohne {noun} {labels[0]}", None
            return f"weder {_join(labels, 'noch')}", None
        word = "oder" if op == "has_any" else "und"
        return prefix + _join(labels, word), word if len(labels) > 1 else None
    prefix = f"{KIND_LABELS[kind]} "
    return prefix + _join(labels, "oder"), "oder" if len(labels) > 1 else None


def _combine(items, match):
    word = "und" if match == "all" else "oder"
    parts = []
    for text, joiner in items:
        parts.append(f"({text})" if joiner and joiner != word and len(items) > 1 else text)
    return " ".join(f"{p}" if i == 0 else f"{word} {p}" for i, p in enumerate(parts))


def summarize(rule, names=None):
    """Plain-German sentence for a valid rule, e.g. ``Maschinist und (Gruppenführer oder Zugführer) und Alter ab 18``."""
    if not rule.get("rules"):
        return "Keine besonderen Voraussetzungen"
    names = names or Names.for_rule(rule)
    items = []
    for item in rule["rules"]:
        if "kind" in item:
            items.append(_condition_text(item, names))
        else:
            sub = [_condition_text(c, names) for c in item["rules"]]
            items.append((_combine(sub, item["match"]), "und" if item["match"] == "all" else "oder"))
    if len(items) == 1:
        return items[0][0]
    return _combine(items, rule["match"])


@dataclass
class Validation:
    errors: dict = field(default_factory=dict)
    summary: str = ""

    @property
    def ok(self):
        return not self.errors


def validate_and_summarize(rule):
    errors = validate_rule(rule)
    if errors:
        return Validation(errors=errors)
    return Validation(summary=summarize(rule))
