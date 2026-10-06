"""Serializers for TrainingSession."""

from rest_framework import serializers

from members.models import Group
from training.api.permissions import can_manage_training_department
from training.api.validation import validate_block_times, validate_session_times
from training.models import TrainingSession
from training.workflow import requires_service_confirmation, validate_workflow

from .block import GroupMiniSerializer, TrainingBlockSerializer


class TrainingSessionListSerializer(serializers.ModelSerializer):
    group_count = serializers.SerializerMethodField()
    groups = GroupMiniSerializer(many=True, read_only=True)
    block_count = serializers.SerializerMethodField()
    linked_service_id = serializers.SerializerMethodField()
    linked_service_start = serializers.SerializerMethodField()
    requires_service_confirmation = serializers.SerializerMethodField()
    can_manage_plan = serializers.SerializerMethodField()

    class Meta:
        model = TrainingSession
        fields = [
            "id",
            "revision",
            "status",
            "title",
            "date",
            "start_time",
            "end_time",
            "location",
            "group_count",
            "groups",
            "block_count",
            "series_parent",
            "recurrence_rule",
            "department",
            "linked_service_id",
            "linked_service_start",
            "requires_service_confirmation",
            "can_manage_plan",
        ]

    def get_group_count(self, obj):
        return obj.groups.count()

    def get_block_count(self, obj):
        return obj.blocks.count()

    def get_can_manage_plan(self, obj):
        request = self.context.get("request")
        return bool(request and can_manage_training_department(request.user, obj.department_id))

    def get_requires_service_confirmation(self, obj):
        return requires_service_confirmation(obj)

    def get_linked_service_id(self, obj):
        service = getattr(obj, "servicebook_entry", None)
        return service.id if service else None

    def get_linked_service_start(self, obj):
        service = getattr(obj, "servicebook_entry", None)
        return service.start if service else None


class TrainingSessionDetailSerializer(serializers.ModelSerializer):
    confirm_service_change = serializers.BooleanField(write_only=True, default=False)
    groups = GroupMiniSerializer(many=True, read_only=True)
    group_ids = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        source="groups",
        many=True,
        write_only=True,
        required=False,
    )
    blocks = TrainingBlockSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True, default=None)
    linked_service_id = serializers.SerializerMethodField()
    linked_service_start = serializers.SerializerMethodField()
    requires_service_confirmation = serializers.SerializerMethodField()
    can_manage_plan = serializers.SerializerMethodField()

    class Meta:
        model = TrainingSession
        fields = [
            "id",
            "revision",
            "status",
            "title",
            "description",
            "confirm_service_change",
            "date",
            "start_time",
            "end_time",
            "location",
            "notes",
            "groups",
            "group_ids",
            "blocks",
            "series_parent",
            "recurrence_rule",
            "department",
            "linked_service_id",
            "linked_service_start",
            "requires_service_confirmation",
            "can_manage_plan",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["revision", "created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        confirmed = attrs.pop("confirm_service_change", False)
        validate_workflow(self.instance, attrs, confirmed)
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start is not None and end is not None:
            duration = validate_session_times(start, end)
            if self.instance is not None and not self.context.get("complete_plan"):
                for block in self.instance.blocks.all():
                    validate_block_times(block.start_offset_minutes, block.duration_minutes, duration)
        request = self.context.get("request")
        if request is None:
            return attrs

        department = attrs.get("department", getattr(self.instance, "department", None))
        department_id = getattr(department, "pk", None)
        if not can_manage_training_department(request.user, department_id):
            raise serializers.ValidationError({"department": "Keine Schreibberechtigung für die Zielabteilung."})

        groups = attrs.get("groups")
        if groups is None:
            groups = self.instance.groups.all() if self.instance is not None else []
        if any(group.department_id != department_id for group in groups):
            raise serializers.ValidationError({"group_ids": "Gruppen müssen zur Trainingsabteilung gehören."})

        series_parent = attrs.get("series_parent", getattr(self.instance, "series_parent", None))
        if series_parent is not None and series_parent.department_id != department_id:
            raise serializers.ValidationError({"series_parent": "Die Serie gehört zu einer anderen Abteilung."})
        return attrs

    def create(self, validated_data):
        groups = validated_data.pop("groups", [])
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        session = super().create(validated_data)
        session.groups.set(groups)
        return session

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        instance = super().update(instance, validated_data)
        if groups is not None:
            instance.groups.set(groups)
        return instance

    def get_can_manage_plan(self, obj):
        request = self.context.get("request")
        return bool(request and can_manage_training_department(request.user, obj.department_id))

    def get_requires_service_confirmation(self, obj):
        return requires_service_confirmation(obj)

    def get_linked_service_id(self, obj):
        service = getattr(obj, "servicebook_entry", None)
        return service.id if service else None

    def get_linked_service_start(self, obj):
        service = getattr(obj, "servicebook_entry", None)
        return service.start if service else None


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
            "id",
            "revision",
            "status",
            "title",
            "description",
            "date",
            "start_time",
            "end_time",
            "location",
            "notes",
            "groups",
            "blocks",
        ]
