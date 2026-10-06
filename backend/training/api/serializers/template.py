"""Serializers for whole-exercise templates (read-mostly, independent copies)."""

from rest_framework import serializers

from training.models import TrainingTemplate, TrainingTemplateBlock

from .block import GroupMiniSerializer


class TrainingTemplateBlockSerializer(serializers.ModelSerializer):
    groups = GroupMiniSerializer(many=True, read_only=True)

    class Meta:
        model = TrainingTemplateBlock
        fields = [
            "id",
            "title",
            "content",
            "groups",
            "duration_minutes",
            "start_offset_minutes",
            "position_order",
            "color",
        ]
        read_only_fields = fields


class TrainingTemplateSerializer(serializers.ModelSerializer):
    groups = GroupMiniSerializer(many=True, read_only=True)
    block_count = serializers.IntegerField(source="blocks.count", read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, default=None)

    class Meta:
        model = TrainingTemplate
        fields = [
            "id",
            "title",
            "description",
            "start_time",
            "end_time",
            "location",
            "department",
            "groups",
            "block_count",
            "source_session",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        # Only the name and description are edited; contents change by saving a new template.
        read_only_fields = [name for name in fields if name not in ("title", "description")]


class TrainingTemplateDetailSerializer(TrainingTemplateSerializer):
    blocks = TrainingTemplateBlockSerializer(many=True, read_only=True)

    class Meta(TrainingTemplateSerializer.Meta):
        fields = [*TrainingTemplateSerializer.Meta.fields, "notes", "blocks"]
        read_only_fields = [name for name in fields if name not in ("title", "description")]


class SaveAsTemplateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=300)


class CopyToDateSerializer(serializers.Serializer):
    date = serializers.DateField()
    title = serializers.CharField(required=False, allow_blank=True, max_length=300)
