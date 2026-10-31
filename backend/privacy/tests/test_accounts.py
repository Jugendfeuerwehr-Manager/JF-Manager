"""DSGVO: portal accounts without records end, ended and deactivated accounts are cleaned up. Fictional data."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from members.models import Member, Parent
from portal.lifecycle import daily
from portal.models import AccountLink
from privacy.models import ConsentRecord
from privacy.services.retention import purge_personal_data

User = get_user_model()


def portal_account(username, **record):
    user = User.objects.create_user(username, password="x", account_kind=User.AccountKind.PORTAL)
    AccountLink.objects.create(user=user, status=AccountLink.Status.CONFIRMED, **record)
    return user


class PortalAccountEndTests(TestCase):
    def setUp(self):
        self.child = Member.objects.create(name="Mia", lastname="Muster", birthday=date(2015, 1, 1))
        self.parent = Parent.objects.create(name="Eva", lastname="Muster")
        self.parent.children.add(self.child)
        self.user = portal_account("eva@example.invalid", parent=self.parent)

    def test_deleting_the_record_ends_the_account(self):
        self.parent.delete()
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_parent_without_children_is_ended_by_the_daily_job(self):
        self.parent.children.clear()
        result = daily()
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIn(self.user.pk, result["ended_accounts"])

    def test_parent_with_a_minor_child_stays(self):
        daily()
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)


class AccountRetentionTests(TestCase):
    def age(self, user, days):
        User.objects.filter(pk=user.pk).update(last_login=timezone.now() - timedelta(days=days))

    def test_ended_portal_accounts_are_deleted_after_the_period(self):
        old = User.objects.create_user("alt@example.invalid", account_kind=User.AccountKind.PORTAL, is_active=False)
        ConsentRecord.objects.create(user=old, kind="privacy_notice_ack", status="granted", source="self")
        recent = User.objects.create_user("neu@example.invalid", account_kind=User.AccountKind.PORTAL, is_active=False)
        active = User.objects.create_user("aktiv@example.invalid", account_kind=User.AccountKind.PORTAL)
        for user in (old, active):
            self.age(user, 200)
        self.age(recent, 10)
        results = {result.name: result.count for result in purge_personal_data()}
        self.assertEqual(results["portal_account_delete_days"], 1)
        self.assertFalse(User.objects.filter(pk=old.pk).exists())
        self.assertEqual(User.objects.filter(pk__in=[recent.pk, active.pk]).count(), 2)
        self.assertFalse(ConsentRecord.objects.filter(user_id=old.pk).exists())

    def test_deactivated_staff_keeps_only_the_name(self):
        staff = User.objects.create_user(
            "ehemalig",
            first_name="Max",
            last_name="Muster",
            email="max@example.invalid",
            street="Musterweg 1",
            city="Musterstadt",
            email_signature="<p>Max</p>",
            is_active=False,
        )
        active = User.objects.create_user("aktiv", email="aktiv@example.invalid")
        self.age(staff, 400)
        self.age(active, 400)
        purge_personal_data()
        staff.refresh_from_db()
        self.assertEqual((staff.first_name, staff.last_name), ("Max", "Muster"))
        self.assertEqual((staff.email, staff.street, staff.city, staff.email_signature), ("", "", "", ""))
        active.refresh_from_db()
        self.assertEqual(active.email, "aktiv@example.invalid")
        results = {result.name: result.count for result in purge_personal_data()}
        self.assertEqual(results["staff_account_anonymize_days"], 0)  # idempotent
