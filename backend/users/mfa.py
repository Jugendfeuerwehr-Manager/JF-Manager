"""TOTP (RFC 6238), one-time recovery codes and recent re-authentication.

Implemented with the standard library to avoid an extra dependency. Codes use
SHA-1, six digits and 30-second steps, which every common authenticator app
supports. A code is accepted at most once per user (replay protection).
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode

from django.db import transaction
from django.utils import timezone

from users.models import MFADevice, MFARecoveryCode

TOTP_STEP = 30
TOTP_DIGITS = 6
# Accept one step of clock drift in either direction.
TOTP_WINDOW = 1
RECOVERY_CODE_COUNT = 10
RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
RECOVERY_CODE_LENGTH = 12
REAUTH_KEY = "_reauthenticated_at"
REAUTH_MAX_AGE = 300


def generate_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _key(secret):
    padding = "=" * (-len(secret) % 8)
    return base64.b32decode(secret.upper() + padding)


def totp_at(secret, step):
    digest = hmac.new(_key(secret), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**TOTP_DIGITS).zfill(TOTP_DIGITS)


def current_step(now=None):
    return int((time.time() if now is None else now) // TOTP_STEP)


def provisioning_uri(secret, account, issuer="JF-Manager"):
    label = quote(f"{issuer}:{account}")
    query = urlencode({"secret": secret, "issuer": issuer, "digits": TOTP_DIGITS, "period": TOTP_STEP})
    return f"otpauth://totp/{label}?{query}"


def _normalize_totp(code):
    code = "".join(str(code or "").split())
    return code if code.isdigit() and len(code) == TOTP_DIGITS else None


def verify_totp(device_id, code, *, require_confirmed=True):
    """Accept a fresh code once; returns False for wrong, stale or replayed codes."""
    code = _normalize_totp(code)
    if code is None:
        return False
    with transaction.atomic():
        device = MFADevice.objects.select_for_update().filter(pk=device_id).first()
        if device is None or (require_confirmed and not device.is_confirmed):
            return False
        now_step = current_step()
        for step in range(now_step - TOTP_WINDOW, now_step + TOTP_WINDOW + 1):
            if step <= device.last_used_step:
                continue
            if hmac.compare_digest(totp_at(device.secret, step), code):
                device.last_used_step = step
                device.save(update_fields=["last_used_step"])
                return True
    return False


def _digest(salt, code):
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


def _normalize_recovery(code):
    return "".join(ch for ch in str(code or "").lower() if ch.isalnum())


def issue_recovery_codes(user):
    """Replace all recovery codes; the plain codes are returned exactly once."""
    codes = [
        "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(RECOVERY_CODE_LENGTH))
        for _ in range(RECOVERY_CODE_COUNT)
    ]
    with transaction.atomic():
        MFARecoveryCode.objects.filter(user=user).delete()
        rows = []
        for code in codes:
            salt = secrets.token_hex(16)
            rows.append(MFARecoveryCode(user=user, salt=salt, code_hash=_digest(salt, code)))
        MFARecoveryCode.objects.bulk_create(rows)
    return [f"{code[:4]}-{code[4:8]}-{code[8:]}" for code in codes]


def use_recovery_code(user, code):
    code = _normalize_recovery(code)
    if len(code) != RECOVERY_CODE_LENGTH:
        return False
    with transaction.atomic():
        for row in MFARecoveryCode.objects.select_for_update().filter(user=user, used_at__isnull=True):
            if hmac.compare_digest(row.code_hash, _digest(row.salt, code)):
                row.used_at = timezone.now()
                row.save(update_fields=["used_at"])
                return True
    return False


def has_mfa(user):
    return MFADevice.objects.filter(user=user, confirmed_at__isnull=False).exists()


def verify_second_factor(user, code):
    """Check a TOTP code or, failing that, a recovery code."""
    device = MFADevice.objects.filter(user=user, confirmed_at__isnull=False).first()
    if device is None:
        return False
    if _normalize_totp(code) is not None:
        return verify_totp(device.pk, code)
    return use_recovery_code(user, code)


def mark_reauthenticated(request):
    request.session[REAUTH_KEY] = int(time.time())


def recently_reauthenticated(request):
    stamp = request.session.get(REAUTH_KEY)
    return stamp is not None and 0 <= time.time() - stamp <= REAUTH_MAX_AGE


MFA_VERIFIED_KEY = "_mfa_verified_at"


def mark_mfa_verified(request):
    request.session[MFA_VERIFIED_KEY] = int(time.time())
