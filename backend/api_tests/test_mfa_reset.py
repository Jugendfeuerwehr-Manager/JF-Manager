"""MFA reset: console command (SEC-11.3) and administrators in the UI (SEC-11.4)."""

from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.management import CommandError, call_command
from rest_framework.test import APIClient, APITestCase

from users import mfa
from users.models import MFADevice, MFARecoveryCode, PasskeyCredential, UserSession

User = get_user_model()
PASSWORD = "Synthetic-Passw0rd!"
SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


def give_factors(user):
    MFADevice.objects.create(user=user, secret=SECRET, confirmed_at="2026-01-01T00:00:00Z")
    PasskeyCredential.objects.create(
        user=user, name="Laptop", credential_id=f"cred-{user.pk}".encode(), public_key=b"k"
    )
    mfa.issue_recovery_codes(user)


def signed_in(user):
    """A real session row with its device entry, as created by a login."""
    client = APIClient()
    client.force_login(user)
    key = client.cookies[settings.SESSION_COOKIE_NAME].value
    assert UserSession.objects.filter(session_id=key, user=user).exists()
    return key


class ConsoleResetTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser(username="chef", password=PASSWORD)
        give_factors(self.admin)
        self.session_key = signed_in(self.admin)

    def test_command_removes_all_factors_and_sessions_of_an_admin_account(self):
        out = StringIO()
        with self.assertLogs("security.mfa", level="WARNING") as logs:
            call_command("reset_mfa", "--user", "chef", stdout=out)
        self.assertIn("zurückgesetzt", out.getvalue())
        self.assertFalse(MFADevice.objects.filter(user=self.admin).exists())
        self.assertFalse(PasskeyCredential.objects.filter(user=self.admin).exists())
        self.assertFalse(MFARecoveryCode.objects.filter(user=self.admin).exists())
        self.assertFalse(Session.objects.filter(pk=self.session_key).exists())
        self.assertFalse(mfa.has_mfa(self.admin))
        self.assertIn(f"target={self.admin.pk}", logs.output[0])
        self.assertIn("channel=console", logs.output[0])
        self.assertNotIn("chef", logs.output[0])

    def test_unknown_user_is_an_error(self):
        with self.assertRaises(CommandError):
            call_command("reset_mfa", "--user", "nobody", stdout=StringIO())

    def test_other_accounts_are_untouched(self):
        other = User.objects.create_user(username="other", password=PASSWORD)
        give_factors(other)
        call_command("reset_mfa", "--user", "chef", stdout=StringIO())
        self.assertTrue(mfa.has_totp(other))
        self.assertTrue(mfa.has_passkeys(other))


class AdminUIResetTests(APITestCase):
    """Superusers reset MFA of ordinary accounts; administrative ones need the console."""

    def setUp(self):
        cache.clear()
        self.now = mfa.time.time()
        from unittest.mock import patch

        for target in ("users.mfa.time.time", "users.session_views.time.time", "users.session_policy.time.time"):
            patcher = patch(target, side_effect=lambda: self.now)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.admin = User.objects.create_superuser(username="chef", password=PASSWORD)
        MFADevice.objects.create(user=self.admin, secret=SECRET, confirmed_at="2026-01-01T00:00:00Z")
        self.member = User.objects.create_user(username="betreuer", password=PASSWORD)
        give_factors(self.member)
        self.member_session = signed_in(self.member)
        self.client = self.login(self.admin)

    def login(self, user):
        client = APIClient(enforce_csrf_checks=True)
        client.get("/api/v1/auth/session/")
        client.credentials(HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)
        client.post("/api/v1/auth/session/login/", {"username": user.username, "password": PASSWORD}, format="json")
        status = client.post(
            "/api/v1/auth/session/mfa/", {"code": mfa.totp_at(SECRET, mfa.current_step())}, format="json"
        )
        assert status.data["authenticated"], status.data
        client.credentials(HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)
        return client

    def url(self, user):
        return f"/api/v1/admin/users/{user.pk}/reset-mfa/"

    def test_list_and_detail_show_mfa_state(self):
        rows = {row["username"]: row for row in self.client.get("/api/v1/admin/users/").data["results"]}
        self.assertTrue(rows["betreuer"]["mfa_enabled"])
        self.assertTrue(rows["chef"]["mfa_enabled"])
        detail = self.client.get(f"/api/v1/admin/users/{self.member.pk}/").data["mfa"]
        self.assertEqual(
            detail, {"enabled": True, "totp": True, "passkeys": 1, "ui_reset_allowed": True, "reset_blocker": None}
        )
        own = self.client.get(f"/api/v1/admin/users/{self.admin.pk}/").data["mfa"]
        self.assertEqual(own["reset_blocker"], "self")

    def test_superuser_resets_ordinary_account(self):
        with self.assertLogs("security.mfa", level="WARNING") as logs:
            response = self.client.post(self.url(self.member))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.data["mfa"]["enabled"])
        self.assertEqual(response.data["removed"]["passkeys"], 1)
        self.assertFalse(mfa.has_mfa(self.member))
        self.assertFalse(Session.objects.filter(pk=self.member_session).exists())
        self.assertIn(f"actor={self.admin.pk}", logs.output[0])
        self.assertIn("channel=admin-ui", logs.output[0])

    def test_administrative_accounts_are_console_only(self):
        other_admin = User.objects.create_user(username="zweiter", password=PASSWORD, is_staff=True)
        give_factors(other_admin)
        leader = User.objects.create_user(username="leitung", password=PASSWORD)
        leader.user_permissions.add(Permission.objects.get(codename="change_customuser"))
        give_factors(leader)
        for target in (other_admin, leader):
            response = self.client.post(self.url(target))
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["code"], "mfa_reset_console_only")
            self.assertIn("jfctl admin reset-mfa", response.json()["detail"])
            self.assertTrue(mfa.has_mfa(target))

    def test_own_account_is_managed_in_the_profile(self):
        response = self.client.post(self.url(self.admin))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "mfa_reset_self")
        self.assertTrue(mfa.has_mfa(self.admin))

    def test_reset_needs_step_up(self):
        self.now += 301
        response = self.client.post(self.url(self.member))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "reauthentication_required")
        self.assertTrue(mfa.has_mfa(self.member))

    def test_staff_without_superuser_cannot_reset(self):
        staff = User.objects.create_user(username="leser", password=PASSWORD, is_staff=True)
        MFADevice.objects.create(user=staff, secret=SECRET, confirmed_at="2026-01-01T00:00:00Z")
        self.now += 60  # next TOTP step for the second login
        client = self.login(staff)
        self.assertEqual(client.post(self.url(self.member)).status_code, 403)
        self.assertTrue(mfa.has_mfa(self.member))
