"""Regression coverage for collaborative youth/staff attendance."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Member
from servicebook.models import Attendance, Service, StaffAttendance


class AttendanceBoardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            username="board-admin", email="board@example.test", password="test-pass"
        )
        self.client.force_authenticate(self.user)
        self.department = Department.objects.create(name="Nord")
        self.other = Department.objects.create(name="Süd")
        now = timezone.now()
        self.service = Service.objects.create(start=now, end=now + timedelta(hours=2), department=self.department)
        self.member = Member.objects.create(name="Ada", lastname="Beispiel")
        self.member.departments.add(self.department)
        self.other_member = Member.objects.create(name="Max", lastname="Beispiel")
        self.other_member.departments.add(self.department)
        self.staff = get_user_model().objects.create_user(
            username="instructor", first_name="Alex", last_name="Ausbildung"
        )
        UserDepartmentRole.objects.create(user=self.staff, department=self.department)
        self.url = f"/api/v1/servicebook/services/{self.service.pk}/attendance_board/"

    def change(self, person, state="A", expected=None, kind="member"):
        return self.client.patch(
            self.url, {"kind": kind, "person_id": person.pk, "state": state, "expected_state": expected}, format="json"
        )

    def test_independent_updates_preserve_other_participants(self):
        self.assertEqual(self.change(self.member).status_code, 200)
        self.assertEqual(self.change(self.other_member, state="E").status_code, 200)
        data = self.client.get(self.url).json()
        states = {row["id"]: row["state"] for row in data["members"]}
        self.assertEqual(states, {self.member.pk: "A", self.other_member.pk: "E"})

    def test_stale_same_person_update_is_rejected(self):
        self.assertEqual(self.change(self.member).status_code, 200)
        response = self.change(self.member, state="F")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["state"], "A")
        self.assertEqual(Attendance.objects.get(person=self.member).state, "A")
        self.assertEqual(self.change(self.member, state=None, expected="A").status_code, 200)
        self.assertFalse(Attendance.objects.filter(person=self.member).exists())

    def test_staff_attendance_and_hours_report(self):
        self.assertEqual(self.change(self.staff, kind="staff").status_code, 200)
        self.assertEqual(StaffAttendance.objects.get(person=self.staff).state, "A")
        self.assertFalse(Attendance.objects.exists())
        report = self.client.get("/api/v1/servicebook/services/staff_statistics/").json()["results"]
        self.assertEqual(report[0]["present"], 1)
        self.assertEqual(report[0]["hours"], 2)
        empty = self.client.get("/api/v1/servicebook/services/staff_statistics/", {"date_to": "2000-01-01"})
        self.assertEqual(empty.json()["results"], [])

    def test_invalid_person_and_state_are_rejected(self):
        outsider = Member.objects.create(name="Outside", lastname="Department")
        outsider.departments.add(self.other)
        self.assertEqual(self.change(outsider).status_code, 400)
        self.assertEqual(self.change(self.member, state="X").status_code, 400)
        self.assertEqual(
            self.client.patch(
                self.url, {"kind": "member", "person_id": self.member.pk, "state": "A"}, format="json"
            ).status_code,
            400,
        )

    def test_permission_and_department_boundaries(self):
        self.staff.user_permissions.add(
            Permission.objects.get(codename="view_service", content_type__app_label="servicebook")
        )
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.staff.user_permissions.add(
            Permission.objects.get(codename="view_attendance", content_type__app_label="servicebook")
        )
        # A fresh instance avoids Django's permission cache.
        self.client.force_authenticate(get_user_model().objects.get(pk=self.staff.pk))
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.change(self.member).status_code, 403)
        self.service.department = self.other
        self.service.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/servicebook/services/staff_statistics/").json()["results"], [])

    def test_staff_flag_alone_grants_no_attendance_access(self):
        self.staff.is_staff = True
        self.staff.save(update_fields=["is_staff"])
        self.client.force_authenticate(get_user_model().objects.get(pk=self.staff.pk))

        board = self.client.get(self.url)
        update = self.change(self.member)
        statistics = self.client.get("/api/v1/servicebook/services/staff_statistics/")

        self.assertEqual(board.status_code, 403)
        self.assertEqual(update.status_code, 403)
        self.assertEqual(statistics.status_code, 403)
        self.assertFalse(Attendance.objects.filter(service=self.service, person=self.member).exists())

        self.staff.user_permissions.add(
            Permission.objects.get(codename="view_attendance", content_type__app_label="servicebook")
        )
        self.client.force_authenticate(get_user_model().objects.get(pk=self.staff.pk))
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/servicebook/services/staff_statistics/").status_code, 200)

    def test_legacy_attendance_endpoints_cannot_bypass_department_scope(self):
        foreign_service = Service.objects.create(start=self.service.start, end=self.service.end, department=self.other)
        record = Attendance.objects.create(service=foreign_service, person=self.member, state="A")
        self.staff.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="servicebook",
                codename__in=["view_attendance", "add_attendance", "change_attendance"],
            )
        )
        self.client.force_authenticate(get_user_model().objects.get(pk=self.staff.pk))
        response = self.client.patch(f"/api/v1/servicebook/attendances/{record.pk}/", {"state": "F"}, format="json")
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            "/api/v1/servicebook/attendances/bulk_update/",
            {"service": foreign_service.pk, "attendances": [{"person_id": self.member.pk, "state": "F"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        record.refresh_from_db()
        self.assertEqual(record.state, "A")

    def test_department_roles_allow_only_their_own_attendance(self):
        own_role = self.staff.department_roles.get(department=self.department)
        other_role = UserDepartmentRole.objects.create(user=self.staff, department=self.other)
        own_group = Group.objects.create(name="Dienstleitung Nord")
        other_group = Group.objects.create(name="Dienstansicht Süd")
        own_group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="servicebook",
                codename__in=["view_service", "view_attendance", "change_attendance"],
            )
        )
        other_group.permissions.add(
            Permission.objects.get(content_type__app_label="servicebook", codename="view_service")
        )
        own_role.groups.add(own_group)
        other_role.groups.add(other_group)
        foreign_service = Service.objects.create(start=self.service.start, end=self.service.end, department=self.other)
        Attendance.objects.create(person=self.member, service=self.service, state="A")
        self.client.force_authenticate(get_user_model().objects.get(pk=self.staff.pk))

        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.change(self.other_member).status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/v1/servicebook/services/{foreign_service.pk}/attendance_board/").status_code, 403
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/servicebook/services/{foreign_service.pk}/attendance_board/",
                {"kind": "staff", "person_id": self.staff.pk, "state": "A", "expected_state": None},
                format="json",
            ).status_code,
            403,
        )
        response = self.client.get("/api/v1/servicebook/services/staff_statistics/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])
        self.assertEqual(self.client.get("/api/v1/servicebook/services/statistics/").status_code, 200)

    def test_service_statistics_and_chart_do_not_leak_other_department(self):
        own_group = Group.objects.create(name="Nord Sicht")
        own_group.permissions.add(
            Permission.objects.get(content_type__app_label="servicebook", codename="view_service")
        )
        self.staff.department_roles.get(department=self.department).groups.add(own_group)
        foreign_service = Service.objects.create(start=self.service.start, end=self.service.end, department=self.other)
        Attendance.objects.create(person=self.member, service=foreign_service, state="A")
        self.client.force_authenticate(get_user_model().objects.get(pk=self.staff.pk))
        statistics = self.client.get("/api/v1/servicebook/services/statistics/")
        self.assertEqual(statistics.status_code, 200)
        self.assertEqual(statistics.json()["total_services"], 1)
        self.assertEqual(statistics.json()["top_lists"]["most_present"], [])
        chart = self.client.get("/api/v1/servicebook/services/attendance_chart/")
        self.assertEqual(chart.status_code, 200)
        self.assertEqual(chart.json()["attendance_data"]["A"], [0])


class SystemAccountRosterTests(TestCase):
    """UX-02.1b: guardian's AnonymousUser is active but must never appear in the team roster."""

    def test_service_without_department_lists_only_people(self):
        admin = get_user_model().objects.create_superuser(username="org-admin", password="test-pass")
        get_user_model().objects.get_or_create(username="AnonymousUser", defaults={"is_active": True})
        get_user_model().objects.create_user(username="leitung", first_name="Kim", last_name="Leitung")
        now = timezone.now()
        service = Service.objects.create(start=now, end=now + timedelta(hours=2))
        client = APIClient()
        client.force_authenticate(admin)
        staff = client.get(f"/api/v1/servicebook/services/{service.pk}/attendance_board/").json()["staff"]
        names = [row["full_name"] for row in staff]
        self.assertIn("Kim Leitung", names)
        self.assertNotIn("AnonymousUser", names)
