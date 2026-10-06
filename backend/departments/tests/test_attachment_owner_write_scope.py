"""Generic attachment writes need the change right in the owner's department (SEC-01.57c)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Attachment, Member
from qualifications.models import Qualification, QualificationType, SpecialTask, SpecialTaskType


def permissions(*names):
    return [
        Permission.objects.get(content_type__app_label=name.split(".")[0], codename=name.split(".")[1])
        for name in names
    ]


class AttachmentOwnerWriteScopeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="attachment-owner-a")
        cls.department_b = Department.objects.create(name="B", code="attachment-owner-b")
        cls.member_a = Member.objects.create(name="A", lastname="Member")
        cls.member_b = Member.objects.create(name="B", lastname="Member")
        cls.member_a.departments.add(cls.department_a)
        cls.member_b.departments.add(cls.department_b)
        course = QualificationType.objects.create(name="Course")
        duty = SpecialTaskType.objects.create(name="Duty")
        cls.qualification_a = Qualification.objects.create(
            member=cls.member_a, type=course, date_acquired=date(2026, 1, 1)
        )
        cls.qualification_b = Qualification.objects.create(
            member=cls.member_b, type=course, date_acquired=date(2026, 1, 1)
        )
        cls.task_b = SpecialTask.objects.create(member=cls.member_b, task=duty, start_date=date(2026, 1, 1))
        cls.attachment_a = Attachment.objects.create(content_object=cls.qualification_a, name="A certificate")
        cls.attachment_b = Attachment.objects.create(content_object=cls.qualification_b, name="B certificate")
        cls.task_attachment_b = Attachment.objects.create(content_object=cls.task_b, name="B duty")

        cls.user = get_user_model().objects.create_user(username="qualification-writer", password="test-only-password")
        writer_a = Group.objects.create(name="Qualification writer A")
        writer_a.permissions.add(
            *permissions(
                "members.view_member",
                "qualifications.view_qualification",
                "qualifications.change_qualification",
                "qualifications.view_specialtask",
                "qualifications.change_specialtask",
            )
        )
        reader_b = Group.objects.create(name="Qualification reader B")
        reader_b.permissions.add(
            *permissions("members.view_member", "qualifications.view_qualification", "qualifications.view_specialtask")
        )
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_a).groups.add(writer_a)
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_b).groups.add(reader_b)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_attachment_of_read_only_qualification_cannot_be_changed_or_deleted(self):
        change = self.client.patch(f"/api/v1/attachments/{self.attachment_b.pk}/", {"name": "changed"}, format="json")
        delete = self.client.delete(f"/api/v1/attachments/{self.attachment_b.pk}/")

        self.assertIn(change.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.assertIn(delete.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.attachment_b.refresh_from_db()
        self.assertEqual(self.attachment_b.name, "B certificate")

    def test_attachment_of_read_only_special_task_cannot_be_deleted(self):
        response = self.client.delete(f"/api/v1/attachments/{self.task_attachment_b.pk}/")

        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.assertTrue(Attachment.objects.filter(pk=self.task_attachment_b.pk).exists())

    def test_attachment_of_writable_qualification_can_be_changed(self):
        response = self.client.patch(f"/api/v1/attachments/{self.attachment_a.pk}/", {"name": "renamed"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_read_only_attachments_stay_visible(self):
        response = self.client.get(f"/api/v1/attachments/{self.attachment_b.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
