"""Serializers for TrainingBlock."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from inventory.models import Item, ItemVariant
from jf_manager_backend.html_safety import SanitizedHTMLField, sanitize_rich_html
from members.models import Group
from training.api.permissions import can_manage_training_department
from training.api.validation import validate_block_times, validate_session_times
from training.copying import copied_files, copy_owned_files, eligible_instructors
from training.models import TrainingBlock, TrainingBlockMaterial, TrainingMedia

from .library_block import TrainingMediaSerializer


def validate_block_target(serializer, attrs):
    session = attrs.get("session", getattr(serializer.instance, "session", None))
    if session is not None:
        duration = validate_session_times(session.start_time, session.end_time)
        offset = attrs.get("start_offset_minutes", getattr(serializer.instance, "start_offset_minutes", 0))
        length = attrs.get("duration_minutes", getattr(serializer.instance, "duration_minutes", 15))
        validate_block_times(offset, length, duration)
    request = serializer.context.get("request")
    if request is None:
        return attrs
    session = attrs.get("session", getattr(serializer.instance, "session", None))
    if session is None or not can_manage_training_department(request.user, session.department_id):
        raise serializers.ValidationError({"session": "Keine Schreibberechtigung für die Zielübung."})

    groups = attrs.get("groups")
    if groups is None:
        groups = serializer.instance.groups.all() if serializer.instance is not None else []
    if any(group.department_id != session.department_id for group in groups):
        raise serializers.ValidationError({"groups": "Gruppen müssen zur Übungsabteilung gehören."})
    instructors = attrs.get("instructors")
    if instructors is not None:
        ids = {user.pk for user in instructors}
        allowed = set(
            eligible_instructors(get_user_model().objects.filter(pk__in=ids), session.department_id).values_list(
                "pk", flat=True
            )
        )
        if ids - allowed:
            raise serializers.ValidationError(
                {"instructor_ids": "Ausbilder benötigen ein aktives Konto mit Rolle in der Übungsabteilung."}
            )
    for index, material in enumerate(attrs.get("materials") or []):
        item = material.get("item")
        if item is not None and item.department_id not in (None, session.department_id):
            raise serializers.ValidationError(
                {"materials": {index: "Material muss zur Übungsabteilung gehören oder abteilungsübergreifend sein."}}
            )
    return attrs


class InstructorMiniSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ["id", "name"]

    def get_name(self, obj):
        return obj.get_full_name() or obj.username


class MaterialSerializer(serializers.ModelSerializer):
    """Item/variant need with quantity, or free text. Never books stock."""

    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all(), allow_null=True, required=False)
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ItemVariant.objects.select_related("parent_item"), allow_null=True, required=False
    )
    quantity = serializers.IntegerField(min_value=1, max_value=100000, default=1)
    label = serializers.CharField(max_length=200, required=False, allow_blank=True)

    class Meta:
        model = TrainingBlockMaterial
        fields = ["id", "item", "variant", "quantity", "label"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        item, variant = attrs.get("item"), attrs.get("variant")
        if variant is not None:
            if item is not None and variant.parent_item_id != item.pk:
                raise serializers.ValidationError({"variant": "Die Variante gehört zu einem anderen Artikel."})
            attrs["item"] = item = variant.parent_item
        label = (attrs.get("label") or "").strip()
        if not label:
            label = str(variant) if variant is not None else (item.name if item is not None else "")
        if not label:
            raise serializers.ValidationError({"label": "Artikel wählen oder Bezeichnung angeben."})
        attrs["label"] = label
        return attrs


def save_resources(block, instructors, materials):
    if instructors is not None:
        block.instructors.set(instructors)
    if materials is not None:
        block.materials.all().delete()
        TrainingBlockMaterial.objects.bulk_create(TrainingBlockMaterial(block=block, **row) for row in materials)


class GroupMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class TrainingBlockSerializer(serializers.ModelSerializer):
    content = SanitizedHTMLField(required=False, allow_blank=True)
    groups = GroupMiniSerializer(many=True, read_only=True)
    library_block_title = serializers.CharField(source="library_block.title", read_only=True, default=None)
    media = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    instructors = InstructorMiniSerializer(many=True, read_only=True)
    materials = MaterialSerializer(many=True, read_only=True)

    class Meta:
        model = TrainingBlock
        fields = [
            "id",
            "title",
            "content",
            "session",
            "kind",
            "location",
            "learning_objective",
            "safety_notes",
            "instructors",
            "materials",
            "groups",
            "library_block",
            "library_block_title",
            "duration_minutes",
            "start_offset_minutes",
            "position_order",
            "color",
            "nextcloud_folder_url",
            "created_at",
            "updated_at",
            "media",
            "attachments",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        return validate_block_target(self, super().validate(attrs))

    def get_media(self, obj):
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(obj)
        qs = TrainingMedia.objects.filter(content_type=ct, object_id=obj.pk)
        return TrainingMediaSerializer(qs, many=True, context=self.context).data

    def get_attachments(self, obj):
        from django.contrib.contenttypes.models import ContentType

        from members.api.serializers import AttachmentSerializer
        from members.models import Attachment

        ct = ContentType.objects.get_for_model(obj)
        qs = Attachment.objects.filter(content_type=ct, object_id=obj.pk)
        return AttachmentSerializer(qs, many=True, context=self.context).data


class TrainingBlockCreateSerializer(serializers.ModelSerializer):
    content = SanitizedHTMLField(required=False, allow_blank=True)
    group_ids = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        source="groups",
        many=True,
        required=False,
    )
    instructor_ids = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), source="instructors", many=True, required=False
    )
    materials = MaterialSerializer(many=True, required=False)

    class Meta:
        model = TrainingBlock
        fields = [
            "id",
            "title",
            "content",
            "session",
            "kind",
            "location",
            "learning_objective",
            "safety_notes",
            "instructor_ids",
            "materials",
            "group_ids",
            "library_block",
            "duration_minutes",
            "start_offset_minutes",
            "position_order",
            "color",
            "nextcloud_folder_url",
        ]

    def validate(self, attrs):
        if len(attrs.get("materials") or []) > 50:
            raise serializers.ValidationError({"materials": "Höchstens 50 Materialpositionen je Baustein."})
        return validate_block_target(self, super().validate(attrs))

    def update(self, instance, validated_data):
        instructors = validated_data.pop("instructors", None)
        materials = validated_data.pop("materials", None)
        groups = validated_data.pop("groups", None)
        instance = super().update(instance, validated_data)
        if groups is not None:
            instance.groups.set(groups)
        save_resources(instance, instructors, materials)
        return instance

    def create(self, validated_data):
        instructors = validated_data.pop("instructors", None)
        materials = validated_data.pop("materials", None)
        groups = validated_data.pop("groups", [])
        # If library_block supplied with no content, copy content from it
        library_block = validated_data.get("library_block")
        if library_block and not validated_data.get("content"):
            validated_data["content"] = sanitize_rich_html(library_block.content)
        if library_block and not validated_data.get("color"):
            validated_data["color"] = library_block.color
        block = super().create(validated_data)
        block.groups.set(groups)
        save_resources(block, instructors, materials)
        if library_block:
            # The planned block owns its images/attachments; later library edits or
            # deletions never change or break it.
            request = self.context.get("request")
            user = getattr(request, "user", None)
            files = self.context.get("copied_files")
            if files is None:
                with copied_files() as files:
                    copy_owned_files(library_block, block, user, files, referenced_only=True)
            else:
                copy_owned_files(library_block, block, user, files, referenced_only=True)
        return block


class TrainingBlockMoveSerializer(serializers.ModelSerializer):
    """Minimal serializer for drag-and-drop position updates."""

    class Meta:
        model = TrainingBlock
        fields = ["start_offset_minutes", "position_order", "duration_minutes", "groups"]

    groups = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        many=True,
        required=False,
    )

    def validate(self, attrs):
        return validate_block_target(self, super().validate(attrs))

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        instance = super().update(instance, validated_data)
        if groups is not None:
            instance.groups.set(groups)
        return instance
