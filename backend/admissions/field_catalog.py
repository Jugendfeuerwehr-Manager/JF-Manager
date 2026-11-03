"""Fields of a member or guardian that an application form may fill.

Form elements point at a catalog key (``target``); elements without a target are free
fields that only live in the application.
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


def as_payload():
    """The catalog as the builder needs it."""

    def rows(fields):
        return [{"key": f.key, "label": f.label, "input_type": f.input_type, "sensitive": f.sensitive} for f in fields]

    return {"member": rows(MEMBER_FIELDS), "guardian": rows(GUARDIAN_FIELDS), "gender_options": list(GENDER_OPTIONS)}
