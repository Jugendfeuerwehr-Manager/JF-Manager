"""Change requests for name and contact data (PORTAL-03, concept 4.4, E2).

Nothing changes on the record before a reviewer approves. Per target there is at
most one open request; submitting again updates it (new version). Values are
cleaned on the server: HTML and control characters are removed, formula
prefixes stay plain text (SEC-08) because values are only ever rendered as text.
"""

import re
import unicodedata

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils.html import strip_tags

from members.models import Parent

from .models import ChangeRequest

MEMBER_FIELDS = {
    "name": "Vorname",
    "lastname": "Nachname",
    "email": "E-Mail",
    "phone": "Telefon",
    "mobile": "Mobil",
    "street": "Straße",
    "zip_code": "PLZ",
    "city": "Ort",
}
PARENT_FIELDS = {**MEMBER_FIELDS, "email": "E-Mail 1", "email2": "E-Mail 2"}
REQUIRED = {"name", "lastname"}
PHONE = re.compile(r"^[0-9+ /-]*$")
ZIP = re.compile(r"^[0-9A-Za-z -]{3,10}$")
MAX_LENGTH = 200  # all requestable model fields are CharField(max_length=200)


class ChangeRequestError(Exception):
    def __init__(self, detail, code="invalid", status=400, fields=None):
        super().__init__(detail)
        self.detail, self.code, self.status, self.fields = detail, code, status, fields or {}


def field_labels(kind):
    return PARENT_FIELDS if kind == "parent" else MEMBER_FIELDS


def kind_of(record):
    return "parent" if isinstance(record, Parent) else "member"


def clean_text(value):
    """Plain single-line text: no HTML, no control or format characters, collapsed spaces."""
    text = strip_tags(str(value if value is not None else ""))
    text = "".join(" " if unicodedata.category(ch) in {"Cc", "Cf", "Zl", "Zp"} else ch for ch in text)
    return " ".join(text.split())


def validate(kind, raw):
    """Return ``{field: cleaned}`` or raise with per-field messages."""
    labels = field_labels(kind)
    if not isinstance(raw, dict):
        raise ChangeRequestError("Ungültige Angaben.")
    unknown = set(raw) - set(labels)
    if unknown:
        raise ChangeRequestError(
            "Diese Angaben lassen sich nicht per Antrag ändern.", fields={f: "Nicht änderbar." for f in unknown}
        )
    cleaned, errors = {}, {}
    for field, value in raw.items():
        if value is not None and not isinstance(value, str):
            errors[field] = "Ungültiger Wert."
            continue
        text = clean_text(value)
        if len(text) > MAX_LENGTH:
            errors[field] = f"Höchstens {MAX_LENGTH} Zeichen."
        elif field in REQUIRED and not text:
            errors[field] = "Darf nicht leer sein."
        elif field.startswith("email") and text:
            try:
                validate_email(text)
            except DjangoValidationError:
                errors[field] = "Bitte eine gültige E-Mail-Adresse angeben."
        elif field in {"phone", "mobile"} and not PHONE.match(text):
            errors[field] = "Nur Ziffern, +, Leerzeichen, / und - erlaubt."
        elif field == "zip_code" and text and not ZIP.match(text):
            errors[field] = "Bitte eine gültige Postleitzahl angeben."
        cleaned[field] = text
    if errors:
        raise ChangeRequestError("Bitte die markierten Angaben prüfen.", fields=errors)
    return cleaned


def current_values(record):
    return {field: getattr(record, field) or "" for field in field_labels(kind_of(record))}


def open_request(record):
    lookup = {"target_parent": record} if kind_of(record) == "parent" else {"target_member": record}
    return ChangeRequest.objects.filter(status=ChangeRequest.Status.OPEN, **lookup).first()


def submit(record, raw, user):
    """Create or update the open request for ``record``; fields equal to the current value are dropped."""
    kind = kind_of(record)
    cleaned = validate(kind, raw)
    now = current_values(record)
    entries = [{"field": f, "old": now[f], "new": v} for f, v in cleaned.items() if v != now[f]]
    if not entries:
        raise ChangeRequestError("Keine Änderung gegenüber den gespeicherten Daten.", code="unchanged")
    lookup = {"target_parent": record} if kind == "parent" else {"target_member": record}
    for _attempt in range(2):
        try:
            with transaction.atomic():
                existing = (
                    ChangeRequest.objects.select_for_update().filter(status=ChangeRequest.Status.OPEN, **lookup).first()
                )
                if existing is None:
                    return ChangeRequest.objects.create(requested_by=user, fields=entries, **lookup), True
                existing.fields = entries
                existing.version += 1
                existing.requested_by = user
                existing.save(update_fields=["fields", "version", "requested_by", "updated_at"])
                return existing, False
        except IntegrityError:
            continue  # a parallel submit created the open request first; update it
    raise ChangeRequestError("Der Antrag wurde gerade geändert. Bitte erneut versuchen.", code="conflict", status=409)


def withdraw(change_request):
    with transaction.atomic():
        locked = ChangeRequest.objects.select_for_update().get(pk=change_request.pk)
        if locked.status != ChangeRequest.Status.OPEN:
            raise ChangeRequestError("Der Antrag ist bereits entschieden.", code="decided", status=409)
        locked.status = ChangeRequest.Status.WITHDRAWN
        locked.save(update_fields=["status", "updated_at"])
    return locked


def target_record(change_request):
    return change_request.target_parent if change_request.target_parent_id else change_request.target_member


def payload(change_request, record=None, with_current=False):
    record = record or target_record(change_request)
    kind = change_request.kind
    labels = field_labels(kind)
    current = {}
    if with_current:  # fresh read: a cached target instance may be stale
        current = type(record).objects.filter(pk=record.pk).values(*labels).first() or {}
    rows = []
    for entry in change_request.fields:
        row = {
            "field": entry["field"],
            "label": labels.get(entry["field"], entry["field"]),
            "old": entry["old"],
            "new": entry["new"],
        }
        if "decision" in entry:
            row["decision"] = entry["decision"]
        if with_current:
            row["current"] = current.get(entry["field"]) or ""
            row["conflict"] = row["current"] != entry["old"] and row["current"] != entry["new"]
        rows.append(row)
    return {
        "id": change_request.pk,
        "kind": kind,
        "target_id": record.pk,
        "person_name": record.get_full_name() if kind == "parent" else f"{record.name} {record.lastname}".strip(),
        "status": change_request.status,
        "status_label": change_request.get_status_display(),
        "version": change_request.version,
        "fields": rows,
        "decision_note": change_request.decision_note,
        "created_at": change_request.created_at,
        "updated_at": change_request.updated_at,
        "decided_at": change_request.decided_at,
    }
