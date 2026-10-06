"""One validated, versioned transaction for a complete training plan."""

from copy import copy

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rest_framework import serializers

from members.models import Attachment
from training.api.serializers.block import TrainingBlockCreateSerializer
from training.api.serializers.session import TrainingSessionCreateSerializer
from training.copying import copied_files
from training.models import TrainingBlock, TrainingMedia, TrainingSession


class PlanInputSerializer(serializers.Serializer):
    expected_revision = serializers.IntegerField(min_value=1)
    session = serializers.DictField()
    blocks = serializers.ListField(child=serializers.DictField(), max_length=1000)


def lock_sessions(ids):
    """All plan writers lock the same parent rows in a stable order."""
    return list(TrainingSession.objects.select_for_update().filter(pk__in=ids).order_by("pk"))


def advance_revision(session):
    session.revision += 1
    session.save(update_fields=["revision", "updated_at"])


def delete_plan_blocks(blocks):
    """Delete owned generic records too; file cleanup runs after commit."""
    ct = ContentType.objects.get_for_model(TrainingBlock)
    ids = list(blocks.values_list("pk", flat=True))
    Attachment.objects.filter(content_type=ct, object_id__in=ids).delete()
    TrainingMedia.objects.filter(content_type=ct, object_id__in=ids).delete()
    blocks.delete()


@transaction.atomic
def save_plan(session, data, context, sync_service):
    """Caller has locked the session and checked the expected revision."""
    context = {**context, "complete_plan": True}
    session_serializer = TrainingSessionCreateSerializer(session, data=data["session"], context=context)
    session_serializer.is_valid(raise_exception=True)
    candidate = copy(session)
    for key, value in session_serializer.validated_data.items():
        if key != "groups":
            setattr(candidate, key, value)

    existing = {block.pk: block for block in session.blocks.all()}
    retained = set()
    prepared = []
    for index, raw in enumerate(data["blocks"]):
        raw = dict(raw)
        block_id = raw.pop("id", None)
        block = None
        if block_id is not None:
            # Avoid coercing strings/bools or disclosing foreign block owners.
            if type(block_id) is not int or block_id not in existing or block_id in retained:
                raise serializers.ValidationError({"blocks": {index: "Ungültige oder doppelte Baustein-ID."}})
            retained.add(block_id)
            block = existing[block_id]
        if "session" in raw and raw["session"] != session.pk:
            raise serializers.ValidationError({"blocks": {index: "Bausteine gehören zu dieser Übung."}})
        raw["session"] = session.pk
        serializer = TrainingBlockCreateSerializer(block, data=raw, context=context)
        # Resolve relations against the prospective session, including time and
        # department changes that must be validated together with all blocks.
        serializer.fields["session"] = serializers.HiddenField(default=candidate)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"blocks": {index: exc.detail}}) from exc
        prepared.append(serializer)

    session = session_serializer.save()
    with copied_files() as files:
        for serializer in prepared:
            serializer.context["copied_files"] = files
            serializer.save(session=session)
    delete_plan_blocks(session.blocks.exclude(pk__in=retained | {serializer.instance.pk for serializer in prepared}))
    advance_revision(session)
    sync_service(session)
    # Prefetched blocks/groups describe the old revision; never return them.
    return TrainingSession.objects.get(pk=session.pk)
