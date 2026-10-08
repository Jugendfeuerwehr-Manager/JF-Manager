"""Events follow their member's department and the event view right."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Event, Member


class EventScopePermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="event-scope-a")
        cls.department_b = Department.objects.create(name="B", code="event-scope-b")
        cls.member_a = Member.objects.create(name="A", lastname="Member")
        cls.member_b = Member.objects.create(name="B", lastname="Member")
        cls.member_a.departments.add(cls.department_a)
        cls.member_b.departments.add(cls.department_b)
        cls.event_a = Event.objects.create(member=cls.member_a, datetime=date(2026, 1, 1), notes="A event")
        cls.event_b = Event.objects.create(member=cls.member_b, datetime=date(2026, 1, 2), notes="B event")

        cls.viewer = get_user_model().objects.create_user(username="event-viewer", password="test-only-password")
        group_a = AuthGroup.objects.create(name="Event viewer A")
        group_a.permissions.add(
            Permission.objects.get(content_type__app_label="members", codename="view_member"),
            Permission.objects.get(content_type__app_label="members", codename="view_event"),
        )
        group_b = AuthGroup.objects.create(name="Member viewer B")
        group_b.permissions.add(Permission.objects.get(content_type__app_label="members", codename="view_member"))
        UserDepartmentRole.objects.create(user=cls.viewer, department=cls.department_a).groups.add(group_a)
        UserDepartmentRole.objects.create(user=cls.viewer, department=cls.department_b).groups.add(group_b)

    def setUp(self):
        self.client.force_authenticate(user=self.viewer)

    def test_event_list_contains_only_event_permitted_department(self):
        response = self.client.get("/api/v1/events/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual({row["id"] for row in rows}, {self.event_a.pk})

    def test_event_detail_in_read_only_department_is_hidden(self):
        response = self.client.get(f"/api/v1/events/{self.event_b.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_member_events_excludes_events_without_event_view_right(self):
        response = self.client.get(f"/api/v1/members/{self.member_b.pk}/events/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_member_events_in_permitted_department_are_visible(self):
        response = self.client.get(f"/api/v1/members/{self.member_a.pk}/events/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data], [self.event_a.pk])

    def test_change_right_in_a_does_not_allow_event_change_in_b(self):
        group_a = AuthGroup.objects.get(name="Event viewer A")
        group_a.permissions.add(Permission.objects.get(content_type__app_label="members", codename="change_event"))

        response = self.client.patch(f"/api/v1/events/{self.event_b.pk}/", {"notes": "changed"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.event_b.refresh_from_db()
        self.assertEqual(self.event_b.notes, "B event")
