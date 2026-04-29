"""Serializers for TrainingSession."""

from rest_framework import serializers

from members.models import Group
from training.models import TrainingSession

from .block import GroupMiniSerializer, TrainingBlockSerializer


class TrainingSessionListSerializer(serializers.ModelSerializer):
    group_count = serializers.SerializerMethodField()
    groups = GroupMiniSerializer(many=True, read_only=True)
    block_count = serializers.SerializerMethodField()

    class Meta:
        model = TrainingSession
        fields = [
            'id', 'title', 'date', 'start_time', 'end_time',
            'location', 'group_count', 'groups', 'block_count',
            'series_parent', 'recurrence_rule',
        ]

    def get_group_count(self, obj):
        return obj.groups.count()

    def get_block_count(self, obj):
        return obj.blocks.count()


class TrainingSessionDetailSerializer(serializers.ModelSerializer):
    groups = GroupMiniSerializer(many=True, read_only=True)
    group_ids = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        source='groups',
        many=True,
        write_only=True,
        required=False,
    )
    blocks = TrainingBlockSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True, default=None
    )

    class Meta:
        model = TrainingSession
        fields = [
            'id', 'title', 'description', 'date', 'start_time', 'end_time',
            'location', 'notes', 'groups', 'group_ids', 'blocks',
            'series_parent', 'recurrence_rule',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        groups = validated_data.pop('groups', [])
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        session = super().create(validated_data)
        session.groups.set(groups)
        return session

    def update(self, instance, validated_data):
        groups = validated_data.pop('groups', None)
        instance = super().update(instance, validated_data)
        if groups is not None:
            instance.groups.set(groups)
        return instance


class TrainingSessionCreateSerializer(TrainingSessionDetailSerializer):
    """Alias with same logic — separate name for get_serializer_class clarity."""
    pass


class TrainingSessionHandoutSerializer(serializers.ModelSerializer):
    """
    Optimised for the handout view: full blocks with all content and media URLs.
    """
    groups = GroupMiniSerializer(many=True, read_only=True)
    blocks = TrainingBlockSerializer(many=True, read_only=True)

    class Meta:
        model = TrainingSession
        fields = [
            'id', 'title', 'description', 'date', 'start_time', 'end_time',
            'location', 'notes', 'groups', 'blocks',
        ]
