"""Server seals: a canonical SHA-256 of the content, signed with the installation's Ed25519 key.

A seal proves that a record has not changed since it was sealed. Seals of the same subject
are chained through ``prev_hash`` so a removed or reordered seal is noticed as well.
"""

import base64
import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from admissions.models import Seal


def canonical(payload):
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _private_key():
    configured = settings.ADMISSIONS_SEAL_KEY
    if configured:
        raw = base64.b64decode(configured)
        if len(raw) != 32:
            raise ImproperlyConfigured("ADMISSIONS_SEAL_KEY muss 32 Bytes (Base64) enthalten.")
        return Ed25519PrivateKey.from_private_bytes(raw)
    if not settings.SECRET_KEY:
        raise ImproperlyConfigured("Für Siegel wird ADMISSIONS_SEAL_KEY oder DJANGO_SECRET_KEY benötigt.")
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"jf-manager-admissions", info=b"seal-v1").derive(
        settings.SECRET_KEY.encode("utf-8")
    )
    return Ed25519PrivateKey.from_private_bytes(derived)


def _public_bytes(public_key):
    return public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def current_public_key():
    """Base64 of the public key that verifies new seals."""
    return base64.b64encode(_public_bytes(_private_key().public_key())).decode()


def _key_id(public_b64):
    return sha256(public_b64.encode())[:16]


def _seal_payload(*, subject_type, subject_id, kind, content_hash, prev_hash, created_at):
    return {
        "subject": f"{subject_type}:{subject_id}",
        "kind": kind,
        "content": content_hash,
        "prev": prev_hash,
        "at": created_at.isoformat(),
    }


def chain(subject_type, subject_id):
    return Seal.objects.filter(subject_type=subject_type, subject_id=subject_id).order_by("created_at", "pk")


def seal(*, subject_type, subject_id, kind, content):
    """Seal ``content`` (any JSON-able data) for a subject and append it to its chain."""
    previous = chain(subject_type, subject_id).last()
    prev_hash = previous.seal_hash if previous else ""
    created_at = timezone.now()
    content_hash = sha256(canonical(content))
    payload = canonical(
        _seal_payload(
            subject_type=subject_type,
            subject_id=subject_id,
            kind=kind,
            content_hash=content_hash,
            prev_hash=prev_hash,
            created_at=created_at,
        )
    )
    private_key = _private_key()
    public_b64 = base64.b64encode(_public_bytes(private_key.public_key())).decode()
    return Seal.objects.create(
        subject_type=subject_type,
        subject_id=subject_id,
        kind=kind,
        content_hash=content_hash,
        prev_hash=prev_hash,
        seal_hash=sha256(payload),
        signature=base64.b64encode(private_key.sign(payload)).decode(),
        public_key=public_b64,
        key_id=_key_id(public_b64),
        created_at=created_at,
    )


def verify_signature(stored):
    """Whether the seal row itself is intact and signed by the stored key."""
    payload = canonical(
        _seal_payload(
            subject_type=stored.subject_type,
            subject_id=stored.subject_id,
            kind=stored.kind,
            content_hash=stored.content_hash,
            prev_hash=stored.prev_hash,
            created_at=stored.created_at,
        )
    )
    if sha256(payload) != stored.seal_hash:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(stored.public_key)).verify(
            base64.b64decode(stored.signature), payload
        )
    except (InvalidSignature, ValueError):
        return False
    return True


def verify(stored, content=None):
    """Check one seal; with ``content`` also that the record still matches it.

    Returns a dict with ``valid`` and the individual findings for the UI.
    """
    signature_ok = verify_signature(stored)
    content_ok = content is None or sha256(canonical(content)) == stored.content_hash
    previous = chain(stored.subject_type, stored.subject_id).filter(created_at__lt=stored.created_at).last()
    chain_ok = stored.prev_hash == (previous.seal_hash if previous else "")
    trusted_key = stored.public_key == current_public_key()
    return {
        "valid": signature_ok and content_ok and chain_ok,
        "signature": signature_ok,
        "content": content_ok,
        "chain": chain_ok,
        "current_key": trusted_key,
        "kind": stored.kind,
        "sealed_at": stored.created_at,
        "public_id": stored.public_id,
        "seal_hash": stored.seal_hash,
    }
