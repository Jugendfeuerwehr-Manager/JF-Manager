"""Independent snapshots, including files, with rollback cleanup."""

import hashlib
import json
import mimetypes
import re
from contextlib import contextmanager

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from jf_manager_backend.html_safety import sanitize_rich_html
from members.models import Attachment
from training.models import TrainingBlock, TrainingMedia, TrainingSession

SESSION_FIELDS = ("title", "description", "start_time", "end_time", "location", "notes", "department_id")
BLOCK_FIELDS = (
    "title",
    "content",
    "duration_minutes",
    "start_offset_minutes",
    "position_order",
    "color",
    "nextcloud_folder_url",
    "library_block_id",
)


def snapshot_hash(session):
    data = {name: str(getattr(session, name)) for name in (*SESSION_FIELDS, "date", "status")}
    data["groups"] = sorted(session.groups.values_list("pk", flat=True))
    data["blocks"] = []
    for block in session.blocks.order_by("start_offset_minutes", "position_order", "pk"):
        data["blocks"].append(
            {
                **{name: getattr(block, name) for name in BLOCK_FIELDS},
                "groups": sorted(block.groups.values_list("pk", flat=True)),
            }
        )
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


@contextmanager
def copied_files():
    created = []
    try:
        yield created
    except BaseException:
        for field in created:
            if field._committed and field.name:
                field.storage.delete(field.name)
        raise


def copy_file(source, target, created):
    if not source.file:
        target.save()
        return
    with source.file.open("rb") as stream:
        name = getattr(source, "original_filename", "") or source.file.name.rsplit("/", 1)[-1]
        target.file = SimpleUploadedFile(
            name,
            stream.read(),
            content_type=getattr(source, "mime_type", "")
            or mimetypes.guess_type(name)[0]
            or "application/octet-stream",
        )
    # Keep the FieldFile object, also if insertion fails after the file was written.
    created.append(target.file)
    target.save()


def copy_block(source, target_session, user, created):
    block = TrainingBlock.objects.create(
        session=target_session,
        **{
            field: sanitize_rich_html(source.content) if field == "content" else getattr(source, field)
            for field in BLOCK_FIELDS
        },
    )
    block.groups.set(source.groups.all())
    source_type = ContentType.objects.get_for_model(source)
    target_type = ContentType.objects.get_for_model(block)
    for media in TrainingMedia.objects.filter(content_type=source_type, object_id=source.pk):
        fresh = TrainingMedia(
            content_type=target_type, object_id=block.pk, original_filename=media.original_filename, uploaded_by=user
        )
        copy_file(media, fresh, created)
        # Sanitized rich HTML only keeps absolute image URLs; keep scheme and host.
        pattern = r"(https?://[^/\s\"<>]+)" + re.escape(media.url) + r"(?![0-9])"
        block.content = re.sub(pattern, lambda match, url=fresh.url: match.group(1) + url, block.content)
    for attachment in Attachment.objects.filter(content_type=source_type, object_id=source.pk):
        fresh = Attachment(
            content_type=target_type,
            object_id=block.pk,
            name=attachment.name,
            description=attachment.description,
            uploaded_by=user,
        )
        copy_file(attachment, fresh, created)
    block.save(update_fields=["content"])
    return block


def copy_session(source, target_date, user, created, **overrides):
    target = TrainingSession.objects.create(
        date=target_date,
        created_by=user,
        **{
            **{field: getattr(source, field) for field in SESSION_FIELDS},
            **overrides,
        },
    )
    target.groups.set(source.groups.all())
    for block in source.blocks.all():
        copy_block(block, target, user, created)
    return target
