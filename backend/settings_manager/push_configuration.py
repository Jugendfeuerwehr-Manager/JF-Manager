import base64
import hmac
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.conf import settings
from django.core.validators import validate_email
from django.db import connection
from rest_framework import serializers

from settings_manager.models import PushConfiguration

PUSH_FIELDS = ("enabled", "public_key", "private_key", "subject")


def encode_key(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def generate_key_pair():
    private = ec.generate_private_key(ec.SECP256R1())
    return {
        "private_key": encode_key(private.private_numbers().private_value.to_bytes(32, "big")),
        "public_key": encode_key(private.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)),
    }


def environment_keys():
    return any(getattr(settings, f"WEB_PUSH_{field.upper()}") for field in ("public_key", "private_key", "subject"))


def effective_push(include_secret=False):
    installed = PushConfiguration._meta.db_table in connection.introspection.table_names()
    config = PushConfiguration.objects.filter(pk=1).first() if installed else None
    locked = environment_keys()
    result = {
        name: getattr(settings, f"WEB_PUSH_{name.upper()}") if locked else getattr(config, name, "")
        for name in ("public_key", "private_key", "subject")
    }
    configured = bool(result["public_key"] and result["private_key"] and result["subject"])
    result["enabled"] = bool(config.enabled if config else configured) and configured
    result["has_private_key"] = bool(result["private_key"])
    result["fields"] = {
        name: {
            "source": "environment" if locked and name != "enabled" else "database" if config else "default",
            "locked": locked and name != "enabled",
            "effective": "next_push_operation",
        }
        for name in PUSH_FIELDS
    }
    if not include_secret:
        result.pop("private_key")
    return result


def validate_push(values):
    if not any(values[name] for name in ("public_key", "private_key", "subject")) and not values["enabled"]:
        return values
    try:
        private_raw = base64.b64decode(
            values["private_key"] + "=" * (-len(values["private_key"]) % 4), altchars=b"-_", validate=True
        )
        public_raw = base64.b64decode(
            values["public_key"] + "=" * (-len(values["public_key"]) % 4), altchars=b"-_", validate=True
        )
        if len(private_raw) != 32 or len(public_raw) != 65:
            raise ValueError
        private = ec.derive_private_key(int.from_bytes(private_raw, "big"), ec.SECP256R1())
        if not hmac.compare_digest(
            private.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint), public_raw
        ):
            raise ValueError
    except (ValueError, TypeError, OverflowError) as exc:
        raise serializers.ValidationError(
            {"public_key": "Ein zusammengehörendes VAPID-P256-Schlüsselpaar ist erforderlich."}
        ) from exc
    subject = values["subject"]
    try:
        if subject.startswith("mailto:"):
            validate_email(subject[7:])
        else:
            parsed = urlsplit(subject)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError
    except Exception as exc:
        raise serializers.ValidationError(
            {"subject": "Bitte mailto:kontakt@example.org oder eine HTTPS-Kontaktadresse verwenden."}
        ) from exc
    return values
