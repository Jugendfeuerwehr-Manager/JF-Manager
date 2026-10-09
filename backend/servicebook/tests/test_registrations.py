"""PART-02.1: registrations and excused takeover in the servicebook."""

from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, RoleTemplate, UserDepartmentRole
from members.models import Group
from participation import service
from participation.models import Registration
from participation.tests.helpers import configure, make_member, make_session
from servicebook.models import Attendance, Service

User = get_user_model()


def role(user, department, *codenames, template=None):
    assignment = UserDepartmentRole.objects.create(user=user, department=department)
    if codenames:
        group = AuthGroup.objects.create(name=f"{user.username}-{department.pk}")
        group.permissions.set(Permission.objects.filter(codename__in=codenames))
        assignment.groups.add(group)
    if template:
        assignment.groups.add(RoleTemplate.objects.get(key=template).group)


class RegistrationsBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.dept = Department.objects.create(name="A", code="a")
        cls.other = Department.objects.create(name="B", code="b")
        cls.group = Group.objects.create(name="Rot", department=cls.dept)
        cls.planner = User.objects.create_user("planer")
        role(cls.planner, cls.dept, "view_service", "view_attendance", "change_attendance", template="training_planner")
        cls.viewer = User.objects.create_user("betrachter")
        role(cls.viewer, cls.dept, "view_service", "view_attendance")
        cls.outsider = User.objects.create_user("fremd")
        role(cls.outsider, cls.other, "view_service", "view_attendance", "change_attendance")
        cls.portal = User.objects.create_user("eltern", account_kind="portal")
        cls.session = make_session(
            cls.dept, day=timezone.localdate() + timedelta(days=5), groups=[cls.group], created_by=cls.planner
        )
        configure(cls.session, mode="opt_out")
        start = timezone.now() + timedelta(days=5)
        cls.service = Service.objects.create(
            start=start, end=start + timedelta(hours=2), department=cls.dept, training_session=cls.session, topic="T"
        )
        cls.mia = make_member(cls.dept, "Mia", cls.group)
        cls.ole = make_member(cls.dept, "Ole", cls.group)
        cls.eva = make_member(cls.dept, "Eva", cls.group)

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def cancel(self, member, note=""):
        service.set_registration(
            self.session.pk,
            member.pk,
            "cancelled",
            actor=self.planner,
            source=Registration.Source.STAFF,
            reason_category="krankheit",
            reason_note=note,
        )

    @property
    def reg_url(self):
        return f"/api/v1/servicebook/services/{self.service.pk}/registrations/"

    @property
    def apply_url(self):
        return self.reg_url + "apply-excused/"


class RegistrationsTests(RegistrationsBase):
    def test_permissions(self):
        self.assertEqual(self.api(self.planner).get(self.reg_url).status_code, 200)
        self.assertIn(self.api(self.outsider).get(self.reg_url).status_code, (403, 404))
        self.assertEqual(self.api(self.portal).get(self.reg_url).status_code, 403)
        self.assertEqual(self.api(self.portal).post(self.apply_url, {}, format="json").status_code, 403)
        self.assertEqual(self.api(self.portal).get("/api/v1/servicebook/services/overview/").status_code, 403)

    def test_counts_and_people(self):
        self.cancel(self.ole)
        body = self.api(self.planner).get(self.reg_url).json()
        self.assertEqual(body["session"]["mode"], "opt_out")
        self.assertEqual(body["session"]["id"], self.session.pk)
        self.assertEqual(body["counts"]["expected"], 2)
        self.assertEqual(body["counts"]["cancelled"], 1)
        self.assertEqual(body["counts"]["guests"], 0)
        states = {p["name"]: p["state"] for p in body["people"]}
        self.assertEqual(states, {"Mia Test": "expected", "Ole Test": "cancelled", "Eva Test": "expected"})
        self.assertEqual([p["name"] for p in body["people"]], sorted(states))
        ole = next(p for p in body["people"] if p["member_id"] == self.ole.pk)
        self.assertEqual(ole["reason_category"], "krankheit")
        self.assertEqual(ole["group"], "Rot")
        self.assertEqual(ole["source"], "staff")
        self.assertTrue(ole["in_target"])

    def test_reason_note_only_for_responsible_staff(self):
        self.cancel(self.ole, "Grippe")
        ole = lambda body: next(p for p in body["people"] if p["member_id"] == self.ole.pk)  # noqa: E731
        self.assertEqual(ole(self.api(self.planner).get(self.reg_url).json())["reason_note"], "Grippe")
        self.assertIsNone(ole(self.api(self.viewer).get(self.reg_url).json())["reason_note"])

    def test_guest_registration_and_board(self):
        guest = make_member(self.other, "Gast", None)
        configure(self.session, mode="opt_in")
        # Staff cannot register outsiders through the service (not_target): the row stems from a group change.
        Registration.objects.create(
            session=self.session, member=guest, state="registered", source="staff", state_changed_at=timezone.now()
        )
        body = self.api(self.planner).get(self.reg_url).json()
        row = next(p for p in body["people"] if p["member_id"] == guest.pk)
        self.assertFalse(row["in_target"])
        self.assertEqual(body["counts"]["guests"], 1)
        self.assertEqual(body["counts"]["no_response"], 3)
        board = self.api(self.planner).get(f"/api/v1/servicebook/services/{self.service.pk}/attendance_board/").json()
        self.assertIn(guest.pk, [m["id"] for m in board["members"]])
        patch = self.api(self.planner).patch(
            f"/api/v1/servicebook/services/{self.service.pk}/attendance_board/",
            {"kind": "member", "person_id": guest.pk, "state": "A", "expected_state": None},
            format="json",
        )
        self.assertEqual(patch.status_code, 200)

    def test_service_without_session(self):
        start = timezone.now() + timedelta(days=9)
        plain = Service.objects.create(start=start, end=start + timedelta(hours=1), department=self.dept)
        Attendance.objects.create(service=plain, person=self.mia, state="A")
        body = self.api(self.planner).get(f"/api/v1/servicebook/services/{plain.pk}/registrations/").json()
        self.assertIsNone(body["session"])
        self.assertEqual(body["counts"]["recorded"], 1)
        self.assertEqual(len(body["people"]), 1)
        self.assertIsNone(body["people"][0]["state"])
        self.assertEqual(body["people"][0]["attendance"], "A")


class ApplyExcusedTests(RegistrationsBase):
    def post(self, **body):
        return self.api(self.planner).post(self.apply_url, body, format="json")

    def test_dry_run_then_apply_and_idempotent(self):
        self.cancel(self.ole)
        self.cancel(self.eva)
        Attendance.objects.create(service=self.service, person=self.eva, state="A")
        dry = self.post(dry_run=True).json()
        self.assertEqual([a["member_id"] for a in dry["apply"]], [self.ole.pk])
        self.assertEqual([(s["member_id"], s["reason"]) for s in dry["skipped"]], [(self.eva.pk, "has_attendance")])
        self.assertEqual(dry["applied"], 0)
        self.assertFalse(Attendance.objects.filter(person=self.ole, service=self.service).exists())
        done = self.post(dry_run=False).json()
        self.assertEqual(done["applied"], 1)
        self.assertEqual(Attendance.objects.get(person=self.ole, service=self.service).state, "E")
        self.assertEqual(Attendance.objects.get(person=self.eva, service=self.service).state, "A")
        again = self.post().json()
        self.assertEqual(again["applied"], 0)
        self.assertEqual(again["apply"], [])

    def test_selected_members_and_not_cancelled(self):
        self.cancel(self.ole)
        body = self.post(member_ids=[self.mia.pk]).json()
        self.assertEqual(body["applied"], 0)
        self.assertEqual(body["skipped"][0]["reason"], "not_cancelled")
        self.assertEqual(self.post(member_ids=[self.ole.pk]).json()["applied"], 1)

    def test_requires_write_permission(self):
        self.cancel(self.ole)
        self.assertEqual(self.api(self.viewer).post(self.apply_url, {}, format="json").status_code, 403)
        self.assertIn(self.api(self.outsider).post(self.apply_url, {}, format="json").status_code, (403, 404))
        self.assertEqual(Attendance.objects.count(), 0)

    def test_parallel_attendance_change_wins(self):
        self.cancel(self.ole)
        from servicebook.api import registrations

        real = registrations.set_attendance

        def racing(svc, model, person_id, state, expected):
            Attendance.objects.create(service=svc, person_id=person_id, state="A")  # the board was faster
            return real(svc, model, person_id, state, expected)

        with mock.patch.object(registrations, "set_attendance", racing):
            body = self.post().json()
        self.assertEqual(body["applied"], 0)
        self.assertEqual(body["skipped"][0]["reason"], "has_attendance")
        self.assertEqual(Attendance.objects.get(person=self.ole, service=self.service).state, "A")


class OverviewTests(RegistrationsBase):
    def make(self, offset_days, topic, department=None, session=None):
        start = timezone.now() + timedelta(days=offset_days)
        return Service.objects.create(
            start=start,
            end=start + timedelta(hours=1),
            department=department or self.dept,
            topic=topic,
            training_session=session,
        )

    def test_buckets(self):
        self.service.delete()
        now = timezone.localtime()
        today_start = now.replace(hour=23, minute=0, second=0, microsecond=0)
        today = Service.objects.create(
            start=today_start, end=today_start + timedelta(minutes=30), department=self.dept, topic="heute"
        )
        soon = self.make(3, "bald")
        self.make(30, "fern")
        past_session = make_session(self.dept, day=timezone.localdate() - timedelta(days=4), groups=[self.group])
        configure(past_session, mode="opt_out")
        past = self.make(-4, "offen", session=past_session)
        Attendance.objects.create(service=past, person=self.mia, state="A")
        done = self.make(-5, "fertig")
        Attendance.objects.create(service=done, person=self.mia, state="A")
        self.make(-90, "alt")
        self.make(2, "andere", department=self.other)
        body = self.api(self.planner).get("/api/v1/servicebook/services/overview/").json()
        self.assertEqual([c["topic"] for c in body["today"]], ["heute"])
        self.assertEqual([c["topic"] for c in body["upcoming"]], ["bald"])
        self.assertEqual([c["topic"] for c in body["open"]], ["offen"])
        card = body["open"][0]
        self.assertEqual(card["groups"], ["Rot"])
        self.assertEqual(card["session_id"], past_session.pk)
        self.assertEqual(card["counts"], {"expected": 3, "cancelled": 0, "recorded": 1, "total": 3})
        self.assertEqual(soon.pk, body["upcoming"][0]["id"])
        self.assertEqual(today.pk, body["today"][0]["id"])
        self.assertEqual(card["mode"], "opt_out")
