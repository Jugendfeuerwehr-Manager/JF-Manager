"""Serializers for TrainingBlock."""

from rest_framework import serializers

from members.models import Group
from training.models import TrainingBlock, TrainingMedia

from .library_block import LibraryBlockListSerializer, TrainingMediaSerializer


class GroupMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class TrainingBlockSerializer(serializers.ModelSerializer):
    groups = GroupMiniSerializer(many=True, read_only=True)
    library_block_title = serializers.CharField(
        source='library_block.title', read_only=True, default=None
    )
    media = serializers.SerializerMethodField()

    class Meta:
        model = TrainingBlock
        fields = [
            'id', 'title', 'content', 'session', 'groups',
            'library_block', 'library_block_title',
            'duration_minutes', 'start_offset_minutes', 'position_order',
            'color', 'nextcloud_folder_url',
            'created_at', 'updated_at', 'media',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_media(self, obj):
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(obj)
        qs = TrainingMedia.objects.filter(content_type=ct, object_id=obj.pk)
        return TrainingMediaSerializer(qs, many=True, context=self.context).data


class TrainingBlockCreateSerializer(serializers.ModelSerializer):
    group_ids = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        source='groups',
        many=True,
        required=False,
    )

    class Meta:
        model = TrainingBlock
        fields = [
            'id', 'title', 'content', 'session', 'group_ids',
            'library_block', 'duration_minutes', 'start_offset_minutes',
            'position_order', 'color', 'nextcloud_folder_url',
        ]

    def create(self, validated_data):
        groups = validated_data.pop('groups', [])
        # If library_block supplied with no content, copy content from it
        library_block = validated_data.get('library_block')
        if library_block and not validated_data.get('content'):
            validated_data['content'] = library_block.content
        if library_block and not validated_data.get('color'):
            validated_data['color'] = library_block.color
        block = super().create(validated_data)
        block.groups.set(groups)
        return block


class TrainingBlockMoveSerializer(serializers.ModelSerializer):
    """Minimal serializer for drag-and-drop position updates."""

    class Meta:
        model = TrainingBlock
        fields = ['start_offset_minutes', 'position_order', 'duration_minutes', 'groups']

    groups = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        many=True,
        required=False,
    )

    def update(self, instance, validated_data):
        groups = validated_data.pop('groups', None)
        instance = super().update(instance, validated_data)
        if groups is not None:
            instance.groups.set(groups)
        return instance
