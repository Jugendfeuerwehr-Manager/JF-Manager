from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import connection
from django.test import SimpleTestCase
from rest_framework.test import APIClient, APITestCase

from users import mfa
from users.models import MFADevice, MFARecoveryCode

User = get_user_model()
PASSWORD = "Synthetic-Passw0rd!"


class TOTPVectorTests(SimpleTestCase):
    def test_rfc6238_sha1_vectors(self):
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        self.assertEqual(mfa.totp_at(secret, mfa.current_step(59)), "287082")
        self.assertEqual(mfa.totp_at(secret, mfa.current_step(1111111109)), "081804")

    def test_provisioning_uri_contains_issuer_and_secret(self):
        uri = mfa.provisioning_uri("ABC", "user name")
        self.assertTrue(uri.startswith("otpauth://totp/JF-Manager%3Auser%20name?"))
        self.assertIn("secret=ABC", uri)


def session_client(username, password=PASSWORD):
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/v1/auth/session/").cookies[settings.CSRF_COOKIE_NAME].value
    response = client.post(
        "/api/v1/auth/session/login/",
        {"username": username, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200, response.content
    client.credentials(HTTP_X_CSRFTOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)
    return client


class MFAEnrolmentTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="mfa-user", password=PASSWORD)
        self.client = session_client("mfa-user")
        # Freeze the TOTP clock so tests never straddle a 30-second step boundary.
        frozen = mfa.time.time()
        patcher = patch("users.mfa.time.time", return_value=frozen)
        patcher.start()
        self.addCleanup(patcher.stop)

    def enrol(self):
        secret = self.client.post("/api/v1/auth/mfa/setup/").data["secret"]
        response = self.client.post(
            "/api/v1/auth/mfa/confirm/", {"code": mfa.totp_at(secret, mfa.current_step())}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        return secret, response.data["recovery_codes"]

    def test_enrolment_stores_only_encrypted_secret_and_hashed_codes(self):
        self.assertEqual(self.client.get("/api/v1/auth/mfa/").data["enabled"], False)
        secret, codes = self.enrol()
        self.assertEqual(len(codes), 10)
        self.assertTrue(self.client.get("/api/v1/auth/mfa/").data["enabled"])
        with connection.cursor() as cursor:
            cursor.execute("SELECT secret FROM users_mfadevice")
            raw_secret = cursor.fetchone()[0]
        self.assertNotIn(secret, raw_secret)
        stored = list(MFARecoveryCode.objects.values_list("code_hash", flat=True))
        for code in codes:
            self.assertNotIn(code.replace("-", ""), stored)
        self.assertEqual(self.client.post("/api/v1/auth/mfa/setup/").status_code, 409)

    def test_wrong_confirmation_code_does_not_enable(self):
        self.client.post("/api/v1/auth/mfa/setup/")
        response = self.client.post("/api/v1/auth/mfa/confirm/", {"code": "000000"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(MFADevice.objects.get(user=self.user).is_confirmed)

    def test_security_changes_need_recent_reauthentication(self):
        start = mfa.time.time()
        with patch("users.mfa.time.time", return_value=start + 301):
            response = self.client.post("/api/v1/auth/mfa/setup/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "reauthentication_required")

    def test_totp_codes_cannot_be_replayed(self):
        secret, _codes = self.enrol()
        step = mfa.current_step()
        replay = self.client.post(
            "/api/v1/auth/reauthenticate/", {"password": PASSWORD, "code": mfa.totp_at(secret, step)}, format="json"
        )
        self.assertEqual(replay.status_code, 400)
        fresh = self.client.post(
            "/api/v1/auth/reauthenticate/", {"password": PASSWORD, "code": mfa.totp_at(secret, step + 1)}, format="json"
        )
        self.assertEqual(fresh.status_code, 200)

    def test_recovery_codes_are_single_use(self):
        _secret, codes = self.enrol()
        payload = {"password": PASSWORD, "code": codes[0].upper()}
        self.assertEqual(self.client.post("/api/v1/auth/reauthenticate/", payload, format="json").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/auth/reauthenticate/", payload, format="json").status_code, 400)
        self.assertEqual(self.client.get("/api/v1/auth/mfa/").data["recovery_codes_remaining"], 9)

    def test_reauthentication_requires_password_and_second_factor(self):
        _secret, codes = self.enrol()
        wrong_password = {"password": "wrong", "code": codes[0]}
        missing_code = {"password": PASSWORD}
        for payload in (wrong_password, missing_code):
            self.assertEqual(self.client.post("/api/v1/auth/reauthenticate/", payload, format="json").status_code, 400)

    def test_disable_and_regenerate_require_recent_reauthentication(self):
        self.enrol()
        later = mfa.time.time() + 301
        with patch("users.mfa.time.time", return_value=later):
            self.assertEqual(self.client.post("/api/v1/auth/mfa/recovery-codes/").status_code, 403)
            self.assertEqual(self.client.post("/api/v1/auth/mfa/disable/").status_code, 403)
        self.assertEqual(len(self.client.post("/api/v1/auth/mfa/recovery-codes/").data["recovery_codes"]), 10)
        self.assertEqual(self.client.post("/api/v1/auth/mfa/disable/").data["enabled"], False)
        self.assertFalse(MFARecoveryCode.objects.exists())

    def test_mfa_endpoints_require_csrf(self):
        client = session_client("mfa-user")
        client.credentials()
        self.assertEqual(client.post("/api/v1/auth/mfa/setup/").status_code, 403)
        self.assertFalse(MFADevice.objects.exists())

    def test_password_change_keeps_current_session_and_ends_others(self):
        other = session_client("mfa-user")
        response = self.client.post(
            "/api/v1/users/change_password/",
            {
                "old_password": PASSWORD,
                "new_password": "Another-Synthetic-9!",
                "new_password_confirm": "Another-Synthetic-9!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.client.get("/api/v1/users/me/").status_code, 200)
        self.assertIn(other.get("/api/v1/users/me/").status_code, (401, 403))
        self.assertGreaterEqual(Session.objects.count(), 1)
