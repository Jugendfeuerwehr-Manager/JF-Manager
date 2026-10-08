"""PORTAL-01.3: invitation by staff, acceptance via password page."""

import re
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from departments.models import Department, UserDepartmentRole
from departments.role_catalog import ROLE_SPECS
from members.models import Member, Parent
from portal.invitations import hash_token
from portal.models import AccountLink, Invitation

User = get_user_model()
STRONG = "Feuerwehr-Zugang-2026!"


def token_from_mail(message):
    return re.search(r"passwort-festlegen\?token=([\w-]+)", message.body).group(1)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class InvitationTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mitte = Department.objects.create(name="Mitte")
        cls.nord = Department.objects.create(name="Nord")
        cls.inviters = Group.objects.create(name="Einladende")
        cls.inviters.permissions.add(Permission.objects.get(codename="invite_portal_account"))
        cls.staff = cls.staff_in(cls.mitte, "leitung.mitte")
        cls.child = Member.objects.create(name="Mia", lastname="Beispiel")
        cls.child.departments.add(cls.mitte)
        cls.parent = Parent.objects.create(name="Eva", lastname="Beispiel", email="eva@example.invalid")
        cls.parent.children.add(cls.child)

    @classmethod
    def staff_in(cls, department, username):
        user = User.objects.create_user(username, password="x")
        role = UserDepartmentRole.objects.create(user=user, department=department)
        role.groups.add(cls.inviters)
        return user

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(self.staff)

    def invite_parent(self, parent=None):
        return self.client.post("/api/v1/portal/invitations/", {"parent": (parent or self.parent).pk}, format="json")


class InviteTests(InvitationTestBase):
    def test_invite_parent_sends_one_time_link(self):
        response = self.invite_parent()
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["state"], "open")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["eva@example.invalid"])
        self.assertIn("Mia", message.body)
        token = token_from_mail(message)
        invitation = Invitation.objects.get()
        self.assertEqual(invitation.token_hash, hash_token(token))
        self.assertNotIn(token, str(Invitation.objects.values().get()))
        self.assertAlmostEqual(invitation.expires_at, timezone.now() + timedelta(days=7), delta=timedelta(minutes=1))

    def test_names_in_the_mail_are_escaped(self):
        self.parent.name = '<script>alert("x")</script>'
        self.parent.save()
        self.invite_parent()
        self.assertNotIn("<script>", mail.outbox[0].alternatives[0][0])

    def test_other_department_and_missing_right_look_like_missing_records(self):
        for user in (self.staff_in(self.nord, "leitung.nord"), User.objects.create_user("ohne", password="x")):
            with self.subTest(user=user.username):
                self.client.force_authenticate(user)
                self.assertEqual(self.invite_parent().status_code, 404)
        self.assertFalse(Invitation.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_portal_accounts_cannot_invite(self):
        portal = User.objects.create_user("p@example.invalid", password="x", account_kind="portal")
        client = APIClient()
        client.force_login(portal)
        self.assertEqual(client.post("/api/v1/portal/invitations/", {"parent": self.parent.pk}).status_code, 403)

    def test_refusals(self):
        no_mail = Parent.objects.create(name="Ohne", lastname="Mail")
        no_mail.children.add(self.child)
        cases = [
            (no_mail, 400, "email_missing"),
        ]
        User.objects.create_user("vorhanden", email="taken@example.invalid", password="x")
        taken = Parent.objects.create(name="Tom", lastname="X", email="TAKEN@example.invalid")
        taken.children.add(self.child)
        cases.append((taken, 409, "account_exists"))
        linked = Parent.objects.create(name="Lin", lastname="K", email="lin@example.invalid")
        linked.children.add(self.child)
        AccountLink.objects.create(
            user=User.objects.create_user("lin", password="x", account_kind="portal"), parent=linked
        )
        cases.append((linked, 409, "already_linked"))
        for parent, status, code in cases:
            with self.subTest(code=code):
                response = self.invite_parent(parent)
                self.assertEqual((response.status_code, response.json()["code"]), (status, code))
        self.assertEqual(mail.outbox, [])

    def test_member_invitation_follows_the_member_portal_switch(self):
        self.child.email = "mia@example.invalid"
        self.child.save()
        response = self.client.post("/api/v1/portal/invitations/", {"member": self.child.pk}, format="json")
        self.assertEqual((response.status_code, response.json()["code"]), (422, "member_portal_disabled"))
        with mock.patch("portal.invitations.member_portal_allowed", return_value=True):
            response = self.client.post("/api/v1/portal/invitations/", {"member": self.child.pk}, format="json")
        self.assertEqual(response.status_code, 201)

    def test_mail_failure_leaves_no_open_invitation(self):
        with mock.patch("portal.invitations.send_mail", side_effect=ImproperlyConfigured("kein SMTP")):
            response = self.invite_parent()
        self.assertEqual((response.status_code, response.json()["code"]), (503, "mail_failed"))
        self.assertFalse(Invitation.objects.exists())
        with mock.patch("portal.invitations.send_mail", side_effect=OSError("down")):
            bulk = self.client.post("/api/v1/portal/invitations/bulk/", {"parents": [self.parent.pk]}, format="json")
        self.assertEqual(
            bulk.json()["results"],
            [{"parent": self.parent.pk, "result": "skipped", "code": "mail_failed", "detail": mock.ANY}],
        )
        self.assertEqual(self.invite_parent().status_code, 201)

    def test_one_open_invitation_resend_and_revoke(self):
        first = self.invite_parent().json()
        self.assertEqual(self.invite_parent().json()["code"], "invitation_open")
        old_token = token_from_mail(mail.outbox[0])
        resent = self.client.post(f"/api/v1/portal/invitations/{first['id']}/resend/")
        self.assertEqual(resent.status_code, 200)
        new_token = token_from_mail(mail.outbox[1])
        self.assertNotEqual(old_token, new_token)
        anonymous = APIClient()
        self.assertEqual(anonymous.get(f"/api/v1/portal/invitations/accept/?token={old_token}").status_code, 404)
        self.assertEqual(anonymous.get(f"/api/v1/portal/invitations/accept/?token={new_token}").status_code, 200)
        revoked = self.client.post(f"/api/v1/portal/invitations/{first['id']}/revoke/")
        self.assertEqual(revoked.json()["state"], "revoked")
        self.assertEqual(anonymous.get(f"/api/v1/portal/invitations/accept/?token={new_token}").status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/portal/invitations/{first['id']}/revoke/").status_code, 409)
        self.assertEqual(self.invite_parent().status_code, 201)  # a revoked invitation frees the record

    def test_list_is_scoped_to_the_inviting_departments(self):
        self.invite_parent()
        self.assertEqual(len(self.client.get("/api/v1/portal/invitations/").json()["results"]), 1)
        self.client.force_authenticate(self.staff_in(self.nord, "leitung.nord"))
        self.assertEqual(self.client.get("/api/v1/portal/invitations/").json()["results"], [])

    def test_leadership_templates_carry_the_invite_right(self):
        specs = {spec.key: spec for spec in ROLE_SPECS}
        for key in ("youth_director", "department_youth_director"):
            self.assertIn("portal.invite_portal_account", specs[key].permissions)
        self.assertNotIn("portal.invite_portal_account", specs["youth_leader"].permissions)


class AcceptTests(InvitationTestBase):
    def setUp(self):
        super().setUp()
        self.invite_parent()
        self.token = token_from_mail(mail.outbox[0])
        self.anonymous = APIClient()

    def accept(self, **overrides):
        data = {"token": self.token, "password": STRONG, "password_confirm": STRONG, "privacy_accepted": True}
        return self.anonymous.post("/api/v1/portal/invitations/accept/", {**data, **overrides}, format="json")

    def test_info_shows_only_the_invited_address(self):
        data = self.anonymous.get(f"/api/v1/portal/invitations/accept/?token={self.token}").json()
        self.assertEqual(data["email"], "eva@example.invalid")
        self.assertEqual(data["kind"], "parent")
        self.assertNotIn("Mia", str(data))

    def test_accept_creates_a_linked_portal_account_that_can_log_in(self):
        response = self.accept()
        self.assertEqual(response.status_code, 201, response.content)
        user = User.objects.get(username="eva@example.invalid")
        self.assertTrue(user.is_portal_account)
        self.assertTrue(user.dsgvo_external)
        self.assertEqual((user.first_name, user.last_name), ("Eva", "Beispiel"))
        link = user.account_link
        self.assertEqual((link.parent, link.status, link.linked_by), (self.parent, "confirmed", self.staff))
        self.assertEqual(Invitation.objects.get().accepted_user, user)
        browser = self.client_class()
        login = browser.post(
            "/api/v1/auth/session/login/",
            {"username": "eva@example.invalid", "password": STRONG},
            content_type="application/json",
        )
        self.assertEqual(login.json().get("account_kind"), "portal")
        self.assertEqual(browser.get("/api/v1/portal/me/").json()["people"][0]["first_name"], "Mia")

    def test_link_works_only_once(self):
        self.assertEqual(self.accept().status_code, 201)
        self.assertEqual(self.accept().json()["code"], "invalid")

    def test_expired_link(self):
        Invitation.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.accept()
        self.assertEqual((response.status_code, response.json()["code"]), (410, "expired"))
        self.assertFalse(User.objects.filter(username="eva@example.invalid").exists())

    def test_unknown_token(self):
        self.assertEqual(self.accept(token="x" * 43).status_code, 404)

    def test_validation(self):
        for overrides, field in [
            ({"password": "kurz", "password_confirm": "kurz"}, "password"),
            ({"password_confirm": STRONG + "x"}, "password_confirm"),
            ({"privacy_accepted": False}, "privacy_accepted"),
        ]:
            with self.subTest(field=field):
                response = self.accept(**overrides)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        self.assertFalse(User.objects.filter(username="eva@example.invalid").exists())
        self.assertEqual(Invitation.objects.get().state, "open")

    def test_account_created_meanwhile_is_never_taken_over(self):
        User.objects.create_user("eva", email="eva@example.invalid", password="x")
        self.assertEqual(self.accept().json()["code"], "account_exists")
        self.assertFalse(AccountLink.objects.exists())

    def test_csrf_is_enforced(self):
        strict = APIClient(enforce_csrf_checks=True)
        response = strict.post(
            "/api/v1/portal/invitations/accept/",
            {"token": self.token, "password": STRONG, "password_confirm": STRONG, "privacy_accepted": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_rate_limit(self):
        codes = [self.accept(token=f"falsch{i}").status_code for i in range(6)]
        self.assertEqual(codes[-1], 429)
