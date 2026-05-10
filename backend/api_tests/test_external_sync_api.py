from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from departments.models import Department, UserDepartmentRole
from external_sync.models import SyncJob, SyncRun

User = get_user_model()


class ExternalSyncApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.department = Department.objects.create(name="Abteilung Nord", code="nord")

        self.staff_user = User.objects.create_user(
            username="sync_staff",
            email="sync-staff@test.com",
            password="staff123!",
            is_staff=True,
        )

        self.department_user = User.objects.create_user(
            username="sync_department",
            email="sync-department@test.com",
            password="dept123!",
        )

        sync_group = Group.objects.create(name="Sync Managers")
        sync_permissions = Permission.objects.filter(
            codename__in=[
                "view_syncjob",
                "add_syncjob",
                "change_syncjob",
                "view_syncrun",
            ]
        )
        sync_group.permissions.add(*sync_permissions)

        role = UserDepartmentRole.objects.create(user=self.department_user, department=self.department)
        role.groups.add(sync_group)

    def test_staff_user_can_create_organization_sync_job(self):
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.post(
            "/api/v1/sync-jobs/",
            {
                "name": "Spond Org Import",
                "provider": SyncJob.Provider.SPOND,
                "scope": SyncJob.Scope.ORGANIZATION,
                "run_mode": SyncJob.RunMode.MANUAL,
                "deletion_mode": SyncJob.DeletionMode.REVIEW,
                "enabled": True,
                "config": {"members": True, "groups": True, "group_id": "top-1"},
                "credentials": {"token": "secret-token"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SyncJob.objects.count(), 1)
        self.assertTrue(response.data["has_credentials"])
        self.assertNotIn("credentials", response.data)

    def test_department_user_can_create_department_sync_job(self):
        self.client.force_authenticate(user=self.department_user)

        response = self.client.post(
            "/api/v1/sync-jobs/",
            {
                "name": "Spond Dept Import",
                "provider": SyncJob.Provider.SPOND,
                "scope": SyncJob.Scope.DEPARTMENT,
                "department": self.department.id,
                "run_mode": SyncJob.RunMode.INTERVAL,
                "interval_minutes": 60,
                "deletion_mode": SyncJob.DeletionMode.REVIEW,
                "enabled": True,
                "config": {"group_id": "top-1"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SyncJob.objects.count(), 1)
        self.assertEqual(SyncJob.objects.get().department_id, self.department.id)

    def test_department_user_cannot_create_organization_sync_job(self):
        self.client.force_authenticate(user=self.department_user)

        response = self.client.post(
            "/api/v1/sync-jobs/",
            {
                "name": "Illegal Org Import",
                "provider": SyncJob.Provider.HI_ORG,
                "scope": SyncJob.Scope.ORGANIZATION,
                "run_mode": SyncJob.RunMode.MANUAL,
                "deletion_mode": SyncJob.DeletionMode.REVIEW,
                "enabled": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("scope", response.data)

    def test_run_now_records_failed_run_for_unimplemented_provider(self):
        job = SyncJob.objects.create(
            name="Hi Org Import",
            provider=SyncJob.Provider.HI_ORG,
            scope=SyncJob.Scope.ORGANIZATION,
            run_mode=SyncJob.RunMode.MANUAL,
            deletion_mode=SyncJob.DeletionMode.REVIEW,
            created_by=self.staff_user,
        )
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.post(f"/api/v1/sync-jobs/{job.id}/run_now/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
        self.assertEqual(SyncRun.objects.count(), 1)

        run = SyncRun.objects.get()
        job.refresh_from_db()

        self.assertEqual(run.status, SyncRun.Status.FAILED)
        self.assertIn("noch nicht implementiert", run.error_message)
        self.assertEqual(job.last_error, run.error_message)

    def test_test_connection_marks_job_as_failed_when_provider_missing(self):
        job = SyncJob.objects.create(
            name="Hi Org Import",
            provider=SyncJob.Provider.HI_ORG,
            scope=SyncJob.Scope.ORGANIZATION,
            run_mode=SyncJob.RunMode.MANUAL,
            deletion_mode=SyncJob.DeletionMode.REVIEW,
            created_by=self.staff_user,
        )
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.post(f"/api/v1/sync-jobs/{job.id}/test_connection/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
        job.refresh_from_db()
        self.assertFalse(job.last_test_status)
        self.assertIn("noch nicht implementiert", job.last_error)
        self.assertIsNotNone(job.last_tested_at)

    def test_run_now_serializes_datetime_values_in_summary(self):
        class DummyProvider:
            def run(self, job, triggered_by):
                now = timezone.now()
                return {
                    "started_at": now,
                    "finished_at": now,
                    "imported_members": 1,
                    "provider": "dummy",
                }

        job = SyncJob.objects.create(
            name="Spond Sync",
            provider=SyncJob.Provider.SPOND,
            scope=SyncJob.Scope.ORGANIZATION,
            run_mode=SyncJob.RunMode.MANUAL,
            deletion_mode=SyncJob.DeletionMode.REVIEW,
            created_by=self.staff_user,
        )
        self.client.force_authenticate(user=self.staff_user)

        with patch("external_sync.api.viewsets.get_provider", return_value=DummyProvider()):
            response = self.client.post(f"/api/v1/sync-jobs/{job.id}/run_now/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        run = SyncRun.objects.get(job=job)
        self.assertEqual(run.status, SyncRun.Status.SUCCEEDED)
        self.assertIsInstance(run.summary.get("started_at"), str)
        self.assertIsInstance(run.summary.get("finished_at"), str)

    def test_spond_top_level_groups_endpoint_accepts_post(self):
        class DummyProvider:
            def list_top_level_groups(self, credentials):
                return [{"id": "top-1", "name": "Top Level"}]

        self.client.force_authenticate(user=self.staff_user)

        with patch("external_sync.api.viewsets.get_provider", return_value=DummyProvider()):
            response = self.client.post(
                "/api/v1/sync-jobs/spond-top-level-groups/",
                {"username": "user@example.com", "password": "secret"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [{"id": "top-1", "name": "Top Level"}])
