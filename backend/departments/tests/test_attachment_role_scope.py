"""Attachment writes must follow the actual owner's department rights."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Attachment, Member


class AttachmentRoleScopeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        department_a = Department.objects.create(name="A", code="attachment-role-a")
        department_b = Department.objects.create(name="B", code="attachment-role-b")
        member_a = Member.objects.create(name="A", lastname="Member")
        cls.member_b = Member.objects.create(name="B", lastname="Member")
        member_a.departments.add(department_a)
        cls.member_b.departments.add(department_b)
        cls.attachment_b = Attachment.objects.create(content_object=cls.member_b, name="B document")

        cls.editor = get_user_model().objects.create_user(username="attachment-editor", password="test-only-password")
        group_a = Group.objects.create(name="Member editor A")
        group_a.permissions.add(
            Permission.objects.get(content_type__app_label="members", codename="view_member"),
            Permission.objects.get(content_type__app_label="members", codename="change_member"),
        )
        UserDepartmentRole.objects.create(user=cls.editor, department=department_a).groups.add(group_a)
        UserDepartmentRole.objects.create(user=cls.editor, department=department_b)

    def setUp(self):
        self.client.force_authenticate(user=self.editor)

    def test_member_attachment_upload_needs_target_department_edit_right(self):
        response = self.client.post(
            f"/api/v1/members/{self.member_b.pk}/attachments/", {"name": "New document"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Attachment.objects.count(), 1)

    def test_generic_attachment_change_needs_owner_department_edit_right(self):
        response = self.client.patch(
            f"/api/v1/attachments/{self.attachment_b.pk}/", {"name": "Changed"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.attachment_b.refresh_from_db()
        self.assertEqual(self.attachment_b.name, "B document")

    def test_generic_attachment_delete_needs_owner_department_edit_right(self):
        response = self.client.delete(f"/api/v1/attachments/{self.attachment_b.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Attachment.objects.filter(pk=self.attachment_b.pk).exists())
