from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from notifications.models import PushDelivery, PushSubscription
from notifications.services import deliver_pending
from settings_manager.models import PushConfiguration
from settings_manager.push_configuration import effective_push, generate_key_pair


@override_settings(WEB_PUSH_PUBLIC_KEY="", WEB_PUSH_PRIVATE_KEY="", WEB_PUSH_SUBJECT="")
class PushConfigurationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-push-admin")
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="settings_manager", codename__in=["view_all_settings", "change_all_settings"]
            )
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def generate(self):
        response = self.client.post(
            "/api/v1/settings/push/generate-keys/", {"subject": "mailto:synthetic@example.org"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def test_generated_private_key_is_encrypted_write_only_and_not_yet_enabled(self):
        response = self.generate()
        self.assertTrue(response.data["has_private_key"])
        self.assertFalse(response.data["enabled"])
        self.assertNotIn("private_key", response.data)
        private = PushConfiguration.objects.get().private_key
        with connection.cursor() as cursor:
            cursor.execute("SELECT private_key FROM settings_manager_pushconfiguration")
            self.assertNotEqual(cursor.fetchone()[0], private)
        for url in ["/api/v1/settings/push/", "/api/v1/settings/"]:
            self.assertNotIn(private, str(self.client.get(url).data))

    def test_keys_are_not_silently_replaced_and_invalid_partial_pair_is_atomic(self):
        self.generate()
        previous = PushConfiguration.objects.get().public_key
        self.assertEqual(
            self.client.post(
                "/api/v1/settings/push/generate-keys/", {"subject": "mailto:synthetic@example.org"}, format="json"
            ).status_code,
            400,
        )
        response = self.client.patch(
            "/api/v1/settings/push/", {"public_key": generate_key_pair()["public_key"]}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PushConfiguration.objects.get().public_key, previous)

    def test_enable_and_disable_change_actual_runtime_without_losing_keys(self):
        self.generate()
        response = self.client.patch("/api/v1/settings/push/", {"enabled": True}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(effective_push()["enabled"])
        self.client.patch("/api/v1/settings/push/", {"enabled": False}, format="json")
        self.assertFalse(effective_push()["enabled"])
        self.assertTrue(effective_push()["has_private_key"])

    @override_settings(
        WEB_PUSH_PUBLIC_KEY="host-public",
        WEB_PUSH_PRIVATE_KEY="host-private",
        WEB_PUSH_SUBJECT="mailto:host@example.org",
    )
    def test_host_keys_remain_locked_but_activation_is_web_configurable(self):
        response = self.client.get("/api/v1/settings/push/")
        self.assertTrue(response.data["enabled"])
        self.assertTrue(response.data["fields"]["private_key"]["locked"])
        self.assertNotIn("host-private", str(response.data))
        self.assertEqual(
            self.client.patch("/api/v1/settings/push/", {"private_key": "synthetic"}, format="json").status_code, 400
        )
        self.assertEqual(
            self.client.patch("/api/v1/settings/push/", {"enabled": False}, format="json").status_code, 200
        )
        self.assertFalse(effective_push()["enabled"])

    def test_invalid_contact_and_incomplete_activation_create_no_configuration(self):
        self.assertEqual(
            self.client.post(
                "/api/v1/settings/push/generate-keys/", {"subject": "http://example.org"}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(self.client.patch("/api/v1/settings/push/", {"enabled": True}, format="json").status_code, 400)
        self.assertFalse(PushConfiguration.objects.exists())

    @patch("pywebpush.webpush")
    def test_real_delivery_consumer_uses_the_db_key_and_subject(self, send):
        self.generate()
        self.client.patch("/api/v1/settings/push/", {"enabled": True}, format="json")
        subscription = PushSubscription.objects.create(
            user=self.user,
            endpoint="https://fcm.googleapis.com/fcm/send/synthetic",
            p256dh="synthetic",
            auth="synthetic",
        )
        PushDelivery.objects.create(subscription=subscription, kind="test", object_id=self.user.pk)
        self.assertEqual(deliver_pending(), 1)
        self.assertEqual(send.call_args.kwargs["vapid_private_key"], PushConfiguration.objects.get().private_key)
        self.assertEqual(send.call_args.kwargs["vapid_claims"]["sub"], "mailto:synthetic@example.org")

    def test_staff_alone_has_no_configuration_access(self):
        self.client.force_authenticate(
            get_user_model().objects.create_user(username="synthetic-push-staff", is_staff=True)
        )
        self.assertEqual(self.client.get("/api/v1/settings/push/").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/v1/settings/push/generate-keys/", {"subject": "mailto:synthetic@example.org"}, format="json"
            ).status_code,
            403,
        )

    def test_explicit_removal_disables_push_and_allows_a_new_key_pair(self):
        response = self.client.post(
            "/api/v1/settings/push/generate-keys/", {"subject": "mailto:synthetic@example.org"}, format="json"
        )
        original_public_key = response.data["public_key"]
        response = self.client.patch(
            "/api/v1/settings/push/",
            {"enabled": False, "public_key": "", "private_key": "", "subject": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["enabled"])
        self.assertFalse(response.data["has_private_key"])
        response = self.client.post(
            "/api/v1/settings/push/generate-keys/", {"subject": "mailto:synthetic@example.org"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotEqual(response.data["public_key"], original_public_key)
        self.assertNotIn("private_key", response.data)
