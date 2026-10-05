from rest_framework import serializers

from .private_media import private_media_url


class PrivateAvatarField(serializers.ImageField):
    def __init__(self, *args, kind, **kwargs):
        self.kind = kind
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        from .upload_safety import clean_avatar

        return clean_avatar(super().to_internal_value(data))

    def to_representation(self, value):
        if not value:
            return None
        return private_media_url(self.kind, value.instance.pk, self.context.get("request"))
