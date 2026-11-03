"""Movement timeline and department-scoped stages: anonymous, missing right, foreign department, allowed."""

from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from departments.models import Department
from members.models import Member, Status
from membership.models import MembershipEvent
from membership.tests.test_lifecycle import role

User = get_user_model()
URL = "/api/v1/membership/events/"


class MembershipEventApiTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="ev-mitte")
        self.nord = Department.objects.create(name="Nord", code="ev-nord")
        self.member = Member.objects.create(name="Mia", lastname="Muster")
        self.member.departments.add(self.mitte)
        self.event = MembershipEvent.objects.create(
            member=self.member, department=self.mitte, date=date(2026, 5, 1), kind=MembershipEvent.Kind.EXIT_OTHER
        )

    def user(self, name, department, *codenames):
        user = User.objects.create_user(name, password="x")
        role(user, department, *codenames)
        return user

    def test_anonymous_is_rejected(self):
        self.assertIn(self.client.get(URL).status_code, (401, 403))

    def test_user_without_member_right_is_refused(self):
        self.client.force_authenticate(self.user("ohne", self.mitte, "view_group"))
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_foreign_department_sees_nothing_and_cannot_correct(self):
        self.client.force_authenticate(self.user("nord", self.nord, "view_member", "change_member"))
        self.assertEqual(self.client.get(URL).json()["count"], 0)
        response = self.client.patch(f"{URL}{self.event.pk}/", {"exit_reason": "school"}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_reader_lists_but_cannot_correct(self):
        self.client.force_authenticate(self.user("leser", self.mitte, "view_member"))
        response = self.client.get(URL, {"member": self.member.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()["results"]], [self.event.pk])
        response = self.client.patch(f"{URL}{self.event.pk}/", {"exit_reason": "school"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_editor_completes_the_exit_reason(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_member", "change_member"))
        response = self.client.patch(f"{URL}{self.event.pk}/", {"exit_reason": "school"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.event.refresh_from_db()
        self.assertEqual(self.event.exit_reason, "school")

    def test_an_exit_cannot_become_a_join(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_member", "change_member"))
        response = self.client.patch(f"{URL}{self.event.pk}/", {"kind": "joined_new"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_movements_cannot_be_created_or_deleted_directly(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_member", "change_member", "add_member"))
        self.assertIn(self.client.post(URL, {}, format="json").status_code, (403, 405))
        self.assertIn(self.client.delete(f"{URL}{self.event.pk}/").status_code, (403, 405))
        self.assertTrue(MembershipEvent.objects.filter(pk=self.event.pk).exists())


class StatusScopeTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="st-mitte")
        self.nord = Department.objects.create(name="Nord", code="st-nord")
        self.central = Status.objects.create(name="Aktiv")
        self.own = Status.objects.create(name="Schnupperphase", department=self.mitte, category=Status.Category.TRIAL)
        self.foreign = Status.objects.create(name="Nord-Stufe", department=self.nord)
        self.leader = User.objects.create_user("leiter", password="x")
        role(self.leader, self.mitte, "view_status", "add_status", "change_status")
        self.client.force_authenticate(self.leader)

    def test_anonymous_is_rejected(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get("/api/v1/statuses/").status_code, (401, 403))

    def test_department_sees_own_and_central_stages_only(self):
        names = {row["name"] for row in self.client.get("/api/v1/statuses/").json()["results"]}
        self.assertEqual(names, {"Aktiv", "Schnupperphase"})

    def test_department_cannot_change_central_stage(self):
        response = self.client.patch(f"/api/v1/statuses/{self.central.pk}/", {"name": "x"}, format="json")
        self.assertIn(response.status_code, (403, 404))

    def test_department_cannot_create_stage_for_another_department(self):
        response = self.client.post("/api/v1/statuses/", {"name": "x", "department": self.nord.pk}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_department_creates_and_sorts_own_stage(self):
        response = self.client.post(
            "/api/v1/statuses/",
            {"name": "Übertritt EA", "department": self.mitte.pk, "category": "transferred", "sort_order": 5},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["category"], "transferred")
