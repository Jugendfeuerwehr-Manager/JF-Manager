"""Tests for the date range filters behind the upcoming/past split of the service list."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from servicebook.models import Service

User = get_user_model()


class ServiceScopeFilterTestCase(TestCase):
    """Range lookups must filter instead of being silently ignored."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="scope-user",
            email="scope@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.user)

        self.now = timezone.now()
        self.past = Service.objects.create(
            start=self.now - timedelta(days=2),
            end=self.now - timedelta(days=2) + timedelta(hours=2),
            topic="Vergangen",
            place="Ort",
        )
        self.upcoming = Service.objects.create(
            start=self.now + timedelta(days=2),
            end=self.now + timedelta(days=2) + timedelta(hours=2),
            topic="Kommend",
            place="Ort",
        )

    def _topics(self, params):
        response = self.client.get("/api/v1/servicebook/services/", params)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data["results"] if isinstance(data, dict) else data
        return {item["topic"] for item in results}

    def test_upcoming_scope_excludes_past_services(self):
        self.assertEqual(self._topics({"end__gte": self.now.isoformat()}), {"Kommend"})

    def test_past_scope_excludes_upcoming_services(self):
        self.assertEqual(self._topics({"end__lte": self.now.isoformat()}), {"Vergangen"})

    def test_start_range_limits_to_window(self):
        params = {
            "start__gte": (self.now + timedelta(days=1)).isoformat(),
            "start__lte": (self.now + timedelta(days=3)).isoformat(),
        }
        self.assertEqual(self._topics(params), {"Kommend"})
