"""
Serializers for the MemberList and MemberListEntry models.
"""

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from departments.models import Department
from members.api_serializers import MemberListSerializer as MemberSerializer
from members.models import Member, MemberList, MemberListEntry


def can_write_list_department(user, department, codename):
    """A model right must apply to the list's actual department.

    ``department=None`` stands for an organization-wide list, which needs the
    organization-wide scope together with the global model right.
    """
    if user.is_superuser:
        return True
    if department is None:
        return user.has_perm("departments.can_access_all_departments") and user.has_perm(
            f"members.{codename}_memberlist"
        )
    if (
        not user.has_perm("departments.can_access_all_departments")
        and not user.department_roles.filter(department=department).exists()
    ):
        return False
    permission = f"members.{codename}_memberlist"
    if user.has_perm(permission):
        return True
    return user.department_roles.filter(
        department=department,
        groups__permissions__content_type__app_label="members",
        groups__permissions__codename=f"{codename}_memberlist",
    ).exists()


class MemberListEntrySerializer(serializers.ModelSerializer):
    """Entry in a list — includes nested member data for display."""

    member = MemberSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        source="member",
        queryset=Member.objects.all(),
        write_only=True,
    )

    class Meta:
        model = MemberListEntry
        fields = ["id", "member", "member_id", "checked", "checked_at", "notes", "added_at"]
        read_only_fields = ["id", "member", "checked_at", "added_at"]

    def validate(self, attrs):
        member = attrs.get("member", getattr(self.instance, "member", None))
        member_list = attrs.get("member_list", getattr(self.instance, "member_list", None))
        if (
            member_list is not None
            and member is not None
            and not member_list.organization_wide
            and (
                member_list.department_id is None
                or not member.departments.filter(pk=member_list.department_id).exists()
            )
        ):
            raise serializers.ValidationError({"member_id": "Das Mitglied muss zur Listenabteilung gehören."})
        return attrs


class MemberListSerializer(serializers.ModelSerializer):
    """Lightweight list representation for overview grids."""

    member_count = serializers.IntegerField(read_only=True)
    checked_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MemberList
        fields = [
            "id",
            "name",
            "description",
            "color",
            "department",
            "organization_wide",
            "member_count",
            "checked_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization_wide", "member_count", "checked_count", "created_at", "updated_at"]


class MemberListDetailSerializer(serializers.ModelSerializer):
    """Full list with all entries (members)."""

    entries = MemberListEntrySerializer(many=True, read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    checked_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MemberList
        fields = [
            "id",
            "name",
            "description",
            "color",
            "department",
            "organization_wide",
            "member_count",
            "checked_count",
            "entries",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_wide",
            "member_count",
            "checked_count",
            "entries",
            "created_at",
            "updated_at",
        ]


class MemberListCreateUpdateSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), required=True, allow_null=True)

    class Meta:
        model = MemberList
        fields = ["id", "name", "description", "color", "department", "organization_wide"]
        read_only_fields = ["id", "organization_wide"]

    def validate(self, attrs):
        department = attrs.get("department", getattr(self.instance, "department", None))
        if self.instance is None:
            if department is None:
                validate_organization_wide_target()
            elif not department.is_active:
                raise serializers.ValidationError({"department": "Die Abteilung ist nicht aktiv."})
        elif self.instance.is_unresolved_legacy or department != self.instance.department:
            raise serializers.ValidationError({"department": "Die Listenabteilung kann nicht geändert werden."})

        request = self.context.get("request")
        if request is not None:
            if self.instance is not None and not can_write_list_department(
                request.user, self.instance.department, "change"
            ):
                raise PermissionDenied("Keine Schreibberechtigung für die bisherige Listenabteilung.")
            codename = "add" if self.instance is None else "change"
            if not can_write_list_department(request.user, department, codename):
                raise PermissionDenied("Keine Schreibberechtigung für die Listenabteilung.")

        return attrs

    def create(self, validated_data):
        validated_data["organization_wide"] = validated_data.get("department") is None
        return super().create(validated_data)


def validate_organization_wide_target():
    """Lists without a department are only allowed while no active department exists."""
    if Department.objects.filter(is_active=True).exists():
        raise serializers.ValidationError({"department": "Eine Abteilung ist erforderlich."})


class CreateFromEventTypeInputSerializer(serializers.Serializer):
    """Input serializer for the create_from_event_type action."""

    name = serializers.CharField(max_length=200)
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.filter(is_active=True), allow_null=True)
    description = serializers.CharField(required=False, default="", allow_blank=True)
    event_type_id = serializers.IntegerField(required=False, allow_null=True)
    invert = serializers.BooleanField(default=False)
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)


class ResolveLegacyListInputSerializer(serializers.Serializer):
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.filter(is_active=True))
    entry_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
    attachment_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
    target_list_id = serializers.IntegerField(min_value=1, required=False)
    assign_description = serializers.BooleanField(required=False, default=False)
    complete = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        for key in ("entry_ids", "attachment_ids"):
            values = attrs.get(key, [])
            if len(values) != len(set(values)):
                raise serializers.ValidationError({key: "IDs dürfen nicht doppelt vorkommen."})
        return attrs


class LegacyListEntryInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    member_id = serializers.IntegerField()
    member_name = serializers.CharField()
    department_ids = serializers.ListField(child=serializers.IntegerField())
    checked = serializers.BooleanField()
    checked_at = serializers.DateTimeField(allow_null=True)
    notes = serializers.CharField(allow_blank=True)
    added_at = serializers.DateTimeField()


class LegacyListAttachmentInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    file_size = serializers.IntegerField()
    mime_type = serializers.CharField()


class LegacyListTargetInfoSerializer(serializers.Serializer):
    department = serializers.IntegerField()
    list_id = serializers.IntegerField()


class LegacyListPendingSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    entries = LegacyListEntryInfoSerializer(many=True)
    attachments = LegacyListAttachmentInfoSerializer(many=True)
    targets = LegacyListTargetInfoSerializer(many=True)


class LegacyListResolutionResultSerializer(serializers.Serializer):
    target_list_id = serializers.IntegerField()
    complete = serializers.BooleanField()
    pending = LegacyListPendingSerializer(allow_null=True)
