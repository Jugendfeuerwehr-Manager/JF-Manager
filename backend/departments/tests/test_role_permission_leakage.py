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
