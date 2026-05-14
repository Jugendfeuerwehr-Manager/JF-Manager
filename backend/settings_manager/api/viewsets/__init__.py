"""
ViewSets for Settings API
"""

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from dynamic_preferences.registries import global_preferences_registry
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from settings_manager.models import LDAPConfig, OIDCConfig
from users.ldap_tls import apply_ldap_tls_options

from ..serializers import (
    AllSettingsSerializer,
    CategorySettingsUpdateSerializer,
    EmailSettingsSerializer,
    GeneralSettingsSerializer,
    LDAPConnectionTestSerializer,
    LDAPSettingsSerializer,
    MemberSettingsSerializer,
    OIDCDiscoveryResultSerializer,
    OIDCSettingsSerializer,
    OrderSettingsSerializer,
    ServiceSettingsSerializer,
    UserPermissionsSerializer,
)

# Import email template viewset
from .email_layout_template import EmailLayoutTemplateViewSet
from .email_template import EmailTemplateViewSet
from .ldap_mappings import LDAPDepartmentMappingViewSet
from .oidc_mappings import OIDCGroupMappingViewSet

__all__ = [
    "EmailLayoutTemplateViewSet",
    "EmailTemplateViewSet",
    "LDAPDepartmentMappingViewSet",
    "OIDCGroupMappingViewSet",
    "SettingsViewSet",
]


class SettingsViewSet(viewsets.ViewSet):
    """
    ViewSet for managing application settings

    Provides endpoints to:
    - List all settings (GET /settings/)
    - Get settings by category (GET /settings/general/, /settings/email/, etc.)
    - Update settings by category (PATCH /settings/general/, etc.)
    - Get user permissions (GET /settings/permissions/)
    """

    permission_classes = [IsAuthenticated]

    # Mapping of category to preference prefix
    CATEGORY_MAPPINGS = {
        "general": {"prefix": "general", "fields": ["title", "slug", "logo_url"]},
        "email": {
            "prefix": "email",
            "fields": [
                "email_host",
                "email_port",
                "email_use_tls",
                "email_use_ssl",
                "email_host_user",
                "email_host_password",
                "default_from_email",
            ],
        },
        "member": {"prefix": "members", "fields": ["alert_threshold", "alert_threshold_last_entries"]},
        "service": {"prefix": "service", "fields": ["service_start_time", "service_end_time"]},
        "order": {"prefix": "orders", "fields": ["equipment_manager_email"]},
        "ldap": {"prefix": "ldap", "fields": []},
        "oidc": {"prefix": "oidc", "fields": []},
    }

    LDAP_FIELDS = [
        "enabled",
        "server_uri",
        "start_tls",
        "ca_cert_file",
        "ca_cert_content",
        "disable_cert_validation",
        "bind_dn",
        "user_search_base_dn",
        "user_search_filter",
        "group_search_base_dn",
        "group_search_filter",
        "group_type",
        "mirror_groups",
        "require_group",
    ]

    OIDC_FIELDS = [
        "enabled",
        "provider_name",
        "issuer_url",
        "client_id",
        "scope",
        "groups_claim",
        "staff_group",
        "admin_group",
        "require_group_mapping",
        "hide_local_login",
    ]

    def _get_category_settings(self, category):
        """Helper to retrieve settings for a specific category"""
        global_preferences = global_preferences_registry.manager()
        mapping = self.CATEGORY_MAPPINGS.get(category)

        if not mapping:
            return None

        settings = {}
        prefix = mapping["prefix"]

        for field in mapping["fields"]:
            pref_key = f"{prefix}__{field}"
            try:
                value = global_preferences.get(pref_key)
                settings[field] = value
            except Exception:
                # If preference doesn't exist, skip it
                pass

        return settings

    def _save_category_settings(self, category, data):
        """Helper to save settings for a specific category"""
        global_preferences = global_preferences_registry.manager()
        mapping = self.CATEGORY_MAPPINGS.get(category)

        if not mapping:
            return False

        prefix = mapping["prefix"]

        for field, value in data.items():
            if field in mapping["fields"]:
                pref_key = f"{prefix}__{field}"
                try:
                    # Handle time fields - convert to string format
                    if hasattr(value, "strftime"):
                        value = value.strftime("%H:%M")
                    global_preferences[pref_key] = value
                except Exception as e:
                    # Log error but continue
                    print(f"Error saving {pref_key}: {e}")

        return True

    def _check_category_permission(self, user, category, permission_type="view"):
        """Check if user has permission for a specific category"""
        if user.is_superuser:
            return True

        if user.is_staff and category not in ("ldap", "oidc"):
            return True

        # Check specific permission
        permission = f"settings_manager.{permission_type}_{category}_settings"
        if user.has_perm(permission):
            return True

        # Check global permission
        global_permission = f"settings_manager.{permission_type}_all_settings"
        return bool(user.has_perm(global_permission))

    def _get_ldap_settings(self):
        config = LDAPConfig.get_or_create_default()
        settings = {field: getattr(config, field) for field in self.LDAP_FIELDS}
        settings["has_bind_password"] = bool(config.bind_password)
        return settings

    def _save_ldap_settings(self, data):
        config = LDAPConfig.get_or_create_default()
        for field in self.LDAP_FIELDS:
            if field in data:
                setattr(config, field, data[field])

        if "bind_password" in data:
            config.bind_password = data["bind_password"]

        config.save()
        return config

    def _get_oidc_settings(self, request=None):
        config = OIDCConfig.get_or_create_default()
        settings = {field: getattr(config, field) for field in self.OIDC_FIELDS}
        settings["has_client_secret"] = bool(config.client_secret)
        if request is not None:
            settings["callback_url"] = request.build_absolute_uri("/api/v1/auth/oidc/callback/")
        return settings

    def _save_oidc_settings(self, data):
        config = OIDCConfig.get_or_create_default()
        for field in self.OIDC_FIELDS:
            if field in data:
                setattr(config, field, data[field])

        if "client_secret" in data:
            config.client_secret = data["client_secret"]

        config.save()
        return config

    @extend_schema(
        summary="List all settings",
        description="Get all application settings grouped by category. Only returns categories the user has permission to view.",
        responses={200: AllSettingsSerializer},
    )
    def list(self, request):
        """GET /api/v1/settings/ - List all settings"""
        # Check if user has permission to view all settings
        if not (
            request.user.is_superuser
            or request.user.is_staff
            or request.user.has_perm("settings_manager.view_all_settings")
        ):
            return Response(
                {"detail": "You do not have permission to view settings."}, status=status.HTTP_403_FORBIDDEN
            )

        all_settings = {}

        # Get settings for each category the user can access
        for category in self.CATEGORY_MAPPINGS:
            if self._check_category_permission(request.user, category, "view"):
                if category == "ldap":
                    category_settings = self._get_ldap_settings()
                elif category == "oidc":
                    category_settings = self._get_oidc_settings()
                else:
                    category_settings = self._get_category_settings(category)
                if category_settings is not None:
                    all_settings[category] = category_settings

        serializer = AllSettingsSerializer(all_settings)
        return Response(serializer.data)

    @extend_schema(
        summary="Get general settings",
        description="Get general application settings",
        responses={200: GeneralSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def general(self, request):
        """GET/PATCH /api/v1/settings/general/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "general", "view"):
                return Response(
                    {"detail": "You do not have permission to view general settings."}, status=status.HTTP_403_FORBIDDEN
                )

            settings = self._get_category_settings("general")
            serializer = GeneralSettingsSerializer(settings)
            return Response(serializer.data)

        else:  # PATCH
            if not self._check_category_permission(request.user, "general", "change"):
                return Response(
                    {"detail": "You do not have permission to change general settings."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = GeneralSettingsSerializer(data=request.data, partial=True)
            if serializer.is_valid():
                self._save_category_settings("general", serializer.validated_data)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Get email settings",
        description="Get email/SMTP configuration settings",
        responses={200: EmailSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def email(self, request):
        """GET/PATCH /api/v1/settings/email/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "email", "view"):
                return Response(
                    {"detail": "You do not have permission to view email settings."}, status=status.HTTP_403_FORBIDDEN
                )

            settings = self._get_category_settings("email")
            serializer = EmailSettingsSerializer(settings)
            return Response(serializer.data)

        else:  # PATCH
            if not self._check_category_permission(request.user, "email", "change"):
                return Response(
                    {"detail": "You do not have permission to change email settings."}, status=status.HTTP_403_FORBIDDEN
                )

            serializer = EmailSettingsSerializer(data=request.data, partial=True)
            if serializer.is_valid():
                self._save_category_settings("email", serializer.validated_data)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Get member settings",
        description="Get member-related settings (absence alerts, etc.)",
        responses={200: MemberSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def member(self, request):
        """GET/PATCH /api/v1/settings/member/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "member", "view"):
                return Response(
                    {"detail": "You do not have permission to view member settings."}, status=status.HTTP_403_FORBIDDEN
                )

            settings = self._get_category_settings("member")
            serializer = MemberSettingsSerializer(settings)
            return Response(serializer.data)

        else:  # PATCH
            if not self._check_category_permission(request.user, "member", "change"):
                return Response(
                    {"detail": "You do not have permission to change member settings."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = MemberSettingsSerializer(data=request.data, partial=True)
            if serializer.is_valid():
                self._save_category_settings("member", serializer.validated_data)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Get service settings",
        description="Get service-related settings (default times, etc.)",
        responses={200: ServiceSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def service(self, request):
        """GET/PATCH /api/v1/settings/service/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "service", "view"):
                return Response(
                    {"detail": "You do not have permission to view service settings."}, status=status.HTTP_403_FORBIDDEN
                )

            settings = self._get_category_settings("service")
            serializer = ServiceSettingsSerializer(settings)
            return Response(serializer.data)

        else:  # PATCH
            if not self._check_category_permission(request.user, "service", "change"):
                return Response(
                    {"detail": "You do not have permission to change service settings."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = ServiceSettingsSerializer(data=request.data, partial=True)
            if serializer.is_valid():
                self._save_category_settings("service", serializer.validated_data)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Get order settings",
        description="Get order-related settings (equipment manager email, etc.)",
        responses={200: OrderSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def order(self, request):
        """GET/PATCH /api/v1/settings/order/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "order", "view"):
                return Response(
                    {"detail": "You do not have permission to view order settings."}, status=status.HTTP_403_FORBIDDEN
                )

            settings = self._get_category_settings("order")
            serializer = OrderSettingsSerializer(settings)
            return Response(serializer.data)

        else:  # PATCH
            if not self._check_category_permission(request.user, "order", "change"):
                return Response(
                    {"detail": "You do not have permission to change order settings."}, status=status.HTTP_403_FORBIDDEN
                )

            serializer = OrderSettingsSerializer(data=request.data, partial=True)
            if serializer.is_valid():
                self._save_category_settings("order", serializer.validated_data)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Get LDAP settings",
        description="Get LDAP authentication and group sync configuration",
        responses={200: LDAPSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def ldap(self, request):
        """GET/PATCH /api/v1/settings/ldap/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "ldap", "view"):
                return Response(
                    {"detail": "You do not have permission to view LDAP settings."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = LDAPSettingsSerializer(self._get_ldap_settings())
            return Response(serializer.data)

        if not self._check_category_permission(request.user, "ldap", "change"):
            return Response(
                {"detail": "You do not have permission to change LDAP settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = LDAPSettingsSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            try:
                self._save_ldap_settings(serializer.validated_data)
            except ValidationError as exc:
                if hasattr(exc, "message_dict"):
                    return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
                return Response({"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST)
            response_serializer = LDAPSettingsSerializer(self._get_ldap_settings())
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Test LDAP connection",
        description="Test LDAP server bind and configured user/group search bases",
        responses={200: LDAPConnectionTestSerializer, 400: LDAPConnectionTestSerializer},
    )
    @action(detail=False, methods=["post"], url_path="ldap/test-connection", permission_classes=[IsAuthenticated])
    def ldap_test_connection(self, request):
        """POST /api/v1/settings/ldap/test-connection/"""
        if not self._check_category_permission(request.user, "ldap", "change"):
            return Response(
                {"detail": "You do not have permission to test LDAP settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        config = LDAPConfig.get_or_create_default()
        if not config.server_uri:
            return Response(
                {"ok": False, "detail": "LDAP server URI is not configured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            import ldap

            apply_ldap_tls_options(config)
            connection = ldap.initialize(config.server_uri)
            connection.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)

            if config.start_tls:
                connection.start_tls_s()

            if config.bind_dn:
                connection.simple_bind_s(config.bind_dn, config.bind_password or "")
            else:
                connection.simple_bind_s()

            if config.user_search_base_dn and config.user_search_filter:
                connection.search_s(config.user_search_base_dn, ldap.SCOPE_SUBTREE, config.user_search_filter)

            if config.group_search_base_dn and config.group_search_filter:
                connection.search_s(config.group_search_base_dn, ldap.SCOPE_SUBTREE, config.group_search_filter)

            connection.unbind_s()
            return Response({"ok": True, "detail": "LDAP connection test succeeded."})
        except Exception as exc:
            return Response(
                {"ok": False, "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Browse LDAP directory",
        description=(
            "Browse the LDAP directory at a given base DN using the saved server credentials. "
            "Returns up to 200 entries with their DN and requested attributes."
        ),
    )
    @action(detail=False, methods=["post"], url_path="ldap/browse", permission_classes=[IsAuthenticated])
    def ldap_browse(self, request):
        """POST /api/v1/settings/ldap/browse/"""
        if not request.user.is_superuser:
            return Response(
                {"detail": "Keine Berechtigung für LDAP-Einstellungen."},
                status=status.HTTP_403_FORBIDDEN,
            )

        config = LDAPConfig.get_or_create_default()
        if not config.server_uri:
            return Response(
                {"ok": False, "detail": "LDAP Server URI ist nicht konfiguriert.", "entries": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_dn = request.data.get("base_dn", "")
        filter_str = request.data.get("filter", "(objectClass=*)")
        scope_str = request.data.get("scope", "one")
        requested_attrs = request.data.get("attributes", ["cn", "ou", "description", "objectClass"])

        # Restrict scope to known safe values
        if scope_str not in ("one", "sub"):
            scope_str = "one"

        # Guard against LDAP filter injection: cap length and allow only safe characters
        import re

        if len(filter_str) > 512 or not re.fullmatch(r"[\w\s=*()\-.,@:/\\+<>\"'#;!%&|~]+", filter_str):
            return Response(
                {"ok": False, "detail": "Ungültiger LDAP-Filter.", "entries": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            import ldap

            apply_ldap_tls_options(config)
            conn = ldap.initialize(config.server_uri)
            conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)

            if config.start_tls:
                conn.start_tls_s()

            if config.bind_dn:
                conn.simple_bind_s(config.bind_dn, config.bind_password or "")
            else:
                conn.simple_bind_s()

            scope = ldap.SCOPE_ONELEVEL if scope_str == "one" else ldap.SCOPE_SUBTREE
            raw_results = conn.search_s(base_dn, scope, filter_str, requested_attrs)
            conn.unbind_s()

            entries = []
            for dn, attrs_dict in raw_results:
                if dn is None:
                    continue
                entry: dict = {"dn": dn}
                for attr_name, values in attrs_dict.items():
                    decoded = []
                    for v in values if isinstance(values, list) else [values]:
                        if isinstance(v, bytes):
                            try:
                                decoded.append(v.decode("utf-8"))
                            except Exception:
                                decoded.append(v.hex())
                        else:
                            decoded.append(str(v))
                    entry[attr_name] = decoded[0] if len(decoded) == 1 else decoded
                entries.append(entry)

            return Response({"ok": True, "entries": entries, "total": len(entries)})
        except Exception as exc:
            return Response(
                {"ok": False, "detail": str(exc), "entries": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Get OIDC settings",
        description="Get OpenID Connect authentication configuration",
        responses={200: OIDCSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def oidc(self, request):
        """GET/PATCH /api/v1/settings/oidc/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "oidc", "view"):
                return Response(
                    {"detail": "You do not have permission to view OIDC settings."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = OIDCSettingsSerializer(self._get_oidc_settings(request))
            return Response(serializer.data)

        if not self._check_category_permission(request.user, "oidc", "change"):
            return Response(
                {"detail": "You do not have permission to change OIDC settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OIDCSettingsSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            self._save_oidc_settings(serializer.validated_data)
            response_serializer = OIDCSettingsSerializer(self._get_oidc_settings(request))
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Test OIDC discovery",
        description="Test whether the OIDC Discovery Document can be fetched from the given issuer URL",
        responses={200: OIDCDiscoveryResultSerializer},
    )
    @action(detail=False, methods=["post"], url_path="oidc/test-discovery", permission_classes=[IsAuthenticated])
    def oidc_test_discovery(self, request):
        """POST /api/v1/settings/oidc/test-discovery/"""
        if not self._check_category_permission(request.user, "oidc", "change"):
            return Response(
                {"detail": "You do not have permission to test OIDC settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        from users.oidc_views import OIDCTestDiscoveryView

        # Delegate to the reusable view logic
        view = OIDCTestDiscoveryView()
        view.request = request
        return view.post(request)

    @extend_schema(
        summary="Get user permissions",
        description="Get current user's permissions for viewing and changing settings",
        responses={200: UserPermissionsSerializer},
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def permissions(self, request):
        """GET /api/v1/settings/permissions/"""
        user = request.user

        permissions_data = {
            "can_view_all": user.is_superuser or user.is_staff or user.has_perm("settings_manager.view_all_settings"),
            "can_change_all": user.is_superuser
            or user.is_staff
            or user.has_perm("settings_manager.change_all_settings"),
            "categories": {},
        }

        # Check permissions for each category
        for category in self.CATEGORY_MAPPINGS:
            permissions_data["categories"][category] = {
                "can_view": self._check_category_permission(user, category, "view"),
                "can_change": self._check_category_permission(user, category, "change"),
            }

        serializer = UserPermissionsSerializer(permissions_data)
        return Response(serializer.data)
