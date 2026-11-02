"""Guided leave: the leave date starts the anonymization deadline. Fictional data."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from departments.models import Department
from members.models import Member, Status
from privacy.tests.test_erasure import role

User = get_user_model()


class LeaveApiTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="leave-mitte")
        self.nord = Department.objects.create(name="Nord", code="leave-nord")
        self.former = Status.objects.create(name="Ausgetreten")
        self.member = Member.objects.create(name="Mia", lastname="Muster", joined=date(2020, 4, 1))
        self.member.departments.add(self.mitte)
        self.url = f"/api/v1/members/{self.member.pk}/leave/"

    def user(self, name, department, *codenames):
        user = User.objects.create_user(name, password="x")
        role(user, department, *codenames)
        return user

    def test_anonymous_is_rejected(self):
        self.assertIn(self.client.post(self.url, {"left_at": "2026-10-31"}).status_code, (401, 403))

    def test_reader_without_change_right_is_refused(self):
        self.client.force_authenticate(self.user("betreuer", self.mitte, "view_member"))
        self.assertEqual(self.client.post(self.url, {"left_at": "2026-10-31"}, format="json").status_code, 403)
        self.assertIsNone(Member.objects.get(pk=self.member.pk).left_at)

    def test_foreign_department_cannot_reach_the_member(self):
        self.client.force_authenticate(self.user("nord", self.nord, "view_member", "change_member"))
        self.assertEqual(self.client.post(self.url, {"left_at": "2026-10-31"}, format="json").status_code, 404)

    def test_leave_sets_date_status_and_announces_the_anonymization(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_member", "change_member"))
        response = self.client.post(self.url, {"left_at": "2026-10-31", "status_id": self.former.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        member = Member.objects.get(pk=self.member.pk)
        self.assertEqual((member.left_at, member.status_id), (date(2026, 10, 31), self.former.pk))
        self.assertEqual(response.json()["anonymize_due"], str(date(2026, 10, 31) + timedelta(days=365)))

    def test_leave_can_be_withdrawn(self):
        self.member.left_at = date(2026, 10, 31)
        self.member.save(update_fields=["left_at"])
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_member", "change_member"))
        response = self.client.post(self.url, {"left_at": None}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(Member.objects.get(pk=self.member.pk).left_at)
        self.assertIsNone(response.json()["anonymize_due"])

    def test_leave_before_joining_is_rejected(self):
        self.client.force_authenticate(self.user("leiter", self.mitte, "view_member", "change_member"))
        response = self.client.post(self.url, {"left_at": "2019-12-31"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("left_at", response.json())
