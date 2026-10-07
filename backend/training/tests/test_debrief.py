from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, RoleTemplate, UserDepartmentRole
from servicebook.models import Service
from training.models import TrainingDebrief, TrainingSession
from training.workflow import sync_linked_service


class DebriefTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from io import StringIO

        from django.core.management import call_command

        call_command("seed_role_templates", stdout=StringIO())

    def setUp(self):
        User = get_user_model()
        self.department = Department.objects.create(name="Nachbereitung", code="debrief")
        self.planner = User.objects.create_user(username="nach-planer", first_name="Pia", last_name="Planer")
        UserDepartmentRole.objects.create(user=self.planner, department=self.department).groups.add(
            RoleTemplate.objects.get(key="training_planner").group
        )
        self.client = APIClient()
        self.client.force_authenticate(self.planner)
        self.session = self.held(date(2026, 1, 13))

    def held(self, day, status="published"):
        session = TrainingSession.objects.create(
            title="Gehaltene Übung", date=day, start_time=time(18), end_time=time(20), department=self.department
        )
        if status == "published":
            session.status = status
            session.save()
            sync_linked_service(session)
        return session

    def url(self, session=None):
        return f"/api/v1/training/sessions/{(session or self.session).pk}/debrief/"

    def put(self, session=None, **data):
        payload = {"expected_revision": 0, "actual_start": "18:05", "actual_end": "20:15", **data}
        return self.client.put(self.url(session), payload, format="json")

    def test_saves_actual_times_apart_from_plan_with_revision(self):
        empty = self.client.get(self.url()).data
        self.assertEqual((empty["revision"], empty["planned_minutes"], empty["actual_minutes"]), (0, 120, None))
        response = self.put(reflection="Gut geklappt", improvements="Mehr Leinen")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            (response.data["revision"], response.data["actual_minutes"], response.data["planned_minutes"]),
            (1, 130, 120),
        )
        self.assertEqual(response.data["updated_by_name"], "Pia Planer")
        self.session.refresh_from_db()
        # Plan time and plan version are untouched.
        self.assertEqual(
            (self.session.start_time, self.session.end_time, self.session.revision), (time(18), time(20), 1)
        )

    def test_stale_revision_is_rejected_with_current_state(self):
        self.put(reflection="Erste Fassung")
        response = self.put(reflection="Überschreiben?")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["current"]["reflection"], "Erste Fassung")
        self.assertEqual(TrainingDebrief.objects.get().reflection, "Erste Fassung")
        self.assertEqual(self.put(expected_revision=1, reflection="Zweite Fassung").data["revision"], 2)

    def test_rejects_invalid_times_drafts_and_future_exercises(self):
        self.assertEqual(self.put(actual_start="20:00", actual_end="19:00").status_code, 400)
        self.assertEqual(self.put(actual_start="18:00", actual_end=None).status_code, 400)
        draft = self.held(date(2026, 1, 14), status="draft")
        self.assertEqual(self.put(draft).status_code, 400)
        future = self.held(timezone.localdate() + timedelta(days=3))
        self.assertEqual(self.put(future).status_code, 400)
        self.assertFalse(TrainingDebrief.objects.exists())
        # Without actual times the follow-up can still be saved.
        self.assertEqual(self.put(actual_start=None, actual_end=None, reflection="Nur Notiz").status_code, 200)

    def test_complete_together_keeps_service_and_attendance(self):
        service = Service.objects.get(training_session=self.session)
        response = self.put(complete=True, reflection="Fertig")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["session_status"], "completed")
        self.session.refresh_from_db()
        self.assertEqual((self.session.status, self.session.revision), ("completed", 2))
        self.assertTrue(Service.objects.filter(pk=service.pk, training_session=self.session).exists())
        # Later edits of a completed exercise stay possible.
        self.assertEqual(self.put(expected_revision=1, improvements="Nachtrag").status_code, 200)

    def test_only_planners_read_and_write_and_copies_never_carry_it(self):
        self.put(reflection="Intern")
        reader = get_user_model().objects.create_user(username="nach-leser")
        reader.user_permissions.add(Permission.objects.get(codename="view_trainingsession"))
        UserDepartmentRole.objects.create(user=reader, department=self.department)
        other = APIClient()
        other.force_authenticate(reader)
        self.assertEqual(other.get(self.url()).status_code, 403)
        self.assertEqual(other.put(self.url(), {"expected_revision": 1}, format="json").status_code, 403)
        copy = self.client.post(
            f"/api/v1/training/sessions/{self.session.pk}/copy/", {"date": "2099-01-01"}, format="json"
        )
        self.assertEqual(copy.status_code, 201, copy.data)
        self.assertFalse(TrainingDebrief.objects.filter(session_id=copy.data["id"]).exists())
