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

    def test_org_scope_without_global_model_right_stays_in_role_department(self):
        self.staff.user_permissions.add(Permission.objects.get(codename="can_access_all_departments"))
        self.client.force_authenticate(user=get_user_model().objects.get(pk=self.staff.pk))

        jobs = self.client.get("/api/v1/sync-jobs/")
        runs = self.client.get("/api/v1/sync-runs/")

        self.assertEqual(jobs.status_code, status.HTTP_200_OK, jobs.data)
        self.assertEqual(runs.status_code, status.HTTP_200_OK, runs.data)
        self.assertEqual({item["id"] for item in jobs.data["results"]}, {self.job_a.pk})
        self.assertEqual({item["id"] for item in runs.data["results"]}, {self.run_a.pk})

    def test_staff_role_cannot_create_organization_job_without_org_scope(self):
        role = self.staff.department_roles.get(department=self.department_a)
        role.groups.get().permissions.add(
            Permission.objects.get(content_type__app_label="external_sync", codename="add_syncjob")
        )
        self.client.force_authenticate(user=get_user_model().objects.get(pk=self.staff.pk))

        response = self.client.post(
            "/api/v1/sync-jobs/",
            {
                "name": "Not allowed",
                "provider": SyncJob.Provider.HI_ORG,
                "scope": SyncJob.Scope.ORGANIZATION,
                "run_mode": SyncJob.RunMode.MANUAL,
                "deletion_mode": SyncJob.DeletionMode.REVIEW,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(SyncJob.objects.filter(name="Not allowed").exists())
