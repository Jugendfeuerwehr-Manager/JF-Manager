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
from training.models import TrainingBlock, TrainingMedia, TrainingSession, TrainingTemplate, TrainingTemplateBlock

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


def owned_files(block):
    block_type = ContentType.objects.get_for_model(TrainingBlock)
    return {
        "media": sorted(
            TrainingMedia.objects.filter(content_type=block_type, object_id=block.pk).values_list("pk", flat=True)
        ),
        "attachments": sorted(
            Attachment.objects.filter(content_type=block_type, object_id=block.pk).values_list("pk", flat=True)
        ),
    }


def snapshot_hash(session):
    """Content fingerprint of a plan; status and date are compared separately."""
    data = {name: str(getattr(session, name)) for name in SESSION_FIELDS}
    data["groups"] = sorted(session.groups.values_list("pk", flat=True))
    data["blocks"] = []
    for block in session.blocks.order_by("start_offset_minutes", "position_order", "pk"):
        data["blocks"].append(
            {
                **{name: getattr(block, name) for name in BLOCK_FIELDS},
                "groups": sorted(block.groups.values_list("pk", flat=True)),
                **owned_files(block),
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


def copy_owned_files(source, target, user, created, *, referenced_only=False):
    """Copy images/attachments of any block-like owner and point the content at the copies."""
    source_type = ContentType.objects.get_for_model(source)
    target_type = ContentType.objects.get_for_model(target)
    for media in TrainingMedia.objects.filter(content_type=source_type, object_id=source.pk):
        if referenced_only and not re.search(re.escape(media.url) + r"(?![0-9])", target.content):
            continue
        fresh = TrainingMedia(
            content_type=target_type, object_id=target.pk, original_filename=media.original_filename, uploaded_by=user
        )
        copy_file(media, fresh, created)
        # Sanitized rich HTML only keeps absolute image URLs; keep scheme and host.
        pattern = r"(https?://[^/\s\"<>]+)" + re.escape(media.url) + r"(?![0-9])"
        target.content = re.sub(pattern, lambda match, url=fresh.url: match.group(1) + url, target.content)
    for attachment in Attachment.objects.filter(content_type=source_type, object_id=source.pk):
        fresh = Attachment(
            content_type=target_type,
            object_id=target.pk,
            name=attachment.name,
            description=attachment.description,
            uploaded_by=user,
        )
        copy_file(attachment, fresh, created)
    target.save(update_fields=["content"])


def copy_block(source, user, created, *, model=TrainingBlock, department_id=None, **parent):
    """Independent copy of a planned or template block into ``parent`` (session= or template=)."""
    block = model.objects.create(
        **parent,
        **{
            field: sanitize_rich_html(source.content) if field == "content" else getattr(source, field)
            for field in BLOCK_FIELDS
        },
    )
    groups = source.groups.all()
    block.groups.set(groups.filter(department_id=department_id) if department_id is not None else groups)
    copy_owned_files(source, block, user, created)
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
        copy_block(block, user, created, session=target)
    return target


def session_to_template(session, user, created, title=""):
    template = TrainingTemplate.objects.create(
        title=title or session.title,
        source_session=session,
        created_by=user,
        **{field: getattr(session, field) for field in SESSION_FIELDS if field != "title"},
    )
    template.groups.set(session.groups.all())
    for block in session.blocks.all():
        copy_block(block, user, created, model=TrainingTemplateBlock, template=template)
    return template


def template_to_session(template, target_date, user, created, title=""):
    """New draft; groups that left the template department are not carried over."""
    session = TrainingSession.objects.create(
        date=target_date,
        created_by=user,
        title=title or template.title,
        **{field: getattr(template, field) for field in SESSION_FIELDS if field != "title"},
    )
    department_id = template.department_id
    session.groups.set(template.groups.filter(department_id=department_id))
    for block in template.blocks.all():
        copy_block(block, user, created, department_id=department_id, session=session)
    return session
