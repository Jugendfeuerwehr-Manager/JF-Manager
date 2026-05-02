"""
Tests for email attachment feature and signature fix.
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from members.models import EmailAttachment, EmailMessage, Group, Member

User = get_user_model()


class EmailAttachmentTests(APITestCase):
    """Tests for the email attachment upload and sending feature."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123!",
        )
        self.admin_user.email_signature = "<p>Best regards, Admin</p>"
        self.admin_user.save()

        self.group = Group.objects.create(name="Test Group")
        self.member = Member.objects.create(
            name="Max",
            lastname="Mustermann",
            email="max@example.com",
            group=self.group,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
        self.send_url = "/api/v1/emails/send/"

    def _make_file(self, name="test.pdf", content=b"%PDF-1.4 test", content_type="application/pdf", size=None):
        if size:
            content = b"x" * size
        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_send_email_with_attachment(self):
        """Sending an email with a file attachment should succeed."""
        pdf = self._make_file()
        response = self.client.post(
            self.send_url,
            {
                "subject": "Test with attachment",
                "body_html": "<p>Hello {{vorname}}</p>",
                "recipient_type": "individual",
                "recipient_member": self.member.id,
                "attachments": [pdf],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        email_id = response.data["email"]["id"]
        email_msg = EmailMessage.objects.get(id=email_id)
        self.assertEqual(email_msg.attachments.count(), 1)
        att = email_msg.attachments.first()
        self.assertEqual(att.original_filename, "test.pdf")
        self.assertEqual(att.content_type, "application/pdf")

    def test_send_email_with_multiple_attachments(self):
        """Sending an email with multiple file attachments should succeed."""
        pdf = self._make_file("doc.pdf")
        img = self._make_file("photo.png", b"\x89PNG\r\n\x1a\n", "image/png")
        response = self.client.post(
            self.send_url,
            {
                "subject": "Multiple attachments",
                "body_html": "<p>See attached</p>",
                "recipient_type": "individual",
                "recipient_member": self.member.id,
                "attachments": [pdf, img],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        email_id = response.data["email"]["id"]
        self.assertEqual(EmailAttachment.objects.filter(email_message_id=email_id).count(), 2)

    def test_send_email_without_attachment(self):
        """Sending an email without attachments should still work."""
        response = self.client.post(
            self.send_url,
            {
                "subject": "No attachment",
                "body_html": "<p>Hello</p>",
                "recipient_type": "individual",
                "recipient_member": self.member.id,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        email_id = response.data["email"]["id"]
        self.assertEqual(EmailAttachment.objects.filter(email_message_id=email_id).count(), 0)

    def test_reject_disallowed_file_type(self):
        """Uploading a disallowed file type should return 400."""
        exe = self._make_file("virus.exe", b"MZ", "application/x-msdownload")
        response = self.client.post(
            self.send_url,
            {
                "subject": "Bad file",
                "body_html": "<p>Hello</p>",
                "recipient_type": "individual",
                "recipient_member": self.member.id,
                "attachments": [exe],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nicht erlaubt", response.data["error"])
        # Email should not have been created
        self.assertEqual(EmailMessage.objects.count(), 0)

    def test_reject_oversized_file(self):
        """Uploading a file exceeding 10 MB should return 400."""
        big_file = self._make_file("large.pdf", size=11 * 1024 * 1024)
        response = self.client.post(
            self.send_url,
            {
                "subject": "Big file",
                "body_html": "<p>Hello</p>",
                "recipient_type": "individual",
                "recipient_member": self.member.id,
                "attachments": [big_file],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("zu groß", response.data["error"])

    def test_attachments_in_detail_response(self):
        """Email detail response should include attachments list."""
        pdf = self._make_file()
        response = self.client.post(
            self.send_url,
            {
                "subject": "Detail test",
                "body_html": "<p>Hello</p>",
                "recipient_type": "individual",
                "recipient_member": self.member.id,
                "attachments": [pdf],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        email_data = response.data["email"]
        self.assertIn("attachments", email_data)
        self.assertEqual(len(email_data["attachments"]), 1)
        self.assertEqual(email_data["attachments"][0]["original_filename"], "test.pdf")


class SignatureNoDuplicationTests(APITestCase):
    """Tests ensuring signature is NOT added twice."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123!",
        )
        self.admin_user.email_signature = "<p>Best regards, Admin</p>"
        self.admin_user.save()

        self.group = Group.objects.create(name="Test Group")
        self.member = Member.objects.create(
            name="Max",
            lastname="Mustermann",
            email="max@example.com",
            group=self.group,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

    def test_signature_not_duplicated_on_send(self):
        """When body_html already contains signature, backend should not add it again."""
        body_with_sig = "<p>Hello {{vorname}}</p><br><br>---<br><p>Best regards, Admin</p>"
        response = self.client.post(
            "/api/v1/emails/send/",
            {
                "subject": "Sig test",
                "body_html": body_with_sig,
                "recipient_type": "individual",
                "recipient_member": self.member.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        email_id = response.data["email"]["id"]
        recipient = EmailMessage.objects.get(id=email_id).recipients.first()
        # Signature should appear exactly once
        sig_count = recipient.personalized_body_html.count("Best regards, Admin")
        self.assertEqual(sig_count, 1, f"Signature appeared {sig_count} times instead of 1")

    def test_signature_not_duplicated_on_preview(self):
        """Preview should not add signature on top of already-included one."""
        body_with_sig = "<p>Hello {{vorname}}</p><br><br>---<br><p>Best regards, Admin</p>"
        response = self.client.post(
            "/api/v1/emails/preview/",
            {
                "body_html": body_with_sig,
                "member_id": self.member.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sig_count = response.data["rendered_html"].count("Best regards, Admin")
        self.assertEqual(sig_count, 1, f"Signature appeared {sig_count} times instead of 1")
