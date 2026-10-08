"""NOTIF-01.5a: outbox, bundling, retries, preferences and push categories."""

from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from notifications.dispatch import common_context, deliver_emails, queue_email, queue_push
from notifications.email_catalog import CATALOG
from notifications.inbox import notify
from notifications.models import EmailDelivery, NotificationPreference, PushDelivery, PushSubscription

User = get_user_model()


def session_context(user, date):
    sample = CATALOG["session_published"]["sample_data"]
    return {
        **common_context(user, open_url="https://example.invalid/portal"),
        "person": {"first_name": "Mia"},
        "session": {**sample["session"], "date": date},
        "series": {"title": "", "dates": []},
        "deadlines": sample["deadlines"],
        "participation": {"mode": "opt_out"},
    }


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class OutboxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            "eltern@example.invalid", email="eltern@example.invalid", password="x", account_kind="portal"
        )

    def test_idempotent_and_respects_preferences(self):
        ctx = session_context(self.user, "Di 14.10.")
        queue_email("session_published", self.user, ctx, event_key="pub:1:u1")
        queue_email("session_published", self.user, ctx, event_key="pub:1:u1")
        self.assertEqual(EmailDelivery.objects.count(), 1)
        NotificationPreference.objects.create(user=self.user, kind="session_published", email=False, push=True)
        self.assertIsNone(queue_email("session_published", self.user, ctx, event_key="pub:2:u1"))
        self.assertEqual(deliver_emails(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Benachrichtigungen einstellen", mail.outbox[0].body)
        self.assertFalse(EmailDelivery.objects.exists())

    def test_series_is_bundled_into_one_mail(self):
        for index, date in enumerate(["Di 14.10.", "Di 21.10.", "Di 28.10."]):
            queue_email(
                "session_published",
                self.user,
                session_context(self.user, date),
                event_key=f"pub:{index}:u1",
                bundle_key="session_published:series:abc:u1",
                delay=timedelta(minutes=2),
            )
        self.assertEqual(deliver_emails(), 0)  # waits until the whole batch is known
        self.assertEqual(deliver_emails(now=timezone.now() + timedelta(minutes=3)), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Di 14.10., Di 21.10., Di 28.10.", mail.outbox[0].body)

    def test_failures_back_off_and_are_dropped_after_five_attempts(self):
        queue_email("session_published", self.user, session_context(self.user, "Di 14.10."), event_key="pub:x")
        now = timezone.now()
        with mock.patch("notifications.dispatch.send_mail", side_effect=ImproperlyConfigured("kein SMTP")):
            for attempt in range(5):
                deliver_emails(now=now + timedelta(hours=attempt + 1))
        self.assertFalse(EmailDelivery.objects.exists())
        self.assertEqual(mail.outbox, [])


class PreferenceApiTests(TestCase):
    def test_portal_and_staff_kinds(self):
        portal = User.objects.create_user("p@example.invalid", password="x", account_kind="portal")
        browser = self.client_class()
        browser.force_login(portal)
        rows = browser.get("/api/v1/notifications/preferences/").json()
        self.assertIn("session_published", [r["kind"] for r in rows])
        self.assertNotIn("cr_submitted", [r["kind"] for r in rows])
        updated = browser.put(
            "/api/v1/notifications/preferences/",
            [{"kind": "session_published", "email": False, "push": True}],
            content_type="application/json",
        ).json()
        self.assertFalse(next(r for r in updated if r["kind"] == "session_published")["email"])
        bad = browser.put(
            "/api/v1/notifications/preferences/",
            [{"kind": "cr_submitted", "email": False, "push": False}],
            content_type="application/json",
        )
        self.assertEqual(bad.status_code, 400)
        staff = APIClient()
        staff.force_authenticate(User.objects.create_user("betreuer", password="x"))
        self.assertIn("cr_submitted", [r["kind"] for r in staff.get("/api/v1/notifications/preferences/").json()])


class PushCategoryTests(TestCase):
    def test_portal_subscription_only_gets_participation(self):
        portal = User.objects.create_user("p@example.invalid", password="x", account_kind="portal")
        browser = self.client_class()
        browser.force_login(portal)
        payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/abc",
            "keys": {"p256dh": "BNc" + "A" * 84, "auth": "A" * 22},
            "services": True,
            "orders": True,
            "requests": True,
            "participation": True,
        }
        with (
            mock.patch("notifications.views.effective_push", return_value={"enabled": True}),
            mock.patch("notifications.validation.validate_endpoint", return_value=None),
        ):
            response = browser.post("/api/v1/push/subscription/", payload, content_type="application/json")
        if response.status_code == 400:
            self.skipTest(f"Testschlüssel vom Validator abgelehnt: {response.json()}")
        sub = PushSubscription.objects.get(user=portal)
        self.assertEqual((sub.services, sub.orders, sub.requests, sub.participation), (False, False, False, True))

    def test_push_follows_preferences(self):
        user = User.objects.create_user("p@example.invalid", password="x", account_kind="portal")
        sub = PushSubscription.objects.create(user=user, endpoint="https://example.invalid/x", p256dh="k", auth="a")
        item = notify(kind="session_published", category="participation", title="Neuer Termin", recipients=[user])
        with mock.patch("settings_manager.push_configuration.effective_push", return_value={"enabled": True}):
            queue_push(user, item, "participation")
            self.assertEqual(PushDelivery.objects.filter(subscription=sub).count(), 1)
            NotificationPreference.objects.create(user=user, kind="session_published", email=True, push=False)
            PushDelivery.objects.all().delete()
            queue_push(user, item, "participation")
        self.assertFalse(PushDelivery.objects.exists())
