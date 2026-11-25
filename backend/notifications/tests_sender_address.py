"""Mails sent outside a request (RQ worker) use the configured sender, not the settings fallback."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from django.test import TestCase, override_settings
from dynamic_preferences.registries import global_preferences_registry

from jf_manager_backend.email_backend import ConfiguredSMTPBackend, default_from_email
from notifications.dispatch import common_context, deliver_emails, queue_email
from notifications.email_catalog import CATALOG

User = get_user_model()
SENDER = "jugendfeuerwehr@example.invalid"


@override_settings(DEFAULT_FROM_EMAIL="webmaster@localhost")
class SenderAddressTests(TestCase):
    def setUp(self):
        global_preferences_registry.manager()["email__default_from_email"] = SENDER

    def test_default_from_email_reads_configured_sender(self):
        self.assertEqual(default_from_email(), SENDER)

    def test_falls_back_to_settings_without_configured_sender(self):
        global_preferences_registry.manager()["email__default_from_email"] = ""
        self.assertEqual(default_from_email(), "webmaster@localhost")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_worker_delivery_uses_configured_sender(self):
        user = User.objects.create_user("eltern@example.invalid", email="eltern@example.invalid", password="x")
        sample = CATALOG["session_published"]["sample_data"]
        context = {
            **common_context(user, open_url="https://example.invalid/portal"),
            "person": {"first_name": "Mia"},
            "session": {**sample["session"], "date": "Di 14.10."},
            "series": {"title": "", "dates": []},
            "deadlines": sample["deadlines"],
            "participation": {"mode": "opt_out"},
        }
        queue_email("session_published", user, context, event_key="pub:sender")
        self.assertEqual(deliver_emails(), 1)
        self.assertEqual(mail.outbox[0].from_email, SENDER)

    def test_smtp_backend_replaces_settings_fallback_sender(self):
        messages = [
            EmailMessage("a", "b", "webmaster@localhost", ["x@example.invalid"]),
            EmailMessage("a", "b", "explizit@example.invalid", ["x@example.invalid"]),
        ]
        with mock.patch.object(EmailBackend, "send_messages", return_value=2) as send:
            ConfiguredSMTPBackend().send_messages(messages)
        send.assert_called_once()
        self.assertEqual(messages[0].from_email, SENDER)
        self.assertEqual(messages[1].from_email, "explizit@example.invalid")
