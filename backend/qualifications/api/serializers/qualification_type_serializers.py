"""
Serializers for QualificationType model.
"""

from rest_framework import serializers

from qualifications.models import QualificationType


class QualificationTypeSerializer(serializers.ModelSerializer):
    """Full serializer for QualificationType."""

    class Meta:
        model = QualificationType
        fields = ["id", "name", "expires", "validity_period", "description"]


class QualificationTypeListSerializer(serializers.ModelSerializer):
    """Minimal serializer for dropdown/list views."""

    class Meta:
        model = QualificationType
        fields = ["id", "name", "expires"]
