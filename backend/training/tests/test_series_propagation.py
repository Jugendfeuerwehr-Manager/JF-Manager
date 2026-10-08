from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department
from members.models import Group
from servicebook.models import Service
from training.models import TrainingBlock, TrainingSession


class SeriesPropagationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="propagation-test")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.department = Department.objects.create(name="Serie", code="propagation")
        self.root = TrainingSession.objects.create(
            title="Dienstabend",
            date=date(2099, 1, 5),
            start_time=time(18),
            end_time=time(20),
            department=self.department,
            recurrence_rule={"frequency": "WEEKLY", "end_date": "2099-02-02"},
        )
        TrainingBlock.objects.create(session=self.root, title="Knoten", duration_minutes=30)
        preview = self.client.get(f"/api/v1/training/sessions/{self.root.pk}/series_preview/").data
        self.client.post(
            f"/api/v1/training/sessions/{self.root.pk}/generate_series/",
            {"preview_token": preview["preview_token"]},
            format="json",
        )
        self.occurrences = list(TrainingSession.objects.filter(series_parent=self.root).order_by("date"))
        self.assertEqual(len(self.occurrences), 4)

    def save_plan(self, session, title, blocks, start="18:00:00", end="20:00:00"):
        session.refresh_from_db()
        response = self.client.put(
            f"/api/v1/training/sessions/{session.pk}/plan/",
            {
                "expected_revision": session.revision,
                "session": {
                    "title": title,
                    "date": str(session.date),
                    "start_time": start,
                    "end_time": end,
                    "department": self.department.pk,
                },
                "blocks": blocks,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def preview(self, session, **data):
        response = self.client.post(f"/api/v1/training/sessions/{session.pk}/propagation_preview/", data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def apply(self, session, token, **data):
        return self.client.post(
            f"/api/v1/training/sessions/{session.pk}/propagate_series/", {"preview_token": token, **data}, format="json"
        )

    def test_this_and_following_updates_only_later_unchanged_dates(self):
        first, second, third, fourth = self.occurrences
        # Third occurrence was edited individually and must be preserved by default.
        self.save_plan(third, "Sonderthema", [{"title": "Erste Hilfe", "duration_minutes": 60}])
        self.save_plan(second, "Neuer Ablauf", [{"title": "Leinen", "duration_minutes": 45}], "18:30:00", "20:30:00")
        preview = self.preview(second)
        rows = {row["session_id"]: row for row in preview["occurrences"]}
        self.assertNotIn(first.pk, rows)
        self.assertNotIn(self.root.pk, rows)
        self.assertEqual(rows[third.pk]["action"], "deviating")
        self.assertTrue(rows[third.pk]["overridable"])
        self.assertEqual(rows[fourth.pk]["action"], "update")
        self.assertIn("Zeit: 18:00–20:00 → 18:30–20:30", rows[fourth.pk]["changes"])
        self.assertTrue(any(change.startswith("Ablauf") for change in rows[fourth.pk]["changes"]))
        third_revision = TrainingSession.objects.get(pk=third.pk).revision

        response = self.apply(second, preview["preview_token"])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["session_ids"], [fourth.pk])
        fourth.refresh_from_db()
        third.refresh_from_db()
        first.refresh_from_db()
        self.assertEqual((fourth.title, fourth.start_time), ("Neuer Ablauf", time(18, 30)))
        self.assertEqual(list(fourth.blocks.values_list("title", flat=True)), ["Leinen"])
        self.assertEqual(fourth.date, date(2099, 2, 2))
        self.assertEqual((third.title, third.revision), ("Sonderthema", third_revision))
        self.assertEqual(first.title, "Dienstabend")

        # The updated occurrence counts as unchanged again; a repeated preview is a no-op.
        again = self.preview(second)
        self.assertEqual({row["session_id"]: row["action"] for row in again["occurrences"]}[fourth.pk], "unchanged")

    def test_deviating_dates_change_only_when_explicitly_selected(self):
        first, second, third, _ = self.occurrences
        self.save_plan(third, "Sonderthema", [])
        self.save_plan(second, "Neu", [])
        preview = self.preview(second, include_deviating=[third.pk])
        self.assertEqual({r["session_id"]: r["action"] for r in preview["occurrences"]}[third.pk], "update")
        self.assertEqual(self.apply(second, preview["preview_token"], include_deviating=[third.pk]).status_code, 200)
        third.refresh_from_db()
        self.assertEqual(third.title, "Neu")
        # Only deviating rows may be selected.
        response = self.client.post(
            f"/api/v1/training/sessions/{second.pk}/propagation_preview/",
            {"include_deviating": [first.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_moved_occurrence_is_deviating(self):
        _, second, third, _ = self.occurrences
        TrainingSession.objects.filter(pk=third.pk).update(date=date(2099, 1, 20))
        self.save_plan(second, "Neu", [])
        rows = {row["session_id"]: row for row in self.preview(second)["occurrences"]}
        self.assertEqual(rows[third.pk]["action"], "deviating")

    def test_history_and_documented_services_stay_untouched(self):
        _, second, third, fourth = self.occurrences
        group = Group.objects.create(name="JF", department=self.department)
        TrainingSession.objects.filter(pk=third.pk).update(status="completed")
        TrainingSession.objects.filter(pk=fourth.pk).update(status="published")
        fourth.refresh_from_db()
        service = Service.objects.create(
            training_session=fourth,
            start=timezone.make_aware(datetime.combine(fourth.date, time(18))),
            end=timezone.make_aware(datetime.combine(fourth.date, time(20))),
            topic="Dienstabend",
            department=self.department,
            events="Vorkommnis dokumentiert",
        )
        self.save_plan(second, "Neu", [])
        TrainingSession.objects.get(pk=second.pk).groups.add(group)
        preview = self.preview(second)
        rows = {row["session_id"]: row for row in preview["occurrences"]}
        self.assertEqual(rows[third.pk]["action"], "history")
        self.assertEqual(rows[fourth.pk]["action"], "history")
        self.assertFalse(rows[fourth.pk]["overridable"])
        response = self.client.post(
            f"/api/v1/training/sessions/{second.pk}/propagation_preview/",
            {"include_deviating": [fourth.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.apply(second, preview["preview_token"]).data["updated"], 0)
        service.refresh_from_db()
        self.assertEqual(service.topic, "Dienstabend")

    def test_published_future_occurrence_keeps_service_identity(self):
        _, second, third, _ = self.occurrences
        self.client.patch(f"/api/v1/training/sessions/{third.pk}/", {"status": "published"}, format="json")
        third.refresh_from_db()
        service = Service.objects.get(training_session=third)
        # Publishing alone is not a content deviation.
        self.save_plan(second, "Neu", [], "17:00:00", "19:00:00")
        preview = self.preview(second)
        self.assertEqual({r["session_id"]: r["action"] for r in preview["occurrences"]}[third.pk], "update")
        self.apply(second, preview["preview_token"])
        third.refresh_from_db()
        self.assertEqual(third.status, "published")
        refreshed = Service.objects.get(training_session=third)
        self.assertEqual(refreshed.pk, service.pk)
        self.assertEqual(timezone.localtime(refreshed.start).time(), time(17))

    def test_stale_preview_is_rejected_without_changes(self):
        _, second, third, _ = self.occurrences
        self.save_plan(second, "Neu", [])
        token = self.preview(second)["preview_token"]
        self.save_plan(third, "Parallel geändert", [])
        response = self.apply(second, token)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "series_preview_changed")
        third.refresh_from_db()
        self.assertEqual(third.title, "Parallel geändert")

    def test_past_occurrences_are_history(self):
        _, second, third, _ = self.occurrences
        past = timezone.localdate() - timedelta(days=1)
        TrainingSession.objects.filter(pk=third.pk).update(date=past)
        self.save_plan(second, "Neu", [])
        rows = {row["session_id"]: row for row in self.preview(second)["occurrences"]}
        self.assertEqual(rows[third.pk]["action"], "history")

    def test_standalone_session_cannot_propagate(self):
        single = TrainingSession.objects.create(
            title="Einzeln", date=date(2099, 3, 1), start_time=time(18), end_time=time(20), department=self.department
        )
        response = self.client.post(f"/api/v1/training/sessions/{single.pk}/propagation_preview/", {}, format="json")
        self.assertEqual(response.status_code, 400)
