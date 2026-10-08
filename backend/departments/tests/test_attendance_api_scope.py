"""The generic attendance API follows department roles and the service's department (SEC-01.57)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member
from servicebook.models import Attendance, Service


def permissions(*codenames):
    return [Permission.objects.get(content_type__app_label="servicebook", codename=codename) for codename in codenames]


class AttendanceApiScopeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="attendance-api-a")
        cls.department_b = Department.objects.create(name="B", code="attendance-api-b")
        cls.member_a = Member.objects.create(name="Anna", lastname="A")
        cls.member_a2 = Member.objects.create(name="Arne", lastname="A")
        cls.member_b = Member.objects.create(name="Berta", lastname="B")
        cls.member_a.departments.add(cls.department_a)
        cls.member_a2.departments.add(cls.department_a)
        cls.member_b.departments.add(cls.department_b)
        now = timezone.now()
        cls.service_a = Service.objects.create(start=now, end=now + timedelta(hours=2), department=cls.department_a)
        cls.service_b = Service.objects.create(start=now, end=now + timedelta(hours=2), department=cls.department_b)
        cls.attendance_a = Attendance.objects.create(service=cls.service_a, person=cls.member_a, state="F")
        cls.attendance_b = Attendance.objects.create(service=cls.service_b, person=cls.member_b, state="F")

        cls.leader = get_user_model().objects.create_user(username="attendance-leader", password="test-only-password")
        writer_a = AuthGroup.objects.create(name="Attendance writer A")
        writer_a.permissions.add(
            *permissions("view_service", "view_attendance", "add_attendance", "change_attendance", "delete_attendance")
        )
        viewer_b = AuthGroup.objects.create(name="Attendance viewer B")
        viewer_b.permissions.add(*permissions("view_service", "view_attendance"))
        UserDepartmentRole.objects.create(user=cls.leader, department=cls.department_a).groups.add(writer_a)
        UserDepartmentRole.objects.create(user=cls.leader, department=cls.department_b).groups.add(viewer_b)

    def setUp(self):
        self.client.force_authenticate(user=self.leader)

    def rows(self, response):
        return response.data.get("results", response.data) if isinstance(response.data, dict) else response.data

    def test_department_role_lists_attendance_of_viewable_departments(self):
        response = self.client.get("/api/v1/servicebook/attendances/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({row["id"] for row in self.rows(response)}, {self.attendance_a.pk, self.attendance_b.pk})

    def test_department_role_records_attendance_in_its_department(self):
        response = self.client.post(
            "/api/v1/servicebook/attendances/",
            {"service": self.service_a.pk, "person": self.member_a2.pk, "state": "A"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(Attendance.objects.filter(service=self.service_a, person=self.member_a2, state="A").exists())

    def test_department_role_changes_attendance_in_its_department(self):
        response = self.client.patch(
            f"/api/v1/servicebook/attendances/{self.attendance_a.pk}/", {"state": "A"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_read_only_department_cannot_be_written(self):
        create = self.client.post(
            "/api/v1/servicebook/attendances/",
            {"service": self.service_b.pk, "person": self.member_b.pk, "state": "A"},
            format="json",
        )
        change = self.client.patch(
            f"/api/v1/servicebook/attendances/{self.attendance_b.pk}/", {"state": "A"}, format="json"
        )
        delete = self.client.delete(f"/api/v1/servicebook/attendances/{self.attendance_b.pk}/")

        self.assertIn(create.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.assertEqual(change.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete.status_code, status.HTTP_403_FORBIDDEN)
        self.attendance_b.refresh_from_db()
        self.assertEqual(self.attendance_b.state, "F")
        self.assertEqual(Attendance.objects.filter(service=self.service_b).count(), 1)

    def test_attendance_cannot_be_moved_to_a_read_only_department(self):
        response = self.client.patch(
            f"/api/v1/servicebook/attendances/{self.attendance_a.pk}/",
            {"service": self.service_b.pk, "person": self.member_b.pk},
            format="json",
        )

        self.assertIn(response.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.attendance_a.refresh_from_db()
        self.assertEqual(self.attendance_a.service_id, self.service_a.pk)

    def test_foreign_member_cannot_be_added_to_own_service(self):
        response = self.client.post(
            "/api/v1/servicebook/attendances/",
            {"service": self.service_a.pk, "person": self.member_b.pk, "state": "A"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_update_respects_the_service_department(self):
        allowed = self.client.post(
            "/api/v1/servicebook/attendances/bulk_update/",
            {"service": self.service_a.pk, "attendances": [{"person_id": self.member_a2.pk, "state": "E"}]},
            format="json",
        )
        denied = self.client.post(
            "/api/v1/servicebook/attendances/bulk_update/",
            {"service": self.service_b.pk, "attendances": [{"person_id": self.member_b.pk, "state": "A"}]},
            format="json",
        )

        self.assertEqual(allowed.status_code, status.HTTP_200_OK, allowed.data)
        self.assertIn(denied.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.attendance_b.refresh_from_db()
        self.assertEqual(self.attendance_b.state, "F")

    def test_bulk_update_rejects_foreign_members(self):
        response = self.client.post(
            "/api/v1/servicebook/attendances/bulk_update/",
            {"service": self.service_a.pk, "attendances": [{"person_id": self.member_b.pk, "state": "A"}]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Attendance.objects.filter(service=self.service_a, person=self.member_b).exists())

    def test_assignment_without_attendance_right_hides_attendance(self):
        service_only = AuthGroup.objects.create(name="Service viewer B")
        service_only.permissions.add(*permissions("view_service"))
        outsider = get_user_model().objects.create_user(username="service-only", password="test-only-password")
        UserDepartmentRole.objects.create(user=outsider, department=self.department_b).groups.add(service_only)
        self.client.force_authenticate(user=outsider)

        listing = self.client.get("/api/v1/servicebook/attendances/")
        detail = self.client.get(f"/api/v1/servicebook/attendances/{self.attendance_b.pk}/")
        by_member = self.client.get("/api/v1/servicebook/attendances/by_member/", {"member_id": self.member_b.pk})

        self.assertIn(listing.status_code, (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN))
        if listing.status_code == status.HTTP_200_OK:
            self.assertEqual(self.rows(listing), [])
        self.assertIn(detail.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        if by_member.status_code == status.HTTP_200_OK:
            self.assertEqual(by_member.data["summary"]["total"], 0)
