"""PORTAL-01.4 lifecycle and the portal administration API (PORTAL-01.6 backend)."""

from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from members.models import Member, Parent
from portal.lifecycle import child_access, daily, eighteenth_birthday
from portal.models import AccountLink, Invitation, ParentAccessExtension
from portal.people import visible_children
from users.models import UserSession

User = get_user_model()


def born_years_ago(years, days=0):
    today = timezone.localdate()
    return date(today.year - years, today.month, min(today.day, 28)) - timedelta(days=days)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AdminTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        cls.nord = Department.objects.create(name="Nord")
        cls.managers = Group.objects.create(name="Portalverwaltung")
        cls.managers.permissions.add(Permission.objects.get(codename="invite_portal_account"))
        cls.staff = cls.staff_in(cls.mitte, "leitung.mitte")
        cls.child = Member.objects.create(name="Mia", lastname="Beispiel", birthday=born_years_ago(12))
        cls.child.departments.add(cls.mitte)
        cls.parent = Parent.objects.create(name="Eva", lastname="Beispiel", email="eva@example.invalid")
        cls.parent.children.add(cls.child)
        cls.account = User.objects.create_user("eva@example.invalid", password="x", account_kind="portal")
        cls.link = AccountLink.objects.create(user=cls.account, parent=cls.parent, status="confirmed")

    @classmethod
    def staff_in(cls, department, username):
        user = User.objects.create_user(username, password="x")
        UserDepartmentRole.objects.create(user=user, department=department).groups.add(cls.managers)
        return user

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.staff)

    def portal_session(self):
        browser = self.client_class()
        browser.force_login(self.account)
        return browser


class LifecycleApiTests(AdminTestBase):
    def act(self, name, **record):
        return self.client.post(f"/api/v1/portal/access/{name}/", record or {"parent": self.parent.pk}, format="json")

    def test_suspend_revokes_sessions_and_resume_restores_login(self):
        browser = self.portal_session()
        self.assertTrue(UserSession.objects.filter(user=self.account).exists())
        response = self.act("suspend")
        self.assertEqual(response.json()["state"], "suspended")
        self.account.refresh_from_db()
        self.assertFalse(self.account.is_active)
        self.assertFalse(UserSession.objects.filter(user=self.account).exists())
        self.assertIn(browser.get("/api/v1/portal/me/").status_code, {401, 403})
        self.assertEqual(self.act("resume").json()["state"], "active")

    def test_end_detaches_record_and_deactivates_empty_account(self):
        response = self.act("end")
        self.assertEqual(response.json()["state"], "none")
        self.account.refresh_from_db()
        self.assertFalse(self.account.is_active)
        self.assertFalse(AccountLink.objects.exists())
        self.assertTrue(User.objects.filter(pk=self.account.pk).exists())  # deactivated, not deleted

    def test_end_keeps_the_other_record(self):
        own = Member.objects.create(name="Eva", lastname="Beispiel", birthday=born_years_ago(40))
        own.departments.add(self.mitte)
        AccountLink.objects.filter(pk=self.link.pk).update(member=own)
        self.act("end")
        self.account.refresh_from_db()
        self.assertTrue(self.account.is_active)
        link = AccountLink.objects.get()
        self.assertEqual((link.parent, link.member), (None, own))

    def test_scope_and_errors(self):
        self.client.force_authenticate(self.staff_in(self.nord, "leitung.nord"))
        self.assertEqual(self.act("suspend").status_code, 404)
        self.client.force_authenticate(self.staff)
        other = Parent.objects.create(name="Ohne", lastname="Zugang")
        other.children.add(self.child)
        self.assertEqual(self.act("suspend", parent=other.pk).json()["code"], "no_access")
        self.assertEqual(self.client.post("/api/v1/portal/access/delete/", {"parent": 1}).status_code, 404)

    def test_portal_accounts_cannot_use_the_admin_api(self):
        self.assertEqual(self.portal_session().get(f"/api/v1/portal/access/?parent={self.parent.pk}").status_code, 403)


class AdminOverviewTests(AdminTestBase):
    def test_records_with_states_and_filters(self):
        invited = Parent.objects.create(name="Ina", lastname="Eingeladen", email="ina@example.invalid")
        invited.children.add(self.child)
        self.client.post("/api/v1/portal/invitations/", {"parent": invited.pk}, format="json")
        expired = Parent.objects.create(name="Alt", lastname="Abgelaufen", email="alt@example.invalid")
        expired.children.add(self.child)
        self.client.post("/api/v1/portal/invitations/", {"parent": expired.pk}, format="json")
        Invitation.objects.filter(parent=expired).update(expires_at=timezone.now() - timedelta(days=1))
        none = Parent.objects.create(name="Kein", lastname="Zugang")
        none.children.add(self.child)
        rows = self.client.get("/api/v1/portal/access/records/?kind=parent").json()["results"]
        states = {row["name"]: row["state"] for row in rows}
        self.assertEqual(
            states,
            {"Eva Beispiel": "active", "Ina Eingeladen": "invited", "Alt Abgelaufen": "expired", "Kein Zugang": "none"},
        )
        filtered = self.client.get("/api/v1/portal/access/records/?kind=parent&state=expired").json()
        self.assertEqual([row["name"] for row in filtered["results"]], ["Alt Abgelaufen"])
        searched = self.client.get("/api/v1/portal/access/records/?kind=parent&search=ina@").json()["results"]
        self.assertEqual([row["name"] for row in searched], ["Ina Eingeladen"])

    def test_records_are_scoped(self):
        self.client.force_authenticate(self.staff_in(self.nord, "leitung.nord"))
        self.assertEqual(self.client.get("/api/v1/portal/access/records/").json()["results"], [])

    def test_access_detail(self):
        data = self.client.get(f"/api/v1/portal/access/?parent={self.parent.pk}").json()
        self.assertEqual(data["state"], "active")
        self.assertEqual(data["account"]["username"], "eva@example.invalid")
        self.assertEqual(data["children"][0]["name"], "Mia Beispiel")
        self.assertNotIn("notes", str(data))

    def test_bulk_invite_reports_each_parent(self):
        ok = Parent.objects.create(name="Neu", lastname="Eins", email="neu@example.invalid")
        ok.children.add(self.child)
        outside = Parent.objects.create(name="Fremd", lastname="Nord", email="fremd@example.invalid")
        nord_child = Member.objects.create(name="Nils", lastname="Nord")
        nord_child.departments.add(self.nord)
        outside.children.add(nord_child)
        response = self.client.post(
            "/api/v1/portal/invitations/bulk/", {"parents": [ok.pk, self.parent.pk, outside.pk, ok.pk]}, format="json"
        )
        results = {row["parent"]: (row["result"], row.get("code")) for row in response.json()["results"]}
        self.assertEqual(
            results,
            {
                ok.pk: ("sent", None),
                self.parent.pk: ("skipped", "already_linked"),
                outside.pk: ("skipped", "not_found"),
            },
        )


class ParentAccessEndTests(AdminTestBase):
    def test_child_disappears_on_18th_birthday_unless_extended(self):
        adult = Member.objects.create(name="Tom", lastname="Beispiel", birthday=born_years_ago(18))
        adult.departments.add(self.mitte)
        self.parent.children.add(adult)
        today = timezone.localdate()
        self.assertNotIn(adult, visible_children(self.parent, today))
        self.assertIn(adult, visible_children(self.parent, eighteenth_birthday(adult) - timedelta(days=1)))
        response = self.client.post(
            "/api/v1/portal/access/extensions/",
            {
                "parent": self.parent.pk,
                "member": adult.pk,
                "until": str(today + timedelta(days=60)),
                "reason": "Ausbildung",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIn(adult, visible_children(self.parent, today))
        self.assertNotIn(adult, visible_children(self.parent, today + timedelta(days=61)))
        names = [p["first_name"] for p in self.portal_session().get("/api/v1/portal/me/").json()["people"]]
        self.assertEqual(names, ["Mia", "Tom"])

    def test_extension_limits(self):
        adult = Member.objects.create(name="Tom", lastname="Beispiel", birthday=born_years_ago(18))
        self.parent.children.add(adult)
        stranger = Member.objects.create(name="Fremd", lastname="Kind", birthday=born_years_ago(18))
        stranger.departments.add(self.mitte)
        base = {"parent": self.parent.pk, "member": adult.pk, "reason": "Ausbildung"}
        too_long = str(eighteenth_birthday(adult) + timedelta(days=400))
        cases = [
            ({"until": too_long}, "too_long"),
            ({"until": str(timezone.localdate() - timedelta(days=1))}, "in_past"),
        ]
        for overrides, code in cases:
            with self.subTest(code=code):
                response = self.client.post("/api/v1/portal/access/extensions/", {**base, **overrides}, format="json")
                self.assertEqual(response.json().get("code"), code, response.content)
        blank = self.client.post(
            "/api/v1/portal/access/extensions/",
            {**base, "until": str(timezone.localdate()), "reason": "  "},
            format="json",
        )
        self.assertIn("reason", blank.json())
        response = self.client.post(
            "/api/v1/portal/access/extensions/", {**base, "member": stranger.pk, "until": str(timezone.localdate())}
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ParentAccessExtension.objects.exists())

    def test_child_access_rows_and_ending_list(self):
        soon = Member.objects.create(name="Lea", lastname="Beispiel", birthday=born_years_ago(18, days=-10))
        soon.departments.add(self.mitte)
        self.parent.children.add(soon)
        rows = {row["name"]: row for row in child_access(self.parent)}
        self.assertTrue(rows["Lea Beispiel"]["ends_soon"])
        self.assertFalse(rows["Lea Beispiel"]["ended"])
        self.assertEqual(rows["Lea Beispiel"]["access_ends_on"], eighteenth_birthday(soon) - timedelta(days=1))
        ending = self.client.get("/api/v1/portal/access/ending/").json()
        self.assertEqual([row["name"] for row in ending], ["Lea Beispiel"])

    def test_daily_job_ends_accounts_without_visible_children(self):
        Member.objects.filter(pk=self.child.pk).update(birthday=born_years_ago(18, days=5))
        browser = self.portal_session()
        out = StringIO()
        call_command("portal_access_lifecycle", stdout=out)
        self.account.refresh_from_db()
        self.assertFalse(self.account.is_active)
        self.assertIn(browser.get("/api/v1/portal/me/").status_code, {401, 403})
        self.assertIn("Beendete Elternzugänge: 1", out.getvalue())
        self.assertEqual(daily()["ended_accounts"], [])  # idempotent

    def test_daily_job_keeps_parents_with_minors_or_member_link(self):
        result = daily()
        self.assertEqual(result["ended_accounts"], [])
        self.account.refresh_from_db()
        self.assertTrue(self.account.is_active)

    def test_leap_day_birthday(self):
        leap = Member.objects.create(name="Leo", lastname="Beispiel", birthday=date(2008, 2, 29))
        self.parent.children.add(leap)
        self.assertEqual(eighteenth_birthday(leap), date(2026, 3, 1))
        rows = {row["member"]: row for row in child_access(self.parent, date(2026, 2, 28))}
        self.assertFalse(rows[leap.pk]["ended"])
        rows = {row["member"]: row for row in child_access(self.parent, date(2026, 3, 1))}
        self.assertTrue(rows[leap.pk]["ended"])
