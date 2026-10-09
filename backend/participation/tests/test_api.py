from datetime import date, time
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from departments.models import Department, RoleTemplate, UserDepartmentRole
from members.models import Group, Member
from qualifications.models import Qualification, QualificationType
from training.models import TrainingSession

PREVIEW = "/api/v1/participation/eligibility/preview/"
VALIDATE = "/api/v1/participation/eligibility/validate/"
User = get_user_model()


class PreviewApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.dept = Department.objects.create(name="A", code="a")
        cls.other = Department.objects.create(name="B", code="b")
        cls.planner = User.objects.create_user("planer")
        UserDepartmentRole.objects.create(user=cls.planner, department=cls.dept).groups.add(
            RoleTemplate.objects.get(key="training_planner").group
        )
        cls.reader = User.objects.create_user("leser")
        UserDepartmentRole.objects.create(user=cls.reader, department=cls.dept)
        cls.other_planner = User.objects.create_user("planer-b")
        UserDepartmentRole.objects.create(user=cls.other_planner, department=cls.other).groups.add(
            RoleTemplate.objects.get(key="training_planner").group
        )
        cls.qtype = QualificationType.objects.create(name="Maschinist")
        cls.red = Group.objects.create(name="Rot", department=cls.dept)
        cls.blue = Group.objects.create(name="Blau", department=cls.dept)
        cls.session = TrainingSession.objects.create(
            title="Übung", date=date(2026, 10, 10), start_time=time(18), end_time=time(20), department=cls.dept
        )
        cls.members = []
        for i in range(30):
            m = Member.objects.create(name=f"M{i:02d}", lastname="Test", birthday=date(2000, 1, 1), group=cls.red)
            m.departments.add(cls.dept)
            if i % 3 == 0:
                Qualification.objects.create(type=cls.qtype, member=m, date_acquired=date(2020, 1, 1))
            cls.members.append(m)
        cls.rule = {
            "v": 1,
            "match": "all",
            "rules": [{"kind": "qualification", "op": "has_any", "values": [cls.qtype.pk]}],
        }

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.planner)

    def post(self, rule=None, session=None):
        return self.client.post(
            PREVIEW,
            {"rule": rule if rule is not None else self.rule, "session": session or self.session.pk},
            format="json",
        )

    def test_preview_in_department_without_groups(self):
        res = self.post()
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual((body["total"], body["eligible"], len(body["excluded"])), (30, 10, 20))
        self.assertEqual(body["summary"], "Maschinist")
        self.assertEqual(body["excluded"][0]["reasons"], ["Qualifikation ‚Maschinist‘ fehlt"])
        self.assertEqual(body["errors"], {})
        self.assertEqual(set(body["excluded"][0]), {"member_id", "name", "reasons"})

    def test_preview_with_groups_uses_group_members(self):
        blue_member = Member.objects.create(name="Blau", lastname="Mitglied", group=self.blue)
        self.session.groups.set([self.blue])
        body = self.post().json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["excluded"][0]["member_id"], blue_member.pk)
        self.assertEqual(body["excluded"][0]["name"], "Blau Mitglied")

    def test_query_count_does_not_grow_with_members(self):
        self.post()  # warm up caches (content types, permissions)
        with self.assertNumQueries(self._count()):
            self.post()
        for i in range(30):
            m = Member.objects.create(name=f"X{i}", lastname="Neu", group=self.red)
            m.departments.add(self.dept)
        with self.assertNumQueries(self._count()):
            body = self.post().json()
        self.assertEqual(body["total"], 60)

    def _count(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            self.post()
        self.assertLess(len(ctx), 25)
        # Same count independent of the number of members: compare against the stored baseline.
        self.__class__._baseline = getattr(self.__class__, "_baseline", len(ctx))
        return self.__class__._baseline

    def test_invalid_rule_is_located(self):
        bad = {"v": 1, "match": "all", "rules": [{"kind": "age", "op": "between", "min": 9, "max": 5}]}
        res = self.post(bad)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["errors"], {"rules[0].max": "Mindestalter größer als Höchstalter"})

    def test_session_without_target_and_bad_session(self):
        orphan = TrainingSession.objects.create(
            title="x", date=date(2026, 10, 10), start_time=time(18), end_time=time(19), department=self.dept
        )
        Member.objects.all().delete()
        body = self.post(session=orphan.pk).json()
        self.assertEqual(body["total"], 0)
        self.assertEqual(self.post(session=999999).status_code, 404)
        self.assertEqual(self.client.post(PREVIEW, {"rule": self.rule}, format="json").status_code, 400)
        self.assertEqual(self.client.post(PREVIEW, {"rule": self.rule, "session": "1"}, format="json").status_code, 400)

    def test_target_cap(self):
        Member.objects.bulk_create([Member(name="B", lastname=str(i), group=self.red) for i in range(470)])
        self.session.groups.set([self.red])
        self.assertEqual(self.post().status_code, 200)  # exactly 500
        Member.objects.create(name="Z", lastname="Z", group=self.red)
        res = self.post()
        self.assertEqual(res.status_code, 400)
        self.assertIn("session", res.json()["errors"])

    def test_permissions(self):
        for user in (self.other_planner, self.reader):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.post().status_code, 403)
        self.client.logout()
        self.assertIn(self.post().status_code, (401, 403))
        # Invalid rule must not be a side channel for unauthorised users.
        self.client.force_login(self.other_planner)
        self.assertEqual(self.post({"v": 9}).status_code, 403)

    def test_portal_account_is_refused(self):
        portal = User.objects.create_user("eltern", password="x", account_kind="portal")
        self.client.force_login(portal)
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(self.client.post(VALIDATE, {"rule": self.rule}, format="json").status_code, 403)

    def test_validate_endpoint(self):
        res = self.client.post(VALIDATE, {"rule": self.rule}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["summary"], "Maschinist")
        res = self.client.post(VALIDATE, {"rule": {"v": 1, "match": "all", "rules": [{"kind": "x"}]}}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("rules[0].kind", res.json()["errors"])
        self.assertEqual(self.client.post(VALIDATE, {}, format="json").status_code, 400)
        self.client.force_login(self.reader)
        self.assertEqual(self.client.post(VALIDATE, {"rule": self.rule}, format="json").status_code, 403)
