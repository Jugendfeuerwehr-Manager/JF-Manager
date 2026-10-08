"""Member actions must use the permission for their actual effect."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member


class MemberDeletionActionPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="A", code="member-action-a")
        cls.member = Member.objects.create(name="A", lastname="Member")
        cls.member.departments.add(cls.department)

        cls.creator = get_user_model().objects.create_user(username="member-creator", password="test-only-password")
        create_group = AuthGroup.objects.create(name="Member creator A")
        create_group.permissions.add(Permission.objects.get(content_type__app_label="members", codename="add_member"))
        UserDepartmentRole.objects.create(user=cls.creator, department=cls.department).groups.add(create_group)

        cls.deleter = get_user_model().objects.create_user(username="member-deleter", password="test-only-password")
        delete_group = AuthGroup.objects.create(name="Member deleter A")
        delete_group.permissions.add(Permission.objects.get(content_type__app_label="members", codename="delete_member"))
        UserDepartmentRole.objects.create(user=cls.deleter, department=cls.department).groups.add(delete_group)

    def test_add_only_role_cannot_delete_member_with_strategy(self):
        self.client.force_authenticate(user=self.creator)

        response = self.client.post(
            f"/api/v1/members/{self.member.pk}/delete-with-strategy/", {"strategy": "unlink"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Member.objects.filter(pk=self.member.pk).exists())

    def test_delete_role_can_delete_member_with_strategy(self):
        self.client.force_authenticate(user=self.deleter)

        response = self.client.post(
            f"/api/v1/members/{self.member.pk}/delete-with-strategy/", {"strategy": "unlink"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertFalse(Member.objects.filter(pk=self.member.pk).exists())

    def test_delete_role_cannot_delete_member_in_read_only_department(self):
        department_b = Department.objects.create(name="B", code="member-action-b")
        member_b = Member.objects.create(name="B", lastname="Member")
        member_b.departments.add(department_b)
        UserDepartmentRole.objects.create(user=self.deleter, department=department_b)
        self.client.force_authenticate(user=self.deleter)

        response = self.client.post(
            f"/api/v1/members/{member_b.pk}/delete-with-strategy/", {"strategy": "unlink"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Member.objects.filter(pk=member_b.pk).exists())
