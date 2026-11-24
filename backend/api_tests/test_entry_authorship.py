"""Entries on a member record who created them; the author comes from the session, never from the client."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import Attachment, Event, EventType, Member
from membership.models import MembershipEvent
from qualifications.models import Qualification, QualificationType, SpecialTask, SpecialTaskType

RIGHTS = {
    "members": ["view_member", "change_member", "view_event", "add_event", "change_event"],
    "qualifications": [
        "view_qualification",
        "add_qualification",
        "view_specialtask",
        "add_specialtask",
        "change_specialtask",
    ],
}


class EntryAuthorshipTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.department_a = Department.objects.create(name="A", code="authorship-a")
        cls.department_b = Department.objects.create(name="B", code="authorship-b")
        cls.member_a = Member.objects.create(name="Anna", lastname="Muster")
        cls.member_a.departments.add(cls.department_a)
        cls.member_b = Member.objects.create(name="Bert", lastname="Fremd")
        cls.member_b.departments.add(cls.department_b)
        cls.event_type = EventType.objects.create(name="Gespräch")
        cls.qualification_type = QualificationType.objects.create(name="Erste Hilfe")
        cls.task_type = SpecialTaskType.objects.create(name="Kassenwart")

        cls.leader = User.objects.create_user(
            username="leader", first_name="Lena", last_name="Leiterin", password="test-only-password"
        )
        cls.colleague = User.objects.create_user(username="colleague", password="test-only-password")
        role = AuthGroup.objects.create(name="Authorship role A")
        for app_label, codenames in RIGHTS.items():
            role.permissions.add(*Permission.objects.filter(content_type__app_label=app_label, codename__in=codenames))
        for user in (cls.leader, cls.colleague):
            UserDepartmentRole.objects.create(user=user, department=cls.department_a).groups.add(role)
        cls.no_rights = User.objects.create_user(username="no-rights", password="test-only-password")
        UserDepartmentRole.objects.create(user=cls.no_rights, department=cls.department_a)

    def _create_event(self, member, **extra):
        payload = {"member": member.pk, "type_id": self.event_type.pk, "datetime": "2026-11-01", "notes": "Notiz"}
        return self.client.post("/api/v1/events/", {**payload, **extra}, format="json")

    # ── Events (notes on the member) ────────────────────────────────────────

    def test_event_records_the_creating_user(self):
        self.client.force_authenticate(self.leader)

        response = self._create_event(self.member_a)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["created_by_name"], "Lena Leiterin")
        self.assertIsNotNone(response.data["created_at"])
        self.assertEqual(Event.objects.get(pk=response.data["id"]).created_by, self.leader)

    def test_event_author_cannot_be_set_by_the_client(self):
        self.client.force_authenticate(self.leader)

        response = self._create_event(self.member_a, created_by=self.colleague.pk, created_by_name="Jemand")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Event.objects.get(pk=response.data["id"]).created_by, self.leader)

    def test_editing_an_event_keeps_the_original_author(self):
        event = Event.objects.create(
            member=self.member_a, type=self.event_type, datetime=date(2026, 1, 1), created_by=self.leader
        )
        self.client.force_authenticate(self.colleague)

        response = self.client.patch(f"/api/v1/events/{event.pk}/", {"notes": "ergänzt"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        event.refresh_from_db()
        self.assertEqual(event.created_by, self.leader)

    def test_member_event_list_shows_author_and_falls_back_to_username(self):
        Event.objects.create(member=self.member_a, datetime=date(2026, 1, 1), created_by=self.colleague)
        Event.objects.create(member=self.member_a, datetime=date(2026, 1, 2))
        self.client.force_authenticate(self.leader)

        response = self.client.get(f"/api/v1/members/{self.member_a.pk}/events/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["created_by_name"] for row in response.data], [None, "colleague"])

    def test_event_create_anonymous_is_rejected(self):
        response = self._create_event(self.member_a)

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertFalse(Event.objects.exists())

    def test_event_create_without_right_is_rejected(self):
        self.client.force_authenticate(self.no_rights)

        response = self._create_event(self.member_a)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Event.objects.exists())

    def test_event_create_for_foreign_department_is_rejected(self):
        self.client.force_authenticate(self.leader)

        response = self._create_event(self.member_b)

        self.assertIn(response.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.assertFalse(Event.objects.exists())

    # ── Qualifications and special tasks ────────────────────────────────────

    def test_qualification_records_the_creating_user(self):
        self.client.force_authenticate(self.leader)

        response = self.client.post(
            "/api/v1/qualifications/",
            {"type": self.qualification_type.pk, "member": self.member_a.pk, "date_acquired": "2026-10-01"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        qualification = Qualification.objects.get(member=self.member_a)
        self.assertEqual(qualification.created_by, self.leader)
        listing = self.client.get("/api/v1/qualifications/", {"member": self.member_a.pk})
        self.assertEqual(listing.data["results"][0]["created_by_name"], "Lena Leiterin")

    def test_qualification_create_anonymous_is_rejected(self):
        response = self.client.post(
            "/api/v1/qualifications/",
            {"type": self.qualification_type.pk, "member": self.member_a.pk, "date_acquired": "2026-10-01"},
            format="json",
        )

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertFalse(Qualification.objects.exists())

    def test_special_task_records_the_creating_user(self):
        self.client.force_authenticate(self.leader)

        response = self.client.post(
            "/api/v1/qualifications/specialtasks/",
            {"task": self.task_type.pk, "member": self.member_a.pk, "start_date": "2026-10-01"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        task = SpecialTask.objects.get(member=self.member_a)
        self.assertEqual(task.created_by, self.leader)
        detail = self.client.get(f"/api/v1/qualifications/specialtasks/{task.pk}/")
        self.assertEqual(detail.data["created_by_name"], "Lena Leiterin")

    def test_special_task_for_foreign_department_is_rejected(self):
        self.client.force_authenticate(self.leader)

        response = self.client.post(
            "/api/v1/qualifications/specialtasks/",
            {"task": self.task_type.pk, "member": self.member_b.pk, "start_date": "2026-10-01"},
            format="json",
        )

        self.assertIn(response.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))
        self.assertFalse(SpecialTask.objects.exists())

    # ── Attachments and membership history ──────────────────────────────────

    def test_member_attachment_shows_uploader(self):
        self.client.force_authenticate(self.leader)

        response = self.client.post(
            f"/api/v1/members/{self.member_a.pk}/attachments/",
            {"name": "Attest", "file": SimpleUploadedFile("attest.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["uploaded_by_name"], "Lena Leiterin")
        listing = self.client.get(f"/api/v1/members/{self.member_a.pk}/attachments/")
        self.assertEqual([row["uploaded_by_name"] for row in listing.data], ["Lena Leiterin"])

    def test_member_attachments_of_foreign_department_are_hidden(self):
        Attachment.objects.create(
            content_type=ContentType.objects.get_for_model(Member),
            object_id=self.member_b.pk,
            name="Fremd",
            uploaded_by=self.colleague,
        )
        self.client.force_authenticate(self.leader)

        response = self.client.get(f"/api/v1/members/{self.member_b.pk}/attachments/")

        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_membership_history_shows_author(self):
        MembershipEvent.objects.create(
            member=self.member_a,
            department=self.department_a,
            date=date(2026, 1, 1),
            kind=MembershipEvent.Kind.JOINED_NEW,
            created_by=self.leader,
        )
        self.client.force_authenticate(self.leader)

        response = self.client.get("/api/v1/membership/events/", {"member": self.member_a.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["results"][0]["created_by_name"], "Lena Leiterin")
