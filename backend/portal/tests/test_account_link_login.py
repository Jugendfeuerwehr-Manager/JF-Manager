"""PORTAL-04.2: the login answers with the pending link (password + MFA, passkey), then confirm/reject."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from api_tests.test_passkeys import ORIGIN, PasskeyTestCase, csrf_client, login, refresh_csrf
from members.models import Member, Parent
from portal.models import AccountLink
from users import mfa
from users.models import MFADevice

User = get_user_model()
PASSWORD = "Synthetic-Passw0rd!"
SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


class PasswordAndMfaLoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser("admin", password=PASSWORD)
        self.user = User.objects.create_user(username="leitung", password=PASSWORD)
        MFADevice.objects.create(user=self.user, secret=SECRET, confirmed_at="2026-01-01T00:00:00Z")
        self.member = Member.objects.create(name="Tobias", lastname="Lehmann")
        self.link = AccountLink.objects.create(user=self.user, member=self.member, linked_by=self.admin)
        self.client = csrf_client()

    def sign_in(self):
        response = self.client.post(
            "/api/v1/auth/session/login/", {"username": "leitung", "password": PASSWORD}, format="json"
        )
        self.assertTrue(response.data["mfa_required"])
        # The pending link is not revealed before the second factor.
        self.assertNotIn("account_link_pending", response.data)
        code = mfa.totp_at(SECRET, mfa.current_step())
        response = self.client.post("/api/v1/auth/session/mfa/", {"code": code}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        refresh_csrf(self.client)
        return response.data

    def test_pending_link_stops_at_the_confirmation_step(self):
        status = self.sign_in()
        self.assertTrue(status["authenticated"])
        self.assertTrue(status["account_link_pending"])
        self.assertEqual(status["linked_person"], {"member": False, "children": False})
        pending = self.client.get("/api/v1/portal/account-links/pending-for-me/").data["link"]
        self.assertEqual(pending["id"], self.link.pk)
        response = self.client.post(f"/api/v1/portal/account-links/{self.link.pk}/confirm/")
        self.assertEqual(response.status_code, 200, response.content)
        status = self.client.get("/api/v1/auth/session/").data
        self.assertFalse(status["account_link_pending"])
        self.assertEqual(status["linked_person"], {"member": True, "children": False})

    def test_rejecting_ends_the_step_without_effect(self):
        self.sign_in()
        self.assertEqual(self.client.post(f"/api/v1/portal/account-links/{self.link.pk}/reject/").status_code, 200)
        status = self.client.get("/api/v1/auth/session/").data
        self.assertFalse(status["account_link_pending"])
        self.assertFalse(status["linked_person"]["member"])

    def test_confirm_needs_csrf(self):
        self.sign_in()
        self.client.credentials()
        response = self.client.post(f"/api/v1/portal/account-links/{self.link.pk}/confirm/")
        self.assertEqual(response.status_code, 403)
        self.link.refresh_from_db()
        self.assertEqual(self.link.status, "pending")

    def test_children_flag_needs_a_confirmed_parent_link_with_minor_children(self):
        parent = Parent.objects.create(name="Tobias", lastname="Lehmann")
        parent.children.add(Member.objects.create(name="Ella", lastname="Lehmann"))
        self.link.parent = parent
        self.link.status = "confirmed"
        self.link.save()
        status = self.sign_in()
        self.assertEqual(status["linked_person"], {"member": True, "children": True})
        self.assertFalse(status["account_link_pending"])

    def test_portal_accounts_get_no_link_flags(self):
        portal = User.objects.create_user("p@example.invalid", password=PASSWORD, account_kind="portal")
        AccountLink.objects.create(user=portal, member=Member.objects.create(name="P"), status="confirmed")
        client = csrf_client()
        status = client.post(
            "/api/v1/auth/session/login/", {"username": "p@example.invalid", "password": PASSWORD}, format="json"
        ).data
        self.assertEqual(status["account_kind"], "portal")
        self.assertNotIn("account_link_pending", status)


@override_settings(FRONTEND_URL=ORIGIN, WEBAUTHN_RP_ID="", WEBAUTHN_ORIGINS=[])
class PasskeyLoginTests(PasskeyTestCase):
    def setUp(self):
        super().setUp()
        setup_client = csrf_client()
        login(setup_client, "passkey-user")
        self.assertEqual(self.register(client=setup_client).status_code, 200)
        AccountLink.objects.create(user=self.user, member=Member.objects.create(name="Pia", lastname="Passkey"))
        self.client = csrf_client()

    def test_passkey_sign_in_reports_the_pending_link(self):
        options = self.client.post("/api/v1/auth/session/passkey/options/").json()
        assertion = self.authenticator.get(options, user_handle=f"jf-user-{self.user.pk}".encode())
        response = self.client.post("/api/v1/auth/session/passkey/", {"passkey": assertion}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data["account_link_pending"])
