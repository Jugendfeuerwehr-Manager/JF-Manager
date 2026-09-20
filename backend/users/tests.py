from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from django.test import TestCase, override_settings


@override_settings(
    ALLOWED_HOSTS=["app.example.com"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class OIDCRedirectURITests(TestCase):
    @patch("users.oidc_views._fetch_discovery_document")
    @patch("users.oidc_views._get_oidc_config")
    @patch("users.oidc_views.requests.post")
    def test_https_forwarded_proto_is_used_for_login_and_token_exchange(
        self, post, get_config, fetch_discovery
    ):
        get_config.return_value = SimpleNamespace(
            enabled=True,
            issuer_url="https://idp.example.com",
            client_id="client",
            client_secret="secret",
            scope="openid",
            provider_name="Example",
        )
        fetch_discovery.return_value = {
            "authorization_endpoint": "https://idp.example.com/authorize",
            "token_endpoint": "https://idp.example.com/token",
        }
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {}  # Stop after checking the token request.

        login = self.client.get(
            "/api/v1/auth/oidc/login/",
            HTTP_HOST="app.example.com",
            HTTP_X_FORWARDED_PROTO="https",
        )
        self.assertEqual(login.status_code, 200)
        params = parse_qs(urlparse(login.json()["authorization_url"]).query)
        expected = "https://app.example.com/api/v1/auth/oidc/callback/"
        self.assertEqual(params["redirect_uri"], [expected])

        self.client.get(
            "/api/v1/auth/oidc/callback/",
            {"code": "authorization-code", "state": params["state"][0]},
            HTTP_HOST="app.example.com",
            HTTP_X_FORWARDED_PROTO="https",
        )
        self.assertEqual(post.call_args.kwargs["data"]["redirect_uri"], expected)
