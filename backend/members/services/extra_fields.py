"""Values of additional member fields (``Member.extra_fields``).

A member may carry the fields of the organisation and of its own departments. Every
write path (member dialog, application takeover) cleans values here.
"""

from datetime import date

from django.db.models import Q

from members.models import MemberFieldDefinition

TEXT_LIMITS = {"text": 300, "textarea": 4000}


def definitions_for(department_ids):
    """Active definitions that apply to members of ``department_ids`` (plus the organisation's)."""
    return MemberFieldDefinition.objects.filter(
        Q(department__isnull=True) | Q(department_id__in=[d for d in department_ids if d is not None]), active=True
    )


def coerce(definition, value):
    """The stored form of ``value``; ``None`` means empty. Raises ``ValueError`` with a message."""
    field_type = definition.field_type
    if field_type == MemberFieldDefinition.FieldType.CHECKBOX:
        if not isinstance(value, bool):
            raise ValueError("Bitte Ja oder Nein angeben.")
        return value
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if field_type == MemberFieldDefinition.FieldType.NUMBER:
        return _number(value)
    if not isinstance(value, str):
        raise ValueError("Bitte einen Text angeben.")
    value = value.strip()
    if field_type == MemberFieldDefinition.FieldType.DATE:
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValueError("Bitte ein gültiges Datum angeben.") from exc
    if field_type == MemberFieldDefinition.FieldType.SELECT:
        if value not in definition.options:
            raise ValueError("Bitte eine der Möglichkeiten wählen.")
        return value
    if len(value) > TEXT_LIMITS.get(field_type, 300):
        raise ValueError("Der Text ist zu lang.")
    return value


def _number(value):
    if isinstance(value, bool):
        raise ValueError("Bitte eine Zahl angeben.")
    if isinstance(value, int | float):
        return value
    try:
        number = float(str(value).replace(",", "."))
    except ValueError as exc:
        raise ValueError("Bitte eine Zahl angeben.") from exc
    return int(number) if number.is_integer() else number


def clean_values(values, definitions, current=None):
    """Merge ``values`` into ``current``; returns ``(merged, errors)``.

    Unknown keys are errors; empty values remove the key. Values of fields that no longer
    apply (another department, deactivated) stay untouched in ``current``.
    """
    by_key = {definition.key: definition for definition in definitions}
    merged = dict(current or {})
    errors = {}
    if not isinstance(values, dict):
        return merged, {"": "Zusatzangaben müssen ein Objekt sein."}
    for key, value in values.items():
        definition = by_key.get(key)
        if definition is None:
            errors[key] = "Unbekanntes Zusatzfeld."
            continue
        try:
            clean = coerce(definition, value)
        except ValueError as error:
            errors[key] = str(error)
            continue
        if clean is None:
            merged.pop(key, None)
            continue
        merged[key] = clean
    return merged, errors


def clean_definition_options(field_type, options):
    """``(options, error)``: choices as distinct, non-empty strings (empty for other types), or a message."""
    if field_type != MemberFieldDefinition.FieldType.SELECT:
        return [], None
    if not isinstance(options, list) or not all(isinstance(option, str) for option in options):
        return [], "Möglichkeiten als Liste von Texten angeben."
    clean = []
    for option in options:
        option = option.strip()[:100]
        if option and option not in clean:
            clean.append(option)
    if not clean:
        return [], "Eine Auswahl braucht mindestens eine Möglichkeit."
    return clean, None
