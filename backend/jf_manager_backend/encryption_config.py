import hashlib

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured


def encryption_keys(environment):
    primary = environment.get("FIELD_ENCRYPTION_KEY", "").strip()
    previous = [
        value.strip() for value in environment.get("FIELD_ENCRYPTION_PREVIOUS_KEYS", "").split(",") if value.strip()
    ]
    if not primary:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY muss explizit gesetzt sein; kein Ersatzschlüssel verfügbar.")
    keys = [primary, *previous]
    try:
        for key in keys:
            Fernet(key.encode("ascii"))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ImproperlyConfigured("Ungültiger Fernet-Schlüssel in der Verschlüsselungskonfiguration.") from exc
    return keys


def cache_key_prefix(keys, base="jf_manager_backend"):
    """Bind cache entries to the primary key: instances with other keys never share encrypted cache values."""
    fingerprint = hashlib.sha256(b"jf-manager-cache-prefix:" + keys[0].encode("ascii")).hexdigest()[:12]
    return f"{base}:{fingerprint}"
