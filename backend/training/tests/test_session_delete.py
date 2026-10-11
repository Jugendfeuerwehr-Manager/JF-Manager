"""NOTIF-02: the planning right of the department is enough to delete an exercise."""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, RoleTemplate, UserDepartmentRole
from training.models import TrainingSession

User = get_user_model()


class SessionDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.dept = Department.objects.create(name="A", code="a")
        cls.other = Department.objects.create(name="B", code="b")
        planner_group = RoleTemplate.objects.get(key="training_planner").group
        cls.planner = User.objects.create_user("planer")
        UserDepartmentRole.objects.create(user=cls.planner, department=cls.dept).groups.add(planner_group)
        cls.foreign = User.objects.create_user("planer-b")
        UserDepartmentRole.objects.create(user=cls.foreign, department=cls.other).groups.add(planner_group)
        readers = AuthGroup.objects.create(name="Leser")
        readers.permissions.add(Permission.objects.get(codename="view_trainingsession"))
        cls.reader = User.objects.create_user("leser")
        UserDepartmentRole.objects.create(user=cls.reader, department=cls.dept).groups.add(readers)

    def setUp(self):
        self.session = TrainingSession.objects.create(
            title="Löschtest",
            date=timezone.localdate() + timedelta(days=5),
            start_time="18:00",
            end_time="19:00",
            department=self.dept,
            status="published",
        )
        self.url = f"/api/v1/training/sessions/{self.session.pk}/"

    def delete_as(self, user):
        client = APIClient()
        client.force_login(user)
        return client.delete(self.url)

    def test_planner_role_can_delete_without_a_separate_delete_right(self):
        self.assertFalse(self.planner.has_perm("training.delete_trainingsession"))
        self.assertEqual(self.delete_as(self.planner).status_code, 204)
        self.assertFalse(TrainingSession.objects.filter(pk=self.session.pk).exists())

    def test_other_department_and_readers_cannot_delete(self):
        self.assertIn(self.delete_as(self.foreign).status_code, (403, 404))
        self.assertEqual(self.delete_as(self.reader).status_code, 403)
        self.assertTrue(TrainingSession.objects.filter(pk=self.session.pk).exists())
