"""Creating a service can publish its exercise in the training calendar at the same time."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from servicebook.models import Service
from training.models import TrainingSession

User = get_user_model()
URL = "/api/v1/servicebook/services/"
# 17:00 UTC = 18:00 Europe/Berlin in November.
PAYLOAD = {
    "start": "2026-12-01T17:00:00Z",
    "end": "2026-12-01T19:00:00Z",
    "topic": "Knoten und Stiche",
    "place": "Gerätehaus",
    "description": "Grundlagen",
    "events": "Keine",
    "create_training_session": True,
}


class ServiceCreateTrainingSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(name="Süd-Ost", code="so")
        cls.foreign = Department.objects.create(name="Nord", code="no")
        service_perms = Permission.objects.filter(
            content_type__app_label="servicebook", codename__in=["add_service", "view_service", "change_service"]
        )
        planner = Group.objects.create(name="Planung")
        planner.permissions.set(
            Permission.objects.filter(content_type__app_label="training", codename="can_manage_training")
        )

        cls.writer = User.objects.create_user("writer")
        cls.writer.user_permissions.set(service_perms)
        UserDepartmentRole.objects.create(user=cls.writer, department=cls.dept)

        cls.planner = User.objects.create_user("planner")
        cls.planner.user_permissions.set(service_perms)
        role = UserDepartmentRole.objects.create(user=cls.planner, department=cls.dept)
        role.groups.add(planner)
        # Rights in the foreign department cover the service, not the exercise.
        UserDepartmentRole.objects.create(user=cls.planner, department=cls.foreign)

    def post(self, user, data=None):
        client = APIClient()
        if user:
            client.force_authenticate(user)
        return client.post(URL, {**PAYLOAD, "department": self.dept.pk, **(data or {})}, format="json")

    def assertNothingCreated(self):
        self.assertFalse(Service.objects.exists())
        self.assertFalse(TrainingSession.objects.exists())

    def test_anonymous_is_rejected(self):
        self.assertIn(self.post(None).status_code, (401, 403))
        self.assertNothingCreated()

    def test_without_training_right_is_rejected(self):
        response = self.post(self.writer)
        self.assertEqual(response.status_code, 403)
        self.assertNothingCreated()

    def test_training_right_of_another_department_does_not_count(self):
        response = self.post(self.planner, {"department": self.foreign.pk})
        self.assertEqual(response.status_code, 403)
        self.assertNothingCreated()

    def test_creates_published_exercise_with_linked_service(self):
        response = self.post(self.planner, {"operations_manager_ids": [self.writer.pk]})
        self.assertEqual(response.status_code, 201)
        session = TrainingSession.objects.get()
        service = Service.objects.get(pk=response.data["id"])
        self.assertEqual(response.data["training_session"], session.pk)
        self.assertEqual(service.training_session_id, session.pk)
        self.assertEqual(session.status, TrainingSession.Status.PUBLISHED)
        self.assertEqual(session.department_id, self.dept.pk)
        self.assertEqual(session.created_by, self.planner)
        self.assertEqual(
            (session.title, session.location, session.description), ("Knoten und Stiche", "Gerätehaus", "Grundlagen")
        )
        self.assertEqual(str(session.date), "2026-12-01")
        self.assertEqual((str(session.start_time), str(session.end_time)), ("18:00:00", "20:00:00"))
        self.assertEqual(service.start.isoformat(), "2026-12-01T17:00:00+00:00")
        self.assertEqual(service.events, "Keine")
        self.assertEqual(list(service.operations_manager.all()), [self.writer])

    def test_service_rights_are_still_checked(self):
        self.planner.user_permissions.remove(Permission.objects.get(codename="add_service"))
        response = self.post(self.planner)
        self.assertEqual(response.status_code, 403)
        self.assertNothingCreated()

    def test_multi_day_service_is_rejected(self):
        response = self.post(self.planner, {"end": "2026-12-02T09:00:00Z"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("create_training_session", response.data)
        self.assertNothingCreated()

    def test_organisation_wide_service_is_rejected(self):
        admin = User.objects.create_superuser("admin", password="x")
        response = self.post(admin, {"department": None})
        self.assertEqual(response.status_code, 400)
        self.assertIn("create_training_session", response.data)
        self.assertNothingCreated()

    def test_topic_is_required(self):
        response = self.post(self.planner, {"topic": "  "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("topic", response.data)
        self.assertNothingCreated()

    def test_without_flag_no_exercise_is_created(self):
        response = self.post(self.planner, {"create_training_session": False})
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(Service.objects.get().training_session_id)
        self.assertFalse(TrainingSession.objects.exists())
