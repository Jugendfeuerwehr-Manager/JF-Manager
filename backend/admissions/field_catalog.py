"""Fields of a member or guardian that an application form may fill.

Form elements point at a catalog key (``target``). Answers without a target would only live
in the application, so data inputs must point at a member field, a guardian field or an
additional member field (``member.extra.<key>``). Only confirmations (required checkboxes)
stay in the application alone.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogField:
    key: str
    label: str
    input_type: str  # the element type a builder offers for this target
    model_field: str
    sensitive: bool = False


MEMBER_FIELDS = (
    CatalogField("member.name", "Vorname", "text", "name"),
    CatalogField("member.lastname", "Nachname", "text", "lastname"),
    CatalogField("member.birthday", "Geburtsdatum", "date", "birthday"),
    CatalogField("member.gender", "Geschlecht", "select", "gender"),
    CatalogField("member.street", "Straße, Hausnr.", "text", "street"),
    CatalogField("member.zip_code", "PLZ", "text", "zip_code"),
    CatalogField("member.city", "Ort", "text", "city"),
    CatalogField("member.phone", "Telefon", "phone", "phone"),
    CatalogField("member.mobile", "Mobil", "phone", "mobile"),
    CatalogField("member.email", "E-Mail-Adresse", "email", "email"),
    CatalogField("member.canSwimm", "Schwimmer*in", "checkbox", "canSwimm"),
    CatalogField("member.avatar", "Passbild", "photo", "avatar"),
    CatalogField("member.health_notes", "Gesundheitsangaben", "textarea", "health_notes", sensitive=True),
)

GUARDIAN_FIELDS = (
    CatalogField("guardian.name", "Vorname", "text", "name"),
    CatalogField("guardian.lastname", "Nachname", "text", "lastname"),
    CatalogField("guardian.street", "Straße, Hausnr.", "text", "street"),
    CatalogField("guardian.zip_code", "PLZ", "text", "zip_code"),
    CatalogField("guardian.city", "Ort", "text", "city"),
    CatalogField("guardian.phone", "Telefon", "phone", "phone"),
    CatalogField("guardian.mobile", "Mobil", "phone", "mobile"),
    CatalogField("guardian.email", "E-Mail-Adresse", "email", "email"),
    CatalogField("guardian.email2", "Zweite E-Mail-Adresse", "email", "email2"),
)

MEMBER_CATALOG = {field.key: field for field in MEMBER_FIELDS}
GUARDIAN_CATALOG = {field.key: field for field in GUARDIAN_FIELDS}

GENDER_OPTIONS = (
    {"value": "male", "label": "Männlich"},
    {"value": "female", "label": "Weiblich"},
    {"value": "diverse", "label": "Divers"},
)


EXTRA_PREFIX = "member.extra."


def extra_definitions(department_id):
    """Additional member fields a form of ``department_id`` may fill (``None``: organisation forms).

    Organisation forms serve every department, so they only offer organisation-wide fields.
    """
    from django.db.models import Q

    from members.models import MemberFieldDefinition

    scope = Q(department__isnull=True)
    if department_id is not None:
        scope |= Q(department_id=department_id)
    return MemberFieldDefinition.objects.filter(scope, active=True).order_by("position", "label")


def extra_catalog(department_id):
    """``{target: CatalogField}`` for the additional fields; ``model_field`` is the value key."""
    return {
        f"{EXTRA_PREFIX}{definition.key}": CatalogField(
            f"{EXTRA_PREFIX}{definition.key}", definition.label, definition.field_type, definition.key
        )
        for definition in extra_definitions(department_id)
    }


def as_payload(department_id=None):
    """The catalog as the builder needs it."""

    def rows(fields):
        return [{"key": f.key, "label": f.label, "input_type": f.input_type, "sensitive": f.sensitive} for f in fields]

    extra = [
        {
            "key": f"{EXTRA_PREFIX}{definition.key}",
            "id": definition.pk,
            "label": definition.label,
            "input_type": definition.field_type,
            "options": definition.options,
            "help_text": definition.help_text,
            "department": definition.department_id,
        }
        for definition in extra_definitions(department_id)
    ]
    return {
        "member": rows(MEMBER_FIELDS),
        "guardian": rows(GUARDIAN_FIELDS),
        "extra": extra,
        "gender_options": list(GENDER_OPTIONS),
    }
