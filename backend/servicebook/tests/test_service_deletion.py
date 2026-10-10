"""Deletion must remain bound to the service department and explicit delete rights."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Member
from servicebook.models import Attendance, Service


class ServiceDeletionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.department = Department.objects.create(name="Nord")
        self.other = Department.objects.create(name="Süd")
        now = timezone.now()
        self.service = Service.objects.create(start=now, end=now + timedelta(hours=2), department=self.department)
        self.url = f"/api/v1/servicebook/services/{self.service.pk}/"
        self.user = get_user_model().objects.create_user(username="delete-test")

    def grant(self, department, codename):
        group = Group.objects.create(name=f"{department.pk}-{codename}")
        group.permissions.add(Permission.objects.get(content_type__app_label="servicebook", codename=codename))
        role, _ = UserDepartmentRole.objects.get_or_create(user=self.user, department=department)
        role.groups.add(group)
        self.client.force_authenticate(get_user_model().objects.get(pk=self.user.pk))

    def test_anonymous_cannot_delete(self):
        self.assertEqual(self.client.delete(self.url).status_code, 401)
        self.assertTrue(Service.objects.filter(pk=self.service.pk).exists())

    def test_view_rights_do_not_allow_delete(self):
        self.grant(self.department, "view_service")
        self.assertEqual(self.client.delete(self.url).status_code, 403)
        self.assertTrue(Service.objects.filter(pk=self.service.pk).exists())

    def test_foreign_delete_rights_do_not_allow_delete(self):
        self.grant(self.department, "view_service")
        self.grant(self.other, "delete_service")
        self.assertIn(self.client.delete(self.url).status_code, (403, 404))
        self.assertTrue(Service.objects.filter(pk=self.service.pk).exists())

    def test_matching_delete_rights_remove_attendance(self):
        self.grant(self.department, "delete_service")
        member = Member.objects.create(name="Demo", lastname="Test")
        Attendance.objects.create(service=self.service, person=member, state="A")
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertFalse(Service.objects.filter(pk=self.service.pk).exists())
        self.assertFalse(Attendance.objects.filter(service_id=self.service.pk).exists())
        self.assertTrue(Member.objects.filter(pk=member.pk).exists())

    def test_admin_can_delete(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.delete(self.url).status_code, 204)
