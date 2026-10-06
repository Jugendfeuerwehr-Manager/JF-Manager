from datetime import date, time
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department
from servicebook.models import Service, StaffAttendance
from training.models import TrainingBlock, TrainingSession
from training.workflow import sync_linked_service


class TrainingWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="workflow-test")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.session = TrainingSession.objects.create(
            title="Entwurf", date=date(2099, 1, 1), start_time=time(18), end_time=time(20)
        )
        self.url = f"/api/v1/training/sessions/{self.session.pk}/"

    def patch(self, **data):
        return self.client.patch(self.url, data, format="json")

    def test_draft_create_does_not_create_service(self):
        response = self.client.post(
            "/api/v1/training/sessions/",
            {
                "title": "Neu",
                "date": "2099-01-01",
                "start_time": "18:00",
                "end_time": "20:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "draft")
        self.assertIsNone(response.data["linked_service_id"])
        self.assertFalse(Service.objects.filter(training_session_id=response.data["id"]).exists())

    def publish(self):
        response = self.patch(status="published")
        self.assertEqual(response.status_code, 200, response.data)
        self.session.refresh_from_db()
        return Service.objects.get(training_session=self.session)

    def test_publish_edit_cancel_and_republish_preserve_identity(self):
        service = self.publish()
        self.assertEqual(self.patch(title="Anderer Titel").status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.topic, "Anderer Titel")
        for state in ("cancelled", "published", "completed"):
            response = self.patch(status=state)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["linked_service_id"], service.pk)
        self.assertEqual(Service.objects.filter(training_session=self.session).count(), 1)
        self.assertEqual(self.patch(status="draft").status_code, 400)

    def test_draft_cannot_complete_without_publication(self):
        self.assertEqual(self.patch(status="completed").status_code, 400)
        self.assertFalse(Service.objects.filter(training_session=self.session).exists())

    def test_past_plan_requires_confirmation_and_preserves_attendance(self):
        service = self.publish()
        self.session.date = date(2000, 1, 1)
        self.session.save()
        sync_linked_service(self.session)
        attendance = StaffAttendance.objects.create(service=service, person=self.user, state="A")
        response = self.client.get(self.url)
        self.assertTrue(response.data["requires_service_confirmation"])
        plan = {
            "expected_revision": response.data["revision"],
            "session": {
                "title": "Historische Korrektur",
                "date": "2000-01-01",
                "start_time": "18:00",
                "end_time": "20:00",
            },
            "blocks": [{"title": "Korrigierter Ablauf", "duration_minutes": 15}],
        }
        url = self.url + "plan/"
        self.assertEqual(self.client.put(url, plan, format="json").status_code, 400)
        self.assertEqual(self.session.blocks.count(), 0)
        plan["session"]["confirm_service_change"] = True
        result = self.client.put(url, plan, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["linked_service_id"], service.pk)
        attendance.refresh_from_db()
        self.assertEqual(attendance.state, "A")
        self.assertEqual(attendance.service_id, service.pk)

    def test_future_documented_service_cannot_change_department_or_be_deleted(self):
        service = self.publish()
        StaffAttendance.objects.create(service=service, person=self.user, state="E")
        department = Department.objects.create(name="Neue Abteilung", code="new-workflow")
        self.assertEqual(self.patch(department=department.pk, confirm_service_change=True).status_code, 400)
        self.assertEqual(self.patch(title="Unbestätigt").status_code, 400)
        self.assertEqual(self.patch(title="Bestätigt", confirm_service_change=True).status_code, 200)
        result = self.client.delete(self.url + "?delete_linked_service=true")
        self.assertEqual(result.status_code, 204)
        service.refresh_from_db()
        self.assertIsNone(service.training_session_id)
        self.assertEqual(service.staff_attendances.count(), 1)

    def test_legacy_block_mutations_require_confirmation(self):
        self.publish()
        self.session.date = date(2000, 1, 1)
        self.session.save()
        sync_linked_service(self.session)
        block = TrainingBlock.objects.create(session=self.session, title="Bestand", duration_minutes=15)
        url = f"/api/v1/training/blocks/{block.pk}/move/"
        self.assertEqual(self.client.patch(url, {"start_offset_minutes": 5}, format="json").status_code, 400)
        self.assertEqual(
            self.client.patch(
                url,
                {
                    "start_offset_minutes": 5,
                    "confirm_service_change": True,
                },
                format="json",
            ).status_code,
            200,
        )
        result = self.client.post(
            "/api/v1/training/blocks/",
            {
                "session": self.session.pk,
                "title": "Unbestätigt",
            },
            format="json",
        )
        self.assertEqual(result.status_code, 400)

    def test_migration_publishes_only_linked_sessions_without_regeneration(self):
        service = self.publish()
        TrainingSession.objects.filter(pk=self.session.pk).update(status="draft")
        draft = TrainingSession.objects.create(
            title="Ohne Dienst", date=date(2099, 1, 2), start_time=time(18), end_time=time(20)
        )
        migration = import_module("training.migrations.0005_trainingsession_status")
        migration.publish_linked_sessions(apps, SimpleNamespace(connection=connection))
        self.session.refresh_from_db()
        draft.refresh_from_db()
        self.assertEqual(self.session.status, "published")
        self.assertEqual(draft.status, "draft")
        self.assertEqual(Service.objects.get(training_session=self.session).pk, service.pk)
        self.assertEqual(self.session.series_children.count(), 0)
