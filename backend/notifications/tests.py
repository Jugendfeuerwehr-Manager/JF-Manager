import base64
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from servicebook.models import Service

from .models import PushDelivery, PushSubscription
from .services import deliver_pending, enqueue_event


@override_settings(WEB_PUSH_PUBLIC_KEY="public", WEB_PUSH_PRIVATE_KEY="private", WEB_PUSH_SUBJECT="mailto:test@example.org")
class PushTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username="leader")
        self.other = get_user_model().objects.create_user(username="other")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.endpoint = "https://fcm.googleapis.com/fcm/send/example"
        def encode(value):
            return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
        self.payload = {"endpoint": self.endpoint, "keys": {"p256dh": encode(b"\x04" + b"a" * 64), "auth": encode(b"b" * 16)}}

    def subscribe(self):
        response = self.client.post("/api/v1/push/subscription/", self.payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return PushSubscription.objects.get(user=self.user)

    def test_authentication_required(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/v1/push/config/").status_code, 401)

    def test_subscription_is_owned_and_cannot_be_stolen(self):
        subscription = self.subscribe()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post("/api/v1/push/subscription/", self.payload, format="json").status_code, 409)
        self.client.delete("/api/v1/push/subscription/", {"endpoint": self.endpoint}, format="json")
        self.assertTrue(PushSubscription.objects.filter(pk=subscription.pk).exists())
        self.assertFalse(self.client.get("/api/v1/push/subscription/", {"endpoint": self.endpoint}).data["subscribed"])

    def test_rejects_ssrf_and_bad_keys(self):
        for endpoint in ("http://fcm.googleapis.com/a", "https://127.0.0.1/a", "https://fcm.googleapis.com.attacker.test/a", "https://fcm.googleapis.com:8443/a", "https://user@fcm.googleapis.com/a"):
            self.payload["endpoint"] = endpoint
            self.assertEqual(self.client.post("/api/v1/push/subscription/", self.payload, format="json").status_code, 400)
        self.payload["endpoint"] = self.endpoint
        self.payload["keys"]["auth"] = "invalid"
        self.assertEqual(self.client.post("/api/v1/push/subscription/", self.payload, format="json").status_code, 400)

    def make_service(self):
        department = Department.objects.create(name="Nord", code="nord")
        role = UserDepartmentRole.objects.create(user=self.user, department=department)
        group = Group.objects.create(name="Leitung")
        group.permissions.add(Permission.objects.get(codename="view_service", content_type__app_label="servicebook"))
        role.groups.add(group)
        service = Service.objects.create(start=timezone.now(), end=timezone.now()+timedelta(hours=2), department=department)
        return service, role

    def test_department_permissions_and_preferences(self):
        subscription = self.subscribe()
        service, role = self.make_service()
        enqueue_event("services", service.pk)
        enqueue_event("services", service.pk)
        self.assertEqual(PushDelivery.objects.count(), 1)
        PushDelivery.objects.all().delete()
        role.delete()
        enqueue_event("services", service.pk)
        self.assertFalse(PushDelivery.objects.exists())
        subscription.services = False
        subscription.save()
        enqueue_event("services", service.pk)
        self.assertFalse(PushDelivery.objects.exists())

    @patch("pywebpush.webpush")
    def test_delivery_rechecks_permissions(self, send):
        self.subscribe()
        service, role = self.make_service()
        enqueue_event("services", service.pk)
        role.delete()
        deliver_pending()
        send.assert_not_called()
        self.assertFalse(PushDelivery.objects.exists())

    @patch("pywebpush.webpush")
    def test_delivery_generic_payload_and_cleanup(self, send):
        subscription = self.subscribe()
        PushDelivery.objects.create(subscription=subscription, kind="test", object_id=self.user.pk)
        self.assertEqual(deliver_pending(), 1)
        self.assertNotIn(self.user.username, send.call_args.kwargs["data"])
        self.assertEqual(send.call_args.kwargs["timeout"], 10)
        self.assertFalse(PushDelivery.objects.exists())

    @patch("pywebpush.webpush")
    def test_expired_provider_subscription_removed(self, send):
        from pywebpush import WebPushException
        from requests import Response
        response = Response()
        response.status_code = 410
        send.side_effect = WebPushException("expired", response=response)
        subscription = self.subscribe()
        PushDelivery.objects.create(subscription=subscription, kind="test", object_id=self.user.pk)
        deliver_pending()
        self.assertFalse(PushSubscription.objects.exists())

    @patch("pywebpush.webpush")
    def test_transient_failure_retries_later(self, send):
        from pywebpush import WebPushException
        send.side_effect = WebPushException("temporary")
        subscription = self.subscribe()
        PushDelivery.objects.create(subscription=subscription, kind="test", object_id=self.user.pk)
        deliver_pending()
        delivery = PushDelivery.objects.get()
        self.assertEqual(delivery.attempts, 1)
        self.assertGreater(delivery.available_at, timezone.now())

    def test_service_event_only_enqueues_after_commit(self):
        self.subscribe()
        service, _ = self.make_service()
        with self.captureOnCommitCallbacks(execute=True):
            service.topic = "Löschübung"
            service.save()
        self.assertEqual(PushDelivery.objects.count(), 1)
