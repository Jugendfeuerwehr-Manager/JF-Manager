"""
Email Layout Template Serializers
"""

from rest_framework import serializers


class EmailLayoutTemplateSerializer(serializers.Serializer):
    """Serializer for a single email layout template (DB record or default)"""

    layout_type = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    html_content = serializers.CharField()
    is_custom = serializers.BooleanField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True, allow_null=True)


class EmailLayoutTemplateUpdateSerializer(serializers.Serializer):
    """Serializer for updating an email layout template"""

    html_content = serializers.CharField()
