import base64
import hashlib
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import jwt
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from settings_manager.models import OIDCConfig
from users import oidc_views
from users.models import MFADevice

User = get_user_model()
DISCOVERY = {
    "authorization_endpoint": "https://idp.example.test/authorize",
    "token_endpoint": "https://idp.example.test/token",
    "jwks_uri": "https://idp.example.test/jwks",
}


@override_settings(FRONTEND_URL="https://app.example.test", ALLOWED_HOSTS=["testserver"])
class OIDCFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.config = OIDCConfig.get_or_create_default()
        self.config.enabled = True
        self.config.issuer_url = "https://idp.example.test"
        self.config.client_id = "client"
        self.config.client_secret = "synthetic-secret"
        self.config.save()
        self.user = User.objects.create_user(username="sso-user", auth_source="oidc")
        self.claims = {"sub": "abc", "email": "person@example.test", "name": "Synthetic Person"}
        patches = {
            "discovery": patch("users.oidc_views._fetch_discovery_document", return_value=dict(DISCOVERY)),
            "post": patch("users.oidc_views.requests.post"),
            "verify": patch("users.oidc_views._verify_id_token", side_effect=lambda *args: dict(self.claims)),
            "authenticate": patch(
                "users.oidc_backend.JFManagerOIDCBackend.authenticate", side_effect=lambda request: self.user
            ),
        }
        self.mocks = {name: item.start() for name, item in patches.items()}
        for item in patches.values():
            self.addCleanup(item.stop)
        self.mocks["post"].return_value = Mock(status_code=200)
        self.mocks["post"].return_value.json.return_value = {"id_token": "synthetic.id.token"}

    def start(self, client=None, next_path="/members"):
        client = client or self.client
        response = client.get("/api/v1/auth/oidc/login/", {"next": next_path})
        self.assertEqual(response.status_code, 200)
        return parse_qs(urlparse(response.json()["authorization_url"]).query)

    def callback(self, state, client=None):
        response = (client or self.client).get(
            "/api/v1/auth/oidc/callback/", {"code": "synthetic-code", "state": state}
        )
        self.assertEqual(response.status_code, 302)
        location = urlparse(response["Location"])
        self.assertEqual(
            f"{location.scheme}://{location.netloc}{location.path}", "https://app.example.test/auth/oidc/callback"
        )
        return response, {key: values[0] for key, values in parse_qs(location.query).items()}

    def authenticated(self, client=None):
        return (client or self.client).get("/api/v1/auth/session/").json()

    def test_login_uses_pkce_and_successful_callback_creates_session(self):
        params = self.start()
        verifier = self.client.session[oidc_views.OIDC_FLOW_KEY]["verifier"]
        expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        self.assertEqual(params["code_challenge"], [expected])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        response, query = self.callback(params["state"][0])
        self.assertEqual(query, {"result": "ok", "next": "/members"})
        self.assertEqual(self.mocks["post"].call_args.kwargs["data"]["code_verifier"], verifier)
        self.assertNotIn("person", response["Location"])
        self.assertTrue(self.authenticated()["authenticated"])
        self.assertEqual(self.client.get("/api/v1/users/me/").status_code, 200)

    def test_state_is_bound_to_starting_browser(self):
        params = self.start()
        other = self.client_class()
        _response, query = self.callback(params["state"][0], client=other)
        self.assertEqual(query, {"error": "expired"})
        self.assertFalse(self.authenticated(other)["authenticated"])
        self.mocks["post"].assert_not_called()

    def test_state_can_only_be_used_once(self):
        params = self.start()
        self.callback(params["state"][0])
        _response, query = self.callback(params["state"][0])
        self.assertEqual(query, {"error": "expired"})
        self.assertEqual(self.mocks["post"].call_count, 1)

    def test_expired_state_is_rejected(self):
        params = self.start()
        with patch("users.oidc_views.time.time", return_value=oidc_views.time.time() + 301):
            _response, query = self.callback(params["state"][0])
        self.assertEqual(query, {"error": "expired"})

    def test_next_must_be_relative(self):
        for target in ("//evil.example/", "https://evil.example/", "/\\\\evil.example", "javascript:alert(1)"):
            params = self.start(next_path=target)
            _response, query = self.callback(params["state"][0])
            self.assertEqual(query["next"], "/", target)
            self.client.logout()

    def test_token_endpoint_on_foreign_host_is_not_called(self):
        self.mocks["discovery"].return_value = {**DISCOVERY, "token_endpoint": "https://collector.example/token"}
        params = self.start()
        _response, query = self.callback(params["state"][0])
        self.assertEqual(query, {"error": "unavailable"})
        self.mocks["post"].assert_not_called()

    def test_errors_do_not_leak_exception_text_or_claims(self):
        self.mocks["verify"].side_effect = ValueError("person@example.test is not allowed")
        params = self.start()
        response, query = self.callback(params["state"][0])
        self.assertEqual(query, {"error": "verification_failed"})
        self.assertNotIn("example.test%40", response["Location"])
        self.assertNotIn("person", response["Location"])

    def test_local_mfa_is_required_after_sso(self):
        MFADevice.objects.create(user=self.user, secret="JBSWY3DPEHPK3PXP", confirmed_at="2026-01-01T00:00:00Z")
        params = self.start()
        _response, query = self.callback(params["state"][0])
        self.assertEqual(query["result"], "mfa_required")
        self.assertEqual(self.authenticated(), {"authenticated": False, "mfa_required": True})

    def test_provider_mfa_counts_only_when_explicitly_trusted(self):
        self.user.is_staff = True
        self.user.save()
        self.claims["amr"] = ["pwd", "otp"]
        params = self.start()
        self.callback(params["state"][0])
        self.assertTrue(self.authenticated()["mfa_setup_required"])
        self.client.logout()
        self.config.trust_provider_mfa = True
        self.config.save()
        params = self.start()
        self.callback(params["state"][0])
        status = self.authenticated()
        self.assertTrue(status["authenticated"])
        self.assertNotIn("mfa_setup_required", status)

    def test_token_exchange_endpoint_is_removed(self):
        self.assertEqual(self.client.post("/api/v1/auth/oidc/exchange/", {"exchange_code": "x"}).status_code, 404)


class IdTokenAlgorithmTests(TestCase):
    @patch("users.oidc_views.requests.get")
    def test_symmetric_or_unsigned_algorithms_are_rejected(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {"keys": [{"kty": "oct", "k": "c2VjcmV0"}]}
        config = Mock(issuer_url="https://idp.example.test", client_id="client")
        for algorithm, key in (("HS256", "secret"), ("none", None)):
            token = jwt.encode({"sub": "x"}, key, algorithm=algorithm)
            with self.assertRaisesMessage(ValueError, "Nicht zugelassener Signaturalgorithmus"):
                oidc_views._verify_id_token(token, DISCOVERY, config, "nonce")
