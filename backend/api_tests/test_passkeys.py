"""Passkeys as second factor (SEC-11.1/11.2) with a software authenticator."""

from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from api_tests.webauthn_soft import SoftAuthenticator
from users import mfa
from users.models import MFADevice, MFARecoveryCode, PasskeyCredential

User = get_user_model()
PASSWORD = "Synthetic-Passw0rd!"
SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
ORIGIN = "https://jf.example.org"


def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/v1/auth/session/")
    client.credentials(HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)
    return client


def refresh_csrf(client):
    client.credentials(HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)


def login(client, username):
    response = client.post("/api/v1/auth/session/login/", {"username": username, "password": PASSWORD}, format="json")
    refresh_csrf(client)
    return response


@override_settings(FRONTEND_URL=ORIGIN, WEBAUTHN_RP_ID="", WEBAUTHN_ORIGINS=[])
class PasskeyTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="passkey-user", password=PASSWORD)
        self.authenticator = SoftAuthenticator(origin=ORIGIN, rp_id="jf.example.org")
        self.client = csrf_client()

    def register(self, client=None, authenticator=None, name="Laptop"):
        client = client or self.client
        authenticator = authenticator or self.authenticator
        options = client.post("/api/v1/auth/mfa/passkeys/register/begin/").json()
        return client.post(
            "/api/v1/auth/mfa/passkeys/register/finish/",
            {"credential": authenticator.create(options), "name": name},
            format="json",
        )


class PasskeyRegistrationTests(PasskeyTestCase):
    def setUp(self):
        super().setUp()
        self.assertEqual(login(self.client, "passkey-user").status_code, 200)

    def test_options_use_frontend_origin_and_request_no_attestation(self):
        options = self.client.post("/api/v1/auth/mfa/passkeys/register/begin/").json()
        self.assertEqual(options["rp"]["id"], "jf.example.org")
        self.assertEqual(options["attestation"], "none")
        self.assertEqual(options["user"]["name"], "passkey-user")

    def test_first_passkey_enables_mfa_and_issues_recovery_codes(self):
        response = self.register()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data["enabled"])
        self.assertFalse(response.data["totp_enabled"])
        self.assertEqual(len(response.data["recovery_codes"]), 10)
        self.assertEqual([p["name"] for p in response.data["passkeys"]], ["Laptop"])
        stored = PasskeyCredential.objects.get(user=self.user)
        self.assertEqual(bytes(stored.credential_id), self.authenticator.credential_id)
        self.assertTrue(mfa.has_mfa(self.user))

    def test_second_passkey_keeps_existing_recovery_codes(self):
        first_codes = self.register().data["recovery_codes"]
        response = self.register(
            authenticator=SoftAuthenticator(origin=ORIGIN, rp_id="jf.example.org"), name="Schlüssel"
        )
        self.assertEqual(response.data["recovery_codes"], [])
        self.assertEqual(len(response.data["passkeys"]), 2)
        self.assertTrue(mfa.use_recovery_code(self.user, first_codes[0]))

    def test_challenge_is_single_use(self):
        options = self.client.post("/api/v1/auth/mfa/passkeys/register/begin/").json()
        credential = self.authenticator.create(options)
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/mfa/passkeys/register/finish/", {"credential": credential}, format="json"
            ).status_code,
            200,
        )
        replay = self.client.post(
            "/api/v1/auth/mfa/passkeys/register/finish/", {"credential": credential}, format="json"
        )
        self.assertEqual(replay.status_code, 400)
        self.assertEqual(PasskeyCredential.objects.count(), 1)

    def test_foreign_origin_is_rejected(self):
        options = self.client.post("/api/v1/auth/mfa/passkeys/register/begin/").json()
        credential = self.authenticator.create(options, origin="https://evil.example")
        response = self.client.post(
            "/api/v1/auth/mfa/passkeys/register/finish/", {"credential": credential}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PasskeyCredential.objects.exists())

    def test_expired_challenge_is_rejected(self):
        options = self.client.post("/api/v1/auth/mfa/passkeys/register/begin/").json()
        with patch("users.passkeys.CHALLENGE_TTL", -1):
            response = self.client.post(
                "/api/v1/auth/mfa/passkeys/register/finish/",
                {"credential": self.authenticator.create(options)},
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PasskeyCredential.objects.exists())

    def test_registration_needs_recent_reauthentication(self):
        later = mfa.time.time() + 301
        with patch("users.mfa.time.time", return_value=later):
            response = self.client.post("/api/v1/auth/mfa/passkeys/register/begin/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "reauthentication_required")

    def test_limit_per_account(self):
        with patch.object(PasskeyCredential, "MAX_PER_USER", 1):
            self.assertEqual(self.register().status_code, 200)
            self.assertEqual(self.client.post("/api/v1/auth/mfa/passkeys/register/begin/").status_code, 409)

    def test_remove_passkey_and_last_factor_rule(self):
        self.register()
        passkey_id = PasskeyCredential.objects.get().pk
        with patch("users.mfa_views.mfa_required", return_value=True):
            response = self.client.post(f"/api/v1/auth/mfa/passkeys/{passkey_id}/remove/")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "mfa_last_factor")
        response = self.client.post(f"/api/v1/auth/mfa/passkeys/{passkey_id}/remove/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["enabled"])
        self.assertFalse(MFARecoveryCode.objects.filter(user=self.user).exists())

    def test_foreign_passkey_cannot_be_removed(self):
        other = User.objects.create_user(username="other", password=PASSWORD)
        foreign = PasskeyCredential.objects.create(user=other, name="x", credential_id=b"f" * 16, public_key=b"x")
        self.assertEqual(self.client.post(f"/api/v1/auth/mfa/passkeys/{foreign.pk}/remove/").status_code, 404)
        self.assertTrue(PasskeyCredential.objects.filter(pk=foreign.pk).exists())

    def test_totp_can_be_added_and_removed_next_to_passkeys(self):
        self.register()
        secret = self.client.post("/api/v1/auth/mfa/setup/").data["secret"]
        confirm = self.client.post(
            "/api/v1/auth/mfa/confirm/", {"code": mfa.totp_at(secret, mfa.current_step())}, format="json"
        )
        self.assertEqual(confirm.status_code, 200, confirm.content)
        self.assertEqual(confirm.data["recovery_codes"], [])
        self.assertTrue(confirm.data["totp_enabled"])
        with patch("users.mfa_views.mfa_required", return_value=True):
            removed = self.client.post("/api/v1/auth/mfa/totp/remove/")
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(removed.data["totp_enabled"])
        self.assertTrue(removed.data["enabled"])

    def test_disable_removes_passkeys(self):
        self.register()
        self.assertFalse(self.client.post("/api/v1/auth/mfa/disable/").data["enabled"])
        self.assertFalse(PasskeyCredential.objects.exists())


class PasskeyLoginTests(PasskeyTestCase):
    def setUp(self):
        super().setUp()
        setup_client = csrf_client()
        login(setup_client, "passkey-user")
        self.codes = self.register(client=setup_client).data["recovery_codes"]
        self.client = csrf_client()

    def test_login_offers_passkey_and_completes_with_it(self):
        response = login(self.client, "passkey-user")
        self.assertEqual(response.data["mfa_methods"], {"totp": False, "passkey": True})
        self.assertFalse(response.data["authenticated"])
        options = self.client.post("/api/v1/auth/session/mfa/passkey-options/").json()
        self.assertEqual(options["rpId"], "jf.example.org")
        done = self.client.post(
            "/api/v1/auth/session/mfa/", {"passkey": self.authenticator.get(options)}, format="json"
        )
        self.assertEqual(done.status_code, 200, done.content)
        self.assertTrue(done.data["authenticated"])
        self.assertIsNotNone(PasskeyCredential.objects.get().last_used_at)

    def test_passkey_options_need_a_pending_login(self):
        self.assertEqual(self.client.post("/api/v1/auth/session/mfa/passkey-options/").status_code, 400)

    def test_assertion_cannot_be_replayed(self):
        login(self.client, "passkey-user")
        options = self.client.post("/api/v1/auth/session/mfa/passkey-options/").json()
        assertion = self.authenticator.get(options)
        self.assertTrue(
            self.client.post("/api/v1/auth/session/mfa/", {"passkey": assertion}, format="json").data["authenticated"]
        )
        other = csrf_client()
        login(other, "passkey-user")
        other.post("/api/v1/auth/session/mfa/passkey-options/")
        replay = other.post("/api/v1/auth/session/mfa/", {"passkey": assertion}, format="json")
        self.assertEqual(replay.status_code, 400)

    def test_cloned_authenticator_with_stale_counter_is_rejected(self):
        login(self.client, "passkey-user")
        options = self.client.post("/api/v1/auth/session/mfa/passkey-options/").json()
        self.client.post(
            "/api/v1/auth/session/mfa/", {"passkey": self.authenticator.get(options, counter_step=5)}, format="json"
        )
        clone = csrf_client()
        login(clone, "passkey-user")
        options = clone.post("/api/v1/auth/session/mfa/passkey-options/").json()
        self.authenticator.sign_count = 1
        response = clone.post("/api/v1/auth/session/mfa/", {"passkey": self.authenticator.get(options)}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_foreign_passkey_does_not_complete_login(self):
        intruder = SoftAuthenticator(origin=ORIGIN, rp_id="jf.example.org")
        login(self.client, "passkey-user")
        options = self.client.post("/api/v1/auth/session/mfa/passkey-options/").json()
        response = self.client.post("/api/v1/auth/session/mfa/", {"passkey": intruder.get(options)}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_recovery_code_works_without_totp(self):
        login(self.client, "passkey-user")
        response = self.client.post("/api/v1/auth/session/mfa/", {"code": self.codes[0]}, format="json")
        self.assertTrue(response.data["authenticated"])

    def test_step_up_with_passkey(self):
        login(self.client, "passkey-user")
        options = self.client.post("/api/v1/auth/session/mfa/passkey-options/").json()
        self.client.post("/api/v1/auth/session/mfa/", {"passkey": self.authenticator.get(options)}, format="json")
        refresh_csrf(self.client)
        missing = self.client.post("/api/v1/auth/reauthenticate/", {"password": PASSWORD}, format="json")
        self.assertEqual(missing.status_code, 400)
        options = self.client.post("/api/v1/auth/reauthenticate/passkey-options/").json()
        response = self.client.post(
            "/api/v1/auth/reauthenticate/",
            {"password": PASSWORD, "passkey": self.authenticator.get(options)},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)


class MandatoryEnrolmentTests(PasskeyTestCase):
    def test_required_account_can_enrol_with_a_passkey(self):
        self.user.is_staff = True
        self.user.save()
        status = login(self.client, "passkey-user").data
        self.assertTrue(status["mfa_setup_required"])
        self.assertEqual(self.client.get("/api/v1/members/").status_code, 403)
        self.assertEqual(self.register().status_code, 200)
        self.assertEqual(self.client.get("/api/v1/auth/session/").data.get("mfa_setup_required"), None)

    def test_totp_users_keep_their_login(self):
        MFADevice.objects.create(user=self.user, secret=SECRET, confirmed_at="2026-01-01T00:00:00Z")
        status = login(self.client, "passkey-user").data
        self.assertEqual(status["mfa_methods"], {"totp": True, "passkey": False})
