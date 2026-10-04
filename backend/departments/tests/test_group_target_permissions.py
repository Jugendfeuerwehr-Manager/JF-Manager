"""Group writes must validate their requested department target."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Group


class GroupTargetPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="group-target-a")
        cls.department_b = Department.objects.create(name="B", code="group-target-b")
        cls.group_a = Group.objects.create(name="A group", department=cls.department_a)
        cls.user = get_user_model().objects.create_user(username="group-target-writer")
        writer = AuthGroup.objects.create(name="Group target writer A")
        for codename in ("add_group", "change_group"):
            writer.permissions.add(Permission.objects.get(content_type__app_label="members", codename=codename))
        reader = AuthGroup.objects.create(name="Group target reader B")
        reader.permissions.add(Permission.objects.get(content_type__app_label="members", codename="view_group"))
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_a).groups.add(writer)
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_b).groups.add(reader)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_create_group_in_read_only_department_is_rejected(self):
        response = self.client.post(
            "/api/v1/groups/", {"name": "Foreign group", "department": self.department_b.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Group.objects.filter(name="Foreign group").exists())

    def test_move_group_to_read_only_department_is_rejected(self):
        response = self.client.patch(
            f"/api/v1/groups/{self.group_a.pk}/", {"department": self.department_b.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.group_a.refresh_from_db()
        self.assertEqual(self.group_a.department_id, self.department_a.pk)

    def test_create_group_in_writable_department_is_allowed(self):
        response = self.client.post(
            "/api/v1/groups/", {"name": "Own group", "department": self.department_a.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Group.objects.filter(name="Own group", department=self.department_a).exists())
