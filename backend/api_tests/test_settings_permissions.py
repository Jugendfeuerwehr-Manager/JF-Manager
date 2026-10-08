"""Settings rights come from settings permissions; is_staff only opens the Django admin (SEC-01.57c)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class SettingsPermissionsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff_user = User.objects.create_user(
            username="staff_settings",
            email="staff-settings@test.com",
            password="staff123!",
            is_staff=True,
        )

    def grant(self, *codenames):
        self.staff_user.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="settings_manager", codename__in=codenames)
        )

    def test_staff_without_settings_rights_has_no_settings_access(self):
        self.client.force_authenticate(user=self.staff_user)

        permissions = self.client.get("/api/v1/settings/permissions/")
        listing = self.client.get("/api/v1/settings/")
        general = self.client.get("/api/v1/settings/general/")
        change = self.client.patch("/api/v1/settings/general/", {"site_name": "Staff"}, format="json")

        self.assertEqual(permissions.status_code, status.HTTP_200_OK)
        self.assertFalse(permissions.data["can_view_all"])
        self.assertFalse(permissions.data["can_change_all"])
        self.assertFalse(permissions.data["categories"]["general"]["can_view"])
        self.assertFalse(permissions.data["categories"]["service"]["can_change"])
        self.assertEqual(listing.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(general.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(change.status_code, status.HTTP_403_FORBIDDEN)

    def test_category_right_grants_only_that_category(self):
        self.grant("view_general_settings")
        self.client.force_authenticate(user=self.staff_user)

        permissions = self.client.get("/api/v1/settings/permissions/")
        listing = self.client.get("/api/v1/settings/")

        self.assertTrue(permissions.data["categories"]["general"]["can_view"])
        self.assertFalse(permissions.data["categories"]["general"]["can_change"])
        self.assertFalse(permissions.data["categories"]["email"]["can_view"])
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertIn("general", listing.data)
        self.assertNotIn("email", listing.data)

    def test_view_all_settings_right_lists_all_settings(self):
        self.grant("view_all_settings")
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.get("/api/v1/settings/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.client.get("/api/v1/settings/permissions/").data["can_view_all"])
