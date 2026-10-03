"""Email previews require a sending right for the recipient's department."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import EmailMessage, Member


class EmailRolePermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="email-role-a")
        cls.department_b = Department.objects.create(name="B", code="email-role-b")
        cls.member_a = Member.objects.create(name="A", lastname="Member", email="a@example.test")
        cls.member_a.departments.add(cls.department_a)
        cls.member_b = Member.objects.create(name="B", lastname="Member", email="b@example.test")
        cls.member_b.departments.add(cls.department_b)

        cls.staff = get_user_model().objects.create_user(username="email-staff", password="test-only-password")
        cls.staff.is_staff = True
        cls.staff.save(update_fields=["is_staff"])
        UserDepartmentRole.objects.create(user=cls.staff, department=cls.department_a)

        cls.sender = get_user_model().objects.create_user(username="email-sender", password="test-only-password")
        send_group = AuthGroup.objects.create(name="Email sender A")
        send_group.permissions.add(Permission.objects.get(content_type__app_label="members", codename="can_send_member_emails"))
        UserDepartmentRole.objects.create(user=cls.sender, department=cls.department_a).groups.add(send_group)
        UserDepartmentRole.objects.create(user=cls.sender, department=cls.department_b)

    def preview(self, member):
        return self.client.post(
            "/api/v1/emails/preview/", {"body_html": "<p>Test</p>", "member_id": member.pk}, format="json"
        )

    def test_staff_flag_does_not_allow_email_preview(self):
        self.client.force_authenticate(user=self.staff)

        response = self.preview(self.member_a)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_department_sender_can_preview_member_in_own_department(self):
        self.client.force_authenticate(user=self.sender)

        response = self.preview(self.member_a)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_department_sender_cannot_preview_member_without_sending_right(self):
        self.client.force_authenticate(user=self.sender)

        response = self.preview(self.member_b)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_department_sender_sees_only_messages_from_sending_department(self):
        message_a = EmailMessage.objects.create(
            sender=self.sender, department=self.department_a, subject="A", body_html="<p>A</p>", recipient_type="all"
        )
        EmailMessage.objects.create(
            sender=self.sender, department=self.department_b, subject="B", body_html="<p>B</p>", recipient_type="all"
        )
        self.client.force_authenticate(user=self.sender)

        response = self.client.get("/api/v1/emails/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual({item["id"] for item in response.data["results"]}, {message_a.pk})

    def test_global_sending_right_still_obeys_department_scope(self):
        self.staff.user_permissions.add(
            Permission.objects.get(content_type__app_label="members", codename="can_send_member_emails")
        )
        self.client.force_authenticate(user=get_user_model().objects.get(pk=self.staff.pk))

        allowed = self.preview(self.member_a)
        denied = self.preview(self.member_b)

        self.assertEqual(allowed.status_code, status.HTTP_200_OK, allowed.data)
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)
