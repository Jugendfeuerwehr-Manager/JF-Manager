"""Attendance evaluation per period (UX-04.2)."""

from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Member
from servicebook.attendance_report import default_period, month_keys
from servicebook.models import Attendance, Service, StaffAttendance
from users.people import ANONYMOUS_USERNAME

URL = "/api/v1/servicebook/attendance-report/"
PERIOD = {"date_from": "2026-01-01", "date_to": "2026-06-30"}


def service_on(day: date, department, hours=2):
    start = timezone.make_aware(datetime(day.year, day.month, day.day, 18, 0))
    return Service.objects.create(start=start, end=start + timedelta(hours=hours), department=department)


class AttendanceReportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            username="report-admin", email="report@example.test", password="test-pass"
        )
        self.client.force_authenticate(self.admin)
        self.north = Department.objects.create(name="Nord")
        self.south = Department.objects.create(name="Süd")
        # Two services per month, January to June.
        self.services = [service_on(date(2026, month, day), self.north) for month in range(1, 7) for day in (5, 19)]
        self.steady = Member.objects.create(name="Ada", lastname="Aktiv")
        self.fading = Member.objects.create(name="Ben", lastname="Bald")
        for index, service in enumerate(self.services):
            Attendance.objects.create(person=self.steady, service=service, state="A")
            # Present in the first half, then excused or absent.
            state = "A" if index < 6 else ("E" if index % 2 else "F")
            Attendance.objects.create(person=self.fading, service=service, state=state)

    def report(self, params=PERIOD):
        response = self.client.get(URL, params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def member_row(self, data, member):
        return next(row for row in data["members"]["people"] if row["id"] == member.pk)

    def test_rates_hours_and_months_per_member(self):
        data = self.report()

        self.assertEqual(data["services"], {"count": 12, "hours": 24.0})
        steady = self.member_row(data, self.steady)
        self.assertEqual(
            (steady["present"], steady["recorded"], steady["rate"], steady["hours"]), (12, 12, 100.0, 24.0)
        )
        self.assertEqual(steady["warnings"], [])
        self.assertEqual([month["month"] for month in data["members"]["months"]][:2], ["2026-01", "2026-02"])
        self.assertEqual(data["members"]["months"][0]["rate"], 100.0)
        self.assertEqual(data["members"]["months"][5]["rate"], 50.0)
        self.assertEqual(data["members"]["summary"]["rate"], 75.0)
        self.assertEqual(data["members"]["summary"]["with_warnings"], 1)

    def test_warnings_for_decline_and_missed_in_a_row(self):
        fading = self.member_row(self.report(), self.fading)

        self.assertEqual(fading["rate"], 50.0)
        self.assertEqual(fading["trend"], {"previous": 100.0, "recent": 0.0, "delta": -100.0})
        self.assertEqual(fading["missed_in_a_row"], 6)
        self.assertIn("declining", fading["warnings"])
        self.assertIn("missed_in_a_row", fading["warnings"])
        self.assertNotIn("low_rate", fading["warnings"])
        self.assertEqual(fading["months"], [100.0, 100.0, 100.0, 0.0, 0.0, 0.0])

    def test_low_rate_needs_enough_records(self):
        rare = Member.objects.create(name="Cem", lastname="Selten")
        for service, state in zip(self.services[:4], ["A", "F", "A", "F"], strict=True):
            Attendance.objects.create(person=rare, service=service, state=state)
        Attendance.objects.create(person=rare, service=self.services[4], state="F")

        row = self.member_row(self.report(), rare)

        self.assertEqual(row["rate"], 40.0)
        self.assertIn("low_rate", row["warnings"])
        self.assertNotIn("missed_in_a_row", row["warnings"])

    def test_trend_needs_enough_entries_per_half(self):
        # A late joiner: two early entries present, then one absence; too few entries for a trend.
        late = Member.objects.create(name="Dana", lastname="Spät")
        for service, state in zip(self.services[8:], ["A", "A", "F", "A"], strict=True):
            Attendance.objects.create(person=late, service=service, state=state)

        row = self.member_row(self.report(), late)

        self.assertIsNone(row["trend"])
        self.assertNotIn("declining", row["warnings"])

    def test_team_report_excludes_system_account(self):
        instructor = get_user_model().objects.create_user(username="instructor", first_name="Alex", last_name="Lehr")
        system, _ = get_user_model().objects.get_or_create(username=ANONYMOUS_USERNAME)
        StaffAttendance.objects.create(person=instructor, service=self.services[0], state="A")
        StaffAttendance.objects.create(person=system, service=self.services[0], state="A")

        staff = self.report()["staff"]

        self.assertEqual([row["id"] for row in staff["people"]], [instructor.pk])
        self.assertEqual(staff["people"][0]["hours"], 2.0)

    def test_period_limits_services(self):
        data = self.report({"date_from": "2026-03-01", "date_to": "2026-03-31"})

        self.assertEqual(data["services"]["count"], 2)
        self.assertEqual([month["month"] for month in data["members"]["months"]], ["2026-03"])

    def test_invalid_period_is_rejected(self):
        response = self.client.get(URL, {"date_from": "2026-06-01", "date_to": "2026-01-01"})

        self.assertEqual(response.status_code, 400)

    def test_only_departments_with_attendance_right(self):
        south_service = service_on(date(2026, 2, 10), self.south)
        Attendance.objects.create(person=self.steady, service=south_service, state="A")
        user = get_user_model().objects.create_user(username="north-lead")
        group = Group.objects.create(name="attendance-readers")
        group.permissions.set(Permission.objects.filter(codename="view_attendance"))
        role = UserDepartmentRole.objects.create(user=user, department=self.north)
        role.groups.add(group)
        UserDepartmentRole.objects.create(user=user, department=self.south)
        self.client.force_authenticate(user)

        data = self.report()

        self.assertEqual(data["services"]["count"], 12)
        self.assertEqual(self.member_row(data, self.steady)["recorded"], 12)

    def test_without_attendance_right_is_forbidden(self):
        user = get_user_model().objects.create_user(username="no-rights")
        UserDepartmentRole.objects.create(user=user, department=self.north)
        self.client.force_authenticate(user)

        self.assertEqual(self.client.get(URL, PERIOD).status_code, 403)


class ReportPeriodTests(TestCase):
    def test_default_period_covers_twelve_months(self):
        self.assertEqual(default_period(date(2026, 10, 7)), (date(2025, 11, 1), date(2026, 10, 7)))
        self.assertEqual(len(month_keys(*default_period(date(2026, 10, 7)))), 12)
