"""Explicit superuser resolution of legacy member lists."""

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from members.models import Attachment, Member, MemberList, MemberListEntry, MemberListLegacyTarget


def _attachments(source):
    content_type = ContentType.objects.get_for_model(MemberList)
    return Attachment.objects.filter(content_type=content_type, object_id=source.pk).order_by("pk")


def pending_resolution_data(source):
    """Return the facts an administrator needs to make an explicit choice."""
    return {
        "id": source.pk,
        "name": source.name,
        "description": source.description,
        "entries": [
            {
                "id": entry.pk,
                "member_id": entry.member_id,
                "member_name": str(entry.member),
                "department_ids": list(entry.member.departments.values_list("pk", flat=True)),
                "checked": entry.checked,
                "checked_at": entry.checked_at,
                "notes": entry.notes,
                "added_at": entry.added_at,
            }
            for entry in source.entries.select_related("member").prefetch_related("member__departments")
        ],
        "attachments": [
            {
                "id": attachment.pk,
                "name": attachment.name,
                "description": attachment.description,
                "file_size": attachment.file_size,
                "mime_type": attachment.mime_type,
            }
            for attachment in _attachments(source)
        ],
        "targets": [
            {"department": mapping.department_id, "list_id": mapping.target_id}
            for mapping in source.legacy_targets.order_by("department_id")
        ],
    }


@transaction.atomic
def resolve_legacy_list(source_id, data):
    """Move selected content once; reject any incomplete finalization before writing."""
    source = (
        MemberList.objects.select_for_update()
        .filter(pk=source_id, department__isnull=True, legacy_resolved_at__isnull=True)
        .first()
    )
    if source is None:
        raise Http404

    department = data["department"]
    entry_ids = set(data.get("entry_ids", []))
    attachment_ids = set(data.get("attachment_ids", []))
    assign_description = data.get("assign_description", False)
    complete = data.get("complete", False)
    requested_target_id = data.get("target_list_id")

    mapping = (
        MemberListLegacyTarget.objects.select_related("target").filter(source=source, department=department).first()
    )
    if mapping and requested_target_id is not None and requested_target_id != mapping.target_id:
        raise ValidationError({"target_list_id": "Für diese Abteilung wurde bereits ein anderes Ziel festgelegt."})
    target = mapping.target if mapping else None
    if target is not None and target.department_id != department.pk:
        raise ValidationError({"department": "Die gespeicherte Zielzuordnung ist inkonsistent."})
    if target is None and requested_target_id is not None:
        target = MemberList.objects.select_for_update().filter(pk=requested_target_id, department=department).first()
        if target is None or MemberListLegacyTarget.objects.filter(target=target).exists():
            raise ValidationError({"target_list_id": "Ungültige oder bereits zugeordnete Zielliste."})
        invalid_entry = MemberListEntry.objects.filter(member_list=target).exclude(member__departments=department)
        if invalid_entry.exists():
            raise ValidationError({"target_list_id": "Die Zielliste enthält fremde Mitglieder."})

    entries = list(MemberListEntry.objects.select_for_update().filter(pk__in=entry_ids).select_related("member"))
    if len(entries) != len(entry_ids) or any(
        entry.member_list_id not in ({source.pk, target.pk} if target else {source.pk}) for entry in entries
    ):
        raise ValidationError({"entry_ids": "Einträge gehören nicht zur Quelle oder diesem Ziel."})
    member_ids = {entry.member_id for entry in entries}
    member_department = Member.departments.through.objects.filter(
        member_id__in=member_ids, department_id=department.pk
    ).values_list("member_id", flat=True)
    if set(member_department) != member_ids:
        raise ValidationError({"entry_ids": "Alle Mitglieder müssen zur Zielabteilung gehören."})
    source_entries = [entry for entry in entries if entry.member_list_id == source.pk]
    if (
        target
        and MemberListEntry.objects.filter(
            member_list=target, member_id__in=[entry.member_id for entry in source_entries]
        ).exists()
    ):
        raise ValidationError({"entry_ids": "Ein Mitglied ist bereits in der Zielliste."})

    attachments = list(Attachment.objects.select_for_update().filter(pk__in=attachment_ids))
    content_type_id = ContentType.objects.get_for_model(MemberList).pk
    if len(attachments) != len(attachment_ids) or any(
        attachment.content_type_id != content_type_id
        or attachment.object_id not in ({source.pk, target.pk} if target else {source.pk})
        for attachment in attachments
    ):
        raise ValidationError({"attachment_ids": "Anhänge gehören nicht zur Quelle oder diesem Ziel."})
    source_attachments = [attachment.pk for attachment in attachments if attachment.object_id == source.pk]

    if assign_description and source.description.strip() and target and target.description.strip():
        raise ValidationError({"assign_description": "Die Zielliste enthält bereits eine Beschreibung."})
    if complete and (
        source.entries.exclude(pk__in=[entry.pk for entry in source_entries]).exists()
        or _attachments(source).exclude(pk__in=source_attachments).exists()
        or (source.description.strip() and not assign_description)
    ):
        raise ValidationError({"complete": "Die Quelle enthält noch nicht zugeordnete Inhalte."})

    if target is None:
        target = MemberList.objects.create(name=source.name, color=source.color, department=department)
        MemberList.objects.filter(pk=target.pk).update(created_at=source.created_at, updated_at=source.updated_at)
    if mapping is None:
        MemberListLegacyTarget.objects.create(source=source, department=department, target=target)

    if source_entries:
        MemberListEntry.objects.filter(pk__in=[entry.pk for entry in source_entries]).update(member_list=target)
    if source_attachments:
        Attachment.objects.filter(pk__in=source_attachments).update(object_id=target.pk)
    if assign_description and source.description.strip():
        MemberList.objects.filter(pk=target.pk).update(description=source.description)
        source.description = ""
        MemberList.objects.filter(pk=source.pk).update(description="")
    if complete:
        source.legacy_resolved_at = timezone.now()
        MemberList.objects.filter(pk=source.pk).update(legacy_resolved_at=source.legacy_resolved_at)

    source.refresh_from_db()
    return {
        "target_list_id": target.pk,
        "complete": source.legacy_resolved_at is not None,
        "pending": pending_resolution_data(source) if source.legacy_resolved_at is None else None,
    }
