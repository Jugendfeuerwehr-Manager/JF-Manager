from datetime import timedelta
from io import StringIO

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
from participation.models import Registration, SessionParticipation
from qualifications.models import QualificationType

from .helpers import configure, future_day, make_member, make_session

User = get_user_model()


def url(session, tail="config/"):
    return f"/api/v1/participation/sessions/{session.pk}/{tail}"


class StaffApiBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.dept = Department.objects.create(name="A", code="a")
        cls.other = Department.objects.create(name="B", code="b")
        planner_group = RoleTemplate.objects.get(key="training_planner").group
        cls.planner = User.objects.create_user("planer")
        UserDepartmentRole.objects.create(user=cls.planner, department=cls.dept).groups.add(planner_group)
        cls.other_planner = User.objects.create_user("planer-b")
        UserDepartmentRole.objects.create(user=cls.other_planner, department=cls.other).groups.add(planner_group)
        reader_group = AuthGroup.objects.create(name="Leser")
        reader_group.permissions.add(Permission.objects.get(codename="view_trainingsession"))
        cls.reader = User.objects.create_user("leser")
        UserDepartmentRole.objects.create(user=cls.reader, department=cls.dept).groups.add(reader_group)
        cls.portal = User.objects.create_user("eltern", account_kind="portal")
        cls.group = Group.objects.create(name="Rot", department=cls.dept)
        cls.day = future_day(20)
        cls.session = make_session(cls.dept, day=cls.day, groups=[cls.group], created_by=cls.planner)
        cls.mia = make_member(cls.dept, "Mia", cls.group)
        cls.ole = make_member(cls.dept, "Ole", cls.group)

    def as_user(self, user):
        client = APIClient()
        client.force_login(user)
        return client

    def setUp(self):
        self.client = self.as_user(self.planner)


class ConfigApiTests(StaffApiBase):
    def test_get_returns_defaults_without_writing(self):
        response = self.client.get(url(self.session))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body["mode"], body["revision"], body["portal_visible"]), ("opt_out", 0, True))
        self.assertEqual(body["defaults"]["registration_offset_h"], 48)
        self.assertIn("registration_closes_at", body["effective"])
        self.assertFalse(SessionParticipation.objects.exists())

    def test_put_creates_lazily_and_bumps_the_revision(self):
        response = self.client.put(
            url(self.session),
            {"revision": 0, "mode": "opt_in", "max_participants": 8, "public_note": "Bitte Sportschuhe"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((response.json()["revision"], response.json()["max_participants"]), (1, 8))
        response = self.client.put(url(self.session), {"revision": 1, "waitlist_mode": "manual"}, format="json")
        self.assertEqual((response.json()["revision"], response.json()["mode"]), (2, "opt_in"))

    def test_stale_revision_is_409_with_the_current_state(self):
        self.client.put(url(self.session), {"revision": 0, "mode": "opt_in"}, format="json")
        response = self.client.put(url(self.session), {"revision": 0, "mode": "assignment"}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual((response.json()["code"], response.json()["current"]["mode"]), ("stale", "opt_in"))
        self.assertEqual(SessionParticipation.objects.get().mode, "opt_in")

    def test_validation(self):
        base = {"revision": 0}
        cases = {
            "max_in_opt_out": {"mode": "opt_out", "max_participants": 5},
            "min_above_max": {"mode": "opt_in", "max_participants": 2, "min_participants": 3},
            "html_note": {"public_note": "<b>Hallo</b>"},
            "long_note": {"public_note": "x" * 1001},
            "bad_mode": {"mode": "x"},
            "bad_rule": {"eligibility": {"v": 2}},
            "deadline_after_start": {"cancellation_closes_at": (timezone.now() + timedelta(days=40)).isoformat()},
            "opens_after_closes": {
                "registration_opens_at": (timezone.now() + timedelta(days=3)).isoformat(),
                "registration_closes_at": (timezone.now() + timedelta(days=2)).isoformat(),
            },
        }
        for name, extra in cases.items():
            with self.subTest(name):
                response = self.client.put(url(self.session), {**base, **extra}, format="json")
                self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(SessionParticipation.objects.exists())

    def test_valid_rule_and_explicit_deadlines(self):
        qtype = QualificationType.objects.create(name="Maschinist")
        rule = {"v": 1, "match": "all", "rules": [{"kind": "qualification", "op": "has_any", "values": [qtype.pk]}]}
        closes = (timezone.now() + timedelta(days=5)).replace(microsecond=0)
        response = self.client.put(
            url(self.session),
            {"revision": 0, "eligibility": rule, "mode": "opt_in", "registration_closes_at": closes.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertIsNotNone(body["eligibility_summary"])
        self.assertEqual(SessionParticipation.objects.get().registration_closes_at, closes)

    def test_switching_to_opt_out_drops_the_maximum(self):
        self.client.put(url(self.session), {"revision": 0, "mode": "opt_in", "max_participants": 4}, format="json")
        response = self.client.put(
            url(self.session), {"revision": 1, "mode": "opt_out", "max_participants": None}, format="json"
        )
        self.assertEqual((response.status_code, response.json()["max_participants"]), (200, None))

    def test_raising_the_maximum_promotes_the_waitlist(self):
        configure(self.session, mode="opt_in", max_participants=1)
        now = timezone.now()
        service.set_registration(self.session.pk, self.mia.pk, "registered", actor=None, source="staff", now=now)
        service.set_registration(self.session.pk, self.ole.pk, "registered", actor=None, source="staff", now=now)
        revision = SessionParticipation.objects.get().revision
        self.client.put(url(self.session), {"revision": revision, "max_participants": 2}, format="json")
        self.assertEqual(Registration.objects.get(member=self.ole).state, "registered")

    def test_permissions(self):
        self.assertEqual(self.as_user(self.other_planner).get(url(self.session)).status_code, 403)
        self.assertEqual(
            self.as_user(self.other_planner).put(url(self.session), {"revision": 0}, format="json").status_code, 403
        )
        self.assertEqual(self.as_user(self.reader).get(url(self.session)).status_code, 200)
        self.assertEqual(
            self.as_user(self.reader).put(url(self.session), {"revision": 0}, format="json").status_code, 403
        )
        self.assertEqual(self.as_user(self.portal).get(url(self.session)).status_code, 403)
        self.assertEqual(self.client.get(url(self.session).replace(str(self.session.pk), "99999")).status_code, 404)
        anonymous = APIClient()
        self.assertIn(anonymous.get(url(self.session)).status_code, (401, 403))

    def test_reader_cannot_see_drafts(self):
        draft = make_session(self.dept, day=self.day, status="draft")
        self.assertEqual(self.as_user(self.reader).get(url(draft)).status_code, 403)
        self.assertEqual(self.client.get(url(draft)).status_code, 200)


class RegistrationsApiTests(StaffApiBase):
    def test_lists_target_members_with_expected_state(self):
        outsider = make_member(self.dept, "Fremd", Group.objects.create(name="Blau", department=self.dept))
        body = self.client.get(url(self.session, "registrations/")).json()
        self.assertEqual({m["member_id"] for m in body["members"]}, {self.mia.pk, self.ole.pk})
        self.assertNotIn(outsider.pk, {m["member_id"] for m in body["members"]})
        self.assertEqual({m["state"] for m in body["members"]}, {"expected"})
        self.assertEqual(
            (body["counts"]["expected"], body["counts"]["cancelled"], body["counts"]["free"]), (2, 0, None)
        )
        configure(self.session, mode="opt_in", max_participants=5)
        body = self.client.get(url(self.session, "registrations/")).json()
        self.assertEqual({m["state"] for m in body["members"]}, {"no_response"})
        self.assertEqual((body["counts"]["no_response"], body["counts"]["free"]), (2, 5))

    def test_staff_registers_a_person_and_the_listing_follows(self):
        response = self.client.put(
            url(self.session, f"registrations/{self.mia.pk}/"),
            {"target": "cancelled", "reason_category": "krankheit", "reason_note": "Grippe", "version": 0},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((response.json()["state"], response.json()["registration"]["version"]), ("cancelled", 1))
        self.assertEqual(response.json()["registration"]["source"], "staff")
        body = self.client.get(url(self.session, "registrations/")).json()
        mia = next(m for m in body["members"] if m["member_id"] == self.mia.pk)
        self.assertEqual((mia["state"], mia["registration"]["reason_note"]), ("cancelled", "Grippe"))
        self.assertEqual((body["counts"]["cancelled"], body["counts"]["expected"]), (1, 1))

    def test_stale_version_is_409(self):
        path = url(self.session, f"registrations/{self.mia.pk}/")
        self.client.put(path, {"target": "cancelled", "version": 0}, format="json")
        response = self.client.put(path, {"target": "registered", "version": 0}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["current"], {"state": "cancelled", "version": 1})

    def test_late_flag_after_the_deadline(self):
        session = make_session(self.dept, day=future_day(1), groups=[self.group], title="morgen")
        configure(session, cancellation_closes_at=timezone.now() - timedelta(minutes=1))
        # the closing time is only set explicitly for the test; the start lies in the future
        response = self.client.put(
            url(session, f"registrations/{self.mia.pk}/"), {"target": "cancelled"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["registration"]["late"])

    def test_errors_use_the_contract(self):
        configure(self.session, mode="opt_in")
        path = url(self.session, f"registrations/{self.mia.pk}/")
        response = self.client.put(path, {"target": "applied"}, format="json")
        self.assertEqual((response.status_code, response.json()["code"]), (422, "mode_forbidden"))
        self.assertEqual(self.client.put(path, {"target": "bogus"}, format="json").status_code, 400)
        self.assertEqual(
            self.client.put(
                url(self.session, "registrations/99999/"), {"target": "cancelled"}, format="json"
            ).status_code,
            404,
        )
        stranger = make_member(self.dept, "Fremd", Group.objects.create(name="Blau", department=self.dept))
        response = self.client.put(
            url(self.session, f"registrations/{stranger.pk}/"), {"target": "cancelled"}, format="json"
        )
        self.assertEqual((response.status_code, response.json()["code"]), (422, "not_target"))

    def test_reason_note_only_for_responsible_staff(self):
        service.set_registration(
            self.session.pk,
            self.mia.pk,
            "cancelled",
            actor=self.planner,
            source="portal_parent",
            reason_category="familie",
            reason_note="Geheim-Kurztext",
            now=timezone.now(),
        )

        def note(user):
            body = self.as_user(user).get(url(self.session, "registrations/")).json()
            return next(m for m in body["members"] if m["member_id"] == self.mia.pk)["registration"]

        self.assertEqual(note(self.planner)["reason_note"], "Geheim-Kurztext")
        reader = note(self.reader)
        self.assertIsNone(reader["reason_note"])
        self.assertEqual(reader["reason_category"], "familie")
        self.assertNotIn(
            "Geheim-Kurztext", self.as_user(self.reader).get(url(self.session, "registrations/")).content.decode()
        )

    def test_permissions(self):
        path = url(self.session, f"registrations/{self.mia.pk}/")
        self.assertEqual(self.as_user(self.portal).put(path, {"target": "cancelled"}, format="json").status_code, 403)
        self.assertEqual(self.as_user(self.portal).get(url(self.session, "registrations/")).status_code, 403)
        self.assertEqual(self.as_user(self.reader).put(path, {"target": "cancelled"}, format="json").status_code, 403)
        self.assertEqual(
            self.as_user(self.other_planner).put(path, {"target": "cancelled"}, format="json").status_code, 403
        )

    def test_eligibility_shown_per_person(self):
        qtype = QualificationType.objects.create(name="Maschinist")
        rule = {"v": 1, "match": "all", "rules": [{"kind": "qualification", "op": "has_any", "values": [qtype.pk]}]}
        configure(self.session, mode="opt_in", eligibility=rule)
        body = self.client.get(url(self.session, "registrations/")).json()
        self.assertTrue(all(not m["eligibility"]["ok"] and m["eligibility"]["reasons"] for m in body["members"]))
        response = self.client.put(
            url(self.session, f"registrations/{self.mia.pk}/"), {"target": "registered"}, format="json"
        )
        self.assertEqual((response.status_code, response.json()["code"]), (422, "not_eligible"))
        self.assertTrue(response.json()["reasons"])

    def test_waitlist_shown_with_position(self):
        configure(self.session, mode="opt_in", max_participants=1)
        for member in (self.mia, self.ole):
            self.client.put(url(self.session, f"registrations/{member.pk}/"), {"target": "registered"}, format="json")
        body = self.client.get(url(self.session, "registrations/")).json()
        ole = next(m for m in body["members"] if m["member_id"] == self.ole.pk)
        self.assertEqual((ole["state"], ole["waitlist_position"]), ("waitlisted", 1))
        self.assertEqual(
            (body["counts"]["registered"], body["counts"]["waitlisted"], body["counts"]["free"]), (1, 1, 0)
        )
