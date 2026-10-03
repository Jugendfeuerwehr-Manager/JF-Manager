"""Regression tests for rights that must stay within their department."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Group


class DepartmentRoleLeakageTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="role-a")
        cls.department_b = Department.objects.create(name="B", code="role-b")
        cls.group_a = Group.objects.create(name="A group", department=cls.department_a)
        cls.group_b = Group.objects.create(name="B group", department=cls.department_b)
        cls.user = get_user_model().objects.create_user(username="mixed-roles", password="test-only-password")

        writer = AuthGroup.objects.create(name="Writer A")
        writer.permissions.add(Permission.objects.get(content_type__app_label="members", codename="change_group"))
        reader = AuthGroup.objects.create(name="Reader B")
        reader.permissions.add(Permission.objects.get(content_type__app_label="members", codename="view_group"))
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_a).groups.add(writer)
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_b).groups.add(reader)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_writer_in_a_cannot_change_group_in_read_only_b_without_filter(self):
        response = self.client.patch(f"/api/v1/groups/{self.group_b.pk}/", {"name": "Changed"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.group_b.refresh_from_db()
        self.assertEqual(self.group_b.name, "B group")

    def test_explicit_department_filter_does_not_grant_b_write(self):
        response = self.client.patch(
            f"/api/v1/groups/{self.group_b.pk}/?department={self.department_b.pk}",
            {"name": "Changed"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.group_b.refresh_from_db()
        self.assertEqual(self.group_b.name, "B group")

    def test_writer_can_change_group_in_a(self):
        response = self.client.patch(f"/api/v1/groups/{self.group_a.pk}/", {"name": "Changed A"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group_a.refresh_from_db()
        self.assertEqual(self.group_a.name, "Changed A")

    def test_same_codename_from_other_app_does_not_grant_write(self):
        writer = AuthGroup.objects.get(name="Writer A")
        writer.permissions.clear()
        writer.permissions.add(Permission.objects.get(content_type__app_label="auth", codename="change_group"))

        response = self.client.patch(f"/api/v1/groups/{self.group_a.pk}/", {"name": "Changed A"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.group_a.refresh_from_db()
        self.assertEqual(self.group_a.name, "A group")


class StaffAndScopePermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="staff-a")
        cls.department_b = Department.objects.create(name="B", code="staff-b")
        cls.group_a = Group.objects.create(name="A group", department=cls.department_a)
        cls.group_b = Group.objects.create(name="B group", department=cls.department_b)
        cls.staff = get_user_model().objects.create_user(username="staff-only", password="test-only-password", is_staff=True)
        cls.org_scope = get_user_model().objects.create_user(username="org-scope", password="test-only-password")
        cls.org_scope.user_permissions.add(Permission.objects.get(codename="can_access_all_departments"))

    def test_staff_without_model_permission_cannot_read_or_write(self):
        self.client.force_authenticate(user=self.staff)

        self.assertEqual(self.client.get("/api/v1/groups/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.patch(f"/api/v1/groups/{self.group_b.pk}/", {"name": "Changed"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_org_scope_without_model_permission_cannot_read_or_write(self):
        self.client.force_authenticate(user=self.org_scope)

        self.assertEqual(self.client.get("/api/v1/groups/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.patch(f"/api/v1/groups/{self.group_b.pk}/", {"name": "Changed"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_department_role_does_not_expose_other_departments(self):
        reader = AuthGroup.objects.create(name="Staff reader A")
        reader.permissions.add(Permission.objects.get(content_type__app_label="members", codename="view_group"))
        UserDepartmentRole.objects.create(user=self.staff, department=self.department_a).groups.add(reader)
        self.client.force_authenticate(user=self.staff)

        response = self.client.get("/api/v1/groups/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["id"] for item in response.data["results"]}, {self.group_a.pk})
        self.assertEqual(
            self.client.get(f"/api/v1/groups/?department={self.department_b.pk}").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_org_scope_with_explicit_global_view_permission_can_read_but_not_write(self):
        self.org_scope.user_permissions.add(
            Permission.objects.get(content_type__app_label="members", codename="view_group")
        )
        self.client.force_authenticate(user=self.org_scope)

        response = self.client.get("/api/v1/groups/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["id"] for item in response.data["results"]}, {self.group_a.pk, self.group_b.pk})
        self.assertEqual(
            self.client.patch(f"/api/v1/groups/{self.group_b.pk}/", {"name": "Changed"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
