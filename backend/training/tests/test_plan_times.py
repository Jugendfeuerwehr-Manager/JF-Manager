from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from training.models import TrainingBlock, TrainingSession


class PlanTimeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(get_user_model().objects.create_superuser(username="plan-times"))
        self.session = TrainingSession.objects.create(
            title="Testplan",
            date=date(2030, 1, 1),
            start_time=time(18),
            end_time=time(20),
        )
        self.block = TrainingBlock.objects.create(session=self.session, title="Block", duration_minutes=30)

    def test_session_requires_same_day_positive_duration(self):
        for end in ("18:00:00", "17:59:00", "00:01:00"):
            with self.subTest(end=end):
                response = self.client.patch(
                    f"/api/v1/training/sessions/{self.session.pk}/",
                    {"end_time": end},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
        self.session.refresh_from_db()
        self.assertEqual(self.session.end_time, time(20))

    def test_individual_block_writes_validate_entire_time_range(self):
        for values in ({"duration_minutes": 0}, {"start_offset_minutes": -1}, {"start_offset_minutes": 100}):
            with self.subTest(values=values):
                for suffix in ("", "move/"):
                    response = self.client.patch(
                        f"/api/v1/training/blocks/{self.block.pk}/{suffix}",
                        values,
                        format="json",
                    )
                    self.assertEqual(response.status_code, 400)
                response = self.client.post(
                    "/api/v1/training/blocks/",
                    {"title": "Invalid", "session": self.session.pk, "duration_minutes": 30, **values},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
        self.block.refresh_from_db()
        self.assertEqual(self.block.start_offset_minutes, 0)
        self.assertEqual(self.block.duration_minutes, 30)
        self.assertEqual(self.session.blocks.count(), 1)

    def test_session_shortening_cannot_leave_blocks_outside_frame(self):
        response = self.client.patch(
            f"/api/v1/training/sessions/{self.session.pk}/",
            {"end_time": "18:15:00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_block_can_end_exactly_at_session_end(self):
        response = self.client.patch(
            f"/api/v1/training/blocks/{self.block.pk}/move/",
            {"start_offset_minutes": 90},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        detail = self.client.get(f"/api/v1/training/sessions/{self.session.pk}/")
        self.assertEqual(detail.data["revision"], 1)
