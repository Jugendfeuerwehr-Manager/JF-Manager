"""SEC-03.5: only a superuser can explicitly resolve ambiguous legacy lists."""

from datetime import UTC, datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from departments.models import Department
from members.models import Attachment, Member, MemberList, MemberListEntry, MemberListLegacyTarget


class LegacyListResolutionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department_a = Department.objects.create(name="Resolution A", code="resolution-a")
        cls.department_b = Department.objects.create(name="Resolution B", code="resolution-b")
        cls.member_a = Member.objects.create(name="A", lastname="Legacy")
        cls.member_b = Member.objects.create(name="B", lastname="Legacy")
        cls.member_shared = Member.objects.create(name="Shared", lastname="Legacy")
        cls.member_a.departments.add(cls.department_a)
        cls.member_b.departments.add(cls.department_b)
        cls.member_shared.departments.add(cls.department_a, cls.department_b)
        cls.source = MemberList.objects.create(name="Legacy", description="Private note")
        cls.checked_at = datetime(2025, 5, 4, 12, 30, tzinfo=UTC)
        cls.entry_a = MemberListEntry.objects.create(
            member_list=cls.source,
            member=cls.member_a,
            checked=True,
            checked_at=cls.checked_at,
            notes="A check",
        )
        cls.entry_b = MemberListEntry.objects.create(member_list=cls.source, member=cls.member_b)
        cls.entry_shared = MemberListEntry.objects.create(member_list=cls.source, member=cls.member_shared)
        cls.attachment = Attachment.objects.create(content_object=cls.source, name="Legacy file")
        cls.superuser = get_user_model().objects.create_superuser(username="legacy-superuser", password="test-only")
        cls.reader = get_user_model().objects.create_user(username="legacy-reader", password="test-only")
        cls.reader.user_permissions.add(Permission.objects.get(codename="can_access_all_departments"))
        cls.reader.user_permissions.add(Permission.objects.get(codename="view_memberlist"))

    def setUp(self):
        self.client.force_authenticate(user=self.superuser)

    def _url(self):
        return f"/api/v1/member-lists/{self.source.pk}/resolve-legacy/"

    def test_pending_queue_is_superuser_only_and_shows_decision_facts(self):
        self.client.force_authenticate(user=self.reader)
        self.assertEqual(self.client.get("/api/v1/member-lists/pending-resolution/").status_code, 403)
        self.assertEqual(self.client.get(self._url()).status_code, 403)
        self.assertEqual(self.client.post(self._url(), {"department": self.department_a.pk}).status_code, 403)

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get("/api/v1/member-lists/pending-resolution/")
        self.assertEqual(response.status_code, 200)
        item = next(item for item in response.data if item["id"] == self.source.pk)
        self.assertEqual(item["description"], "Private note")
        self.assertEqual(
            {entry["id"] for entry in item["entries"]},
            {
                self.entry_a.pk,
                self.entry_b.pk,
                self.entry_shared.pk,
            },
        )
        self.assertEqual(item["attachments"][0]["id"], self.attachment.pk)

    def test_explicit_moves_preserve_entries_and_content_without_copying(self):
        original_added_at = self.entry_a.added_at
        first = self.client.post(
            self._url(),
            {
                "department": self.department_a.pk,
                "entry_ids": [self.entry_a.pk, self.entry_shared.pk],
                "attachment_ids": [self.attachment.pk],
                "assign_description": True,
            },
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        target_a = MemberList.objects.get(pk=first.data["target_list_id"])
        self.assertEqual(target_a.department_id, self.department_a.pk)
        self.assertEqual(target_a.description, "Private note")
        self.assertEqual(target_a.attachments.get().pk, self.attachment.pk)
        self.entry_a.refresh_from_db()
        self.assertEqual(self.entry_a.member_list_id, target_a.pk)
        self.assertEqual(self.entry_a.checked_at, self.checked_at)
        self.assertEqual(self.entry_a.notes, "A check")
        self.assertEqual(self.entry_a.added_at, original_added_at)
        self.source.refresh_from_db()
        self.assertEqual(self.source.description, "")
        self.assertEqual(self.source.attachments.count(), 0)

        second = self.client.post(
            self._url(),
            {"department": self.department_b.pk, "entry_ids": [self.entry_b.pk], "complete": True},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["complete"])
        self.source.refresh_from_db()
        self.assertIsNotNone(self.source.legacy_resolved_at)
        self.assertEqual(self.client.get(self._url()).status_code, 404)
        pending = self.client.get("/api/v1/member-lists/pending-resolution/")
        self.assertNotIn(self.source.pk, {item["id"] for item in pending.data})
        self.assertEqual(MemberListLegacyTarget.objects.filter(source=self.source).count(), 2)

    def test_invalid_mixed_target_does_not_leave_partial_changes(self):
        before_lists = MemberList.objects.count()
        response = self.client.post(
            self._url(),
            {"department": self.department_a.pk, "entry_ids": [self.entry_a.pk, self.entry_b.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MemberList.objects.count(), before_lists)
        self.assertEqual(MemberListLegacyTarget.objects.count(), 0)
        self.assertEqual(self.source.entries.count(), 3)

    def test_partial_request_is_idempotent_and_cannot_retarget_moved_entry(self):
        payload = {
            "department": self.department_a.pk,
            "entry_ids": [self.entry_a.pk],
            "attachment_ids": [self.attachment.pk],
        }
        first = self.client.post(self._url(), payload, format="json")
        second = self.client.post(self._url(), payload, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["target_list_id"], second.data["target_list_id"])
        self.assertEqual(MemberListLegacyTarget.objects.filter(source=self.source).count(), 1)
        self.assertEqual(MemberListEntry.objects.filter(pk=self.entry_a.pk).count(), 1)
        self.assertEqual(Attachment.objects.filter(pk=self.attachment.pk).count(), 1)
        self.assertEqual(Attachment.objects.get(pk=self.attachment.pk).object_id, first.data["target_list_id"])
        rejected = self.client.post(
            self._url(), {"department": self.department_b.pk, "entry_ids": [self.entry_a.pk]}, format="json"
        )
        self.assertEqual(rejected.status_code, 400)

    def test_existing_target_requires_explicit_choice_without_description_overwrite(self):
        existing = MemberList.objects.create(
            name="Existing A", description="Keep existing description", department=self.department_a
        )
        conflicting = self.client.post(
            self._url(),
            {
                "department": self.department_a.pk,
                "target_list_id": existing.pk,
                "entry_ids": [self.entry_a.pk],
                "assign_description": True,
            },
            format="json",
        )
        self.assertEqual(conflicting.status_code, 400)
        self.assertEqual(self.entry_a.member_list_id, self.source.pk)
        self.assertFalse(MemberListLegacyTarget.objects.filter(source=self.source).exists())

        accepted = self.client.post(
            self._url(),
            {"department": self.department_a.pk, "target_list_id": existing.pk, "entry_ids": [self.entry_a.pk]},
            format="json",
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data["target_list_id"], existing.pk)
        self.assertEqual(MemberListLegacyTarget.objects.get(source=self.source).target_id, existing.pk)
        other = MemberList.objects.create(name="Other A", department=self.department_a)
        retarget = self.client.post(
            self._url(), {"department": self.department_a.pk, "target_list_id": other.pk}, format="json"
        )
        self.assertEqual(retarget.status_code, 400)
        self.assertEqual(MemberListLegacyTarget.objects.get(source=self.source).target_id, existing.pk)

    def test_cannot_complete_with_unassigned_content(self):
        response = self.client.post(
            self._url(),
            {"department": self.department_a.pk, "entry_ids": [self.entry_a.pk], "complete": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MemberListLegacyTarget.objects.count(), 0)
        self.source.refresh_from_db()
        self.assertIsNone(self.source.legacy_resolved_at)

    def test_empty_source_requires_explicit_department_and_can_complete(self):
        empty = MemberList.objects.create(name="Empty legacy")
        url = f"/api/v1/member-lists/{empty.pk}/resolve-legacy/"
        missing = self.client.post(url, {"complete": True}, format="json")
        self.assertEqual(missing.status_code, 400)
        response = self.client.post(url, {"department": self.department_a.pk, "complete": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MemberList.objects.get(pk=response.data["target_list_id"]).department_id, self.department_a.pk)
        empty.refresh_from_db()
        self.assertIsNotNone(empty.legacy_resolved_at)

    def test_unresolved_source_cannot_be_deleted(self):
        response = self.client.delete(f"/api/v1/member-lists/{self.source.pk}/")
        self.assertEqual(response.status_code, 409)
        self.assertTrue(MemberList.objects.filter(pk=self.source.pk).exists())

    def test_mapped_target_cannot_be_deleted(self):
        resolved = self.client.post(
            self._url(), {"department": self.department_a.pk, "entry_ids": [self.entry_a.pk]}, format="json"
        )
        self.assertEqual(resolved.status_code, 200)
        target_id = resolved.data["target_list_id"]
        response = self.client.delete(f"/api/v1/member-lists/{target_id}/")
        self.assertEqual(response.status_code, 409)
        self.assertTrue(MemberList.objects.filter(pk=target_id).exists())
