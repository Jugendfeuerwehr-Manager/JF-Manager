"""CSP violation reports: anonymous, bounded, and logged without personal data (SEC-10.3b)."""

import json
from unittest import mock

from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from jf_manager_backend import csp_report

URL = "/api/v1/security/csp-report/"


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class CspReportTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)

    def post(self, payload, content_type="application/csp-report"):
        return self.client.post(URL, data=json.dumps(payload), content_type=content_type)

    def test_legacy_report_is_logged_without_query_or_path_of_blocked_resource(self):
        report = {
            "csp-report": {
                "document-uri": "https://jf.example.org/members/12?search=Max%20Mustermann",
                "violated-directive": "script-src-elem",
                "blocked-uri": "https://cdn.example.net/lib.js?token=secret",
            }
        }
        with self.assertLogs("security.csp", "WARNING") as logs:
            response = self.post(report)
        self.assertEqual(response.status_code, 204)
        line = logs.output[0]
        self.assertIn("directive=script-src-elem", line)
        self.assertIn("blocked=https://cdn.example.net ", line)
        self.assertIn("page=/members/12", line)
        self.assertNotIn("Mustermann", line)
        self.assertNotIn("secret", line)

    def test_reporting_api_batch_is_accepted(self):
        batch = [
            {
                "type": "csp-violation",
                "body": {
                    "effectiveDirective": "img-src",
                    "blockedURL": "inline",
                    "documentURL": "https://jf.example.org/",
                },
            },
            {"type": "deprecation", "body": {"id": "x"}},
        ]
        with self.assertLogs("security.csp", "WARNING") as logs:
            response = self.post(batch, content_type="application/reports+json")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(logs.output), 1)
        self.assertIn("directive=img-src blocked=inline page=/", logs.output[0])

    def test_rejects_oversized_and_invalid_bodies_and_get(self):
        self.assertEqual(self.client.get(URL).status_code, 405)
        self.assertEqual(self.client.post(URL, data="not json", content_type="application/csp-report").status_code, 400)
        big = {"csp-report": {"document-uri": "x" * (csp_report.MAX_BODY_BYTES + 1)}}
        self.assertEqual(self.post(big).status_code, 413)

    def test_global_rate_limit_stops_logging(self):
        report = {"csp-report": {"violated-directive": "img-src", "blocked-uri": "data"}}
        with (
            mock.patch.object(csp_report, "MAX_REPORTS_PER_MINUTE", 2),
            self.assertLogs("security.csp", "WARNING") as logs,
        ):
            for _ in range(4):
                self.assertEqual(self.post(report).status_code, 204)
        self.assertEqual(len(logs.output), 2)
