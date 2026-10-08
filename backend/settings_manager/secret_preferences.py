"""Preference secrets are encrypted in both database and preference cache."""

from dynamic_preferences.serializers import BaseSerializer

from jf_manager_backend.encrypted_fields import crypter, decrypt_secret


class EncryptedPreferenceSerializer(BaseSerializer):
    @classmethod
    def to_db(cls, value, **kwargs):
        return crypter().encrypt(str(value or "").encode("utf-8")).decode("ascii")

    @classmethod
    def to_python(cls, value, **kwargs):
        return decrypt_secret(value)
