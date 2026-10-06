"""Exercise SEC-03.4 through Django's historical migration state."""

from datetime import UTC, datetime
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class LegacyMemberListMigrationTests(TransactionTestCase):
    migrate_from = ("members", "0028_memberlist_export_permission")
    migrate_to = ("members", "0029_scope_legacy_member_lists")

    def test_safe_assignment_split_preservation_repeat_and_rollback(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Department = old_apps.get_model("departments", "Department")
        Member = old_apps.get_model("members", "Member")
        MemberList = old_apps.get_model("members", "MemberList")
        Entry = old_apps.get_model("members", "MemberListEntry")
        Attachment = old_apps.get_model("members", "Attachment")
        ContentType = old_apps.get_model("contenttypes", "ContentType")

        department_a = Department.objects.create(name="Migration A", code="migration-list-a")
        department_b = Department.objects.create(name="Migration B", code="migration-list-b")
        member_a = Member.objects.create(name="A", lastname="Migration")
        member_a2 = Member.objects.create(name="A2", lastname="Migration")
        member_b = Member.objects.create(name="B", lastname="Migration")
        member_shared = Member.objects.create(name="Shared", lastname="Migration")
        member_none = Member.objects.create(name="None", lastname="Migration")
        member_a.departments.add(department_a)
        member_a2.departments.add(department_a)
        member_b.departments.add(department_b)
        member_shared.departments.add(department_a, department_b)

        uniform = MemberList.objects.create(name="Uniform A", color="#123456")
        mixed = MemberList.objects.create(name="Mixed A B")
        empty = MemberList.objects.create(name="Empty")
        described = MemberList.objects.create(name="Described A", description="Private legacy description")
        attached = MemberList.objects.create(name="Attached B")
        shared = MemberList.objects.create(name="Shared A B")
        checked_at = datetime(2025, 5, 4, 12, 30, tzinfo=UTC)
        original_date = datetime(2025, 4, 1, 10, 0, tzinfo=UTC)
        MemberList.objects.filter(pk=mixed.pk).update(created_at=original_date, updated_at=original_date)
        uniform_entry = Entry.objects.create(
            member_list=uniform, member=member_a, checked=True, checked_at=checked_at, notes="Preserve this note"
        )
        uniform_entry_2 = Entry.objects.create(member_list=uniform, member=member_a2)
        mixed_a = Entry.objects.create(member_list=mixed, member=member_a, checked=True, checked_at=checked_at)
        mixed_b = Entry.objects.create(member_list=mixed, member=member_b, notes="B note")
        mixed_shared = Entry.objects.create(member_list=mixed, member=member_shared, notes="Needs review")
        mixed_none = Entry.objects.create(member_list=mixed, member=member_none)
        described_entry = Entry.objects.create(member_list=described, member=member_a)
        attached_entry = Entry.objects.create(member_list=attached, member=member_b)
        shared_unique = Entry.objects.create(member_list=shared, member=member_a)
        shared_ambiguous = Entry.objects.create(member_list=shared, member=member_shared)
        mixed_b_added_at = mixed_b.added_at

        content_type, _ = ContentType.objects.get_or_create(app_label="members", model="memberlist")
        attachment = Attachment.objects.create(
            content_type=content_type, object_id=attached.pk, name="Keep on unresolved source"
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        apps = executor.loader.project_state([self.migrate_to]).apps
        MemberList = apps.get_model("members", "MemberList")
        Entry = apps.get_model("members", "MemberListEntry")
        Attachment = apps.get_model("members", "Attachment")

        self.assertEqual(MemberList.objects.get(pk=uniform.pk).department_id, department_a.pk)
        self.assertEqual(MemberList.objects.get(pk=empty.pk).department_id, None)
        for source in (mixed, described, attached, shared):
            self.assertIsNone(MemberList.objects.get(pk=source.pk).department_id)

        mixed_a_target = MemberList.objects.get(name="Mixed A B", department_id=department_a.pk)
        mixed_b_target = MemberList.objects.get(name="Mixed A B", department_id=department_b.pk)
        self.assertEqual(mixed_a_target.description, "")
        self.assertEqual(mixed_a_target.created_at, original_date)
        self.assertEqual(mixed_a_target.updated_at, original_date)
        self.assertEqual(Entry.objects.get(pk=mixed_a.pk).member_list_id, mixed_a_target.pk)
        self.assertEqual(Entry.objects.get(pk=mixed_b.pk).member_list_id, mixed_b_target.pk)
        self.assertEqual(Entry.objects.get(pk=mixed_shared.pk).member_list_id, mixed.pk)
        self.assertEqual(Entry.objects.get(pk=mixed_none.pk).member_list_id, mixed.pk)

        self.assertEqual(Entry.objects.get(pk=uniform_entry.pk).member_list_id, uniform.pk)
        self.assertEqual(Entry.objects.get(pk=uniform_entry_2.pk).member_list_id, uniform.pk)
        self.assertTrue(Entry.objects.get(pk=uniform_entry.pk).checked)
        self.assertEqual(Entry.objects.get(pk=uniform_entry.pk).checked_at, checked_at)
        self.assertEqual(Entry.objects.get(pk=uniform_entry.pk).notes, "Preserve this note")
        self.assertEqual(Entry.objects.get(pk=mixed_b.pk).notes, "B note")
        self.assertEqual(Entry.objects.get(pk=mixed_b.pk).added_at, mixed_b_added_at)

        described_target = MemberList.objects.get(name="Described A", department_id=department_a.pk)
        attached_target = MemberList.objects.get(name="Attached B", department_id=department_b.pk)
        self.assertEqual(Entry.objects.get(pk=described_entry.pk).member_list_id, described_target.pk)
        self.assertEqual(Entry.objects.get(pk=attached_entry.pk).member_list_id, attached_target.pk)
        self.assertEqual(MemberList.objects.get(pk=described.pk).description, "Private legacy description")
        self.assertEqual(described_target.description, "")
        self.assertEqual(Attachment.objects.get(pk=attachment.pk).object_id, attached.pk)
        self.assertFalse(Attachment.objects.filter(object_id=attached_target.pk).exists())
        self.assertEqual(Entry.objects.get(pk=shared_unique.pk).member_list.department_id, department_a.pk)
        self.assertEqual(Entry.objects.get(pk=shared_ambiguous.pk).member_list_id, shared.pk)

        migration = import_module("members.migrations.0029_scope_legacy_member_lists")
        count_after_first_run = MemberList.objects.count()
        schema_editor = SimpleNamespace(connection=connection)
        migration.scope_legacy_member_lists(apps, schema_editor)
        self.assertEqual(MemberList.objects.count(), count_after_first_run)

        failure_uniform = MemberList.objects.create(name="Rollback direct assignment")
        Entry.objects.create(member_list=failure_uniform, member_id=member_a2.pk)
        failure_source = MemberList.objects.create(name="Fail atomically", description="Must remain unresolved")
        failure_entry = Entry.objects.create(member_list=failure_source, member_id=member_a.pk)
        with (
            patch.object(migration, "_move_entries", side_effect=RuntimeError("synthetic rollback")),
            self.assertRaisesRegex(RuntimeError, "synthetic rollback"),
        ):
            migration.scope_legacy_member_lists(apps, schema_editor)
        self.assertIsNone(MemberList.objects.get(pk=failure_source.pk).department_id)
        self.assertIsNone(MemberList.objects.get(pk=failure_uniform.pk).department_id)
        self.assertEqual(Entry.objects.get(pk=failure_entry.pk).member_list_id, failure_source.pk)
        self.assertEqual(MemberList.objects.count(), count_after_first_run + 2)
