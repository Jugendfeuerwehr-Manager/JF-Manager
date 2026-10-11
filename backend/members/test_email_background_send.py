"""UX-07.2: send member e-mails once per request key, in the background when a worker exists."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import EmailMessage, EmailRecipient, Group, Member
from members.services.email_service import MemberEmailService

URL = "/api/v1/emails/send/"


class BackgroundSendTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(name="A", code="bg-a")
        cls.group = Group.objects.create(name="Gruppe A", department=cls.dept)
        for name in ("Ada", "Ben"):
            member = Member.objects.create(
                name=name, lastname="Beispiel", email=f"{name.lower()}@example.test", group=cls.group
            )
            member.departments.add(cls.dept)
        cls.sender = get_user_model().objects.create_user(username="bg-sender", password="test-only-password")
        send_group = AuthGroup.objects.create(name="BG sender")
        send_group.permissions.add(Permission.objects.get(codename="can_send_member_emails"))
        UserDepartmentRole.objects.create(user=cls.sender, department=cls.dept).groups.add(send_group)

    def setUp(self):
        self.client.force_authenticate(self.sender)

    def send(self, key=None):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        payload = {
            "subject": "Info",
            "body_html": "<p>Hallo</p>",
            "body_text": "Hallo",
            "recipient_type": "group",
            "recipient_group": self.group.pk,
        }
        return self.client.post(f"{URL}?department={self.dept.pk}", payload, format="json", **headers)

    def test_repeated_request_with_the_same_key_sends_once(self):
        first = self.send("k-1")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(first.data["result"], {"successful": 2, "failed": 0})
        replay = self.send("k-1")
        self.assertEqual(replay.status_code, status.HTTP_200_OK)
        self.assertTrue(replay.data["replayed"])
        self.assertEqual(replay.data["email"]["id"], first.data["email"]["id"])
        self.assertEqual(EmailMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_a_second_run_never_sends_claimed_or_sent_recipients_again(self):
        response = self.send()
        message = EmailMessage.objects.get(pk=response.data["email"]["id"])
        self.assertEqual(len(mail.outbox), 2)
        EmailRecipient.objects.filter(email_message=message).update(status="pending")
        first = EmailRecipient.objects.filter(email_message=message).first()
        EmailRecipient.objects.filter(pk=first.pk).update(status="sending")  # claimed by a parallel run
        MemberEmailService.send_email_message(message)
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(EmailRecipient.objects.get(pk=first.pk).status, "sending")

    @override_settings(RQ_QUEUES={"default": {"URL": "redis://example.invalid:6379/0"}})
    def test_queues_the_send_when_a_worker_is_configured(self):
        with mock.patch("members.tasks.send_email_message_job.delay") as delay:
            response = self.send("k-queued")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        self.assertTrue(response.data["queued"])
        self.assertEqual(response.data["email"]["status"], "sending")
        delay.assert_called_once_with(response.data["email"]["id"])
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_retries_only_failed_and_reports_totals(self):
        response = self.send()
        message = EmailMessage.objects.get(pk=response.data["email"]["id"])
        failed = EmailRecipient.objects.filter(email_message=message).first()
        EmailRecipient.objects.filter(pk=failed.pk).update(status="failed", error_message="SMTP")
        mail.outbox.clear()
        result = self.client.post(f"/api/v1/emails/{message.pk}/resend/?department={self.dept.pk}")
        self.assertEqual(result.status_code, status.HTTP_200_OK, result.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(result.data["result"], {"successful": 2, "failed": 0})

    def test_department_from_the_query_is_stored_for_history_and_resend(self):
        response = self.send()
        message = EmailMessage.objects.get(pk=response.data["email"]["id"])
        self.assertEqual(message.department_id, self.dept.pk)
        listed = self.client.get(f"/api/v1/emails/?department={self.dept.pk}")
        self.assertIn(message.pk, [row["id"] for row in listed.data["results"]])

    def test_overlong_keys_are_rejected(self):
        self.assertEqual(self.send("x" * 129).status_code, status.HTTP_400_BAD_REQUEST)
