from django.contrib.auth import get_user_model
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

    def test_staff_user_has_full_settings_permissions(self):
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.get("/api/v1/settings/permissions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["can_view_all"])
        self.assertTrue(response.data["can_change_all"])
        self.assertTrue(response.data["categories"]["general"]["can_change"])
        self.assertTrue(response.data["categories"]["service"]["can_change"])

    def test_staff_user_can_list_all_settings(self):
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.get("/api/v1/settings/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
