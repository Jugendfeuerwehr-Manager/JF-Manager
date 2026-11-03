"""Structure of an application form: pages → sections → elements.

The builder edits this JSON, publishing freezes it and the public form renders it. Checking
happens here so every path (draft save, publish, submission) applies the same rules.
"""

import re

from admissions.field_catalog import GUARDIAN_CATALOG, MEMBER_CATALOG

INPUT_TYPES = {"text", "textarea", "number", "date", "email", "phone", "select", "radio", "checkbox", "photo"}
CONTENT_TYPES = {"heading", "richtext", "divider"}
LEGAL_TYPES = {"legal_ack", "consent"}
ELEMENT_TYPES = INPUT_TYPES | CONTENT_TYPES | LEGAL_TYPES | {"guardians", "signature"}
CHOICE_TYPES = {"select", "radio"}
SIGNATURE_ROLES = {"applicant", "guardian_1", "guardian_2"}
CONSENT_PERSONS = {"applicant", "guardians"}
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,49}$")
MAX_GUARDIANS = 4


def iter_elements(schema):
    """Yield ``(path, element)`` for every element in page/section order."""
    for page_index, page in enumerate(schema.get("pages") or []):
        for section_index, section in enumerate(page.get("sections") or []):
            for element_index, element in enumerate(section.get("elements") or []):
                yield f"pages.{page_index}.sections.{section_index}.elements.{element_index}", element


def answer_keys(schema):
    """Keys under which applicants' answers are stored (inputs, legal elements, guardians, signatures)."""
    return [element["key"] for _, element in iter_elements(schema) if element.get("key")]


class SchemaErrors:
    def __init__(self):
        self.items = []

    def add(self, path, message):
        self.items.append({"path": path, "message": message})

    def __bool__(self):
        return bool(self.items)


def check_structure(schema):
    """Errors that make the JSON unusable for the builder (a draft must at least pass these)."""
    errors = SchemaErrors()
    if not isinstance(schema, dict) or not isinstance(schema.get("pages"), list):
        errors.add("", "Das Formular braucht eine Liste von Seiten.")
        return errors.items
    _check_containers(schema, errors)
    if errors:
        return errors.items
    seen_ids = set()
    for path, element in iter_elements(schema):
        if not isinstance(element, dict) or element.get("type") not in ELEMENT_TYPES:
            errors.add(path, "Ungültiges Element.")
            continue
        if not element.get("id") or element["id"] in seen_ids:
            errors.add(path, "Jedes Element braucht eine eindeutige ID.")
        seen_ids.add(element.get("id"))
    return errors.items


def check_schema(schema, *, legal_kinds=(), consent_kinds=(), extra_catalog=None, for_publish=False):
    """Return a list of ``{"path", "message"}``; empty when the form is valid.

    ``legal_kinds`` and ``consent_kinds`` are the slugs that may be referenced,
    ``extra_catalog`` the additional member fields (``{target: CatalogField}``).
    """
    errors = SchemaErrors()
    if not isinstance(schema, dict) or not isinstance(schema.get("pages"), list):
        errors.add("", "Das Formular braucht eine Liste von Seiten.")
        return errors.items
    if for_publish and not any(True for _ in iter_elements(schema)):
        errors.add("pages", "Ein leeres Formular kann nicht veröffentlicht werden.")

    _check_containers(schema, errors)
    seen_ids, seen_keys, seen_targets, seen_once = set(), set(), set(), set()
    catalog = {**MEMBER_CATALOG, **(extra_catalog or {})}
    guardian_blocks = 0
    for path, element in iter_elements(schema):
        if not isinstance(element, dict):
            errors.add(path, "Ungültiges Element.")
            continue
        element_id = element.get("id")
        if not element_id or element_id in seen_ids:
            errors.add(path, "Jedes Element braucht eine eindeutige ID.")
        seen_ids.add(element_id)

        element_type = element.get("type")
        if element_type not in ELEMENT_TYPES:
            errors.add(path, f"Unbekannter Elementtyp „{element_type}“.")
            continue
        if element_type == "guardians":
            guardian_blocks += 1

        _check_visibility(path, element, seen_keys, errors)
        if element_type in CONTENT_TYPES:
            _check_content(path, element, errors)
            continue

        key = element.get("key")
        if not key or not KEY_PATTERN.match(key):
            errors.add(path, "Kennung: Kleinbuchstaben, Ziffern und _, beginnend mit einem Buchstaben.")
        elif key in seen_keys:
            errors.add(path, f"Die Kennung „{key}“ ist doppelt vergeben.")
        seen_keys.add(key)
        if not (element.get("label") or "").strip() and element_type != "signature":
            errors.add(path, "Bitte eine Beschriftung angeben.")

        _check_by_type(path, element, seen_targets, catalog, legal_kinds, consent_kinds, errors)
        _check_once(path, element, seen_once, errors)

    if guardian_blocks > 1:
        errors.add("pages", "Der Block „Sorgeberechtigte“ darf nur einmal vorkommen.")
    # Taking an application over creates a member, which needs a name.
    if for_publish and not {"member.name", "member.lastname"} <= seen_targets:
        errors.add("pages", "Vorname und Nachname des Mitglieds müssen abgefragt werden.")
    return errors.items


def _check_by_type(path, element, seen_targets, catalog, legal_kinds, consent_kinds, errors):
    element_type = element["type"]
    if element_type in INPUT_TYPES:
        _check_input(path, element, seen_targets, catalog, errors)
        return
    if element_type == "guardians":
        _check_guardians(path, element, errors)
        return
    if element_type == "legal_ack" and element.get("legal_kind") not in legal_kinds:
        errors.add(path, "Bitte einen Rechtstext auswählen.")
    if element_type == "consent" and element.get("consent_kind") not in consent_kinds:
        errors.add(path, "Bitte eine aktive Einwilligungsart auswählen.")
    if element_type == "consent" and element.get("person", "applicant") not in CONSENT_PERSONS:
        errors.add(path, "Einwilligung gilt für Antragsteller*in oder Sorgeberechtigte.")
    if element_type == "signature" and element.get("role") not in SIGNATURE_ROLES:
        errors.add(path, "Bitte festlegen, wer unterschreibt.")


def _check_containers(schema, errors):
    for page_index, page in enumerate(schema["pages"]):
        if not isinstance(page, dict) or not isinstance(page.get("sections"), list):
            errors.add(f"pages.{page_index}", "Jede Seite braucht Abschnitte.")
            continue
        for section_index, section in enumerate(page["sections"]):
            if not isinstance(section, dict) or not isinstance(section.get("elements"), list):
                errors.add(f"pages.{page_index}.sections.{section_index}", "Jeder Abschnitt braucht Elemente.")


def _check_visibility(path, element, known_keys, errors):
    rule = element.get("visible_if")
    if rule is None:
        return
    if not isinstance(rule, dict):
        errors.add(path, "Ungültige Sichtbarkeitsregel.")
        return
    if "age_below" in rule:
        if not isinstance(rule["age_below"], int) or not 1 <= rule["age_below"] <= 120:
            errors.add(path, "Altersgrenze muss eine ganze Zahl zwischen 1 und 120 sein.")
        return
    if rule.get("field") not in known_keys:
        errors.add(path, "Die Sichtbarkeit darf nur von einem vorherigen Feld abhängen.")


def _check_content(path, element, errors):
    if element["type"] == "heading" and not (element.get("label") or "").strip():
        errors.add(path, "Eine Überschrift braucht Text.")
    if element["type"] == "richtext" and not ((element.get("html") or "").strip() or element.get("text_block")):
        errors.add(path, "Bitte Text eingeben oder einen Textbaustein wählen.")


def is_confirmation(element):
    """A required checkbox without target: a declaration that only lives in the sealed application."""
    return element.get("type") == "checkbox" and not element.get("target") and bool(element.get("required"))


def _check_once(path, element, seen, errors):
    """Elements that make sense once per form: one legal text, consent or signature each."""
    element_type = element["type"]
    if element_type == "legal_ack":
        token, label = ("legal", element.get("legal_kind")), "Dieser Rechtstext"
    elif element_type == "consent":
        token = ("consent", element.get("consent_kind"), element.get("person", "applicant"))
        label = "Diese Einwilligung"
    elif element_type == "signature":
        token, label = ("signature", element.get("role")), "Diese Unterschrift"
    else:
        return
    if None in token or "" in token:
        return
    if token in seen:
        errors.add(path, f"{label} kommt schon im Formular vor.")
    seen.add(token)


def _check_input(path, element, seen_targets, catalog, errors):
    element_type = element["type"]
    target = element.get("target")
    if not target:
        if element_type == "photo":
            errors.add(path, "Ein Foto muss dem Passbild zugeordnet sein.")
        elif not is_confirmation(element):
            errors.add(path, "Diese Angabe landet nicht am Mitglied. Bitte ein Mitglieds- oder Zusatzfeld zuordnen.")
    else:
        field = catalog.get(target)
        if field is None:
            errors.add(path, "Das Zielfeld gibt es nicht (mehr). Bitte ein anderes wählen.")
        elif field.input_type != element_type and not (field.input_type == "text" and element_type == "textarea"):
            errors.add(path, f"„{field.label}“ passt nicht zum Elementtyp.")
        elif target in seen_targets:
            errors.add(path, f"„{field.label}“ ist schon einem anderen Feld zugeordnet.")
        seen_targets.add(target)

    # Gender and additional selects take their choices from the member side.
    if element_type not in CHOICE_TYPES or target == "member.gender" or (target or "").startswith("member.extra."):
        return
    options = element.get("options") or []
    values = [option.get("value") for option in options if isinstance(option, dict)]
    if not values or len(values) != len(options) or not all(values):
        errors.add(path, "Auswahlfelder brauchen Optionen mit Wert und Beschriftung.")
    elif len(set(values)) != len(values):
        errors.add(path, "Optionswerte müssen eindeutig sein.")


def _check_guardians(path, element, errors):
    minimum, maximum = element.get("min", 1), element.get("max", 2)
    if not (isinstance(minimum, int) and isinstance(maximum, int) and 0 <= minimum <= maximum <= MAX_GUARDIANS):
        errors.add(path, f"Anzahl Sorgeberechtigte: 0 ≤ Minimum ≤ Maximum ≤ {MAX_GUARDIANS}.")
    fields = element.get("fields") or []
    targets = [field.get("target") for field in fields if isinstance(field, dict)]
    if len(targets) != len(fields) or any(target not in GUARDIAN_CATALOG for target in targets):
        errors.add(path, "Unbekanntes Feld für Sorgeberechtigte.")
    if len(set(targets)) != len(targets):
        errors.add(path, "Felder der Sorgeberechtigten dürfen nicht doppelt vorkommen.")
    if not {"guardian.name", "guardian.lastname"} <= set(targets):
        errors.add(path, "Vor- und Nachname der Sorgeberechtigten sind immer nötig.")
