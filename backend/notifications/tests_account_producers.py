"""NOTIF-01.5c: parent access end, invitation accepted, registration digest."""

import re
from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from departments.models import Department, UserDepartmentRole
from members.models import Member, Parent
from notifications.account_producers import parent_access_warnings, registration_digest
from notifications.dispatch import deliver_emails
from notifications.models import EmailDelivery, InboxItem
from participation import service
from participation.tests.helpers import future_day, make_session
from portal.models import AccountLink

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountProducerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        inviters = Group.objects.create(name="Einladende")
        inviters.permissions.add(Permission.objects.get(codename="invite_portal_account"))
        cls.staff = User.objects.create_user("leitung", email="leitung@example.invalid", password="x")
        UserDepartmentRole.objects.create(user=cls.staff, department=cls.mitte).groups.add(inviters)
        today = timezone.localdate()
        turning = today + timedelta(days=20)
        cls.child = Member.objects.create(
            name="Jonas", lastname="Becker", birthday=date(turning.year - 18, turning.month, min(turning.day, 28))
        )
        cls.child.departments.add(cls.mitte)
        cls.parent = Parent.objects.create(name="Sandra", lastname="Becker", email="sandra@example.invalid")
        cls.parent.children.add(cls.child)
        cls.parent_user = User.objects.create_user(
            "sandra@example.invalid", email="sandra@example.invalid", password="x", account_kind="portal"
        )
        AccountLink.objects.create(user=cls.parent_user, parent=cls.parent, status="confirmed")

    def test_parent_access_warning_once(self):
        out = StringIO()
        call_command("portal_access_lifecycle", stdout=out)
        call_command("portal_access_lifecycle", stdout=StringIO())  # daily repetition stays quiet
        notice = InboxItem.objects.get(kind="parent_access_end", item_type="notice")
        self.assertIn("Jonas", notice.title)
        self.assertEqual(notice.count, 1)
        task = InboxItem.objects.get(kind="parent_access_end", item_type="task")
        self.assertTrue(task.recipients.filter(user=self.staff).exists())
        self.assertEqual(EmailDelivery.objects.filter(kind="parent_access_end").count(), 1)
        deliver_emails()
        self.assertIn("endet am", mail.outbox[0].subject)
        self.assertEqual(parent_access_warnings([self.child.pk]), 0)

    def test_invitation_accepted_notifies_inviter(self):
        other = Parent.objects.create(name="Eva", lastname="Neu", email="eva@example.invalid")
        other.children.add(self.child)
        client = self.client_class()
        client.force_login(self.staff)
        with self.captureOnCommitCallbacks(execute=True):
            from rest_framework.test import APIClient

            api = APIClient()
            api.force_authenticate(self.staff)
            api.post("/api/v1/portal/invitations/", {"parent": other.pk}, format="json")
        token = re.search(r"token=([\w-]+)", mail.outbox[-1].body).group(1)
        with self.captureOnCommitCallbacks(execute=True):
            APIClient().post(
                "/api/v1/portal/invitations/accept/",
                {
                    "token": token,
                    "password": "Feuerwehr-Zugang-2026!",
                    "password_confirm": "Feuerwehr-Zugang-2026!",
                    "privacy_accepted": True,
                },
                format="json",
            )
        item = InboxItem.objects.get(kind="invitation_accepted")
        self.assertIn("Eva Neu", item.title)
        self.assertTrue(item.recipients.filter(user=self.staff).exists())

    def test_digest_once_per_day(self):
        with self.captureOnCommitCallbacks(execute=True):
            session = make_session(self.mitte, day=future_day(20), created_by=self.staff, title="Knoten")
        with self.captureOnCommitCallbacks(execute=True):
            service.set_registration(
                session.pk, self.child.pk, "cancelled", actor=self.parent_user, source="portal_parent"
            )
        self.assertEqual(registration_digest(), 1)
        self.assertEqual(registration_digest(), 0)
        deliver_emails()
        digest = [m for m in mail.outbox if m.subject.startswith("Meldungen von heute")]
        self.assertEqual(len(digest), 1)
        self.assertIn("Knoten", digest[0].body)
        self.assertIn("1 abgemeldet", digest[0].body)
