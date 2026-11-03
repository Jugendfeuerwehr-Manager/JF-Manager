"""DSGVO: personal data is deleted after configurable retention periods. Fictional data."""

import os
import tempfile
from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from departments.models import Department
from members.models import EmailAttachment, EmailMessage, EmailRecipient
from participation.models import Registration
from participation.tests.helpers import make_member, make_session
from portal.models import ChangeLog
from privacy.services.retention import purge_personal_data, retention_days

User = get_user_model()


def age(obj, field, days):
    type(obj).objects.filter(pk=obj.pk).update(**{field: timezone.now() - timedelta(days=days)})


class RetentionTests(TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        media = override_settings(MEDIA_ROOT=root.name)
        media.enable()
        self.addCleanup(media.disable)
        self.department = Department.objects.create(name="Mitte", code="retention-mitte")
        self.sender = User.objects.create_user("sender", password="x")

    def message(self, days, status="sent"):
        message = EmailMessage.objects.create(
            sender=self.sender, subject="Elternabend", department=self.department, body_html="", status=status
        )
        EmailRecipient.objects.create(email_message=message, email_address="eva@example.invalid", recipient_name="Eva")
        EmailAttachment.objects.create(
            email_message=message, file=SimpleUploadedFile("einladung.txt", b"x"), original_filename="einladung.txt"
        )
        age(message, "created_at", days)
        return message

    def test_old_email_history_goes_with_recipients_and_files(self):
        old, fresh, sending = self.message(400), self.message(10), self.message(400, status="sending")
        path = old.attachments.get().file.path
        with self.captureOnCommitCallbacks(execute=True):  # django_cleanup removes files on commit
            results = {result.name: result.count for result in purge_personal_data()}
        self.assertEqual(results["email_history_days"], 1)
        self.assertFalse(EmailMessage.objects.filter(pk=old.pk).exists())
        self.assertFalse(EmailRecipient.objects.filter(email_message_id=old.pk).exists())
        self.assertEqual(EmailMessage.objects.filter(pk__in=[fresh.pk, sending.pk]).count(), 2)
        self.assertFalse(os.path.exists(path))

    def test_dry_run_changes_nothing_and_periods_are_configurable(self):
        self.message(100)
        from dynamic_preferences.registries import global_preferences_registry

        global_preferences_registry.manager()["privacy__email_history_days"] = 30
        self.assertEqual(retention_days("email_history_days"), 30)
        out = StringIO()
        call_command("purge_personal_data", "--dry-run", stdout=out)
        self.assertIn("Würden bereinigt: 1 – E-Mail-Verlauf", out.getvalue())
        self.assertEqual(EmailMessage.objects.count(), 1)
        call_command("purge_personal_data", stdout=StringIO())
        self.assertEqual(EmailMessage.objects.count(), 0)

    def test_illness_reason_is_blanked_after_the_service(self):
        member = make_member(self.department)
        past = make_session(self.department, day=date.today() - timedelta(days=120))
        recent = make_session(self.department, day=date.today() - timedelta(days=10))
        common = {"member": member, "state": "cancelled", "source": "staff", "state_changed_at": timezone.now()}
        old = Registration.objects.create(session=past, reason_category="krankheit", **common)
        new = Registration.objects.create(session=recent, reason_category="krankheit", **common)
        holiday = Registration.objects.create(
            session=past,
            member=make_member(self.department, "Ben"),
            state="cancelled",
            source="staff",
            state_changed_at=timezone.now(),
            reason_category="urlaub",
        )
        purge_personal_data()
        old.refresh_from_db(), new.refresh_from_db(), holiday.refresh_from_db()
        self.assertEqual(
            (old.reason_category, new.reason_category, holiday.reason_category), ("", "krankheit", "urlaub")
        )

    def test_old_change_log_rows_are_deleted(self):
        row = ChangeLog.objects.create(
            target_kind="member", target_id=1, field="street", old="Altweg 1", new="Neuweg 2"
        )
        age(row, "applied_at", 800)
        ChangeLog.objects.create(target_kind="member", target_id=1, field="city", old="A", new="B")
        purge_personal_data()
        self.assertEqual(list(ChangeLog.objects.values_list("field", flat=True)), ["city"])


class RetentionSettingsTests(APITestCase):
    URL = "/api/v1/settings/privacy/"

    def setUp(self):
        self.editor = User.objects.create_user("datenschutz", password="x")
        self.editor.user_permissions.add(
            *Permission.objects.filter(codename__in=["view_privacy_settings", "change_privacy_settings"])
        )
        self.reader = User.objects.create_user("leser", password="x")
        self.reader.user_permissions.add(Permission.objects.get(codename="view_privacy_settings"))

    def test_anonymous_and_without_right(self):
        self.assertIn(self.client.get(self.URL).status_code, (401, 403))
        self.client.force_authenticate(User.objects.create_user("ohne", password="x"))
        self.assertEqual(self.client.get(self.URL).status_code, 403)

    def test_reader_sees_defaults_but_cannot_change(self):
        self.client.force_authenticate(self.reader)
        data = self.client.get(self.URL).json()
        self.assertEqual(data["email_history_days"], 365)
        self.assertEqual(data["absence_illness_days"], 90)
        self.assertEqual(self.client.patch(self.URL, {"email_history_days": 60}, format="json").status_code, 403)

    def test_editor_changes_with_bounds(self):
        self.client.force_authenticate(self.editor)
        self.assertEqual(self.client.patch(self.URL, {"email_history_days": 5}, format="json").status_code, 400)
        response = self.client.patch(self.URL, {"email_history_days": 60}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(retention_days("email_history_days"), 60)

    def test_catalog_lists_the_privacy_category(self):
        self.client.force_authenticate(self.editor)
        catalog = self.client.get("/api/v1/settings/catalog/").json()["categories"]
        self.assertEqual(catalog["privacy"]["fields"]["portal_changelog_days"]["min"], 90)
