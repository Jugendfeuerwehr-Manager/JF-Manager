"""Member read and write permissions across overlapping departments."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Group as MemberGroup
from members.models import Member


class MemberRolePermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="member-role-a")
        cls.department_b = Department.objects.create(name="B", code="member-role-b")
        cls.member_a = Member.objects.create(name="A", lastname="Only")
        cls.member_a.departments.add(cls.department_a)
        cls.member_b = Member.objects.create(name="B", lastname="Only")
        cls.member_b.departments.add(cls.department_b)
        cls.member_shared = Member.objects.create(name="Shared", lastname="Member")
        cls.member_shared.departments.add(cls.department_a, cls.department_b)

        cls.reader = get_user_model().objects.create_user(username="member-reader", password="test-only-password")
        cls.reader.user_permissions.add(Permission.objects.get(codename="can_access_all_departments"))
        reader_group = AuthGroup.objects.create(name="Member reader A")
        reader_group.permissions.add(Permission.objects.get(content_type__app_label="members", codename="view_member"))
        UserDepartmentRole.objects.create(user=cls.reader, department=cls.department_a).groups.add(reader_group)

        cls.writer = get_user_model().objects.create_user(username="member-writer", password="test-only-password")
        writer_group = AuthGroup.objects.create(name="Member writer A")
        writer_group.permissions.add(
            Permission.objects.get(content_type__app_label="members", codename="change_member")
        )
        UserDepartmentRole.objects.create(user=cls.writer, department=cls.department_a).groups.add(writer_group)
        UserDepartmentRole.objects.create(user=cls.writer, department=cls.department_b).groups.add(reader_group)

    def test_org_scope_with_read_role_only_in_a_sees_only_a_members(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/v1/members/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in response.data["results"]},
            {self.member_a.pk, self.member_shared.pk},
        )

    def test_statistics_count_only_members_with_read_permission(self):
        group_a = MemberGroup.objects.create(name="Visible group", department=self.department_a)
        group_b = MemberGroup.objects.create(name="Hidden group", department=self.department_b)
        self.member_a.group = group_a
        self.member_a.save(update_fields=["group"])
        self.member_b.group = group_b
        self.member_b.save(update_fields=["group"])
        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/v1/members/statistics/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 2)
        self.assertNotIn("Hidden group", {group["name"] for group in response.data["by_group"]})

    def test_write_role_in_a_cannot_change_member_only_in_b(self):
        self.client.force_authenticate(user=self.writer)

        response = self.client.patch(f"/api/v1/members/{self.member_b.pk}/", {"name": "Changed"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.member_b.refresh_from_db()
        self.assertEqual(self.member_b.name, "B")

    def test_write_role_in_a_can_change_shared_member(self):
        self.client.force_authenticate(user=self.writer)

        response = self.client.patch(f"/api/v1/members/{self.member_shared.pk}/", {"name": "Changed"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.member_shared.refresh_from_db()
        self.assertEqual(self.member_shared.name, "Changed")
