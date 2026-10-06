import io
import shutil
import tempfile
from datetime import date, time, timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest import mock

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from servicebook.models import Service
from training.models import TrainingBlock, TrainingMedia, TrainingSession
from training.series import add_months

MEDIA = tempfile.mkdtemp(prefix="train-series-media-")


def png(name="bild.png"):
    stream = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(stream, "PNG")
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA)
class SeriesGenerationTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="series-test")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.department = Department.objects.create(name="Serie", code="series")
        self.root = TrainingSession.objects.create(
            title="Dienstabend",
            date=date(2099, 1, 31),
            start_time=time(18),
            end_time=time(20),
            department=self.department,
            recurrence_rule={"frequency": "MONTHLY", "end_date": "2099-05-31"},
        )
        self.block = TrainingBlock.objects.create(session=self.root, title="Knoten", duration_minutes=30)

    def url(self, session=None, action="series_preview"):
        return f"/api/v1/training/sessions/{(session or self.root).pk}/{action}/"

    def preview(self, session=None, **params):
        response = self.client.get(self.url(session), params)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def generate(self, token, session=None, **data):
        return self.client.post(self.url(session, "generate_series"), {"preview_token": token, **data}, format="json")

    def test_month_anchor_returns_to_original_day_including_leap_year(self):
        anchor = date(2099, 1, 31)
        self.assertEqual(
            [add_months(anchor, i) for i in range(1, 4)], [date(2099, 2, 28), date(2099, 3, 31), date(2099, 4, 30)]
        )
        self.assertEqual(add_months(date(2096, 1, 31), 1), date(2096, 2, 29))
        rows = self.preview()["occurrences"]
        self.assertEqual([row["date"] for row in rows], ["2099-02-28", "2099-03-31", "2099-04-30", "2099-05-31"])
        self.assertTrue(all(row["action"] == "new" for row in rows))

    def test_generation_requires_matching_preview_and_never_deletes(self):
        self.assertEqual(self.generate("").status_code, 400)
        stale = self.generate("0" * 64)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.data["code"], "series_preview_changed")
        self.assertFalse(self.root.series_children.exists())

        preview = self.preview()
        created = self.generate(preview["preview_token"])
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["created"], 4)
        self.root.refresh_from_db()
        self.assertIsNotNone(self.root.series_uuid)
        self.assertEqual(self.root.original_date, date(2099, 1, 31))
        children = list(self.root.series_children.order_by("date"))
        self.assertTrue(all(c.series_uuid == self.root.series_uuid and c.status == "draft" for c in children))
        self.assertEqual([c.original_date for c in children], [c.date for c in children])
        self.assertFalse(Service.objects.filter(training_session__in=children).exists())

        # A moved and edited occurrence keeps its plan; re-generation only reports it.
        moved = children[1]
        moved.date = date(2099, 4, 1)
        moved.title = "Verschoben"
        moved.save()
        moved_block = moved.blocks.get()
        again = self.preview()
        row = next(r for r in again["occurrences"] if r["date"] == "2099-03-31")
        self.assertEqual((row["action"], row["session_id"], row["actual_date"]), ("preserved", moved.pk, "2099-04-01"))
        self.assertEqual(again["counts"]["new"], 0)
        self.assertEqual(self.generate(again["preview_token"]).data["created"], 0)
        moved.refresh_from_db()
        self.assertEqual(moved.title, "Verschoben")
        self.assertTrue(TrainingBlock.objects.filter(pk=moved_block.pk).exists())
        self.assertEqual(self.root.series_children.count(), 4)

    def test_extending_series_only_adds_missing_dates(self):
        self.generate(self.preview()["preview_token"])
        existing = set(self.root.series_children.values_list("pk", flat=True))
        self.root.recurrence_rule = {"frequency": "MONTHLY", "end_date": "2099-07-31"}
        self.root.save()
        preview = self.preview()
        self.assertEqual(preview["counts"], {"new": 2, "preserved": 4, "skipped": 0, "conflict": 0})
        self.assertEqual(self.generate(preview["preview_token"]).data["created"], 2)
        self.assertTrue(existing < set(self.root.series_children.values_list("pk", flat=True)))

    def test_preview_changes_when_plan_changes_after_preview(self):
        token = self.preview()["preview_token"]
        self.root.revision += 1
        self.root.save()
        self.assertEqual(self.generate(token).status_code, 409)

    def test_bounds_and_invalid_rules_are_rejected_before_changes(self):
        self.root.recurrence_rule = {"frequency": "WEEKLY", "end_date": "2110-01-01"}
        self.root.save()
        # Without an explicit window the preview stops after 24 months / 200 occurrences.
        bounded = self.preview(window_start="2099-01-31")
        self.assertEqual(bounded["window_end"], "2101-01-31")
        self.assertEqual(len(bounded["occurrences"]), 104)
        response = self.client.get(self.url(), {"window_start": "2099-02-01", "window_end": "2101-03-01"})
        self.assertEqual(response.status_code, 400)
        self.root.recurrence_rule = {"frequency": "DAILY", "end_date": "2099-03-01"}
        self.root.save()
        self.assertEqual(self.client.get(self.url()).status_code, 400)
        response = self.client.patch(
            f"/api/v1/training/sessions/{self.root.pk}/",
            {"recurrence_rule": {"frequency": "YEARLY", "end_date": "2099-03-01"}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(
            f"/api/v1/training/sessions/{self.root.pk}/",
            {"recurrence_rule": {"frequency": "WEEKLY", "end_date": "2098-01-01"}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.root.series_children.exists())

    def test_occurrence_limit_rejects_before_changes(self):
        # 24 months bind first for all supported frequencies; the count limit stays a hard guard.
        with mock.patch("training.series.MAX_OCCURRENCES", 3):
            self.assertEqual(self.client.get(self.url()).status_code, 400)
        self.assertFalse(self.root.series_children.exists())

    def test_past_dates_are_skipped_and_conflicts_reported(self):
        past = date.today() - timedelta(days=21)
        self.root.date = past
        self.root.recurrence_rule = {"frequency": "WEEKLY", "end_date": (past + timedelta(days=42)).isoformat()}
        self.root.save()
        TrainingSession.objects.create(
            title="Andere Übung",
            date=past + timedelta(days=28),
            start_time=time(19),
            end_time=time(21),
            department=self.department,
        )
        rows = {row["date"]: row for row in self.preview(window_start=past.isoformat())["occurrences"]}
        self.assertEqual(rows[(past + timedelta(days=7)).isoformat()]["action"], "skipped")
        warned = rows[(past + timedelta(days=28)).isoformat()]
        self.assertEqual(warned["action"], "new")
        self.assertIn("Andere Übung", warned["warnings"][0])

    def test_generated_occurrence_has_independent_media_copy(self):
        media = TrainingMedia.objects.create(
            content_type=ContentType.objects.get_for_model(TrainingBlock), object_id=self.block.pk, file=png()
        )
        self.block.content = f'<p><img src="https://jf.example{media.url}"></p>'
        self.block.save()
        self.generate(self.preview()["preview_token"])
        child = self.root.series_children.order_by("date").first()
        copied_block = child.blocks.get()
        copy = TrainingMedia.objects.get(object_id=copied_block.pk)
        self.assertNotEqual(copy.file.name, media.file.name)
        self.assertIn(f'src="https://jf.example{copy.url}"', copied_block.content)
        self.assertNotIn(media.url + '"', copied_block.content)
        media.file.delete()
        media.delete()
        with copy.file.open("rb") as stream:
            self.assertTrue(stream.read().startswith(b"\x89PNG"))

    def test_generation_from_occurrence_uses_series_root(self):
        self.generate(self.preview()["preview_token"])
        child = self.root.series_children.order_by("date").first()
        self.assertEqual(self.preview(child)["root_id"], self.root.pk)

    def test_foreign_department_planner_cannot_generate(self):
        planner = get_user_model().objects.create_user(username="other-planner")
        other = Department.objects.create(name="Andere", code="other-series")
        UserDepartmentRole.objects.create(user=planner, department=other)
        self.client.force_authenticate(planner)
        self.assertIn(self.client.get(self.url()).status_code, (403, 404))


class SeriesMigrationTests(TestCase):
    def test_legacy_series_receive_identity_without_regeneration(self):
        parent = TrainingSession.objects.create(
            title="Alt", date=date(2099, 1, 1), start_time=time(18), end_time=time(20)
        )
        child = TrainingSession.objects.create(
            title="Alt", date=date(2099, 1, 8), start_time=time(18), end_time=time(20), series_parent=parent
        )
        duplicate = TrainingSession.objects.create(
            title="Alt", date=date(2099, 1, 8), start_time=time(18), end_time=time(20), series_parent=parent
        )
        single = TrainingSession.objects.create(
            title="Einzeln", date=date(2099, 1, 1), start_time=time(18), end_time=time(20)
        )
        migration = import_module("training.migrations.0006_training_series_identity")
        migration.preserve_existing_series(apps, SimpleNamespace(connection=connection))
        for session in (parent, child, duplicate, single):
            session.refresh_from_db()
        self.assertIsNotNone(parent.series_uuid)
        self.assertEqual({parent.series_uuid, child.series_uuid, duplicate.series_uuid}, {parent.series_uuid})
        self.assertEqual((parent.original_date, child.original_date), (parent.date, child.date))
        self.assertIsNone(duplicate.original_date)
        self.assertIsNone(single.series_uuid)
        self.assertEqual(TrainingSession.objects.count(), 4)
        self.assertEqual(parent.series_baseline_hash, "")
