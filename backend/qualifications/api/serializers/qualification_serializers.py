"""
Serializers for Qualification model (list, detail, create, update variants).
"""

from rest_framework import serializers

from members.api_serializers import AttachmentSerializer
from qualifications.models import Qualification

from .qualification_type_serializers import QualificationTypeSerializer


class QualificationListSerializer(serializers.ModelSerializer):
    """Minimal serializer for list views."""

    type_name = serializers.CharField(source="type.name", read_only=True)
    person_name = serializers.CharField(source="get_person_name", read_only=True)
    is_expired = serializers.SerializerMethodField()
    expires_soon = serializers.SerializerMethodField()
    status_class = serializers.CharField(source="get_status_class", read_only=True)

    class Meta:
        model = Qualification
        fields = [
            "id",
            "type",
            "type_name",
            "person_name",
            "date_acquired",
            "date_expires",
            "is_expired",
            "expires_soon",
            "status_class",
            "issued_by",
        ]

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_expires_soon(self, obj):
        return obj.expires_soon()


class QualificationDetailSerializer(serializers.ModelSerializer):
    """Full serializer for single-qualification views."""

    type_name = serializers.CharField(source="type.name", read_only=True)
    type_details = QualificationTypeSerializer(source="type", read_only=True)
    user_name = serializers.SerializerMethodField()
    member_name = serializers.SerializerMethodField()
    person_name = serializers.CharField(source="get_person_name", read_only=True)
    is_expired = serializers.SerializerMethodField()
    expires_soon = serializers.SerializerMethodField()
    status_class = serializers.CharField(source="get_status_class", read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Qualification
        fields = [
            "id",
            "type",
            "type_name",
            "type_details",
            "user",
            "user_name",
            "member",
            "member_name",
            "person_name",
            "date_acquired",
            "date_expires",
            "issued_by",
            "note",
            "is_expired",
            "expires_soon",
            "status_class",
            "attachments",
        ]

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_expires_soon(self, obj):
        return obj.expires_soon()

    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else None

    def get_member_name(self, obj):
        return obj.member.get_full_name() if obj.member else None


class QualificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating qualifications."""

    class Meta:
        model = Qualification
        fields = ["id", "type", "user", "member", "date_acquired", "date_expires", "issued_by", "note"]

    def validate(self, data):
        user = data.get("user")
        member = data.get("member")
        if not user and not member:
            raise serializers.ValidationError("Either user or member must be provided")
        if user and member:
            raise serializers.ValidationError("Only one of user or member can be provided, not both")
        return data


class QualificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating qualifications (allows partial updates)."""

    class Meta:
        model = Qualification
        fields = ["id", "type", "user", "member", "date_acquired", "date_expires", "issued_by", "note"]
        read_only_fields = ["id"]

    def validate(self, data):
        instance = self.instance
        user = data.get("user", instance.user if instance else None)
        member = data.get("member", instance.member if instance else None)

        if "user" in data or "member" in data:
            if not user and not member:
                raise serializers.ValidationError("Either user or member must be provided")
            if user and member:
                raise serializers.ValidationError("Only one of user or member can be provided, not both")
        return data
