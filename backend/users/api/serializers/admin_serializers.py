from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

User = get_user_model()


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

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "full_name",
            "is_staff", "is_active", "is_superuser",
            "date_joined", "last_login", "groups",
        ]


class AdminUserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    groups = AuthGroupListSerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()
    phone = serializers.CharField(allow_blank=True, required=False)
    mobile_phone = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "full_name",
            "phone", "mobile_phone", "street", "zip_code", "city",
            "is_staff", "is_active", "is_superuser",
            "dsgvo_internal", "dsgvo_external",
            "email_signature", "theme_mode",
            "date_joined", "last_login",
            "groups", "permissions",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]

    def get_permissions(self, obj):
        if obj.is_superuser:
            return ["superuser"]
        user_perms = obj.user_permissions.values_list("codename", flat=True)
        group_perms = Permission.objects.filter(group__user=obj).values_list("codename", flat=True)
        return list(set(list(user_perms) + list(group_perms)))


class AdminUserWriteSerializer(serializers.ModelSerializer):
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
            "id", "username", "email", "first_name", "last_name",
            "phone", "mobile_phone", "street", "zip_code", "city",
            "is_staff", "is_active", "is_superuser",
            "dsgvo_internal", "dsgvo_external",
            "email_signature", "theme_mode",
            "password", "group_ids",
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
        if request and self.instance and (request.user == self.instance
                and request.user.is_superuser
                and data.get("is_superuser") is False):
            raise serializers.ValidationError({
                "is_superuser": "Sie koennen Ihre eigene Superuser-Berechtigung nicht entfernen."
            })
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
