"""
Serializers for SpecialTask and SpecialTaskType models (list, detail, create, update variants).
"""

import logging

from rest_framework import serializers

from members.api_serializers import AttachmentSerializer
from members.models import Member
from qualifications.models import SpecialTask, SpecialTaskType
from users.models import CustomUser

logger = logging.getLogger(__name__)


class SpecialTaskTypeSerializer(serializers.ModelSerializer):
    """Serializer for SpecialTaskType."""

    class Meta:
        model = SpecialTaskType
        fields = ["id", "name", "description"]


class SpecialTaskListSerializer(serializers.ModelSerializer):
    """Minimal serializer for list views."""

    task_name = serializers.CharField(source="task.name", read_only=True)
    person_name = serializers.CharField(source="get_person_name", read_only=True)
    is_active = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    status_class = serializers.CharField(source="get_status_class", read_only=True)

    class Meta:
        model = SpecialTask
        fields = [
            "id",
            "task",
            "task_name",
            "person_name",
            "start_date",
            "end_date",
            "is_active",
            "duration_days",
            "status_class",
        ]

    def get_is_active(self, obj):
        return obj.is_active()

    def get_duration_days(self, obj):
        return obj.get_duration_days()


class SpecialTaskDetailSerializer(serializers.ModelSerializer):
    """Full serializer for single-task views."""

    task_name = serializers.CharField(source="task.name", read_only=True)
    task_details = SpecialTaskTypeSerializer(source="task", read_only=True)
    user_name = serializers.SerializerMethodField()
    member_name = serializers.SerializerMethodField()
    person_name = serializers.CharField(source="get_person_name", read_only=True)
    is_active = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    status_class = serializers.CharField(source="get_status_class", read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = SpecialTask
        fields = [
            "id",
            "task",
            "task_name",
            "task_details",
            "user",
            "user_name",
            "member",
            "member_name",
            "person_name",
            "start_date",
            "end_date",
            "note",
            "is_active",
            "duration_days",
            "status_class",
            "attachments",
        ]

    def get_is_active(self, obj):
        return obj.is_active()

    def get_duration_days(self, obj):
        return obj.get_duration_days()

    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else None

    def get_member_name(self, obj):
        return obj.member.get_full_name() if obj.member else None


class SpecialTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating special tasks."""

    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False, allow_null=True)
    member = serializers.PrimaryKeyRelatedField(queryset=Member.objects.all(), required=False, allow_null=True)

    class Meta:
        model = SpecialTask
        fields = ["id", "task", "user", "member", "start_date", "end_date", "note"]

    def validate(self, data):
        user = data.get("user")
        member = data.get("member")

        if user is None and member is None:
            raise serializers.ValidationError(
                {"non_field_errors": ["Entweder Benutzer oder Mitglied muss ausgewählt werden."]}
            )
        if user is not None and member is not None:
            raise serializers.ValidationError(
                {"non_field_errors": ["Nur Benutzer oder Mitglied kann ausgewählt werden, nicht beide."]}
            )

        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "Enddatum kann nicht vor Startdatum liegen."})
        return data


class SpecialTaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating special tasks (partial updates, relaxed user/member validation)."""

    task = serializers.PrimaryKeyRelatedField(queryset=SpecialTaskType.objects.all(), required=False)
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False, allow_null=True)
    member = serializers.PrimaryKeyRelatedField(queryset=Member.objects.all(), required=False, allow_null=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = SpecialTask
        fields = ["id", "task", "user", "member", "start_date", "end_date", "note"]
        read_only_fields = ["id"]

    def validate(self, data):
        instance = self.instance
        user = data.get("user", instance.user if instance else None)
        member = data.get("member", instance.member if instance else None)

        if "user" in data or "member" in data:
            if user is None and member is None:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Entweder Benutzer oder Mitglied muss ausgewählt werden."]}
                )
            if user is not None and member is not None:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Nur Benutzer oder Mitglied kann ausgewählt werden, nicht beide."]}
                )

        start_date = data.get("start_date", instance.start_date if instance else None)
        end_date = data.get("end_date", instance.end_date if instance else None)
        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "Enddatum kann nicht vor Startdatum liegen."})
        return data
