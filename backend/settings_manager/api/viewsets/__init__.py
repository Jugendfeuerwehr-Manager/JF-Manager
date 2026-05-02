"""
ViewSets for Settings API
"""

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from dynamic_preferences.registries import global_preferences_registry
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..permissions import CanChangeCategorySettings, CanChangeSettings, CanViewCategorySettings, CanViewSettings
from ..serializers import (
    AllSettingsSerializer,
    CategorySettingsUpdateSerializer,
    EmailSettingsSerializer,
    GeneralSettingsSerializer,
    MemberSettingsSerializer,
    OrderSettingsSerializer,
    ServiceSettingsSerializer,
    UserPermissionsSerializer,
)

# Import email template viewset
from .email_template import EmailTemplateViewSet

__all__ = ["EmailTemplateViewSet", "SettingsViewSet"]


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
        "general": {"prefix": "general", "fields": ["title"]},
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
    }

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
        if user.is_superuser or user.is_staff:
            return True

        # Check specific permission
        permission = f"settings_manager.{permission_type}_{category}_settings"
        if user.has_perm(permission):
            return True

        # Check global permission
        global_permission = f"settings_manager.{permission_type}_all_settings"
        return bool(user.has_perm(global_permission))

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
