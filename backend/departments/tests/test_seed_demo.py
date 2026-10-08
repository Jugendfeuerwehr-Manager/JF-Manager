from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from inventory.models import Stock
from members.models import Member
from orders.models import OrderItem
from qualifications.models import Qualification
from servicebook.models import Attendance, Service
from training.models import TrainingSession
from users.mfa import current_step, totp_at
from users.mfa_policy import mfa_required


@override_settings(DEBUG=True)
class SeedDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_role_templates", stdout=StringIO())
        cls.output = StringIO()
        call_command("seed_demo", password="demo-pass-123", stdout=cls.output)

    def test_fills_every_module_consistently(self):
        self.assertEqual(Member.objects.count(), 53)
        self.assertEqual(Member.objects.filter(departments__isnull=True).count(), 0)
        self.assertTrue(Attendance.objects.exists())
        self.assertTrue(Service.objects.filter(training_session__isnull=False).exists())
        statuses = set(TrainingSession.objects.values_list("status", flat=True))
        self.assertEqual(statuses, {"draft", "published", "completed", "cancelled"})
        self.assertTrue(TrainingSession.objects.filter(series_parent__isnull=False).exists())
        self.assertEqual(
            set(OrderItem.objects.values_list("status__code", flat=True)),
            {"NEW", "ORDERED", "RECEIVED", "DELIVERED", "CANCELLED"},
        )
        self.assertTrue(OrderItem.objects.filter(loan_transaction__isnull=False).exists())
        self.assertFalse(Stock.objects.filter(quantity__lt=0).exists())
        self.assertTrue(Qualification.objects.filter(date_expires__lt=self.today()).exists())

    def today(self):
        from django.utils import timezone

        return timezone.localdate()

    def test_accounts_use_the_given_password_and_privileged_ones_have_an_authenticator(self):
        users = get_user_model().objects.filter(email__endswith="@demo.example.invalid")
        self.assertEqual(users.count(), 12)
        for user in users:
            self.assertTrue(user.check_password("demo-pass-123"))
            self.assertEqual(mfa_required(user), hasattr(user, "mfa_device"), user.username)
        self.assertIn("demo-pass-123", self.output.getvalue())
        self.assertEqual(users.get(username="admin").favorite_department.code, "mitte")
        self.assertEqual(users.get(username="leitung.nord").favorite_department.code, "nord")

    def test_refuses_a_non_empty_database_and_production(self):
        with self.assertRaisesMessage(CommandError, "nicht leer"):
            call_command("seed_demo", stdout=StringIO())
        with override_settings(DEBUG=False), self.assertRaisesMessage(CommandError, "DEBUG"):
            call_command("seed_demo", stdout=StringIO())

    def test_demo_totp_only_for_seeded_accounts_in_debug(self):
        out = StringIO()
        call_command("demo_totp", "admin", stdout=out)
        device = get_user_model().objects.get(username="admin").mfa_device
        step = current_step()
        self.assertIn(out.getvalue().strip(), {totp_at(device.secret, step - 1), totp_at(device.secret, step)})
        get_user_model().objects.create_user(username="echt", email="echt@example.org", password="x")
        with self.assertRaises(CommandError):
            call_command("demo_totp", "echt", stdout=StringIO())
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            call_command("demo_totp", "admin", stdout=StringIO())

    def test_parent_and_member_portal_access(self):
        from members.models import Parent
        from portal.models import AccountLink

        model = get_user_model()
        self.assertEqual(
            model.objects.filter(account_kind="staff", email__endswith="@demo.example.invalid").count(), 10
        )
        parent_user = model.objects.get(username="eltern@demo.example.invalid")
        member_user = model.objects.get(username="mitglied@demo.example.invalid")
        for user in (parent_user, member_user):
            self.assertTrue(user.is_portal_account)
            self.assertTrue(user.check_password("demo-pass-123"))
            self.assertFalse(user.groups.exists() or user.department_roles.exists() or hasattr(user, "mfa_device"))
            self.assertEqual(user.account_link.status, AccountLink.Status.CONFIRMED)

        parent = parent_user.account_link.parent
        self.assertIsNone(parent_user.account_link.member)
        self.assertEqual(parent.email, parent_user.email)
        children = list(parent.children.all())
        self.assertEqual(len(children), 2)
        self.assertEqual({c.departments.get().code for c in children}, {"mitte", "kinder"})
        today = self.today()
        self.assertTrue(all(c.birthday.replace(year=c.birthday.year + 18) > today for c in children))

        member = member_user.account_link.member
        self.assertIsNone(member_user.account_link.parent)
        self.assertEqual(member.email, member_user.email)
        self.assertEqual(member.departments.get().code, "mitte")
        from portal.policy import member_portal_allowed

        self.assertTrue(member_portal_allowed(member))  # Mitte allows member accounts from 14
        self.assertFalse(Parent.objects.filter(children=member, account_link__isnull=False).exists())
        self.assertIn("eltern@demo.example.invalid", self.output.getvalue())

    def test_portal_accounts_only_reach_the_allowlist(self):
        self.client.force_login(get_user_model().objects.get(username="eltern@demo.example.invalid"))
        self.assertEqual(self.client.get("/api/v1/users/me/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/members/").status_code, 403)
