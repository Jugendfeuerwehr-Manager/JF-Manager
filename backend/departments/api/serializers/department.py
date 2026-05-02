from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

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

    def create(self, validated_data):
        groups = validated_data.pop("groups", [])
        instance = super().create(validated_data)
        instance.groups.set(groups)
        return instance

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        instance = super().update(instance, validated_data)
        if groups is not None:
            instance.groups.set(groups)
        return instance


class UserDepartmentRoleMiniSerializer(serializers.ModelSerializer):
    """For embedding current user's dept roles in /users/me/ response."""

    department_id = serializers.IntegerField(source="department.id", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    department_code = serializers.CharField(source="department.code", read_only=True)
    department_color = serializers.CharField(source="department.color", read_only=True)
    groups = GroupMiniSerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = UserDepartmentRole
        fields = ["department_id", "department_name", "department_code", "department_color", "groups", "permissions"]

    def get_permissions(self, obj):
        """Return all permission codenames granted by groups in this department role."""
        perms = set()
        for group in obj.groups.all():
            for perm in group.permissions.all():
                perms.add(perm.codename)
        return list(perms)
