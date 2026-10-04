"""
Serializers for the MemberList and MemberListEntry models.
"""

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from departments.models import Department
from members.api_serializers import MemberListSerializer as MemberSerializer
from members.models import Member, MemberList, MemberListEntry


def can_write_list_department(user, department, codename):
    """A model right must apply to the list's actual department."""
    if user.is_superuser:
        return True
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
            "member_count",
            "checked_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "member_count", "checked_count", "created_at", "updated_at"]


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
            "member_count",
            "checked_count",
            "entries",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "member_count", "checked_count", "entries", "created_at", "updated_at"]


class MemberListCreateUpdateSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), required=True, allow_null=False)

    class Meta:
        model = MemberList
        fields = ["id", "name", "description", "color", "department"]

    def validate(self, attrs):
        department = attrs.get("department", getattr(self.instance, "department", None))
        if department is None:
            raise serializers.ValidationError({"department": "Eine Abteilung ist erforderlich."})
        if self.instance is not None and department.pk != self.instance.department_id:
            raise serializers.ValidationError({"department": "Die Listenabteilung kann nicht geändert werden."})
        if self.instance is None and not department.is_active:
            raise serializers.ValidationError({"department": "Die Abteilung ist nicht aktiv."})

        request = self.context.get("request")
        if request is not None:
            if self.instance is not None and (
                self.instance.department_id is None
                or not can_write_list_department(request.user, self.instance.department, "change")
            ):
                raise PermissionDenied("Keine Schreibberechtigung für die bisherige Listenabteilung.")
            codename = "add" if self.instance is None else "change"
            if not can_write_list_department(request.user, department, codename):
                raise PermissionDenied("Keine Schreibberechtigung für die Listenabteilung.")

        return attrs


class CreateFromEventTypeInputSerializer(serializers.Serializer):
    """Input serializer for the create_from_event_type action."""

    name = serializers.CharField(max_length=200)
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.filter(is_active=True))
    description = serializers.CharField(required=False, default="", allow_blank=True)
    event_type_id = serializers.IntegerField(required=False, allow_null=True)
    invert = serializers.BooleanField(default=False)
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)
