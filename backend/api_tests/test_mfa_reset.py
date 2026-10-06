"""MFA reset: console command (SEC-11.3) and administrators in the UI (SEC-11.4)."""

from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
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
