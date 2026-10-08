"""
Serializers for Settings API
"""

from django.contrib.auth.models import Group as AuthGroup
from rest_framework import serializers

from settings_manager.models import LDAPDepartmentRoleMapping, OIDCGroupMapping

from .email_template import (
    EmailTemplateCreateUpdateSerializer,
    EmailTemplateDetailSerializer,
    EmailTemplateListSerializer,
    EmailTemplatePreviewResponseSerializer,
    EmailTemplatePreviewSerializer,
)


class GeneralSettingsSerializer(serializers.Serializer):
    """Serializer for general settings"""

    title = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="Website title displayed in browser tab and login page",
    )
    slug = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Short organisation identifier shown on the login page",
    )
    logo_url = serializers.URLField(
        required=False, allow_blank=True, help_text="Publicly accessible URL to the organisation logo"
    )
    brand_color = serializers.RegexField(
        r"^#[0-9a-fA-F]{6}$",
        required=False,
        help_text="Base colour of the interface as #rrggbb; accessible shades are derived in the browser",
        error_messages={"invalid": "Bitte eine Farbe im Format #rrggbb angeben."},
    )

    def validate_brand_color(self, value):
        return value.lower()


class EmailSettingsSerializer(serializers.Serializer):
    """Serializer for email settings"""

    email_host = serializers.CharField(
        max_length=200, required=False, allow_blank=True, help_text="SMTP server hostname or IP address"
    )
    email_port = serializers.IntegerField(
        required=False, min_value=1, max_value=65535, help_text="SMTP server port (e.g., 587 for TLS, 465 for SSL)"
    )
    email_use_tls = serializers.BooleanField(required=False, help_text="Use TLS encryption for email connection")
    email_use_ssl = serializers.BooleanField(
        required=False, help_text="Use SSL encryption for email connection (not together with TLS)"
    )
    email_host_user = serializers.CharField(
        max_length=200, required=False, allow_blank=True, help_text="Username for SMTP authentication"
    )
    email_host_password = serializers.CharField(
        required=False, allow_blank=True, write_only=True, help_text="Password for SMTP authentication"
    )
    has_email_host_password = serializers.BooleanField(read_only=True)
    email_credentials_unavailable = serializers.BooleanField(read_only=True)
    default_from_email = serializers.EmailField(
        required=False, allow_blank=True, help_text="Email address used as sender"
    )

    def validate(self, data):
        """Validate that TLS and SSL are not both enabled"""
        if data.get("email_use_tls") and data.get("email_use_ssl"):
            raise serializers.ValidationError("TLS and SSL cannot be enabled at the same time")
        return data


class MemberSettingsSerializer(serializers.Serializer):
    """Serializer for member settings"""

    alert_threshold = serializers.IntegerField(
        required=False, min_value=1, help_text="Threshold for absence alert (number of absences)"
    )
    alert_threshold_last_entries = serializers.IntegerField(
        required=False, min_value=1, help_text="Number of recent services to check for absences"
    )


class ServiceSettingsSerializer(serializers.Serializer):
    """Serializer for service settings"""

    service_start_time = serializers.TimeField(required=False, help_text="Default start time for new services")
    service_end_time = serializers.TimeField(required=False, help_text="Default end time for new services")

    def validate(self, data):
        """Validate that start time is before end time"""
        start_time = data.get("service_start_time")
        end_time = data.get("service_end_time")

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("Start time must be before end time")
        return data


class TrainingSettingsSerializer(serializers.Serializer):
    training_start_time = serializers.TimeField(required=False)
    training_end_time = serializers.TimeField(required=False)
    default_block_duration_minutes = serializers.IntegerField(required=False, min_value=1, max_value=480)

    def validate(self, data):
        if data["training_start_time"] >= data["training_end_time"]:
            raise serializers.ValidationError({"training_end_time": "Das Ende muss nach dem Beginn liegen."})
        return data


class VocabularySettingsSerializer(serializers.Serializer):
    member_label = serializers.CharField(required=False, max_length=80)
    service_label = serializers.CharField(required=False, max_length=80)
    training_label = serializers.CharField(required=False, max_length=80)


def _login_text(max_length, help_text, multiline=False):
    style = {"base_template": "textarea.html", "rows": 3} if multiline else {}
    return serializers.CharField(
        required=False, allow_blank=True, max_length=max_length, help_text=help_text, style=style
    )


class LoginPageSettingsSerializer(serializers.Serializer):
    """Public texts of the login page; plain text, rendered escaped, empty hides the text."""

    login_eyebrow = _login_text(80, "Kleine Zeile über der Überschrift. Leer blendet sie aus.")
    login_headline = _login_text(120, "Große Überschrift; Zeilenumbrüche bleiben erhalten.", multiline=True)
    login_intro = _login_text(400, "Einleitender Text unter der Überschrift.", multiline=True)
    login_footer = _login_text(120, "Zeile am unteren Rand der Begrüßungsfläche.")
    login_help = _login_text(
        300, "Hinweis unter dem Anmeldeformular, etwa wen man um einen Zugang bittet.", multiline=True
    )

    def validate(self, data):
        # Windows line breaks from pasted text; keep the stored value canonical.
        return {name: value.replace("\r\n", "\n").strip() for name, value in data.items()}


class OrderSettingsSerializer(serializers.Serializer):
    """Serializer for order settings"""

    equipment_manager_email = serializers.EmailField(
        required=False, allow_blank=True, help_text="Equipment manager email address for order notifications"
    )


class LDAPSettingsSerializer(serializers.Serializer):
    """Serializer for LDAP authentication settings"""

    enabled = serializers.BooleanField(required=False)
    server_uri = serializers.CharField(required=False, allow_blank=True, max_length=255)
    start_tls = serializers.BooleanField(required=False)
    ca_cert_file = serializers.CharField(required=False, allow_blank=True, max_length=512)
    ca_cert_content = serializers.CharField(required=False, allow_blank=True)
    disable_cert_validation = serializers.BooleanField(required=False)
    bind_dn = serializers.CharField(required=False, allow_blank=True, max_length=255)
    bind_password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    has_bind_password = serializers.BooleanField(required=False, read_only=True)
    user_search_base_dn = serializers.CharField(required=False, allow_blank=True, max_length=255)
    user_search_filter = serializers.CharField(required=False, allow_blank=True, max_length=255)
    group_search_base_dn = serializers.CharField(required=False, allow_blank=True, max_length=255)
    group_search_filter = serializers.CharField(required=False, allow_blank=True, max_length=255)
    group_type = serializers.ChoiceField(
        required=False,
        choices=["group_of_names", "active_directory"],
    )
    mirror_groups = serializers.BooleanField(required=False)
    require_group = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs):
        if attrs.get("ca_cert_file") and attrs.get("ca_cert_content"):
            raise serializers.ValidationError(
                {
                    "ca_cert_file": "Bitte entweder Dateipfad oder Zertifikatsinhalt verwenden, nicht beides.",
                    "ca_cert_content": "Bitte entweder Dateipfad oder Zertifikatsinhalt verwenden, nicht beides.",
                }
            )
        return attrs


class LDAPConnectionTestSerializer(serializers.Serializer):
    """Serializer for LDAP connection test results"""

    ok = serializers.BooleanField()
    detail = serializers.CharField()


class AuthGroupMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthGroup
        fields = ["id", "name"]


class RoleMappingValidation:
    def validate(self, attrs):
        from departments.assignment_sources import valid_mapping_group

        department = attrs.get("department", getattr(self.instance, "department", None))
        groups = attrs.get("auth_groups", self.instance.auth_groups.all() if self.instance else [])
        if not groups or any(not valid_mapping_group(group, getattr(department, "pk", None)) for group in groups):
            raise serializers.ValidationError(
                {"auth_group_ids": "Aktive Rollenvorlagen des gewählten Bereichs sind erforderlich."}
            )
        return attrs


class LDAPDepartmentRoleMappingSerializer(RoleMappingValidation, serializers.ModelSerializer):
    """Serializer for LDAP group → Department role mappings"""

    department_name = serializers.CharField(source="department.name", read_only=True)
    auth_groups = AuthGroupMiniSerializer(many=True, read_only=True)
    auth_group_ids = serializers.PrimaryKeyRelatedField(
        source="auth_groups",
        queryset=AuthGroup.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = LDAPDepartmentRoleMapping
        fields = [
            "id",
            "ldap_group_dn",
            "department",
            "department_name",
            "auth_groups",
            "auth_group_ids",
            "revoke_on_mismatch",
        ]
        read_only_fields = ["id", "department_name", "auth_groups"]

    def create(self, validated_data):
        auth_groups = validated_data.pop("auth_groups", [])
        instance = super().create(validated_data)
        instance.auth_groups.set(auth_groups)
        return instance

    def update(self, instance, validated_data):
        auth_groups = validated_data.pop("auth_groups", None)
        instance = super().update(instance, validated_data)
        if auth_groups is not None:
            instance.auth_groups.set(auth_groups)
        return instance


class OIDCSettingsSerializer(serializers.Serializer):
    """Serializer for OIDC authentication settings"""

    enabled = serializers.BooleanField(required=False)
    provider_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    issuer_url = serializers.CharField(required=False, allow_blank=True, max_length=500)
    client_id = serializers.CharField(required=False, allow_blank=True, max_length=255)
    client_secret = serializers.CharField(required=False, allow_blank=True, write_only=True)
    has_client_secret = serializers.BooleanField(required=False, read_only=True)
    callback_url = serializers.CharField(required=False, read_only=True)
    scope = serializers.CharField(required=False, allow_blank=True, max_length=255)
    groups_claim = serializers.CharField(required=False, allow_blank=True, max_length=100)
    staff_group = serializers.CharField(required=False, allow_blank=True, max_length=255)
    admin_group = serializers.CharField(required=False, allow_blank=True, max_length=255)
    require_group_mapping = serializers.BooleanField(required=False)
    hide_local_login = serializers.BooleanField(required=False)
    trust_provider_mfa = serializers.BooleanField(required=False)


class OIDCDiscoveryResultSerializer(serializers.Serializer):
    """Serializer for OIDC discovery test results"""

    ok = serializers.BooleanField()
    detail = serializers.CharField(required=False, allow_blank=True)
    issuer = serializers.CharField(required=False, allow_blank=True)
    authorization_endpoint = serializers.CharField(required=False, allow_blank=True)
    token_endpoint = serializers.CharField(required=False, allow_blank=True)
    userinfo_endpoint = serializers.CharField(required=False, allow_blank=True)
    jwks_uri = serializers.CharField(required=False, allow_blank=True)
    scopes_supported = serializers.ListField(child=serializers.CharField(), required=False)
    claims_supported = serializers.ListField(child=serializers.CharField(), required=False)


class OIDCGroupMappingSerializer(RoleMappingValidation, serializers.ModelSerializer):
    """Serializer for OIDC group → Department role mappings"""

    department_name = serializers.CharField(source="department.name", read_only=True)
    auth_groups = AuthGroupMiniSerializer(many=True, read_only=True)
    auth_group_ids = serializers.PrimaryKeyRelatedField(
        source="auth_groups",
        queryset=AuthGroup.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = OIDCGroupMapping
        fields = [
            "id",
            "group_claim_value",
            "department",
            "department_name",
            "auth_groups",
            "auth_group_ids",
            "revoke_on_mismatch",
        ]
        read_only_fields = ["id", "department_name", "auth_groups"]

    def create(self, validated_data):
        auth_groups = validated_data.pop("auth_groups", [])
        instance = super().create(validated_data)
        instance.auth_groups.set(auth_groups)
        return instance

    def update(self, instance, validated_data):
        auth_groups = validated_data.pop("auth_groups", None)
        instance = super().update(instance, validated_data)
        if auth_groups is not None:
            instance.auth_groups.set(auth_groups)
        return instance


class AllSettingsSerializer(serializers.Serializer):
    """
    Combined serializer for all settings
    Used for GET /api/v1/settings/ to return all settings at once
    """

    training = TrainingSettingsSerializer(required=False)
    vocabulary = VocabularySettingsSerializer(required=False)
    login = LoginPageSettingsSerializer(required=False)
    security = serializers.DictField(required=False)
    push = serializers.DictField(required=False)
    general = GeneralSettingsSerializer(required=False)
    email = EmailSettingsSerializer(required=False)
    member = MemberSettingsSerializer(required=False)
    service = ServiceSettingsSerializer(required=False)
    order = OrderSettingsSerializer(required=False)
    ldap = LDAPSettingsSerializer(required=False)
    oidc = OIDCSettingsSerializer(required=False)


class CategorySettingsUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating a specific category's settings
    Used for PATCH/PUT to update settings by category
    """

    category = serializers.ChoiceField(
        choices=["general", "email", "member", "service", "order", "ldap"],
        required=True,
        help_text="Settings category to update",
    )
    settings = serializers.DictField(required=True, help_text="Settings key-value pairs to update")


class UserPermissionsSerializer(serializers.Serializer):
    """
    Serializer for user's settings permissions
    Returns which categories the user can view/change
    """

    can_view_all = serializers.BooleanField()
    can_change_all = serializers.BooleanField()
    categories = serializers.DictField(child=serializers.DictField(child=serializers.BooleanField()))


__all__ = [
    "AllSettingsSerializer",
    "AuthGroupMiniSerializer",
    "CategorySettingsUpdateSerializer",
    "EmailSettingsSerializer",
    "EmailTemplateCreateUpdateSerializer",
    "EmailTemplateDetailSerializer",
    "EmailTemplateListSerializer",
    "EmailTemplatePreviewResponseSerializer",
    "EmailTemplatePreviewSerializer",
    "GeneralSettingsSerializer",
    "LDAPConnectionTestSerializer",
    "LDAPDepartmentRoleMappingSerializer",
    "LDAPSettingsSerializer",
    "MemberSettingsSerializer",
    "OrderSettingsSerializer",
    "ServiceSettingsSerializer",
    "UserPermissionsSerializer",
]
