"""Sign-in with a passkey alone, without password (SEC-12)."""

from django.contrib.auth import get_user_model
from django.test import override_settings

from api_tests.test_passkeys import ORIGIN, PASSWORD, PasskeyTestCase, csrf_client, login
from api_tests.webauthn_soft import SoftAuthenticator
from users.mfa import MFA_VERIFIED_KEY
from users.models import PasskeyCredential, UserSession

User = get_user_model()


@override_settings(FRONTEND_URL=ORIGIN, WEBAUTHN_RP_ID="", WEBAUTHN_ORIGINS=[])
class PasskeySignInTests(PasskeyTestCase):
    def setUp(self):
        super().setUp()
        setup_client = csrf_client()
        login(setup_client, "passkey-user")
        self.assertEqual(self.register(client=setup_client).status_code, 200)
        self.client = csrf_client()

    def handle(self, user=None):
        return f"jf-user-{(user or self.user).pk}".encode()

    def options(self, client=None):
        response = (client or self.client).post("/api/v1/auth/session/passkey/options/")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def sign_in(self, assertion, client=None):
        return (client or self.client).post("/api/v1/auth/session/passkey/", {"passkey": assertion}, format="json")

    def test_registration_requests_a_discoverable_passkey(self):
        User.objects.create_user(username="fresh", password=PASSWORD)
        client = csrf_client()
        login(client, "fresh")
        options = client.post("/api/v1/auth/mfa/passkeys/register/begin/").json()
        self.assertEqual(options["authenticatorSelection"]["residentKey"], "required")

    def test_options_name_no_account_and_require_user_verification(self):
        options = self.options()
        self.assertEqual(options["rpId"], "jf.example.org")
        self.assertEqual(options.get("allowCredentials", []), [])
        self.assertEqual(options["userVerification"], "required")

    def test_passkey_signs_in_without_password_and_counts_as_mfa(self):
        response = self.sign_in(self.authenticator.get(self.options(), user_handle=self.handle()))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data["authenticated"])
        self.assertNotIn("mfa_required", response.data)
        self.assertIsNotNone(self.client.session.get(MFA_VERIFIED_KEY))
        self.assertTrue(UserSession.objects.filter(user=self.user).exists())
        self.assertEqual(self.client.get("/api/v1/users/me/").status_code, 200)
        self.assertIsNotNone(PasskeyCredential.objects.get().last_used_at)

    def test_assertion_without_user_handle_is_accepted(self):
        response = self.sign_in(self.authenticator.get(self.options()))
        self.assertEqual(response.status_code, 200, response.content)

    def test_mandatory_mfa_account_signs_in(self):
        self.user.is_staff = True
        self.user.save()
        response = self.sign_in(self.authenticator.get(self.options(), user_handle=self.handle()))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotIn("mfa_setup_required", response.data)
        self.assertTrue(response.data["privileged_session"])
        self.assertEqual(self.client.get("/api/v1/users/me/").status_code, 200)

    def test_presence_only_is_not_enough(self):
        response = self.sign_in(self.authenticator.get(self.options(), user_verified=False))
        self.assertEqual(response.status_code, 401)
        self.assertFalse(self.client.get("/api/v1/auth/session/").data["authenticated"])

    def test_unknown_passkey_is_rejected(self):
        stranger = SoftAuthenticator(origin=ORIGIN, rp_id="jf.example.org")
        self.assertEqual(self.sign_in(stranger.get(self.options())).status_code, 401)

    def test_user_handle_of_another_account_is_rejected(self):
        other = User.objects.create_user(username="other", password="x")
        response = self.sign_in(self.authenticator.get(self.options(), user_handle=self.handle(other)))
        self.assertEqual(response.status_code, 401)

    def test_foreign_origin_is_rejected(self):
        response = self.sign_in(self.authenticator.get(self.options(), origin="https://evil.example"))
        self.assertEqual(response.status_code, 401)

    def test_challenge_is_single_use(self):
        assertion = self.authenticator.get(self.options())
        self.assertEqual(self.sign_in(assertion).status_code, 200)
        other = csrf_client()
        self.options(other)
        self.assertEqual(self.sign_in(assertion, client=other).status_code, 401)
        self.assertEqual(
            self.sign_in(self.authenticator.get({"challenge": "AAAA"}), client=csrf_client()).status_code, 401
        )

    def test_stale_counter_is_rejected(self):
        self.sign_in(self.authenticator.get(self.options(), counter_step=5))
        self.authenticator.sign_count = 1
        response = self.sign_in(self.authenticator.get(self.options(csrf_client())), client=csrf_client())
        self.assertEqual(response.status_code, 401)

    def test_inactive_account_is_rejected(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.sign_in(self.authenticator.get(self.options())).status_code, 401)

    def test_directory_accounts_keep_passkey_as_second_factor(self):
        for source in (User.AuthSource.LDAP, User.AuthSource.OIDC):
            self.user.auth_source = source
            self.user.save()
            client = csrf_client()
            response = self.sign_in(self.authenticator.get(self.options(client)), client=client)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["code"], "passkey_second_factor_only")
            self.assertFalse(client.get("/api/v1/auth/session/").data["authenticated"])

    def test_csrf_is_enforced(self):
        from rest_framework.test import APIClient

        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.post("/api/v1/auth/session/passkey/options/").status_code, 403)
