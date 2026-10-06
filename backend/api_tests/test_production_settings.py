"""Production defaults: transport security and a clean deployment check (SEC-10.3)."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet
from django.test import Client, SimpleTestCase, override_settings

BACKEND_DIR = Path(__file__).resolve().parents[1]

SETTINGS_PROBE = """
import json
from django.conf import settings
print(json.dumps({
    "ssl_redirect": settings.SECURE_SSL_REDIRECT,
    "redirect_exempt": settings.SECURE_REDIRECT_EXEMPT,
    "hsts": settings.SECURE_HSTS_SECONDS,
    "proxy_header": settings.SECURE_PROXY_SSL_HEADER,
    "session_secure": settings.SESSION_COOKIE_SECURE,
    "frame": settings.X_FRAME_OPTIONS,
    "referrer": settings.SECURE_REFERRER_POLICY,
}))
"""


class ProductionSettingsTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def environment(self, **overrides):
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("SECURE_", "TRUST_PROXY", "DJANGO_", "DEBUG"))
        }
        env.update(
            {
                "PIPENV_DONT_LOAD_ENV": "1",
                "DJANGO_SETTINGS_MODULE": "jf_manager_backend.docker_settings",
                "DATABASE_URL": f"sqlite:///{self.tmp.name}/db.sqlite3",
                "STATIC_ROOT": f"{self.tmp.name}/static",
                "MEDIA_ROOT": f"{self.tmp.name}/media",
                "DEBUG": "False",
                "ALLOWED_HOSTS": "jf.example.org",
                "REDIS_URL": "none",
                "DJANGO_SECRET_KEY": "production-like-test-key-" + "x" * 50,
                "FIELD_ENCRYPTION_KEY": Fernet.generate_key().decode(),
            }
        )
        env.update(overrides)
        return env

    def run_backend(self, args, **overrides):
        return subprocess.run(
            [sys.executable, *args],
            cwd=BACKEND_DIR,
            env=self.environment(**overrides),
            capture_output=True,
            text=True,
            timeout=120,
        )

    def probe(self, **overrides):
        result = self.run_backend(["manage.py", "shell", "-c", SETTINGS_PROBE], **overrides)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_production_defaults_enforce_https(self):
        values = self.probe()
        self.assertTrue(values["ssl_redirect"])
        self.assertEqual(values["redirect_exempt"], ["^health/$"])
        self.assertGreaterEqual(values["hsts"], 31536000)
        self.assertTrue(values["session_secure"])
        self.assertEqual(values["proxy_header"], ["HTTP_X_FORWARDED_PROTO", "https"])
        self.assertEqual(values["frame"], "DENY")
        self.assertEqual(values["referrer"], "same-origin")

    def test_proxy_trust_can_be_disabled(self):
        self.assertIsNone(self.probe(TRUST_PROXY_SSL_HEADER="false")["proxy_header"])

    def test_development_does_not_redirect_or_send_hsts(self):
        values = self.probe(DEBUG="True")
        self.assertFalse(values["ssl_redirect"])
        self.assertEqual(values["hsts"], 0)
        self.assertFalse(values["session_secure"])

    def test_deploy_check_reports_no_security_findings(self):
        result = self.run_backend(["manage.py", "check", "--deploy"])
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertNotIn("(security.", output)
        self.assertNotIn("drf_spectacular", output)


@override_settings(SECURE_SSL_REDIRECT=True, ALLOWED_HOSTS=["testserver"])
class HttpsRedirectTests(SimpleTestCase):
    databases = {"default"}

    def test_plain_http_api_requests_are_redirected(self):
        response = Client().get("/api/v1/auth/session/")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response["Location"].startswith("https://"))

    def test_container_health_check_stays_on_http(self):
        self.assertNotEqual(Client().get("/health/").status_code, 301)

    def test_forwarded_https_is_not_redirected(self):
        response = Client().get("/api/v1/auth/session/", HTTP_X_FORWARDED_PROTO="https")
        self.assertNotEqual(response.status_code, 301)
