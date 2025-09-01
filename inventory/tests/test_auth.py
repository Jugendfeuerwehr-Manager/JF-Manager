from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from inventory.models import Category


class InventoryAPIPermissionsTest(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="TestCat")
        User = get_user_model()
        # user without special perms (only authenticated) to test view perms via Django model permissions
        self.user = User.objects.create_user(username="apiuser", password="pw12345")

    def test_unauthenticated_denied(self):
        resp = self.client.get("/api/v1/inventory/categories/")
        self.assertIn(resp.status_code, (401, 403))

    def test_authenticated_no_view_perm_denied(self):
        self.client.login(username="apiuser", password="pw12345")
        # Without assigning model permissions, DjangoModelPermissions should deny GET list
        resp = self.client.get("/api/v1/inventory/categories/")
        self.assertEqual(resp.status_code, 403)
