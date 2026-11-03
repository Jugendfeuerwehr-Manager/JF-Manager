"""Public submission of an application through a voucher.

Answers are checked against the published form version (not the draft), images are
re-encoded, the voucher is redeemed atomically and the stored application is sealed.
"""

import base64
import binascii
import hashlib
from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from admissions.field_catalog import GENDER_OPTIONS
from admissions.models import Application, ApplicationFile, Seal
from admissions.schema import iter_elements
from admissions.services import seal as seal_service
from admissions.services.vouchers import open_voucher
from jf_manager_backend.upload_safety import clean_avatar, validate_upload

TEXT_LIMITS = {"text": 300, "email": 254, "phone": 50, "textarea": 4000}
# The whole JSON body must stay below DATA_UPLOAD_MAX_MEMORY_SIZE (2.5 MB); the form scales photos down.
MAX_PHOTO_BYTES = 1536 * 1024
MAX_SIGNATURE_BYTES = 512 * 1024
SUBJECT = "admissions.application"


def age_on(birthday, day):
    if birthday is None:
        return None
    return day.year - birthday.year - ((day.month, day.day) < (birthday.month, birthday.day))


def is_visible(rule, answers, age):
    """Same semantics as the frontend: unknown age shows age-bound elements."""
    if not rule:
        return True
    if "age_below" in rule:
        return age is None or age < rule["age_below"]
    return answers.get(rule.get("field")) == rule.get("equals")


def _decode_image(value, *, limit, name):
    """A ``data:image/...;base64,`` string as an upload, or a ValueError with a message."""
    if not isinstance(value, str) or not value.startswith("data:image/"):
        raise ValueError("Bitte ein Bild hinzufügen.")
    header, _, encoded = value.partition(",")
    extension = {"data:image/png;base64": "png", "data:image/jpeg;base64": "jpg"}.get(header)
    if extension is None:
        raise ValueError("Nur JPG oder PNG.")
    if len(encoded) > limit * 4 // 3 + 4:
        raise ValueError("Das Bild ist zu groß.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Das Bild konnte nicht gelesen werden.") from exc
    upload = SimpleUploadedFile(f"{name}.{extension}", raw, content_type=f"image/{extension}")
    try:
        validate_upload(upload, image_only=True)
    except ValidationError as exc:
        raise ValueError("Das Bild konnte nicht gelesen werden.") from exc
    return upload


class _Checker:
    """Walks the published schema once and collects clean answers, files and errors."""

    def __init__(self, schema, raw):
        self.schema = schema
        self.raw = raw if isinstance(raw, dict) else {}
        self.answers = {}
        self.files = {}
        self.errors = {}

    def run(self):
        birthday = self._birthday()
        age = age_on(birthday, timezone.localdate())
        for _, element in iter_elements(self.schema):
            key = element.get("key")
            if not key:
                continue
            if not is_visible(element.get("visible_if"), self.answers, age):
                continue
            try:
                self._check(element, key, self.raw.get(key))
            except ValueError as error:
                self.errors[key] = str(error)
        return self

    def _birthday(self):
        for _, element in iter_elements(self.schema):
            if element.get("target") != "member.birthday":
                continue
            try:
                return date.fromisoformat(str(self.raw.get(element["key"]) or ""))
            except ValueError:
                return None
        return None

    def _missing(self, element, value):
        if element.get("required") and value in (None, "", False, []):
            raise ValueError("Bitte ausfüllen.")

    def _check(self, element, key, value):
        element_type = element["type"]
        if element_type in TEXT_LIMITS or element_type == "date":
            return self._text(element, key, value)
        if element_type in ("select", "radio"):
            return self._choice(element, key, value)
        if element_type in ("checkbox", "legal_ack", "consent"):
            if element.get("required") and value is not True:
                raise ValueError("Bitte bestätigen.")
            self.answers[key] = value is True
            return None
        if element_type == "guardians":
            return self._guardians(element, key, value)
        if element_type in ("photo", "signature"):
            return self._image(element, key, value)
        return None

    def _text(self, element, key, value):
        value = value.strip() if isinstance(value, str) else ""
        self._missing(element, value)
        if not value:
            self.answers[key] = ""
            return
        element_type = element["type"]
        if element_type == "date":
            try:
                day = date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("Bitte ein gültiges Datum angeben.") from exc
            if element.get("target") == "member.birthday" and not date(1900, 1, 1) < day <= timezone.localdate():
                raise ValueError("Bitte ein gültiges Geburtsdatum angeben.")
        if len(value) > TEXT_LIMITS.get(element_type, 300):
            raise ValueError("Der Text ist zu lang.")
        if element_type == "email":
            try:
                validate_email(value)
            except DjangoValidationError as exc:
                raise ValueError("Bitte eine gültige E-Mail-Adresse angeben.") from exc
        self.answers[key] = value

    def _choice(self, element, key, value):
        options = GENDER_OPTIONS if element.get("target") == "member.gender" else element.get("options") or []
        self._missing(element, value)
        if value in (None, ""):
            self.answers[key] = ""
            return
        if value not in {option["value"] for option in options}:
            raise ValueError("Bitte eine der Möglichkeiten wählen.")
        self.answers[key] = value

    def _guardians(self, element, key, value):
        rows = value if isinstance(value, list) else []
        rows = [row for row in rows if isinstance(row, dict) and any(str(v).strip() for v in row.values())]
        if len(rows) < element.get("min", 1):
            raise ValueError(f"Bitte mindestens {element.get('min', 1)} Person(en) angeben.")
        if len(rows) > element.get("max", 2):
            raise ValueError(f"Höchstens {element.get('max', 2)} Personen.")
        clean_rows = []
        for index, row in enumerate(rows, start=1):
            clean = {}
            for field in element.get("fields") or []:
                name = field["target"].removeprefix("guardian.")
                text = str(row.get(name) or "").strip()[:254]
                if field.get("required") and not text:
                    raise ValueError(f"{index}. Person: Bitte alle Pflichtfelder ausfüllen.")
                if text and name.startswith("email"):
                    try:
                        validate_email(text)
                    except DjangoValidationError as exc:
                        raise ValueError(f"{index}. Person: E-Mail-Adresse ungültig.") from exc
                clean[name] = text
            clean_rows.append(clean)
        self.answers[key] = clean_rows

    def _image(self, element, key, value):
        if value in (None, ""):
            self._missing(element, value)
            return
        is_photo = element["type"] == "photo"
        upload = _decode_image(value, limit=MAX_PHOTO_BYTES if is_photo else MAX_SIGNATURE_BYTES, name=key)
        if is_photo:
            upload = clean_avatar(upload)
        self.files[key] = (ApplicationFile.Kind.PHOTO if is_photo else ApplicationFile.Kind.SIGNATURE, upload)
        self.answers[key] = {"file": key}


def _applicant_name(schema, answers):
    targets = {element.get("target"): element.get("key") for _, element in iter_elements(schema)}
    parts = [answers.get(targets.get("member.name")), answers.get(targets.get("member.lastname"))]
    return " ".join(part for part in parts if part).strip()


def submission_content(application):
    """What the submission seal covers; recomputed to verify the application later."""
    return {
        "form_version": application.form_version_id,
        "schema_hash": application.form_version.schema_hash,
        "department": application.department_id,
        "applicant_name": application.applicant_name,
        "answers": application.answers,
        "files": {item.key: item.sha256 for item in application.files.order_by("key")},
        "submitted_at": application.submitted_at.isoformat(),
    }


def form_for_code(code):
    """The voucher and the published version an applicant fills in."""
    voucher = open_voucher(code)
    version = voucher.form.current_version
    if version is None:
        raise ValidationError({"detail": "Das Formular ist nicht verfügbar."})
    return voucher, version


def submit(code, raw_answers):
    """Store, seal and announce an application. Raises ``VoucherError`` or ``ValidationError``."""
    voucher, version = form_for_code(code)
    checked = _Checker(version.schema, raw_answers).run()
    if checked.errors:
        raise ValidationError({"answers": checked.errors})

    with transaction.atomic():
        voucher = open_voucher(code, lock=True)
        current = voucher.form.current_version
        if current is None or current.pk != version.pk:
            raise ValidationError({"detail": "Das Formular wurde gerade geändert. Bitte die Seite neu laden."})
        now = timezone.now()
        application = Application.objects.create(
            form_version=version,
            department_id=voucher.department_id,
            voucher=voucher,
            answers=checked.answers,
            applicant_name=_applicant_name(version.schema, checked.answers) or voucher.label or "Ohne Namen",
            submitted_at=now,
        )
        for key, (kind, upload) in checked.files.items():
            data = upload.read()
            upload.seek(0)
            ApplicationFile.objects.create(
                application=application, key=key, kind=kind, file=upload, sha256=hashlib.sha256(data).hexdigest()
            )
        voucher.used_at = now
        voucher.save(update_fields=["used_at"])
        submission_seal = seal_service.seal(
            subject_type=SUBJECT,
            subject_id=application.pk,
            kind=Seal.Kind.SUBMISSION,
            content=submission_content(application),
        )
        transaction.on_commit(lambda: _announce(application))
    return application, submission_seal


def _announce(application):
    from notifications import inbox
    from notifications.models import InboxItem

    inbox.notify(
        kind="admission_submitted",
        category=InboxItem.Category.REQUESTS,
        item_type=InboxItem.ItemType.TASK,
        title=f"Aufnahmeantrag von {application.applicant_name}",
        department=application.department_id,
        obj=application,
        permission="admissions.view_application",
        link=f"/aufnahme/antraege/{application.pk}",
    )
