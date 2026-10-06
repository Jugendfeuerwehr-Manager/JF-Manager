from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from dynamic_preferences.registries import global_preferences_registry
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class BrandColorSettingsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username="brand_admin", password="brand123!", is_staff=True)
        # Settings rights are explicit; is_staff alone grants none (SEC-01.57c).
        self.admin.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="settings_manager",
                codename__in=["view_general_settings", "change_general_settings"],
            )
        )
        self.preferences = global_preferences_registry.manager()

    def test_public_branding_defaults_to_feuerwehr_red(self):
        response = APIClient().get("/api/v1/app/branding/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["brand_color"], "#b91c1c")

    def test_admin_sets_brand_color_and_login_page_receives_it(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch("/api/v1/settings/general/", {"brand_color": "#1D4ED8"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.preferences["general__brand_color"], "#1d4ed8")
        self.assertEqual(APIClient().get("/api/v1/app/branding/").data["brand_color"], "#1d4ed8")

    def test_rejects_anything_but_a_hex_colour(self):
        self.client.force_authenticate(user=self.admin)
        for value in ["blue", "#12345", "#1234567", "url(javascript:alert(1))", "#gggggg"]:
            response = self.client.patch("/api/v1/settings/general/", {"brand_color": value}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, value)
        self.assertEqual(self.preferences["general__brand_color"], "#b91c1c")

    def test_public_branding_never_echoes_a_stored_invalid_value(self):
        self.preferences["general__brand_color"] = "red;}body{display:none"
        self.assertEqual(APIClient().get("/api/v1/app/branding/").data["brand_color"], "#b91c1c")
