from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

from jf_manager_backend.html_safety import SanitizedHTMLField

User = get_user_model()


def mfa_reset_blocker(user, actor=None):
    """Why the web interface may not reset this account's MFA, or None (SEC-11.4).

    Administrative accounts (superuser, staff, mandatory MFA) are reset only on
    the console, so a hijacked admin session cannot strip another admin's
    second factor. Own factors are managed in the profile.
    """
    from users.mfa_policy import mfa_required

    if actor is not None and actor.pk == user.pk:
        return "self"
    if user.is_superuser or user.is_staff or mfa_required(user):
        return "console_only"
    return None


def mfa_summary(user, actor=None):
    from users import mfa

    totp = mfa.has_totp(user)
    passkeys = user.passkeys.count()
    blocker = mfa_reset_blocker(user, actor)
    return {
        "enabled": totp or passkeys > 0,
        "totp": totp,
        "passkeys": passkeys,
        "ui_reset_allowed": blocker is None,
        "reset_blocker": blocker,
    }


class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)
    model = serializers.CharField(source="content_type.model", read_only=True)
    full_codename = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "app_label", "model", "full_codename"]

    def get_full_codename(self, obj):
        return f"{obj.content_type.app_label}.{obj.codename}"


class AuthGroupListSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()
    permissions_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "user_count", "permissions_count"]

    def get_user_count(self, obj):
        return obj.user_set.count()

    def get_permissions_count(self, obj):
        return obj.permissions.count()


class AuthGroupDetailSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    users = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "permissions", "users"]

    def get_users(self, obj):
        return list(obj.user_set.values_list("id", flat=True))


class AuthGroupWriteSerializer(serializers.ModelSerializer):
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        required=False,
        source="permissions",
    )

    class Meta:
        model = Group
        fields = ["id", "name", "permission_ids"]

    def create(self, validated_data):
        permissions = validated_data.pop("permissions", [])
        group = Group.objects.create(**validated_data)
        if permissions:
            group.permissions.set(permissions)
        return group

    def update(self, instance, validated_data):
        permissions = validated_data.pop("permissions", None)
        instance.name = validated_data.get("name", instance.name)
        instance.save()
        if permissions is not None:
            instance.permissions.set(permissions)
        return instance


class AdminUserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    groups = AuthGroupListSerializer(many=True, read_only=True)
    # Annotated in AdminUserViewSet.get_queryset (no query per row).
    mfa_enabled = serializers.BooleanField(read_only=True, default=False)

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
            "is_superuser",
            "date_joined",
            "last_login",
            "groups",
            "mfa_enabled",
        ]


class AdminUserDetailSerializer(serializers.ModelSerializer):
    email_signature = SanitizedHTMLField(required=False, allow_blank=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    groups = AuthGroupListSerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()
    mfa = serializers.SerializerMethodField()
    phone = serializers.CharField(allow_blank=True, required=False)
    mobile_phone = serializers.CharField(allow_blank=True, required=False)

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
            "dsgvo_internal",
            "dsgvo_external",
            "email_signature",
            "theme_mode",
            "date_joined",
            "last_login",
            "groups",
            "permissions",
            "mfa",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]

    def get_mfa(self, obj):
        request = self.context.get("request")
        return mfa_summary(obj, getattr(request, "user", None))

    def get_permissions(self, obj):
        if obj.is_superuser:
            return ["superuser"]
        user_perms = obj.user_permissions.values_list("codename", flat=True)
        group_perms = Permission.objects.filter(group__user=obj).values_list("codename", flat=True)
        return list(set(list(user_perms) + list(group_perms)))


class AdminUserWriteSerializer(serializers.ModelSerializer):
    email_signature = SanitizedHTMLField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, min_length=8, allow_blank=True)
    group_ids = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        many=True,
        required=False,
        source="groups",
    )
    phone = serializers.CharField(allow_blank=True, required=False)
    mobile_phone = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "mobile_phone",
            "street",
            "zip_code",
            "city",
            "is_staff",
            "is_active",
            "is_superuser",
            "dsgvo_internal",
            "dsgvo_external",
            "email_signature",
            "theme_mode",
            "password",
            "group_ids",
        ]

    def validate_password(self, value):
        if not value:
            return value
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages)) from e
        return value

    def validate(self, data):
        request = self.context.get("request")
        if (
            request
            and self.instance
            and (request.user == self.instance and request.user.is_superuser and data.get("is_superuser") is False)
        ):
            raise serializers.ValidationError(
                {"is_superuser": "Sie koennen Ihre eigene Superuser-Berechtigung nicht entfernen."}
            )
        return data

    def create(self, validated_data):
        groups = validated_data.pop("groups", [])
        password = validated_data.pop("password", None)
        phone = validated_data.pop("phone", "")
        mobile_phone = validated_data.pop("mobile_phone", "")
        user = User(**validated_data)
        if phone:
            user.phone = phone
        if mobile_phone:
            user.mobile_phone = mobile_phone
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        if groups:
            user.groups.set(groups)
        return user

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        password = validated_data.pop("password", None)
        phone = validated_data.pop("phone", None)
        mobile_phone = validated_data.pop("mobile_phone", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if phone is not None:
            instance.phone = phone
        if mobile_phone is not None:
            instance.mobile_phone = mobile_phone
        if password:
            instance.set_password(password)
        instance.save()
        if groups is not None:
            instance.groups.set(groups)
        return instance
