"""UX-07.1: recipient check before sending (resolved, excluded, merged) with scope tests."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department, UserDepartmentRole
from members.models import EmailMessage, EmailRecipient, Group, Member, Parent
from members.services.email_service import MemberEmailService

URL = "/api/v1/emails/recipient_check/"


class RecipientCheckTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dept_a = Department.objects.create(name="A", code="rc-a")
        cls.dept_b = Department.objects.create(name="B", code="rc-b")
        cls.group_a = Group.objects.create(name="Gruppe A", department=cls.dept_a)
        cls.group_b = Group.objects.create(name="Gruppe B", department=cls.dept_b)

        def member(name, email="", dept=None, group=None):
            created = Member.objects.create(name=name, lastname="Beispiel", email=email, group=group)
            created.departments.add(dept or cls.dept_a)
            return created

        cls.sibling_one = member("Ada", group=cls.group_a)
        cls.sibling_two = member("Ben", group=cls.group_a)
        parent = Parent.objects.create(name="Eva", lastname="Beispiel", email="eltern@example.test")
        parent.children.add(cls.sibling_one, cls.sibling_two)
        cls.no_address = member("Cem", group=cls.group_a)
        cls.invalid = member("Dora", email="kein-at-zeichen", group=cls.group_a)
        cls.own = member("Emil", email="emil@example.test", group=cls.group_a)
        cls.foreign = member("Fritz", email="fritz@example.test", dept=cls.dept_b, group=cls.group_b)

        cls.sender = get_user_model().objects.create_user(username="rc-sender", password="test-only-password")
        send_group = AuthGroup.objects.create(name="RC sender")
        send_group.permissions.add(Permission.objects.get(codename="can_send_member_emails"))
        UserDepartmentRole.objects.create(user=cls.sender, department=cls.dept_a).groups.add(send_group)
        cls.reader = get_user_model().objects.create_user(username="rc-reader", password="test-only-password")
        UserDepartmentRole.objects.create(user=cls.reader, department=cls.dept_a)

    def check(self, payload, user=None):
        self.client.force_authenticate(user=user or self.sender)
        return self.client.post(URL, payload, format="json")

    def test_lists_resolved_and_excluded_recipients_with_reasons(self):
        response = self.check({"recipient_type": "group", "recipient_group": self.group_a.pk, "body_html": "<p>Hi</p>"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["member_count"], 5)
        self.assertEqual(
            sorted(item["email"] for item in response.data["recipients"]),
            ["eltern@example.test", "emil@example.test"],
        )
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["merged_duplicates"], 1)
        reasons = {(item["member_id"], item["reason_code"]) for item in response.data["excluded"]}
        self.assertEqual(reasons, {(self.no_address.pk, "no_address"), (self.invalid.pk, "invalid_address")})
        self.assertTrue(all(item["reason"] for item in response.data["excluded"]))

    def test_personalised_messages_are_not_merged_by_address(self):
        response = self.check(
            {
                "recipient_type": "multiple",
                "recipient_members": [self.sibling_one.pk, self.sibling_two.pk],
                "body_html": "<p>Hallo {{vorname}}</p>",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["personalized"])
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["merged_duplicates"], 0)
        self.assertEqual(
            {item["member_id"] for item in response.data["recipients"]}, {self.sibling_one.pk, self.sibling_two.pk}
        )

    def test_prepared_deliveries_match_the_check(self):
        message = EmailMessage.objects.create(
            sender=self.sender, subject="S", body_html="<p>Hallo {{vorname}}</p>", recipient_type="multiple"
        )
        message.recipient_members.set([self.sibling_one, self.sibling_two])

        count = MemberEmailService.prepare_recipients(message)

        self.assertEqual(count, 2)
        bodies = set(
            EmailRecipient.objects.filter(email_message=message).values_list("personalized_body_html", flat=True)
        )
        self.assertEqual(bodies, {"<p>Hallo Ada</p>", "<p>Hallo Ben</p>"})

    def test_all_stays_inside_the_sending_department(self):
        response = self.check({"recipient_type": "all"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotIn("fritz@example.test", [item["email"] for item in response.data["recipients"]])
        self.assertNotIn(self.foreign.pk, [item["member_id"] for item in response.data["excluded"]])

    def test_foreign_department_targets_are_not_found(self):
        group = self.check({"recipient_type": "group", "recipient_group": self.group_b.pk})
        individual = self.check({"recipient_type": "individual", "recipient_member": self.foreign.pk})
        multiple = self.check({"recipient_type": "multiple", "recipient_members": [self.foreign.pk]})

        self.assertEqual(group.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(individual.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(multiple.status_code, status.HTTP_200_OK)
        self.assertEqual(multiple.data["count"], 0)
        self.assertEqual(multiple.data["member_count"], 0)

    def test_invalid_selection_is_rejected(self):
        self.assertEqual(self.check({"recipient_type": "unknown"}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.check({"recipient_type": "group"}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.check({"recipient_type": "group", "recipient_group": 999999}).status_code, status.HTTP_404_NOT_FOUND
        )

    def test_requires_sending_right_and_login(self):
        self.assertEqual(self.check({"recipient_type": "all"}, user=self.reader).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=None)
        self.assertIn(
            self.client.post(URL, {"recipient_type": "all"}, format="json").status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
