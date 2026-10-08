"""UX-02.1: person pickers list real, active accounts only. Fictional data."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class UserPickerTests(APITestCase):
    def setUp(self):
        self.viewer = User.objects.create_user(username="viewer", password="Viewer!123")
        User.objects.create_user(username="aktiv", password="Aktiv!1234")
        User.objects.create_user(username="ehemalig", password="Ehemalig!1", is_active=False)
        User.objects.get_or_create(username="AnonymousUser")
        self.client.force_authenticate(self.viewer)

    def usernames(self, query=""):
        response = self.client.get(f"/api/v1/users/{query}")
        self.assertEqual(response.status_code, 200)
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        return {row["username"] for row in rows}

    def test_active_filter_is_applied(self):
        names = self.usernames("?is_active=true&limit=1000")
        self.assertIn("aktiv", names)
        self.assertNotIn("ehemalig", names)

    def test_system_account_is_never_listed(self):
        self.assertNotIn("AnonymousUser", self.usernames())
        self.assertNotIn("AnonymousUser", self.usernames("?is_active=true"))
