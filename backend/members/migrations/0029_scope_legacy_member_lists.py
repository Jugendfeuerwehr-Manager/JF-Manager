"""Move only unambiguous legacy list entries into department-owned lists."""

from collections import defaultdict

from django.db import migrations, transaction


def _move_entries(Entry, database, entry_ids, target_id):
    # UPDATE keeps the entry primary key, check state, notes and added_at.
    Entry.objects.using(database).filter(pk__in=entry_ids).update(member_list_id=target_id)


def scope_legacy_member_lists(apps, schema_editor):
    database = schema_editor.connection.alias
    Member = apps.get_model("members", "Member")
    MemberList = apps.get_model("members", "MemberList")
    Entry = apps.get_model("members", "MemberListEntry")
    Attachment = apps.get_model("members", "Attachment")
    ContentType = apps.get_model("contenttypes", "ContentType")
    through = Member._meta.get_field("departments").remote_field.through
    content_type_ids = list(
        ContentType.objects.using(database).filter(app_label="members", model="memberlist").values_list("pk", flat=True)
    )

    # A migration is one transaction. A failed deployment rolls every list
    # back, so restarting the migration never resumes a half-split source.
    with transaction.atomic(using=database):
        source_ids = list(
            MemberList.objects.using(database)
            .filter(department__isnull=True)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        for source_id in source_ids:
            source = MemberList.objects.using(database).get(pk=source_id)
            entries = list(
                Entry.objects.using(database).filter(member_list_id=source_id).values_list("pk", "member_id")
            )
            if not entries:
                # Empty and previously split source lists need human review.
                continue

            member_ids = [member_id for _, member_id in entries]
            departments_by_member = defaultdict(set)
            for member_id, department_id in (
                through.objects.using(database)
                .filter(member_id__in=member_ids)
                .values_list("member_id", "department_id")
            ):
                departments_by_member[member_id].add(department_id)

            entries_by_department = defaultdict(list)
            for entry_id, member_id in entries:
                member_departments = departments_by_member[member_id]
                if len(member_departments) == 1:
                    entries_by_department[next(iter(member_departments))].append(entry_id)

            has_attachments = (
                bool(content_type_ids)
                and Attachment.objects.using(database)
                .filter(content_type_id__in=content_type_ids, object_id=source_id)
                .exists()
            )
            all_entries_unambiguous = sum(map(len, entries_by_department.values())) == len(entries)
            if (
                len(entries_by_department) == 1
                and all_entries_unambiguous
                and not source.description.strip()
                and not has_attachments
            ):
                department_id = next(iter(entries_by_department))
                MemberList.objects.using(database).filter(pk=source_id).update(department_id=department_id)
                continue

            # Description and attachments stay only on the unresolved source.
            # Separate lists inherit the harmless display name, color and dates.
            for department_id, entry_ids in sorted(entries_by_department.items()):
                target = MemberList.objects.using(database).create(
                    name=source.name,
                    description="",
                    color=source.color,
                    department_id=department_id,
                )
                MemberList.objects.using(database).filter(pk=target.pk).update(
                    created_at=source.created_at,
                    updated_at=source.updated_at,
                )
                _move_entries(Entry, database, entry_ids, target.pk)


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("members", "0028_memberlist_export_permission")]

    operations = [
        # Reverse leaves resolved ownership intact; the original source links
        # cannot be reconstructed without an explicit old-to-new mapping.
        migrations.RunPython(scope_legacy_member_lists, reverse_code=migrations.RunPython.noop),
    ]
