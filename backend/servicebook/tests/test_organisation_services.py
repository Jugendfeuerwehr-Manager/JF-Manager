"""Services for the whole organisation (department=NULL), e.g. a general assembly."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Member
from servicebook.models import Attendance, Service

User = get_user_model()
URL = "/api/v1/servicebook/services/"


def role(user, department, *codenames):
    group = Group.objects.create(name=f"{user.username}-{department.code}")
    group.permissions.set(Permission.objects.filter(content_type__app_label="servicebook", codename__in=codenames))
    UserDepartmentRole.objects.create(user=user, department=department).groups.add(group)


class OrganisationServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.north = Department.objects.create(name="Nord", code="no")
        cls.south = Department.objects.create(name="Süd", code="su")
        now = timezone.now()
        cls.assembly = Service.objects.create(topic="Vollversammlung", start=now, end=now + timedelta(hours=2))
        cls.north_service = Service.objects.create(
            topic="Übung Nord", start=now, end=now + timedelta(hours=2), department=cls.north
        )
        cls.ada = Member.objects.create(name="Ada", lastname="Nord")
        cls.ada.departments.add(cls.north)
        cls.ben = Member.objects.create(name="Ben", lastname="Süd")
        cls.ben.departments.add(cls.south)
        cls.leader = User.objects.create_user("leiter-nord")
        role(cls.leader, cls.north, "view_service", "add_service", "change_service", "change_attendance")
        cls.reader = User.objects.create_user("ohne-anwesenheit")
        role(cls.reader, cls.north, "view_service")
        cls.admin = User.objects.create_superuser("admin", password="x")

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def board(self, user):
        return self.client_for(user).get(f"{URL}{self.assembly.pk}/attendance_board/")

    def test_anonymous_sees_nothing(self):
        self.assertIn(APIClient().get(f"{URL}{self.assembly.pk}/").status_code, (401, 403))

    def test_department_view_lists_the_organisation_service(self):
        for user in (self.leader, self.admin):
            response = self.client_for(user).get(URL, {"department": self.north.pk})
            ids = {row["id"] for row in response.data["results"]}
            self.assertEqual(ids, {self.assembly.pk, self.north_service.pk}, user)
            detail = self.client_for(user).get(f"{URL}{self.assembly.pk}/", {"department": self.north.pk})
            self.assertEqual(detail.status_code, 200, user)

    def test_department_role_cannot_edit_or_delete_it(self):
        client = self.client_for(self.leader)
        self.assertEqual(client.patch(f"{URL}{self.assembly.pk}/", {"topic": "x"}, format="json").status_code, 404)
        self.assertIn(client.delete(f"{URL}{self.assembly.pk}/").status_code, (403, 404))
        self.assertEqual(Service.objects.get(pk=self.assembly.pk).topic, "Vollversammlung")

    def test_only_organisation_wide_accounts_create_it_explicitly(self):
        payload = {"start": "2026-11-01T18:00:00Z", "end": "2026-11-01T20:00:00Z", "department": None}
        self.assertEqual(self.client_for(self.leader).post(URL, payload, format="json").status_code, 403)
        response = self.client_for(self.admin).post(URL, payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(Service.objects.get(pk=response.data["id"]).department_id)

    def test_department_roles_record_their_own_people_only(self):
        rows = self.board(self.leader).json()["members"]
        self.assertEqual([row["id"] for row in rows], [self.ada.pk])
        client = self.client_for(self.leader)
        url = f"{URL}{self.assembly.pk}/attendance_board/"
        change = {"kind": "member", "state": "A", "expected_state": None}
        self.assertEqual(client.patch(url, {**change, "person_id": self.ada.pk}, format="json").status_code, 200)
        self.assertEqual(client.patch(url, {**change, "person_id": self.ben.pk}, format="json").status_code, 400)
        self.assertEqual(list(Attendance.objects.values_list("person_id", flat=True)), [self.ada.pk])

    def test_without_attendance_right_the_board_stays_closed(self):
        self.assertEqual(self.board(self.reader).status_code, 403)

    def test_foreign_department_service_stays_hidden(self):
        outsider = User.objects.create_user("leiter-sued")
        role(outsider, self.south, "view_service", "change_attendance")
        response = self.client_for(outsider).get(f"{URL}{self.north_service.pk}/attendance_board/")
        self.assertEqual(response.status_code, 404)

    def test_organisation_wide_account_sees_everybody(self):
        ids = {row["id"] for row in self.board(self.admin).json()["members"]}
        self.assertEqual(ids, {self.ada.pk, self.ben.pk})
