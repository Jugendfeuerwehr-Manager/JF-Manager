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
        department_b = Department.objects.create(name="B", code="sync-action-b")
        cls.job_b = SyncJob.objects.create(
            name="B job", provider=SyncJob.Provider.HI_ORG, scope=SyncJob.Scope.DEPARTMENT, department=department_b
        )
        cls.creator = get_user_model().objects.create_user(username="sync-creator", password="test-only-password")
        group = Group.objects.create(name="Sync job creator A")
        group.permissions.add(Permission.objects.get(content_type__app_label="external_sync", codename="add_syncjob"))
        UserDepartmentRole.objects.create(user=cls.creator, department=cls.department).groups.add(group)
        cls.runner = get_user_model().objects.create_user(username="sync-runner", password="test-only-password")
        run_group = Group.objects.create(name="Sync job runner A")
        run_group.permissions.add(
            Permission.objects.get(content_type__app_label="external_sync", codename="run_syncjob")
        )
        UserDepartmentRole.objects.create(user=cls.runner, department=cls.department).groups.add(run_group)
        UserDepartmentRole.objects.create(user=cls.runner, department=department_b)

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

    def test_add_right_does_not_allow_garbage_collection_preview(self):
        response = self.client.get(f"/api/v1/sync-jobs/{self.job.pk}/garbage-collection-preview/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_run_right_allows_a_job_but_not_read_only_b_job(self):
        self.client.force_authenticate(user=self.runner)
        provider = Mock()
        provider.run.return_value = {"imported_members": 0}
        with patch("external_sync.api.viewsets.get_provider", return_value=provider):
            allowed = self.client.post(f"/api/v1/sync-jobs/{self.job.pk}/run_now/", {}, format="json")
            denied = self.client.post(f"/api/v1/sync-jobs/{self.job_b.pk}/run_now/", {}, format="json")

        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)
        provider.run.assert_called_once()

    def test_scoped_add_right_cannot_query_unbound_provider_groups(self):
        provider = Mock()
        provider.list_top_level_groups.return_value = []
        with patch("external_sync.api.viewsets.get_provider", return_value=provider):
            response = self.client.post(
                "/api/v1/sync-jobs/spond-top-level-groups/",
                {"username": "example", "password": "test-only-password"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        provider.list_top_level_groups.assert_not_called()

    def test_org_scope_and_add_right_cannot_query_provider_without_test_right(self):
        self.creator.user_permissions.add(Permission.objects.get(codename="can_access_all_departments"))
        self.creator.user_permissions.add(
            Permission.objects.get(content_type__app_label="external_sync", codename="add_syncjob")
        )
        provider = Mock()
        provider.list_top_level_groups.return_value = []
        with patch("external_sync.api.viewsets.get_provider", return_value=provider):
            response = self.client.post(
                "/api/v1/sync-jobs/spond-top-level-groups/",
                {"username": "example", "password": "test-only-password"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        provider.list_top_level_groups.assert_not_called()

    def test_scoped_test_right_without_org_scope_cannot_query_unbound_groups(self):
        role = self.runner.department_roles.get(department=self.department)
        role.groups.first().permissions.add(
            Permission.objects.get(content_type__app_label="external_sync", codename="test_syncjob")
        )
        self.client.force_authenticate(user=self.runner)
        response = self.client.post(
            "/api/v1/sync-jobs/spond-top-level-groups/",
            {"username": "example", "password": "test-only-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
