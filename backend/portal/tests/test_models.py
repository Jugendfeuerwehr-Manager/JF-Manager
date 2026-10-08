from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from members.models import Member, Parent
from portal.models import AccountLink

User = get_user_model()


class AccountKindTests(TestCase):
    def test_existing_and_new_accounts_are_staff_by_default(self):
        user = User.objects.create_user("betreuer", password="x")
        self.assertEqual(user.account_kind, User.AccountKind.STAFF)
        self.assertFalse(user.is_portal_account)

    def test_portal_account_is_plain_local_account(self):
        user = User.objects.create_user("eltern", password="x", account_kind=User.AccountKind.PORTAL)
        self.assertTrue(user.is_portal_account)
        for field, value in [
            ("is_staff", True),
            ("is_superuser", True),
            ("auth_source", "ldap"),
            ("auth_source", "oidc"),
        ]:
            with self.subTest(field=field, value=value), transaction.atomic(), self.assertRaises(IntegrityError):
                User.objects.filter(pk=user.pk).update(**{field: value})

    def test_staff_account_may_still_be_superuser(self):
        user = User.objects.create_superuser("admin", password="x")
        self.assertEqual(user.account_kind, User.AccountKind.STAFF)


class AccountLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("eltern", password="x", account_kind=User.AccountKind.PORTAL)
        self.child = Member.objects.create(name="Mia", lastname="Beispiel")
        self.parent = Parent.objects.create(name="Eva", lastname="Beispiel")
        self.parent.children.add(self.child)

    def test_link_needs_a_target(self):
        with self.assertRaises(IntegrityError):
            AccountLink.objects.create(user=self.user)

    def test_new_link_is_pending_and_without_effect(self):
        link = AccountLink.objects.create(user=self.user, parent=self.parent)
        self.assertEqual(link.status, AccountLink.Status.PENDING)
        self.assertFalse(link.is_effective)
        link.status = AccountLink.Status.CONFIRMED
        self.assertTrue(link.is_effective)

    def test_one_link_per_account_parent_and_member(self):
        AccountLink.objects.create(user=self.user, parent=self.parent, member=self.child)
        other = User.objects.create_user("zweites", password="x", account_kind=User.AccountKind.PORTAL)
        for kwargs in [
            {"user": self.user, "parent": Parent.objects.create(name="X")},
            {"user": other, "parent": self.parent},
            {"user": other, "member": self.child},
        ]:
            with self.subTest(kwargs=sorted(kwargs)), transaction.atomic(), self.assertRaises(IntegrityError):
                AccountLink.objects.create(**kwargs)

    def test_deleting_the_only_target_removes_the_link(self):
        AccountLink.objects.create(user=self.user, parent=self.parent)
        self.parent.delete()
        self.assertFalse(AccountLink.objects.exists())
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_deleting_one_target_keeps_the_other(self):
        member = Member.objects.create(name="Eva", lastname="Beispiel")
        link = AccountLink.objects.create(user=self.user, parent=self.parent, member=member)
        self.parent.delete()
        link.refresh_from_db()
        self.assertIsNone(link.parent)
        self.assertEqual(link.member, member)
        member.delete()
        self.assertFalse(AccountLink.objects.exists())

    def test_deleting_the_account_removes_the_link_but_keeps_records(self):
        AccountLink.objects.create(user=self.user, parent=self.parent)
        self.user.delete()
        self.assertFalse(AccountLink.objects.exists())
        self.assertTrue(Parent.objects.filter(pk=self.parent.pk).exists())
