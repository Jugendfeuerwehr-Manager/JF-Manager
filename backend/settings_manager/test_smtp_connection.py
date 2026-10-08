from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient


class SMTPConnectionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user(username="synthetic-smtp-tester")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="settings_manager", codename="change_email_settings")
        )
        self.client.force_authenticate(user)

    @patch("jf_manager_backend.email_backend.ConfiguredSMTPBackend")
    def test_connection_test_never_sends_a_message(self, backend):
        response = self.client.post("/api/v1/settings/email/test-connection/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        backend.return_value.open.assert_called_once()
        backend.return_value.close.assert_called_once()
        backend.return_value.send_messages.assert_not_called()

    @patch("jf_manager_backend.email_backend.ConfiguredSMTPBackend")
    def test_test_message_requires_explicit_confirmation_and_valid_recipient(self, backend):
        for data in [
            {"recipient": "synthetic@example.org", "confirm_send": False},
            {"recipient": "invalid", "confirm_send": True},
        ]:
            self.assertEqual(
                self.client.post("/api/v1/settings/email/send-test/", data, format="json").status_code, 400
            )
        backend.assert_not_called()
        backend.return_value.send_messages.return_value = 1
        response = self.client.post(
            "/api/v1/settings/email/send-test/",
            {"recipient": "synthetic@example.org", "confirm_send": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        message = backend.return_value.send_messages.call_args.args[0][0]
        self.assertEqual(message.to, ["synthetic@example.org"])

    @patch("jf_manager_backend.email_backend.ConfiguredSMTPBackend")
    def test_provider_errors_are_sanitized_and_connection_closed(self, backend):
        backend.return_value.open.side_effect = Exception("synthetic-provider-secret-do-not-expose")
        response = self.client.post("/api/v1/settings/email/test-connection/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("synthetic-provider-secret", str(response.data))
        backend.return_value.close.assert_called_once()

    @patch("jf_manager_backend.email_backend.ConfiguredSMTPBackend")
    def test_ordinary_staff_cannot_trigger_connections_or_messages(self, backend):
        self.client.force_authenticate(
            get_user_model().objects.create_user(username="synthetic-smtp-staff", is_staff=True)
        )
        self.assertEqual(
            self.client.post("/api/v1/settings/email/test-connection/", {}, format="json").status_code, 403
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/settings/email/send-test/",
                {"recipient": "synthetic@example.org", "confirm_send": True},
                format="json",
            ).status_code,
            403,
        )
        backend.assert_not_called()
