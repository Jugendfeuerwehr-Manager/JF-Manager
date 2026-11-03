"""Membership movements: joins, stage changes, transfers and exits. Fictional data."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Member, Status
from membership.models import MembershipEvent
from membership.services import lifecycle

User = get_user_model()
Kind = MembershipEvent.Kind


def role(user, department, *codenames):
    group = Group.objects.create(name=f"{user.username}-{department.code}")
    group.permissions.add(*Permission.objects.filter(codename__in=codenames))
    UserDepartmentRole.objects.create(user=user, department=department).groups.add(group)


class LifecycleServiceTests(TestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="lc-mitte")
        self.nord = Department.objects.create(name="Nord", code="lc-nord")
        self.active = Status.objects.create(name="Aktiv")
        self.trial = Status.objects.create(name="Anwärter", category=Status.Category.TRIAL)
        self.member = Member.objects.create(name="Mia", lastname="Muster", joined=date(2024, 3, 1), status=self.trial)
        self.member.departments.add(self.mitte)

    def test_admit_writes_one_join_per_department(self):
        self.member.departments.add(self.nord)
        lifecycle.admit(self.member)
        events = MembershipEvent.objects.filter(member=self.member)
        self.assertEqual({e.department_id for e in events}, {self.mitte.pk, self.nord.pk})
        self.assertTrue(all(e.kind == Kind.JOINED_NEW and e.date == date(2024, 3, 1) for e in events))

    def test_admit_rejects_an_exit_kind(self):
        with self.assertRaises(ValidationError):
            lifecycle.admit(self.member, kind=Kind.EXIT_EA)

    def test_unchanged_status_logs_nothing(self):
        self.assertEqual(lifecycle.record_stage_change(self.member, from_status=self.trial), [])

    def test_stage_change_keeps_both_statuses(self):
        self.member.status = self.active
        self.member.save()
        (event,) = lifecycle.record_stage_change(self.member, from_status=self.trial)
        self.assertEqual(
            (event.kind, event.from_status, event.to_status), (Kind.STAGE_CHANGED, self.trial, self.active)
        )

    def test_exit_with_reason_sets_left_at_and_logs_the_movement(self):
        lifecycle.record_exit(self.member, left_at=date(2026, 6, 30), kind=Kind.EXIT_OTHER, exit_reason="relocation")
        self.member.refresh_from_db()
        self.assertEqual(self.member.left_at, date(2026, 6, 30))
        event = MembershipEvent.objects.get(member=self.member)
        self.assertEqual(
            (event.kind, event.exit_reason, event.date), (Kind.EXIT_OTHER, "relocation", date(2026, 6, 30))
        )

    def test_reason_only_belongs_to_other_exits(self):
        with self.assertRaises(ValidationError):
            lifecycle.record_exit(self.member, left_at=date(2026, 6, 30), kind=Kind.EXIT_EA, exit_reason="school")
        self.member.refresh_from_db()
        self.assertIsNone(self.member.left_at)

    def test_redating_replaces_and_withdrawing_removes_the_exit(self):
        lifecycle.record_exit(self.member, left_at=date(2026, 6, 30), kind=Kind.EXIT_EA)
        lifecycle.record_exit(self.member, left_at=date(2026, 7, 31), kind=Kind.EXIT_EA)
        self.assertEqual(
            list(MembershipEvent.objects.filter(member=self.member).values_list("date", flat=True)), [date(2026, 7, 31)]
        )
        lifecycle.record_exit(self.member, left_at=None)
        self.assertFalse(MembershipEvent.objects.filter(member=self.member).exists())

    def test_department_move_is_a_transfer(self):
        events = lifecycle.record_department_changes(self.member, added={self.nord.pk}, removed={self.mitte.pk})
        self.assertEqual(
            {(e.department_id, e.kind) for e in events},
            {(self.nord.pk, Kind.JOINED_OTHER_ORG), (self.mitte.pk, Kind.EXIT_OTHER)},
        )


class MemberApiMovementTests(APITestCase):
    def setUp(self):
        self.mitte = Department.objects.create(name="Mitte", code="lca-mitte")
        self.nord = Department.objects.create(name="Nord", code="lca-nord")
        self.active = Status.objects.create(name="Aktiv")
        self.passive = Status.objects.create(name="Passiv", category=Status.Category.PASSIVE)
        self.member = Member.objects.create(name="Mia", lastname="Muster", joined=date(2022, 1, 1), status=self.active)
        self.member.departments.add(self.mitte)
        self.leader = User.objects.create_user("leiter", password="x")
        role(self.leader, self.mitte, "view_member", "change_member", "add_member")
        self.client.force_authenticate(self.leader)

    def test_leave_endpoint_records_kind_and_reason(self):
        response = self.client.post(
            f"/api/v1/members/{self.member.pk}/leave/",
            {"left_at": "2026-09-30", "kind": "exit_other", "exit_reason": "school"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        event = MembershipEvent.objects.get(member=self.member)
        self.assertEqual((event.kind, event.exit_reason, event.created_by), (Kind.EXIT_OTHER, "school", self.leader))

    def test_leave_endpoint_without_kind_stays_compatible(self):
        response = self.client.post(
            f"/api/v1/members/{self.member.pk}/leave/", {"left_at": "2026-09-30"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(MembershipEvent.objects.get(member=self.member).kind, Kind.EXIT_OTHER)

    def test_editing_the_status_logs_a_stage_change(self):
        response = self.client.patch(f"/api/v1/members/{self.member.pk}/", {"status": self.passive.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        event = MembershipEvent.objects.get(member=self.member)
        self.assertEqual(
            (event.kind, event.from_status, event.to_status), (Kind.STAGE_CHANGED, self.active, self.passive)
        )

    def test_status_of_another_department_is_rejected(self):
        foreign = Status.objects.create(name="Nord-Stufe", department=self.nord)
        response = self.client.patch(f"/api/v1/members/{self.member.pk}/", {"status": foreign.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("status", response.json())

    def test_creating_a_member_with_join_date_records_the_join(self):
        response = self.client.post(
            f"/api/v1/members/?department={self.mitte.pk}",
            {"name": "Ben", "lastname": "Beispiel", "joined": "2026-04-01"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        event = MembershipEvent.objects.get(member_id=response.json()["id"])
        self.assertEqual(
            (event.kind, event.department_id, event.date), (Kind.JOINED_NEW, self.mitte.pk, date(2026, 4, 1))
        )
