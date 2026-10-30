"""Creating a service must land in a department (issue #25)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from servicebook.models import Service

User = get_user_model()
URL = "/api/v1/servicebook/services/"
PAYLOAD = {"start": "2026-11-01T18:00:00Z", "end": "2026-11-01T20:00:00Z", "topic": "Übung"}


class ServiceCreateDepartmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(name="Süd-Ost", code="so")
        cls.other = Department.objects.create(name="Mitte", code="mi")
        cls.foreign = Department.objects.create(name="Nord", code="no")
        perms = Permission.objects.filter(codename__in=["add_service", "view_service", "change_service"])
        cls.multi = User.objects.create_user("multi")
        cls.multi.user_permissions.set(perms)
        for department in (cls.dept, cls.other):
            UserDepartmentRole.objects.create(user=cls.multi, department=department)
        cls.single = User.objects.create_user("single")
        cls.single.user_permissions.set(perms)
        UserDepartmentRole.objects.create(user=cls.single, department=cls.dept)

    def post(self, user, data=None, query=""):
        client = APIClient()
        client.force_authenticate(user)
        return client.post(URL + query, {**PAYLOAD, **(data or {})}, format="json")

    def test_anonymous_is_rejected(self):
        self.assertIn(APIClient().post(URL, PAYLOAD, format="json").status_code, (401, 403))

    def test_department_in_payload_is_stored_and_reachable_with_filter(self):
        response = self.post(self.multi, {"department": self.dept.pk})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Service.objects.get(pk=response.data["id"]).department_id, self.dept.pk)
        client = APIClient()
        client.force_authenticate(self.multi)
        detail = client.get(f"{URL}{response.data['id']}/?department={self.dept.pk}")
        self.assertEqual(detail.status_code, 200)

    def test_multi_department_user_without_department_is_rejected(self):
        response = self.post(self.multi)
        self.assertEqual(response.status_code, 400)
        self.assertIn("department", response.data)
        self.assertFalse(Service.objects.exists())

    def test_single_department_user_falls_back_to_own_department(self):
        response = self.post(self.single)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Service.objects.get(pk=response.data["id"]).department_id, self.dept.pk)

    def test_foreign_department_is_rejected(self):
        response = self.post(self.multi, {"department": self.foreign.pk})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Service.objects.exists())

    def test_query_parameter_still_sets_the_department(self):
        response = self.post(self.multi, query=f"?department={self.other.pk}")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Service.objects.get(pk=response.data["id"]).department_id, self.other.pk)
