import re

from drf_spectacular.utils import extend_schema
from dynamic_preferences.registries import global_preferences_registry
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

DEFAULT_BRAND_COLOR = "#b91c1c"
LOGIN_TEXT_FIELDS = ("login_eyebrow", "login_headline", "login_intro", "login_footer", "login_help")


def _brand_color(value):
    """Only a plain #rrggbb value reaches the unauthenticated login page."""
    return value.lower() if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value) else DEFAULT_BRAND_COLOR


class PublicBrandingView(APIView):
    """
    Public API endpoint to retrieve branding/app identity info.
    No authentication required — used by the login page.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Get public branding information",
        description="Returns the app title, slug, logo URL, brand colour and login page texts. No authentication required.",
    )
    def get(self, request):
        global_preferences = global_preferences_registry.manager()

        branding = {
            "title": global_preferences.get("general__title") or "JF Manager",
            "slug": global_preferences.get("general__slug") or "",
            "logo_url": global_preferences.get("general__logo_url") or "",
            "brand_color": _brand_color(global_preferences.get("general__brand_color")),
            # Plain text; the login page renders it escaped.
            "login_texts": {
                name.removeprefix("login_"): str(global_preferences.get(f"general__{name}") or "")
                for name in LOGIN_TEXT_FIELDS
            },
        }

        return Response(branding)


class AppSettingsView(APIView):
    """
    API endpoint to retrieve application settings
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get application settings",
        description="Get public application settings like app name, contact emails, etc.",
    )
    def get(self, request):
        global_preferences = global_preferences_registry.manager()

        # Canonical registered preferences; no connection credentials are exposed.
        result = {
            "app_name": global_preferences["general__title"],
            "organization_name": global_preferences["general__slug"],
            "contact_email": "",
            "equipment_manager_email": global_preferences["orders__equipment_manager_email"],
        }
        for section, names in {
            "service": ["service_start_time", "service_end_time"],
            "training": ["training_start_time", "training_end_time", "default_block_duration_minutes"],
            "general": ["member_label", "service_label", "training_label"],
        }.items():
            result.update({name: global_preferences[f"{section}__{name}"] for name in names})
        return Response(result)
