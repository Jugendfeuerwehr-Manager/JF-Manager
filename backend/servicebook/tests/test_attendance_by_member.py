"""Tests for the attendance by_member endpoint."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from members.models import Member
from servicebook.models import Attendance, Service

User = get_user_model()


class AttendanceByMemberTestCase(TestCase):
    """Validate by_member endpoint behavior."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="attendance-user",
            email="attendance@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.user)

        self.member = Member.objects.create(name="Max", lastname="Mustermann")

        now = timezone.now()
        self.service1 = Service.objects.create(
            start=now - timedelta(days=3),
            end=now - timedelta(days=3) + timedelta(hours=2),
            topic="Dienst 1",
            place="Ort 1",
        )
        self.service2 = Service.objects.create(
            start=now - timedelta(days=2),
            end=now - timedelta(days=2) + timedelta(hours=2),
            topic="Dienst 2",
            place="Ort 2",
        )
        self.service3 = Service.objects.create(
            start=now - timedelta(days=1),
            end=now - timedelta(days=1) + timedelta(hours=2),
            topic="Dienst 3",
            place="Ort 3",
        )

        Attendance.objects.create(person=self.member, service=self.service1, state="A")
        Attendance.objects.create(person=self.member, service=self.service2, state="E")
        Attendance.objects.create(person=self.member, service=self.service3, state="F")

    def test_by_member_returns_limited_results_with_full_summary(self):
        response = self.client.get(
            "/api/v1/servicebook/attendances/by_member/",
            {"member_id": self.member.id, "limit": 2},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(len(payload["attendances"]), 2)
        self.assertEqual(payload["summary"]["total"], 3)
        self.assertEqual(payload["summary"]["present"], 1)
        self.assertEqual(payload["summary"]["excused"], 1)
        self.assertEqual(payload["summary"]["absent"], 1)

    def test_by_member_rejects_invalid_limit(self):
        response = self.client.get(
            "/api/v1/servicebook/attendances/by_member/",
            {"member_id": self.member.id, "limit": "abc"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("limit", response.json()["error"])
