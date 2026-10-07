"""Passkeys (WebAuthn) as second factor next to TOTP (SEC-11).

The relying party is the public address of the web interface (FRONTEND_URL),
because the browser checks the origin of the page that calls WebAuthn.
Challenges live in the server-side session, are single-use and expire after
five minutes. No attestation is requested: it would identify the device
model and is not needed to bind a key to an account.
"""

import time
from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorTransport,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from users.models import PasskeyCredential

CHALLENGE_TTL = 300
REGISTRATION_KEY = "_passkey_registration"
AUTHENTICATION_KEY = "_passkey_authentication"
RP_NAME = "JF-Manager"


class PasskeyError(Exception):
    """Verification failed; the message is safe to show."""


def rp_id():
    configured = getattr(settings, "WEBAUTHN_RP_ID", "")
    return configured or (urlsplit(settings.FRONTEND_URL).hostname or "localhost")


def expected_origins():
    configured = getattr(settings, "WEBAUTHN_ORIGINS", [])
    if configured:
        return list(configured)
    parts = urlsplit(settings.FRONTEND_URL)
    return [f"{parts.scheme}://{parts.netloc}"]


def _descriptors(user):
    descriptors = []
    for credential in PasskeyCredential.objects.filter(user=user):
        transports = []
        for value in credential.transports or []:
            try:
                transports.append(AuthenticatorTransport(value))
            except ValueError:
                continue
        descriptors.append(
            PublicKeyCredentialDescriptor(id=bytes(credential.credential_id), transports=transports or None)
        )
    return descriptors


def _store_challenge(session, key, challenge, user_id):
    session[key] = {"challenge": bytes_to_base64url(challenge), "user_id": user_id, "issued_at": int(time.time())}


def _take_challenge(session, key, user_id):
    """Single use: the stored challenge is removed whatever the outcome."""
    data = session.pop(key, None)
    if not data or data.get("user_id") != user_id or time.time() - data.get("issued_at", 0) > CHALLENGE_TTL:
        raise PasskeyError("Die Passkey-Anfrage ist abgelaufen. Bitte erneut versuchen.")
    return base64url_to_bytes(data["challenge"])


def registration_options(session, user):
    """Options JSON for navigator.credentials.create()."""
    options = generate_registration_options(
        rp_id=rp_id(),
        rp_name=RP_NAME,
        user_id=f"jf-user-{user.pk}".encode(),
        user_name=user.get_username(),
        user_display_name=user.get_full_name() or user.get_username(),
        exclude_credentials=_descriptors(user),
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        timeout=CHALLENGE_TTL * 1000,
    )
    _store_challenge(session, REGISTRATION_KEY, options.challenge, user.pk)
    return options_to_json(options)


def register(session, user, credential, name):
    """Verify the browser response and store the new credential."""
    challenge = _take_challenge(session, REGISTRATION_KEY, user.pk)
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=challenge,
            expected_rp_id=rp_id(),
            expected_origin=expected_origins(),
        )
    except (InvalidRegistrationResponse, ValueError, KeyError, TypeError) as exc:
        raise PasskeyError("Der Passkey konnte nicht bestätigt werden.") from exc
    transports = credential.get("response", {}).get("transports", []) if isinstance(credential, dict) else []
    with transaction.atomic():
        if PasskeyCredential.objects.select_for_update().filter(user=user).count() >= PasskeyCredential.MAX_PER_USER:
            raise PasskeyError(f"Es sind höchstens {PasskeyCredential.MAX_PER_USER} Passkeys möglich.")
        if PasskeyCredential.objects.filter(credential_id=verified.credential_id).exists():
            raise PasskeyError("Dieser Passkey ist bereits registriert.")
        return PasskeyCredential.objects.create(
            user=user,
            name=(name or "").strip()[:64] or "Passkey",
            credential_id=verified.credential_id,
            public_key=verified.credential_public_key,
            sign_count=verified.sign_count,
            transports=[t for t in transports if isinstance(t, str)][:8],
            backed_up=bool(verified.credential_backed_up),
        )


def authentication_options(session, user):
    """Options JSON for navigator.credentials.get(); None without passkeys."""
    descriptors = _descriptors(user)
    if not descriptors:
        return None
    options = generate_authentication_options(
        rp_id=rp_id(),
        allow_credentials=descriptors,
        user_verification=UserVerificationRequirement.PREFERRED,
        timeout=CHALLENGE_TTL * 1000,
    )
    _store_challenge(session, AUTHENTICATION_KEY, options.challenge, user.pk)
    return options_to_json(options)


def authenticate(session, user, credential):
    """Verify an assertion for ``user``; raises PasskeyError on any mismatch."""
    challenge = _take_challenge(session, AUTHENTICATION_KEY, user.pk)
    try:
        raw_id = base64url_to_bytes(credential["rawId"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PasskeyError("Der Passkey konnte nicht bestätigt werden.") from exc
    with transaction.atomic():
        stored = PasskeyCredential.objects.select_for_update().filter(user=user, credential_id=raw_id).first()
        if stored is None:
            raise PasskeyError("Dieser Passkey gehört nicht zu diesem Konto.")
        try:
            verified = verify_authentication_response(
                credential=credential,
                expected_challenge=challenge,
                expected_rp_id=rp_id(),
                expected_origin=expected_origins(),
                credential_public_key=bytes(stored.public_key),
                credential_current_sign_count=stored.sign_count,
            )
        except (InvalidAuthenticationResponse, ValueError, KeyError, TypeError) as exc:
            # Includes a signature counter that did not increase (cloned key).
            raise PasskeyError("Der Passkey konnte nicht bestätigt werden.") from exc
        stored.sign_count = verified.new_sign_count
        stored.backed_up = bool(verified.credential_backed_up)
        stored.last_used_at = timezone.now()
        stored.save(update_fields=["sign_count", "backed_up", "last_used_at"])
    return stored


def serialize(credential):
    return {
        "id": credential.pk,
        "name": credential.name,
        "created_at": credential.created_at,
        "last_used_at": credential.last_used_at,
        "backed_up": credential.backed_up,
    }
