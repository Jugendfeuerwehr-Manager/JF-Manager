"""Qualifications and special tasks must use the related person's department rights."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member
from qualifications.models import Qualification, QualificationType, SpecialTask, SpecialTaskType


class QualificationRolePermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="qualification-role-a")
        cls.department_b = Department.objects.create(name="B", code="qualification-role-b")
        cls.member_a = Member.objects.create(name="A", lastname="Member")
        cls.member_a.departments.add(cls.department_a)
        cls.member_b = Member.objects.create(name="B", lastname="Member")
        cls.member_b.departments.add(cls.department_b)
        qualification_type = QualificationType.objects.create(name="Test type")
        task_type = SpecialTaskType.objects.create(name="Test task")
        cls.qualification_a = Qualification.objects.create(
            type=qualification_type, member=cls.member_a, date_acquired=date(2026, 1, 1)
        )
        cls.qualification_b = Qualification.objects.create(
            type=qualification_type, member=cls.member_b, date_acquired=date(2026, 1, 1)
        )
        cls.task_a = SpecialTask.objects.create(task=task_type, member=cls.member_a, start_date=date(2026, 1, 1))
        cls.task_b = SpecialTask.objects.create(task=task_type, member=cls.member_b, start_date=date(2026, 1, 1))

        cls.reader = get_user_model().objects.create_user(username="qualification-reader", password="test-only-password")
        role_a = AuthGroup.objects.create(name="Qualification reader A")
        role_a.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="qualifications",
                codename__in=["view_qualification", "view_specialtask"],
            )
        )
        UserDepartmentRole.objects.create(user=cls.reader, department=cls.department_a).groups.add(role_a)
        UserDepartmentRole.objects.create(user=cls.reader, department=cls.department_b)

    def test_qualification_list_excludes_department_without_model_right(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/v1/qualifications/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual({item["id"] for item in response.data["results"]}, {self.qualification_a.pk})

    def test_qualification_detail_denies_department_without_model_right(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.get(f"/api/v1/qualifications/{self.qualification_b.pk}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_qualification_statistics_exclude_department_without_model_right(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/v1/qualifications/statistics/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["total_qualifications"], 1)
        self.assertEqual(response.data["active_special_tasks"], 1)

    def test_special_task_list_excludes_department_without_model_right(self):
        self.client.force_authenticate(user=self.reader)

        response = self.client.get("/api/v1/qualifications/specialtasks/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual({item["id"] for item in response.data["results"]}, {self.task_a.pk})
