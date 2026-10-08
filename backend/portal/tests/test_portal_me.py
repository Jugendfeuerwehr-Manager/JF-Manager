from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from members.models import Member, Parent
from portal.models import AccountLink
from portal.people import eighteen_years_before

User = get_user_model()


def years_ago(years, days=0):
    today = timezone.localdate()
    return date(today.year - years, today.month, min(today.day, 28)) - timedelta(days=days)


class PortalMeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            "eltern@example.invalid", email="eltern@example.invalid", password="x", account_kind="portal"
        )
        cls.parent = Parent.objects.create(name="Eva", lastname="Beispiel")
        cls.minor = Member.objects.create(name="Mia", lastname="Beispiel", birthday=years_ago(12))
        cls.adult = Member.objects.create(name="Tom", lastname="Beispiel", birthday=years_ago(18, days=1))
        cls.unknown = Member.objects.create(name="Ole", lastname="Beispiel")
        cls.other = Member.objects.create(name="Fremd", lastname="Kind", birthday=years_ago(10))
        cls.parent.children.add(cls.minor, cls.adult, cls.unknown)
        cls.link = AccountLink.objects.create(user=cls.user, parent=cls.parent, status=AccountLink.Status.CONFIRMED)

    def setUp(self):
        self.client.force_login(self.user)

    def test_lists_minor_children_only(self):
        data = self.client.get("/api/v1/portal/me/").json()
        self.assertEqual(data["account"]["email"], "eltern@example.invalid")
        self.assertEqual(
            [(p["first_name"], p["relation"]) for p in data["people"]], [("Mia", "child"), ("Ole", "child")]
        )
        self.assertEqual(set(data["people"][0]), {"id", "relation", "first_name", "last_name", "age"})
        self.assertEqual(data["people"][0]["age"], 12)
        self.assertNotIn("age", data["people"][1])  # no birthday recorded

    def test_member_link_lists_self(self):
        AccountLink.objects.filter(pk=self.link.pk).update(parent=None, member=self.adult)
        data = self.client.get("/api/v1/portal/me/").json()
        self.assertEqual(
            data["people"],
            [{"id": self.adult.pk, "relation": "self", "first_name": "Tom", "last_name": "Beispiel", "age": 18}],
        )

    def test_pending_link_has_no_effect(self):
        AccountLink.objects.filter(pk=self.link.pk).update(status=AccountLink.Status.PENDING)
        self.assertEqual(self.client.get("/api/v1/portal/me/").json()["people"], [])

    def test_staff_accounts_are_refused(self):
        self.client.force_login(User.objects.create_superuser("admin", password="x"))
        self.assertEqual(self.client.get("/api/v1/portal/me/").status_code, 403)

    def test_eighteenth_birthday_on_29_february(self):
        self.assertEqual(eighteen_years_before(date(2026, 2, 28)), date(2008, 2, 28))
        self.assertEqual(eighteen_years_before(date(2028, 2, 29)), date(2010, 3, 1))


class PortalSessionAndProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("mitglied@example.invalid", password="x", account_kind="portal")

    def setUp(self):
        self.client.force_login(self.user)

    def test_session_reports_account_kind(self):
        self.assertEqual(self.client.get("/api/v1/auth/session/").json()["account_kind"], "portal")
        self.assertEqual(self.client.get("/api/v1/users/me/").json()["account_kind"], "portal")
        self.client.logout()
        self.assertNotIn("account_kind", self.client.get("/api/v1/auth/session/").json())

    def test_portal_profile_only_changes_the_theme(self):
        ok = self.client.patch("/api/v1/users/me/", {"theme_mode": "dark"}, content_type="application/json")
        self.assertEqual(ok.status_code, 200)
        for field, value in [
            ("city", "Musterstadt"),
            ("email_signature", "<p>x</p>"),
            ("dsgvo_internal", True),
            ("first_name", "X"),
            ("account_kind", "staff"),
        ]:
            with self.subTest(field=field):
                response = self.client.patch("/api/v1/users/me/", {field: value}, content_type="application/json")
                self.user.refresh_from_db()
                self.assertEqual(self.user.account_kind, "portal")
                if field != "account_kind":  # read-only fields are silently ignored by DRF
                    self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual((self.user.city, self.user.theme_mode, self.user.first_name), ("", "dark", ""))

    def test_staff_profile_unchanged(self):
        staff = User.objects.create_user("betreuer", password="x")
        self.client.force_login(staff)
        response = self.client.patch("/api/v1/users/me/", {"first_name": "Jan"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/auth/session/").json()["account_kind"], "staff")
