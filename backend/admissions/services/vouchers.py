"""One-time voucher codes for application forms.

Codes use Crockford Base32 (no I, L, O, U) in the form ``XXXX-XXXX-XXXX``: easy to read out and
type, 60 bits of randomness. Only the SHA-256 of the normalised code is stored.
"""

import hashlib
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from admissions.models import AdmissionVoucher

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LENGTH = 12
DEFAULT_VALIDITY_DAYS = 60
MAX_VALIDITY_DAYS = 365
PREFILL_KEYS = ("vorname", "nachname")
# Characters people confuse with Crockford digits.
SUBSTITUTIONS = str.maketrans({"O": "0", "I": "1", "L": "1"})


class VoucherError(Exception):
    """Unknown, used, expired or revoked: deliberately indistinguishable for the public."""


def normalize(code):
    return "".join(char for char in (code or "").upper() if char.isalnum()).translate(SUBSTITUTIONS)


def hash_code(code):
    return hashlib.sha256(normalize(code).encode()).hexdigest()


def format_code(raw):
    return "-".join(raw[index : index + 4] for index in range(0, len(raw), 4))


def new_code():
    return format_code("".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH)))


def create_voucher(form, *, label="", prefill=None, valid_days=DEFAULT_VALIDITY_DAYS, by=None):
    """Return ``(voucher, code)``; the code is not stored and cannot be shown again."""
    if not form.is_active:
        raise ValidationError({"form": "Das Formular ist nicht aktiv."})
    if form.current_version is None:
        raise ValidationError({"form": "Das Formular ist noch nicht veröffentlicht."})
    if not 1 <= valid_days <= MAX_VALIDITY_DAYS:
        raise ValidationError({"valid_days": f"Gültigkeit zwischen 1 und {MAX_VALIDITY_DAYS} Tagen."})
    prefill = {key: str(value)[:100] for key, value in (prefill or {}).items() if key in PREFILL_KEYS and value}
    code = new_code()
    voucher = AdmissionVoucher.objects.create(
        form=form,
        department_id=form.department_id,
        code_hash=hash_code(code),
        code_hint=normalize(code)[-4:],
        label=label[:200],
        prefill=prefill,
        expires_at=timezone.now() + timedelta(days=valid_days),
        created_by=by,
    )
    return voucher, code


def open_voucher(code, *, lock=False):
    """The usable voucher for ``code``; raises ``VoucherError`` otherwise."""
    if len(normalize(code)) != CODE_LENGTH:
        raise VoucherError
    queryset = AdmissionVoucher.objects.select_related("form", "department")
    if lock:
        queryset = queryset.select_for_update()
    voucher = queryset.filter(code_hash=hash_code(code)).first()
    if voucher is None or voucher.state != "open":
        raise VoucherError
    return voucher


def revoke(voucher):
    if voucher.used_at:
        raise ValidationError({"detail": "Ein eingelöster Voucher kann nicht widerrufen werden."})
    with transaction.atomic():
        voucher.revoked_at = voucher.revoked_at or timezone.now()
        voucher.save(update_fields=["revoked_at"])
    return voucher
