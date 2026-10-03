"""Sync jobs and runs follow explicit organisation scope and model rights."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from external_sync.models import SyncJob, SyncRun


class SyncRolePermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="sync-role-a")
        cls.department_b = Department.objects.create(name="B", code="sync-role-b")
        cls.staff = get_user_model().objects.create_user(username="sync-role-staff", password="test-only-password")
        cls.staff.is_staff = True
        cls.staff.save(update_fields=["is_staff"])
        read_group = AuthGroup.objects.create(name="Sync reader A")
        read_group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="external_sync", codename__in=["view_syncjob", "view_syncrun"]
            )
        )
        UserDepartmentRole.objects.create(user=cls.staff, department=cls.department_a).groups.add(read_group)
        UserDepartmentRole.objects.create(user=cls.staff, department=cls.department_b)
        cls.job_a = SyncJob.objects.create(name="Job A", provider=SyncJob.Provider.HI_ORG,
                                           scope=SyncJob.Scope.DEPARTMENT, department=cls.department_a)
        cls.job_b = SyncJob.objects.create(name="Job B", provider=SyncJob.Provider.HI_ORG,
                                           scope=SyncJob.Scope.DEPARTMENT, department=cls.department_b)
        cls.run_a = SyncRun.objects.create(job=cls.job_a)
        cls.run_b = SyncRun.objects.create(job=cls.job_b)

    def test_staff_flag_does_not_expose_foreign_sync_job(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get("/api/v1/sync-jobs/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual({item["id"] for item in response.data["results"]}, {self.job_a.pk})

    def test_staff_flag_does_not_expose_foreign_sync_run(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get("/api/v1/sync-runs/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual({item["id"] for item in response.data["results"]}, {self.run_a.pk})
