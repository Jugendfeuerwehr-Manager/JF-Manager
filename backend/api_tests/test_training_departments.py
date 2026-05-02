from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department
from servicebook.models import Service
from training.models import TrainingSession


class TrainingDepartmentSeriesTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="training_admin",
            email="training_admin@example.com",
            password="pw12345",
        )
        self.client.force_authenticate(user=self.user)

        self.department = Department.objects.create(name="Abteilung Nord", code="nord")

        self.parent = TrainingSession.objects.create(
            title="Geratekunde",
            description="Serie",
            date=date(2026, 5, 1),
            start_time=time(18, 0),
            end_time=time(20, 0),
            department=self.department,
            recurrence_rule={"frequency": "WEEKLY", "end_date": "2026-05-31"},
            created_by=self.user,
        )

    def test_generate_series_inherits_department(self):
        response = self.client.post(f"/api/v1/training/sessions/{self.parent.id}/generate_series/")

        self.assertEqual(response.status_code, 201)
        children = TrainingSession.objects.filter(series_parent=self.parent)
        self.assertGreater(children.count(), 0)
        self.assertTrue(all(child.department_id == self.department.id for child in children))


class TrainingServicebookLinkTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="training_link_admin",
            email="training_link_admin@example.com",
            password="pw12345",
        )
        self.client.force_authenticate(user=self.user)

        self.department = Department.objects.create(name="Abteilung Sud", code="sud")

    def _create_session(self, **overrides):
        payload = {
            "title": "Dienst mit Theorie",
            "description": "Beschreibung",
            "date": "2030-03-15",
            "start_time": "18:00:00",
            "end_time": "20:00:00",
            "location": "Geratehaus",
            "notes": "",
            "group_ids": [],
            "department": self.department.id,
        }
        payload.update(overrides)
        response = self.client.post("/api/v1/training/sessions/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        return response.data["id"]

    def test_training_create_creates_linked_service(self):
        session_id = self._create_session()

        service = Service.objects.get(training_session_id=session_id)
        self.assertEqual(service.topic, "Dienst mit Theorie")
        self.assertEqual(service.place, "Geratehaus")
        self.assertEqual(service.department_id, self.department.id)

    def test_training_update_syncs_linked_service_fields(self):
        session_id = self._create_session()

        response = self.client.patch(
            f"/api/v1/training/sessions/{session_id}/",
            {
                "title": "Neuer Titel",
                "location": "Feuerwache",
                "date": "2030-03-16",
                "start_time": "19:00:00",
                "end_time": "21:00:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        service = Service.objects.get(training_session_id=session_id)
        self.assertEqual(service.topic, "Neuer Titel")
        self.assertEqual(service.place, "Feuerwache")
        self.assertEqual(service.start.date().isoformat(), "2030-03-16")

    def test_delete_training_future_option_deletes_linked_service(self):
        session_id = self._create_session(date="2099-01-01")

        response = self.client.delete(f"/api/v1/training/sessions/{session_id}/?delete_linked_service=true")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Service.objects.filter(training_session_id=session_id).exists())

    def test_delete_training_past_only_unlinks_service(self):
        session_id = self._create_session(date="2000-01-01")

        service = Service.objects.get(training_session_id=session_id)
        self.assertLess(service.start, timezone.now())

        response = self.client.delete(f"/api/v1/training/sessions/{session_id}/?delete_linked_service=true")
        self.assertEqual(response.status_code, 204)

        service.refresh_from_db()
        self.assertIsNone(service.training_session_id)
