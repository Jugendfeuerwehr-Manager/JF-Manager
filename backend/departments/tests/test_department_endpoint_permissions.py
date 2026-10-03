"""Staff status alone must not grant organisation-wide department management."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole


class DepartmentEndpointPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="endpoint-role-a")
        cls.department_b = Department.objects.create(name="B", code="endpoint-role-b")
        cls.staff = get_user_model().objects.create_user(username="department-staff", password="test-only-password")
        cls.staff.is_staff = True
        cls.staff.save(update_fields=["is_staff"])
        UserDepartmentRole.objects.create(user=cls.staff, department=cls.department_a)

    def test_staff_without_scope_right_sees_only_assigned_department(self):
        self.client.force_authenticate(user=self.staff)

        listed = self.client.get("/api/v1/departments/")
        foreign_detail = self.client.get(f"/api/v1/departments/{self.department_b.pk}/")

        self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.data)
        self.assertEqual({item["id"] for item in listed.data["results"]}, {self.department_a.pk})
        self.assertEqual(foreign_detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_without_management_right_cannot_create_department(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.post("/api/v1/departments/", {"name": "New", "code": "endpoint-role-new"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Department.objects.filter(code="endpoint-role-new").exists())

    def test_staff_without_management_right_cannot_change_or_delete_department(self):
        self.client.force_authenticate(user=self.staff)

        changed = self.client.patch(f"/api/v1/departments/{self.department_a.pk}/", {"name": "Changed"})
        deleted = self.client.delete(f"/api/v1/departments/{self.department_a.pk}/")

        self.assertEqual(changed.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(deleted.status_code, status.HTTP_403_FORBIDDEN)
        self.department_a.refresh_from_db()
        self.assertEqual(self.department_a.name, "A")
