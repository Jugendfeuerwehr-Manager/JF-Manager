import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from settings_manager.operations_status import operations_status

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def stamp(hours_ago):
    return (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


class OperationsStatusReaderTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.file = Path(self.directory.name) / "ops-status.json"

    def write(self, data):
        self.file.write_text(json.dumps(data) if not isinstance(data, str) else data)
        return operations_status(str(self.file), now=NOW)

    def test_not_configured_missing_and_broken_files_are_reported_not_raised(self):
        self.assertEqual(operations_status("", now=NOW), {"available": False, "reason": "not_configured"})
        self.assertEqual(operations_status(str(self.file), now=NOW)["reason"], "missing")
        self.assertEqual(self.write("{kaputt")["reason"], "unreadable")
        self.assertEqual(self.write("[1, 2]")["reason"], "unreadable")

    def test_healthy_status_has_no_warnings_and_only_whitelisted_fields(self):
        result = self.write(
            {
                "instance": "jf-test",
                "mode": "compose",
                "version": "1.4.0",
                "workers_held": False,
                "updated": stamp(1),
                "secret": "nie ausgeben",
                "last_backup": {
                    "status": "ok",
                    "finished": stamp(2),
                    "snapshot": "abcdef12",
                    "message": "timer",
                    "last_success": {"finished": stamp(2), "snapshot": "abcdef12"},
                },
            }
        )
        self.assertTrue(result["available"])
        self.assertEqual(result["warnings"], [])
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(result["last_backup"]["last_success"], stamp(2))

    def test_failed_overdue_stale_and_held_states_warn(self):
        result = self.write(
            {
                "instance": "jf-test",
                "mode": "native",
                "workers_held": True,
                "updated": stamp(60),
                "last_backup": {
                    "status": "failed",
                    "finished": stamp(3),
                    "message": "restic backup fehlgeschlagen",
                    "last_success": {"finished": stamp(50)},
                },
            }
        )
        codes = {warning["code"] for warning in result["warnings"]}
        self.assertEqual(codes, {"status_stale", "backup_failed", "backup_overdue", "workers_held"})
        self.assertEqual(self.write({"updated": stamp(1)})["warnings"][0]["code"], "backup_missing")


class OperationsStatusEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.file = Path(self.directory.name) / "ops-status.json"
        self.file.write_text(json.dumps({"instance": "jf-test", "mode": "compose", "updated": "2026-10-07T11:00:00Z"}))

    def test_only_system_administration_reads_the_status(self):
        user = get_user_model().objects.create_user(username="leitung", password="x")
        self.client.force_authenticate(user)
        with override_settings(OPS_STATUS_FILE=str(self.file)):
            self.assertEqual(self.client.get("/api/v1/settings/operations/").status_code, 403)
            user.user_permissions.add(Permission.objects.get(codename="view_all_settings"))
            user = get_user_model().objects.get(pk=user.pk)
            self.client.force_authenticate(user)
            response = self.client.get("/api/v1/settings/operations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["instance"], "jf-test")

    def test_development_without_jfctl_reports_not_configured(self):
        admin = get_user_model().objects.create_superuser(username="admin", password="x")
        self.client.force_authenticate(admin)
        with override_settings(OPS_STATUS_FILE=""):
            response = self.client.get("/api/v1/settings/operations/")
        self.assertEqual(response.json(), {"available": False, "reason": "not_configured"})
