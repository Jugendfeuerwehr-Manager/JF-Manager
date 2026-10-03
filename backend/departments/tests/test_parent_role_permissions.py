"""Parent contacts follow the permissions of their children's departments."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member, Parent


class ParentRolePermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="parent-role-a")
        cls.department_b = Department.objects.create(name="B", code="parent-role-b")
        cls.child_a = Member.objects.create(name="A", lastname="Child")
        cls.child_a.departments.add(cls.department_a)
        cls.child_b = Member.objects.create(name="B", lastname="Child")
        cls.child_b.departments.add(cls.department_b)
        cls.parent_a = Parent.objects.create(name="A", lastname="Parent")
        cls.parent_a.children.add(cls.child_a)
        cls.parent_b = Parent.objects.create(name="B", lastname="Parent")
        cls.parent_b.children.add(cls.child_b)
        cls.parent_shared = Parent.objects.create(name="Shared", lastname="Parent")
        cls.parent_shared.children.add(cls.child_a, cls.child_b)
        cls.parent_orphan = Parent.objects.create(name="Orphan", lastname="Parent")

        cls.reader = get_user_model().objects.create_user(username="parent-reader", password="test-only-password")
        cls.reader.user_permissions.add(Permission.objects.get(codename="can_access_all_departments"))
        read_group = AuthGroup.objects.create(name="Parent reader A")
        read_group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="members", codename__in=["view_parent", "view_member"]
            )
        )
        UserDepartmentRole.objects.create(user=cls.reader, department=cls.department_a).groups.add(read_group)

        cls.writer = get_user_model().objects.create_user(username="parent-writer", password="test-only-password")
        write_group = AuthGroup.objects.create(name="Parent writer A")
        write_group.permissions.add(Permission.objects.get(content_type__app_label="members", codename="change_parent"))
        UserDepartmentRole.objects.create(user=cls.writer, department=cls.department_a).groups.add(write_group)
        UserDepartmentRole.objects.create(user=cls.writer, department=cls.department_b).groups.add(read_group)

    def test_org_scope_with_parent_role_only_in_a_sees_only_a_contacts(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/v1/parents/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in response.data["results"]},
            {self.parent_a.pk, self.parent_shared.pk},
        )

    def test_shared_parent_does_not_expose_child_from_b(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.get(f"/api/v1/parents/{self.parent_shared.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["children"], [self.child_a.pk])

    def test_writer_in_a_cannot_change_parent_only_in_b(self):
        self.client.force_authenticate(user=self.writer)

        response = self.client.patch(f"/api/v1/parents/{self.parent_b.pk}/", {"name": "Changed"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.parent_b.refresh_from_db()
        self.assertEqual(self.parent_b.name, "B")

    def test_writer_in_a_can_change_shared_parent(self):
        self.client.force_authenticate(user=self.writer)

        response = self.client.patch(f"/api/v1/parents/{self.parent_shared.pk}/", {"name": "Changed"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.parent_shared.refresh_from_db()
        self.assertEqual(self.parent_shared.name, "Changed")
