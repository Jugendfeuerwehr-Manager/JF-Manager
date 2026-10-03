"""Sync actions require their declared action rights."""

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from external_sync.models import SyncJob


class SyncActionPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="A", code="sync-action-a")
        cls.job = SyncJob.objects.create(
            name="A job", provider=SyncJob.Provider.HI_ORG, scope=SyncJob.Scope.DEPARTMENT, department=cls.department
        )
        cls.creator = get_user_model().objects.create_user(username="sync-creator", password="test-only-password")
        group = Group.objects.create(name="Sync job creator A")
        group.permissions.add(Permission.objects.get(content_type__app_label="external_sync", codename="add_syncjob"))
        UserDepartmentRole.objects.create(user=cls.creator, department=cls.department).groups.add(group)

    def setUp(self):
        self.client.force_authenticate(user=self.creator)

    def test_add_right_does_not_allow_run_now(self):
        provider = Mock()
        provider.run.return_value = {"imported_members": 0}
        with patch("external_sync.api.viewsets.get_provider", return_value=provider):
            response = self.client.post(f"/api/v1/sync-jobs/{self.job.pk}/run_now/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        provider.run.assert_not_called()

    def test_add_right_does_not_allow_test_connection(self):
        provider = Mock()
        provider.test_connection.return_value = {"ok": True}
        with patch("external_sync.api.viewsets.get_provider", return_value=provider):
            response = self.client.post(f"/api/v1/sync-jobs/{self.job.pk}/test_connection/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        provider.test_connection.assert_not_called()

    def test_add_right_does_not_allow_garbage_collection(self):
        response = self.client.post(f"/api/v1/sync-jobs/{self.job.pk}/garbage-collect/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
