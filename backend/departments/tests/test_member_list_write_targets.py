"""SEC-03.2: member list writes use one explicit, writable department."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Event, EventType, Member, MemberList, MemberListEntry


class MemberListWriteTargetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="List target A", code="list-target-a")
        cls.department_b = Department.objects.create(name="List target B", code="list-target-b")
        cls.member_a = Member.objects.create(name="A", lastname="Target")
        cls.member_b = Member.objects.create(name="B", lastname="Target")
        cls.member_shared = Member.objects.create(name="Shared", lastname="Target")
        cls.member_a.departments.add(cls.department_a)
        cls.member_b.departments.add(cls.department_b)
        cls.member_shared.departments.add(cls.department_a, cls.department_b)
        cls.list_a = MemberList.objects.create(name="A existing", department=cls.department_a)
        MemberListEntry.objects.create(member_list=cls.list_a, member=cls.member_a)

        cls.editor = get_user_model().objects.create_user(username="list-target-editor", password="test-only-password")
        group_a = Group.objects.create(name="List target editor A")
        group_a.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="members",
                codename__in=["view_memberlist", "add_memberlist", "change_memberlist"],
            )
        )
        group_b = Group.objects.create(name="List target reader B")
        group_b.permissions.add(Permission.objects.get(content_type__app_label="members", codename="view_memberlist"))
        UserDepartmentRole.objects.create(user=cls.editor, department=cls.department_a).groups.add(group_a)
        UserDepartmentRole.objects.create(user=cls.editor, department=cls.department_b).groups.add(group_b)

    def setUp(self):
        self.client.force_authenticate(user=self.editor)

    def test_create_requires_explicit_department_even_with_multiple_roles(self):
        before = MemberList.objects.count()

        response = self.client.post("/api/v1/member-lists/", {"name": "No owner"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("department", response.data)
        self.assertEqual(MemberList.objects.count(), before)

    def test_create_needs_add_right_in_chosen_department(self):
        rejected = self.client.post(
            "/api/v1/member-lists/", {"name": "B forbidden", "department": self.department_b.pk}, format="json"
        )
        accepted = self.client.post(
            "/api/v1/member-lists/", {"name": "A allowed", "department": self.department_a.pk}, format="json"
        )

        self.assertEqual(rejected.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(accepted.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MemberList.objects.get(pk=accepted.data["id"]).department_id, self.department_a.pk)

    def test_cannot_move_list_to_other_department_even_for_shared_entries(self):
        MemberListEntry.objects.create(member_list=self.list_a, member=self.member_shared)

        response = self.client.patch(
            f"/api/v1/member-lists/{self.list_a.pk}/",
            {"department": self.department_b.pk, "description": "Exposed"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.list_a.refresh_from_db()
        self.assertEqual(self.list_a.department_id, self.department_a.pk)
        self.assertEqual(self.list_a.description, "")

    def test_add_member_rejects_foreign_target_and_accepts_shared_member(self):
        rejected = self.client.post(
            f"/api/v1/member-lists/{self.list_a.pk}/add_member/",
            {"member_id": self.member_b.pk},
            format="json",
        )
        accepted = self.client.post(
            f"/api/v1/member-lists/{self.list_a.pk}/add_member/",
            {"member_id": self.member_shared.pk},
            format="json",
        )

        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(accepted.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            set(self.list_a.entries.values_list("member_id", flat=True)),
            {self.member_a.pk, self.member_shared.pk},
        )

    def test_bulk_add_rejects_mixed_targets_atomically(self):
        rejected = self.client.post(
            f"/api/v1/member-lists/{self.list_a.pk}/bulk_add/",
            {"member_ids": [self.member_shared.pk, self.member_b.pk]},
            format="json",
        )

        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(self.list_a.entries.values_list("member_id", flat=True)), {self.member_a.pk})

    def test_event_import_inverted_selection_stays_in_explicit_department(self):
        response = self.client.post(
            "/api/v1/member-lists/create_from_event_type/",
            {"name": "A without events", "department": self.department_a.pk, "invert": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = MemberList.objects.get(pk=response.data["id"])
        self.assertEqual(created.department_id, self.department_a.pk)
        self.assertEqual(
            set(created.entries.values_list("member_id", flat=True)),
            {self.member_a.pk, self.member_shared.pk},
        )

    def test_event_import_rejects_read_only_or_conflicting_department(self):
        before = MemberList.objects.count()
        denied = self.client.post(
            "/api/v1/member-lists/create_from_event_type/",
            {"name": "B attempt", "department": self.department_b.pk, "invert": True},
            format="json",
        )
        mismatched = self.client.post(
            f"/api/v1/member-lists/create_from_event_type/?department={self.department_b.pk}",
            {"name": "A mismatched", "department": self.department_a.pk, "invert": True},
            format="json",
        )

        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(mismatched.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.assertEqual(MemberList.objects.count(), before)

    def test_event_import_rejects_foreign_department_event_type(self):
        foreign_type = EventType.objects.create(name="B only", department=self.department_b)

        response = self.client.post(
            "/api/v1/member-lists/create_from_event_type/",
            {
                "name": "A with B event type",
                "department": self.department_a.pk,
                "event_type_id": foreign_type.pk,
                "invert": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(MemberList.objects.filter(name="A with B event type").exists())

    def test_event_import_does_not_use_foreign_events_for_shared_member(self):
        foreign_type = EventType.objects.create(name="B event", department=self.department_b)
        Event.objects.create(type=foreign_type, member=self.member_shared, datetime=date.today())

        response = self.client.post(
            "/api/v1/member-lists/create_from_event_type/",
            {"name": "A without A events", "department": self.department_a.pk, "invert": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = MemberList.objects.get(pk=response.data["id"])
        self.assertEqual(
            set(created.entries.values_list("member_id", flat=True)),
            {self.member_a.pk, self.member_shared.pk},
        )
