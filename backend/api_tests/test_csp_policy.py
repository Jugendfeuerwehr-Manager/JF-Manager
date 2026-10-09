"""Content-Security-Policy is enforced on Django responses; report-only is a switch (SEC-13)."""

import re
from pathlib import Path
from unittest import SkipTest

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings

from jf_manager_backend.csp import ENFORCE_HEADER, REPORT_ONLY_HEADER, build_policy

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


class CspHeaderTests(TestCase):
    def test_policy_is_enforced_by_default(self):
        response = self.client.get("/api/v1/app/branding/")
        self.assertEqual(response[ENFORCE_HEADER], build_policy(settings.CSP_DIRECTIVES))
        self.assertNotIn(REPORT_ONLY_HEADER, response)
        self.assertEqual(response["Permissions-Policy"], settings.PERMISSIONS_POLICY)

    def test_policy_is_strict(self):
        policy = self.client.get("/api/v1/app/branding/")[ENFORCE_HEADER]
        directives = dict(part.split(" ", 1) for part in policy.split("; "))
        self.assertEqual(directives["script-src"], "'self'")
        self.assertEqual(directives["default-src"], "'self'")
        self.assertEqual(directives["object-src"], "'none'")
        self.assertEqual(directives["frame-ancestors"], "'none'")
        self.assertEqual(directives["report-uri"], "/api/v1/security/csp-report/")
        self.assertNotIn("unsafe-eval", policy)
        self.assertNotRegex(policy, r"https?:")

    @override_settings(CSP_REPORT_ONLY=True)
    def test_switch_turns_the_policy_into_report_only(self):
        response = self.client.get("/api/v1/app/branding/")
        self.assertEqual(response[REPORT_ONLY_HEADER], build_policy(settings.CSP_DIRECTIVES))
        self.assertNotIn(ENFORCE_HEADER, response)

    def test_error_and_anonymous_responses_carry_the_policy(self):
        self.assertIn(ENFORCE_HEADER, self.client.get("/api/v1/does-not-exist/"))
        self.assertIn(ENFORCE_HEADER, self.client.get("/api/v1/members/"))

    def test_stricter_view_policy_is_kept(self):
        from django.http import HttpResponse

        from jf_manager_backend.csp import ContentSecurityPolicyMiddleware

        def view(_request):
            response = HttpResponse()
            response[ENFORCE_HEADER] = "sandbox; default-src 'none'"
            return response

        response = ContentSecurityPolicyMiddleware(view)(None)
        self.assertEqual(response[ENFORCE_HEADER], "sandbox; default-src 'none'")
        self.assertNotIn(REPORT_ONLY_HEADER, response)

    def test_api_docs_need_no_inline_script(self):
        page = self.client.get("/api/docs/").content.decode()
        self.assertNotRegex(page, r"<script>")
        self.assertIn("?script", page)
        redoc = self.client.get("/api/redoc/").content.decode()
        self.assertNotIn("fonts.googleapis.com", redoc)
        self.assertNotRegex(redoc, r"<script>")


class NginxPolicyTests(SimpleTestCase):
    """The SPA is served by nginx; its policy must match the Django policy."""

    def setUp(self):
        if not (FRONTEND_DIR / "nginx.conf").exists():
            raise SkipTest("frontend/ is not part of this checkout")
        self.nginx = (FRONTEND_DIR / "nginx.conf").read_text()
        self.snippet = (FRONTEND_DIR / "snippets" / "security-headers.conf").read_text()

    def test_nginx_sends_the_same_policy(self):
        match = re.search(r"map \$host \$jf_csp_policy \{\s*default \"([^\"]+)\";", self.nginx)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), build_policy(settings.CSP_DIRECTIVES))

    def test_nginx_enforces_unless_report_only_is_selected(self):
        self.assertEqual((FRONTEND_DIR / "csp-mode.conf").read_text().split("\n")[-2], "default enforce;")
        self.assertIn("add_header Content-Security-Policy $jf_csp_enforce always;", self.snippet)
        self.assertIn("add_header Content-Security-Policy-Report-Only $jf_csp_report_only always;", self.snippet)
        self.assertIn(f'add_header Permissions-Policy "{settings.PERMISSIONS_POLICY}" always;', self.snippet)
