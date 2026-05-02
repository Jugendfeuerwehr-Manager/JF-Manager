"""
Admin User Management API Tests

Tests cover:
- Admin user CRUD with authentication & permissions
- Auth group CRUD with permission assignment
- Permission listing endpoint
- Non-admin access is blocked
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class AdminUserManagementBaseTestCase(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username="admin", email="admin@test.com", password="admin123!")
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@test.com",
            password="staff123!",
            is_staff=True,
            first_name="Staff",
            last_name="User",
        )
        self.regular_user = User.objects.create_user(
            username="regular", email="regular@test.com", password="regular123!", first_name="Regular", last_name="User"
        )
        self.test_group = Group.objects.create(name="Betreuer")
        self.client = APIClient()


class AdminUserViewSetTests(AdminUserManagementBaseTestCase):
    """Tests for /api/v1/admin/users/"""

    def test_list_users_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(response.data["count"], 3)

    def test_list_users_as_staff(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/v1/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_users_as_regular_forbidden(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get("/api/v1/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_users_unauthenticated(self):
        response = self.client.get("/api/v1/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_user(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "username": "newuser",
            "email": "new@test.com",
            "first_name": "New",
            "last_name": "User",
            "password": "SecurePass123!",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "group_ids": [self.test_group.id],
        }
        response = self.client.post("/api/v1/admin/users/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "newuser")
        user = User.objects.get(username="newuser")
        self.assertTrue(user.check_password("SecurePass123!"))
        self.assertIn(self.test_group, user.groups.all())

    def test_create_user_without_password(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "username": "nopwuser",
            "email": "nopw@test.com",
            "first_name": "NoPW",
            "last_name": "User",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "group_ids": [],
        }
        response = self.client.post("/api/v1/admin/users/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="nopwuser")
        self.assertFalse(user.has_usable_password())

    def test_retrieve_user(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f"/api/v1/admin/users/{self.staff_user.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "staff")
        self.assertIn("permissions", response.data)

    def test_update_user(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            f"/api/v1/admin/users/{self.staff_user.id}/", {"first_name": "Updated", "is_staff": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.staff_user.refresh_from_db()
        self.assertEqual(self.staff_user.first_name, "Updated")
        self.assertFalse(self.staff_user.is_staff)

    def test_update_user_password(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            f"/api/v1/admin/users/{self.staff_user.id}/", {"password": "NewSecure123!"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.staff_user.refresh_from_db()
        self.assertTrue(self.staff_user.check_password("NewSecure123!"))

    def test_delete_user_deactivates(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f"/api/v1/admin/users/{self.staff_user.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.staff_user.refresh_from_db()
        self.assertFalse(self.staff_user.is_active)

    def test_cannot_delete_self(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f"/api/v1/admin/users/{self.admin_user.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_groups(self):
        self.client.force_authenticate(user=self.admin_user)
        group2 = Group.objects.create(name="Verwaltung")
        response = self.client.patch(
            f"/api/v1/admin/users/{self.regular_user.id}/set-groups/",
            {"group_ids": [self.test_group.id, group2.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.regular_user.groups.count(), 2)

    def test_search_users(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/admin/users/?search=staff")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filter_users_active(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/admin/users/?is_active=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 3)


class AuthGroupViewSetTests(AdminUserManagementBaseTestCase):
    """Tests for /api/v1/admin/groups/"""

    def test_list_groups(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/admin/groups/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_list_groups_forbidden_for_regular(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get("/api/v1/admin/groups/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_group_with_permissions(self):
        self.client.force_authenticate(user=self.admin_user)
        perm = Permission.objects.filter(codename="view_customuser").first()
        data = {"name": "Neue Gruppe", "permission_ids": [perm.id] if perm else []}
        response = self.client.post("/api/v1/admin/groups/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        group = Group.objects.get(name="Neue Gruppe")
        if perm:
            self.assertIn(perm, group.permissions.all())

    def test_retrieve_group(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f"/api/v1/admin/groups/{self.test_group.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Betreuer")
        self.assertIn("permissions", response.data)
        self.assertIn("users", response.data)

    def test_update_group(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(
            f"/api/v1/admin/groups/{self.test_group.id}/", {"name": "Betreuer (Updated)"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.test_group.refresh_from_db()
        self.assertEqual(self.test_group.name, "Betreuer (Updated)")

    def test_delete_group(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f"/api/v1/admin/groups/{self.test_group.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Group.objects.filter(id=self.test_group.id).exists())

    def test_group_user_count(self):
        self.client.force_authenticate(user=self.admin_user)
        self.staff_user.groups.add(self.test_group)
        self.regular_user.groups.add(self.test_group)
        response = self.client.get("/api/v1/admin/groups/")
        group_data = next(g for g in response.data["results"] if g["id"] == self.test_group.id)
        self.assertEqual(group_data["user_count"], 2)


class PermissionViewSetTests(AdminUserManagementBaseTestCase):
    """Tests for /api/v1/admin/permissions/"""

    def test_list_permissions(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/admin/permissions/?limit=500")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertGreater(response.data["count"], 0)

    def test_permissions_have_descriptions(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/admin/permissions/?limit=500")
        perms_with_desc = [p for p in response.data["results"] if p.get("description")]
        self.assertGreater(len(perms_with_desc), 0)

    def test_permissions_filtered_by_app(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/admin/permissions/?limit=500")
        app_labels = set(p["app_label"] for p in response.data["results"])
        self.assertIn("training", app_labels)
        # Should not include irrelevant apps like contenttypes, sessions, admin
        self.assertNotIn("contenttypes", app_labels)
        self.assertNotIn("sessions", app_labels)

    def test_permissions_forbidden_for_regular(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get("/api/v1/admin/permissions/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permissions_search(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/admin/permissions/?search=member&limit=500")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data["count"], 0)
