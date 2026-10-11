"""UX-08.1: change preview before a sync run, nothing is stored."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from external_sync.models import SyncJob, SyncRun
from external_sync.services import ProviderRuntimeError
from members.models import Member


class FakeProvider:
    def run(self, job, triggered_by):
        Member.objects.create(name="Neu", lastname="Beispiel")
        return {"imported_members": 1, "updated_members": 2, "flagged_for_review": 3}


class SyncPreviewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(name="Mitte", code="sp-mitte")
        cls.job = SyncJob.objects.create(
            name="Spond", provider=SyncJob.Provider.SPOND, scope=SyncJob.Scope.DEPARTMENT, department=cls.dept
        )
        cls.runner = get_user_model().objects.create_user("sync-runner", password="x")
        role = AuthGroup.objects.create(name="Sync ausführen")
        role.permissions.add(
            Permission.objects.get(codename="run_syncjob"), Permission.objects.get(codename="view_syncjob")
        )
        UserDepartmentRole.objects.create(user=cls.runner, department=cls.dept).groups.add(role)
        cls.reader = get_user_model().objects.create_user("sync-reader", password="x")
        reader_role = AuthGroup.objects.create(name="Sync lesen")
        reader_role.permissions.add(Permission.objects.get(codename="view_syncjob"))
        UserDepartmentRole.objects.create(user=cls.reader, department=cls.dept).groups.add(reader_role)

    def url(self):
        return f"/api/v1/sync-jobs/{self.job.pk}/preview/?department={self.dept.pk}"

    def test_preview_reports_counts_and_stores_nothing(self):
        self.client.force_authenticate(self.runner)
        with mock.patch("external_sync.api.viewsets.get_provider", return_value=FakeProvider()):
            response = self.client.post(self.url(), {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["counts"]["imported_members"], 1)
        self.assertEqual(response.data["counts"]["flagged_for_review"], 3)
        self.assertEqual(response.data["counts"]["deleted_objects"], 0)
        self.assertFalse(Member.objects.filter(name="Neu").exists())
        self.assertFalse(SyncRun.objects.exists())

    def test_provider_errors_are_reported_without_a_run(self):
        self.client.force_authenticate(self.runner)
        failing = mock.Mock()
        failing.run.side_effect = ProviderRuntimeError("Spond nicht erreichbar")
        with mock.patch("external_sync.api.viewsets.get_provider", return_value=failing):
            response = self.client.post(self.url(), {}, format="json")
        self.assertEqual(response.status_code, 502)
        self.assertFalse(SyncRun.objects.exists())

    def test_requires_the_run_right(self):
        self.client.force_authenticate(self.reader)
        with mock.patch("external_sync.api.viewsets.get_provider", return_value=FakeProvider()) as provider:
            response = self.client.post(self.url(), {}, format="json")
        self.assertEqual(response.status_code, 403)
        provider.assert_not_called()
        self.client.force_authenticate(None)
        self.assertIn(self.client.post(self.url(), {}, format="json").status_code, (401, 403))
