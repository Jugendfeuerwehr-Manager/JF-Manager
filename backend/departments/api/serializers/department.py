from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

from departments.assignment_sources import set_local_groups
from departments.models import Department, UserDepartmentRole

User = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "code",
            "color",
            "description",
            "address",
            "phone",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DepartmentMiniSerializer(serializers.ModelSerializer):
    """Minimal representation for embedding in other serializers."""

    class Meta:
        model = Department
        fields = ["id", "name", "code", "color"]


class GroupMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class UserDepartmentRoleSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    groups = GroupMiniSerializer(many=True, read_only=True)
    group_ids = serializers.PrimaryKeyRelatedField(
        source="groups",
        queryset=Group.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = UserDepartmentRole
        fields = [
            "id",
            "user",
            "username",
            "department",
            "groups",
            "group_ids",
        ]
        read_only_fields = ["id", "username", "groups"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["department"] = DepartmentMiniSerializer(instance.department).data
        return data

    def validate(self, attrs):
        user = attrs.get("user", getattr(self.instance, "user", None))
        department = attrs.get("department", getattr(self.instance, "department", None))
        request = self.context.get("request")
        if request and user and user.pk == request.user.pk:
            raise serializers.ValidationError({"user": "Eigene Rollenzuweisungen können nicht geändert werden."})
        if self.instance and (user != self.instance.user or department != self.instance.department):
            raise serializers.ValidationError(
                {"department": "Zuweisungen werden nicht verschoben; neue Zuweisung anlegen."}
            )
        for group in attrs.get("groups", []):
            template = getattr(group, "role_template", None)
            if template and (template.is_archived or template.scope != "department"):
                raise serializers.ValidationError({"group_ids": "Nur aktive Abteilungsvorlagen sind hier zulässig."})
        return attrs

    def create(self, validated_data):
        groups = validated_data.pop("groups", [])
        instance = super().create(validated_data)
        set_local_groups(instance.user, instance.department_id, groups)
        return instance

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        instance = super().update(instance, validated_data)
        if groups is not None:
            set_local_groups(instance.user, instance.department_id, groups)
        return instance


class UserDepartmentRoleMiniSerializer(serializers.ModelSerializer):
    """For embedding current user's dept roles in /users/me/ response."""

    department_id = serializers.IntegerField(source="department.id", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    department_code = serializers.CharField(source="department.code", read_only=True)
    department_color = serializers.CharField(source="department.color", read_only=True)
    groups = GroupMiniSerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()
    qualified_permissions = serializers.SerializerMethodField()

    class Meta:
        model = UserDepartmentRole
        fields = [
            "department_id",
            "department_name",
            "department_code",
            "department_color",
            "groups",
            "permissions",
            "qualified_permissions",
        ]

    def get_qualified_permissions(self, obj):
        return sorted(
            {
                f"{permission.content_type.app_label}.{permission.codename}"
                for group in obj.groups.all()
                for permission in group.permissions.select_related("content_type")
            }
        )

    def get_permissions(self, obj):
        """Return all permission codenames granted by groups in this department role."""
        perms = set()
        for group in obj.groups.all():
            for perm in group.permissions.all():
                perms.add(perm.codename)
        return list(perms)
