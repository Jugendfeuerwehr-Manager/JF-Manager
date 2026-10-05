"""Encrypted fields which fail closed when a stored secret cannot be decrypted."""

import json

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField


def crypter():
    keys = settings.FIELD_ENCRYPTION_KEY
    if isinstance(keys, str):
        keys = [keys]
    return MultiFernet([Fernet(key) for key in keys])


def decrypt_secret(value):
    try:
        return crypter().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeError, AttributeError) as exc:
        raise ImproperlyConfigured("Gespeicherte Zugangsdaten können nicht entschlüsselt werden; Schlüsselring prüfen.") from exc


class StrictEncryptedCharField(EncryptedCharField):
    def from_db_value(self, value, expression, connection):
        return None if value is None else decrypt_secret(value)

    def get_db_prep_save(self, value, connection):
        return None if value is None else crypter().encrypt(str(value).encode("utf-8")).decode("ascii")


class EncryptedJSONField(models.JSONField):
    """Store a Fernet token as a JSON string; expose only decoded dictionaries."""

    def from_db_value(self, value, expression, connection):
        token = super().from_db_value(value, expression, connection)
        if token is None:
            return None
        try:
            decoded = json.loads(decrypt_secret(token))
        except (TypeError, ValueError) as exc:
            raise ImproperlyConfigured("Verschlüsselte Zugangsdaten haben ein ungültiges Format.") from exc
        if not isinstance(decoded, dict):
            raise ImproperlyConfigured("Verschlüsselte Zugangsdaten müssen ein Objekt enthalten.")
        return decoded

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None:
            return super().get_db_prep_value(value, connection, prepared)
        if not isinstance(value, dict):
            raise ValueError("Zugangsdaten müssen ein JSON-Objekt sein.")
        token = crypter().encrypt(json.dumps(value).encode("utf-8")).decode("ascii")
        return super().get_db_prep_value(token, connection, prepared)
