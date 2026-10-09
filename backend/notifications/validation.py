import base64
from urllib.parse import urlsplit

from django.conf import settings
from rest_framework import serializers


def validate_endpoint(value):
    try:
        url = urlsplit(value)
        allowed = any(url.hostname == host or url.hostname.endswith("." + host)
                      for host in settings.WEB_PUSH_ALLOWED_HOSTS)
        if url.scheme != "https" or not allowed or url.port not in (None, 443) or url.username or url.password or url.fragment:
            raise ValueError
    except (ValueError, AttributeError) as exc:
        raise serializers.ValidationError("Kein unterstützter HTTPS-Push-Dienst.") from exc
    return value


class SubscriptionSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2048, validators=[validate_endpoint])
    keys = serializers.DictField(child=serializers.CharField(max_length=200))
    services = serializers.BooleanField(default=True)
    orders = serializers.BooleanField(default=True)
    requests = serializers.BooleanField(default=True)
    participation = serializers.BooleanField(default=True)

    def validate_keys(self, value):
        for name, length in (("p256dh", 65), ("auth", 16)):
            try:
                encoded = value[name]
                decoded = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
                if len(decoded) != length or (name == "p256dh" and decoded[0] != 4):
                    raise ValueError
            except (KeyError, ValueError) as exc:
                raise serializers.ValidationError("Ungültige Push-Schlüssel.") from exc
        return value
