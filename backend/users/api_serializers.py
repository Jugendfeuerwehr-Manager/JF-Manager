from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

from departments.api.serializers.department import UserDepartmentRoleMiniSerializer
from departments.models import Department
from jf_manager_backend.html_safety import SanitizedHTMLField
from jf_manager_backend.media_fields import PrivateAvatarField
from jf_manager_backend.private_media import private_media_url

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "content_type"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class UserInfoSerializer(serializers.ModelSerializer):
    avatar = PrivateAvatarField(kind="user-avatar", required=False, allow_null=True)
    """Complete user information including permissions"""

    email_signature = SanitizedHTMLField(required=False, allow_blank=True)
    permissions = serializers.SerializerMethodField()
    qualified_permissions = serializers.SerializerMethodField()
    groups = GroupSerializer(many=True, read_only=True)
    avatar_url = serializers.SerializerMethodField()
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    department_roles = UserDepartmentRoleMiniSerializer(many=True, read_only=True)
    has_org_wide_access = serializers.SerializerMethodField()
    favorite_department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "mobile_phone",
            "street",
            "zip_code",
            "city",
            "is_staff",
            "is_active",
            "is_superuser",
            "date_joined",
            "last_login",
            "avatar",
            "avatar_url",
            "dsgvo_internal",
            "dsgvo_external",
            "email_signature",
            "theme_mode",
            "auth_source",
            "groups",
            "permissions",
            "qualified_permissions",
            "department_roles",
            "has_org_wide_access",
            "favorite_department",
        ]
        read_only_fields = [
            "id",
            "username",
            "date_joined",
            "last_login",
            "is_staff",
            "is_active",
            "is_superuser",
            "groups",
            "permissions",
            "qualified_permissions",
            "department_roles",
            "has_org_wide_access",
            "auth_source",
        ]

    def validate_email(self, value):
        if self.instance and self.instance.auth_source != "local" and value != self.instance.email:
            raise serializers.ValidationError("Die E-Mail-Adresse wird durch den Anmeldedienst verwaltet.")
        return value

    def get_has_org_wide_access(self, obj):
        return obj.is_superuser or obj.has_perm("departments.can_access_all_departments")

    def validate_favorite_department(self, value):
        """Non-org-wide users can only pick one of their assigned departments."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return value

        actor = request.user
        is_org_wide = actor.is_superuser or actor.has_perm("departments.can_access_all_departments")

        # Only org-wide users may store "All Departments" as favorite (null)
        if value is None:
            if not is_org_wide:
                raise serializers.ValidationError("Bitte wählen Sie eine der Ihnen zugewiesenen Abteilungen.")
            return value

        if is_org_wide:
            return value

        allowed_ids = set(actor.department_roles.values_list("department_id", flat=True))
        if value.id not in allowed_ids:
            raise serializers.ValidationError("Sie können nur eine Abteilung auswählen, für die Sie berechtigt sind.")
        return value

    def get_permissions(self, obj):
        """Get all permissions (user + group permissions)"""
        if obj.is_superuser:
            return ["superuser"]

        # Get direct permissions
        user_perms = obj.user_permissions.values_list("codename", flat=True)
        # Get group permissions
        group_perms = Permission.objects.filter(group__user=obj).values_list("codename", flat=True)

        all_perms = set(list(user_perms) + list(group_perms))
        return list(all_perms)

    def get_qualified_permissions(self, obj):
        return sorted(obj.get_all_permissions())

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return private_media_url("user-avatar", obj.pk, request)
        return None


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for lists"""

    full_name = serializers.CharField(source="get_full_name", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_staff",
            "is_active",
            "avatar_url",
        ]
        read_only_fields = ["id", "username"]

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return private_media_url("user-avatar", obj.pk, request)
        return None


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting password reset"""

    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset with token"""

    token = serializers.CharField(required=True)
    uid = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate(self, data):
        """Validate that passwords match and meet requirements"""
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})

        # Validate password strength
        try:
            validate_password(data["new_password"])
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)}) from e

        return data


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing password when logged in"""

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate_old_password(self, value):
        """Check if old password is correct"""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, data):
        """Validate that passwords match and meet requirements"""
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})

        # Validate password strength
        try:
            validate_password(data["new_password"], user=self.context["request"].user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)}) from e

        return data
