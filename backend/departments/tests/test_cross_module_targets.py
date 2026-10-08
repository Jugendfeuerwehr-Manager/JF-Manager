"""Write targets across modules follow the right in the target department (SEC-02.9).

The user writes in department A and may only read in department B.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import EmailMessage, Event, EventType, Group, Member, Parent
from servicebook.models import Service

WRITE_A = (
    "members.view_member",
    "members.add_member",
    "members.change_member",
    "members.view_group",
    "members.view_event",
    "members.add_event",
    "members.change_event",
    "members.view_eventtype",
    "members.add_eventtype",
    "members.change_eventtype",
    "members.can_send_member_emails",
    "servicebook.view_service",
    "servicebook.add_service",
    "servicebook.change_service",
)
READ_B = ("members.view_member", "members.view_group", "members.view_event", "servicebook.view_service")


def permissions(names):
    return [Permission.objects.get(content_type__app_label=n.split(".")[0], codename=n.split(".")[1]) for n in names]


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CrossModuleTargetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="A", code="cross-target-a")
        cls.department_b = Department.objects.create(name="B", code="cross-target-b")
        cls.member_a = Member.objects.create(name="Anna", lastname="A", email="anna@example.invalid")
        cls.member_b = Member.objects.create(name="Berta", lastname="B", email="berta@example.invalid")
        cls.member_a.departments.add(cls.department_a)
        cls.member_b.departments.add(cls.department_b)
        parent_b = Parent.objects.create(name="Parent", lastname="B", email="parent-b@example.invalid")
        parent_b.children.add(cls.member_b)
        cls.group_b = Group.objects.create(name="Group B", department=cls.department_b)
        now = timezone.now()
        cls.service_a = Service.objects.create(start=now, end=now + timedelta(hours=2), department=cls.department_a)

        cls.user = get_user_model().objects.create_user(username="cross-target", password="test-only-password")
        writer = AuthGroup.objects.create(name="Cross writer A")
        writer.permissions.add(*permissions(WRITE_A))
        reader = AuthGroup.objects.create(name="Cross reader B")
        reader.permissions.add(*permissions(READ_B))
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_a).groups.add(writer)
        UserDepartmentRole.objects.create(user=cls.user, department=cls.department_b).groups.add(reader)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def assertRejected(self, response):
        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
            getattr(response, "data", response),
        )

    # E-Mail ------------------------------------------------------------
    def send(self, **data):
        payload = {"subject": "Hallo", "body_html": "<p>Hallo</p>", "body_text": "Hallo", "layout": "none"}
        payload.update(data)
        return self.client.post("/api/v1/emails/send/", payload, format="json")

    def test_individual_email_to_member_of_read_only_department_is_rejected(self):
        response = self.send(recipient_type="individual", recipient_member=self.member_b.pk)

        self.assertRejected(response)
        sent_to = {address for message in mail.outbox for address in message.to + message.bcc}
        self.assertFalse({"berta@example.invalid", "parent-b@example.invalid"} & sent_to)

    def test_group_email_to_group_of_read_only_department_reaches_nobody(self):
        self.member_b.group = self.group_b
        self.member_b.save()

        response = self.send(recipient_type="group", recipient_group=self.group_b.pk)

        self.assertRejected(response)
        self.assertEqual(mail.outbox, [])

    def test_individual_email_to_own_member_is_sent(self):
        response = self.send(recipient_type="individual", recipient_member=self.member_a.pk)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_email_cannot_be_labelled_with_read_only_department(self):
        response = self.send(
            recipient_type="individual", recipient_member=self.member_a.pk, department=self.department_b.pk
        )

        self.assertRejected(response)
        self.assertFalse(EmailMessage.objects.filter(department=self.department_b).exists())

    # Ereignisse --------------------------------------------------------
    def test_event_cannot_be_created_for_member_of_read_only_department(self):
        response = self.client.post(
            "/api/v1/events/", {"member": self.member_b.pk, "datetime": "2026-01-01", "notes": "x"}, format="json"
        )

        self.assertRejected(response)
        self.assertFalse(Event.objects.filter(member=self.member_b).exists())

    def test_event_can_be_created_for_own_member(self):
        response = self.client.post(
            "/api/v1/events/", {"member": self.member_a.pk, "datetime": "2026-01-01", "notes": "x"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_event_type_cannot_be_created_in_read_only_department(self):
        response = self.client.post(
            "/api/v1/event-types/", {"name": "B type", "department": self.department_b.pk}, format="json"
        )

        self.assertRejected(response)
        self.assertFalse(EventType.objects.filter(department=self.department_b).exists())

    # Dienste -----------------------------------------------------------
    def test_service_cannot_be_created_in_read_only_department(self):
        start = timezone.now() + timedelta(days=1)
        response = self.client.post(
            "/api/v1/servicebook/services/",
            {
                "start": start.isoformat(),
                "end": (start + timedelta(hours=2)).isoformat(),
                "department": self.department_b.pk,
            },
            format="json",
        )

        self.assertRejected(response)
        self.assertFalse(Service.objects.filter(department=self.department_b).exists())

    def test_service_cannot_be_moved_to_read_only_department(self):
        response = self.client.patch(
            f"/api/v1/servicebook/services/{self.service_a.pk}/", {"department": self.department_b.pk}, format="json"
        )

        self.assertRejected(response)
        self.service_a.refresh_from_db()
        self.assertEqual(self.service_a.department_id, self.department_a.pk)

    # Mitglieder --------------------------------------------------------
    def test_member_cannot_be_assigned_group_of_read_only_department(self):
        response = self.client.patch(f"/api/v1/members/{self.member_a.pk}/", {"group": self.group_b.pk}, format="json")

        self.assertRejected(response)
        self.member_a.refresh_from_db()
        self.assertIsNone(self.member_a.group_id)

    def test_member_cannot_be_moved_into_read_only_department(self):
        response = self.client.patch(
            f"/api/v1/members/{self.member_a.pk}/", {"departments": [self.department_b.pk]}, format="json"
        )

        self.assertRejected(response)
        self.assertEqual(list(self.member_a.departments.values_list("pk", flat=True)), [self.department_a.pk])
