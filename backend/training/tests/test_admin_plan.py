from datetime import date, time

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import RequestFactory, TestCase

from training.admin import TrainingBlockAdmin, TrainingSessionAdmin
from training.admin_forms import VersionedBlockForm, VersionedSessionForm
from training.models import TrainingBlock, TrainingSession
from training.workflow import sync_linked_service


class AdminPlanTests(TestCase):
    def setUp(self):
        self.session = TrainingSession.objects.create(
            title="Plan", date=date(2099, 1, 1), start_time=time(18), end_time=time(20)
        )
        self.block = TrainingBlock.objects.create(session=self.session, title="Block", duration_minutes=30)
        self.request = RequestFactory().post("/admin/")
        self.request.user = get_user_model().objects.create_superuser(username="admin-plan")

    def session_form(self, **changes):
        data = {
            "title": "Plan",
            "date": "2099-01-01",
            "start_time": "18:00",
            "end_time": "20:00",
            "status": "draft",
            "expected_revision": self.session.revision,
        }
        data.update(changes)
        return VersionedSessionForm(data, instance=self.session)

    def block_form(self, **changes):
        data = {
            "session": self.session.pk,
            "title": "Block",
            "kind": "block",
            "duration_minutes": 30,
            "start_offset_minutes": 0,
            "position_order": 0,
            "expected_revision": self.session.revision,
        }
        data.update(changes)
        return VersionedBlockForm(data, instance=self.block)

    def test_stale_session_and_block_forms_cannot_save(self):
        TrainingSession.objects.filter(pk=self.session.pk).update(revision=2)
        for form in (self.session_form(expected_revision=1), self.block_form(expected_revision=1)):
            self.assertFalse(form.is_valid())
            self.assertIn("inzwischen geändert", str(form.errors))

    def test_invalid_times_and_frame_shrink_are_rejected(self):
        for form in (
            self.session_form(end_time="18:00"),
            self.session_form(end_time="18:15"),
            self.block_form(start_offset_minutes=110),
        ):
            self.assertFalse(form.is_valid())

    def test_session_admin_advances_revision_and_syncs_publication(self):
        form = self.session_form(status="published")
        self.assertTrue(form.is_valid(), form.errors)
        model_admin = TrainingSessionAdmin(TrainingSession, AdminSite())
        with transaction.atomic():
            obj = form.save(commit=False)
            model_admin.save_model(self.request, obj, form, True)
            form.save_m2m()
        self.session.refresh_from_db()
        self.assertEqual(self.session.revision, 2)
        self.assertEqual(self.session.servicebook_entry.topic, "Plan")

    def test_block_admin_changes_and_deletion_advance_revision(self):
        form = self.block_form(start_offset_minutes=10)
        self.assertTrue(form.is_valid(), form.errors)
        model_admin = TrainingBlockAdmin(TrainingBlock, AdminSite())
        with transaction.atomic():
            model_admin.save_model(self.request, form.save(commit=False), form, True)
            form.save_m2m()
        self.session.refresh_from_db()
        self.assertEqual(self.session.revision, 2)
        model_admin.delete_model(self.request, self.block)
        self.session.refresh_from_db()
        self.assertEqual(self.session.revision, 3)
        self.assertFalse(TrainingBlock.objects.filter(pk=self.block.pk).exists())

    def test_documented_admin_change_requires_confirmation(self):
        self.session.status = "published"
        self.session.date = date(2000, 1, 1)
        self.session.save()
        sync_linked_service(self.session)
        form = self.session_form(date="2000-01-01", status="published")
        self.assertFalse(form.is_valid())
        self.assertIn("ausdrücklich bestätigen", str(form.errors))
        self.assertTrue(
            self.session_form(date="2000-01-01", status="published", confirm_service_change=True).is_valid()
        )
        self.assertFalse(TrainingBlockAdmin(TrainingBlock, AdminSite()).has_delete_permission(self.request, self.block))
