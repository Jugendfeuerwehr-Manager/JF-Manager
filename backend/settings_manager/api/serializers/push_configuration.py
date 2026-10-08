from rest_framework import serializers


class PushConfigurationSerializer(serializers.Serializer):
    enabled = serializers.BooleanField(required=False)
    public_key = serializers.CharField(required=False, allow_blank=True, max_length=512)
    private_key = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=512)
    subject = serializers.CharField(required=False, allow_blank=True, max_length=500)
