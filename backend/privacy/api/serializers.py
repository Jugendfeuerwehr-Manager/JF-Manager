from rest_framework import serializers

from jf_manager_backend.html_safety import SanitizedHTMLField
from privacy.models import ConsentKind, ConsentRecord, LegalPage, LegalPageVersion


def _person(user):
    return user.get_full_name() or user.username if user else ""


class LegalPageVersionSerializer(serializers.ModelSerializer):
    published_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LegalPageVersion
        fields = ["version", "title", "body", "change_note", "published_at", "published_by_name"]

    def get_published_by_name(self, obj):
        return _person(obj.published_by)


class LegalPageSerializer(serializers.ModelSerializer):
    draft_body = SanitizedHTMLField(allow_blank=True, required=False)
    label = serializers.CharField(source="get_kind_display", read_only=True)
    current_version = LegalPageVersionSerializer(read_only=True)
    has_unpublished_changes = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LegalPage
        fields = [
            "kind",
            "label",
            "draft_title",
            "draft_body",
            "updated_at",
            "updated_by_name",
            "current_version",
            "has_unpublished_changes",
        ]
        read_only_fields = ["kind", "updated_at"]

    def get_has_unpublished_changes(self, obj):
        current = obj.current_version
        return current is None or (current.title, current.body) != (obj.draft_title.strip(), obj.draft_body)

    def get_updated_by_name(self, obj):
        return _person(obj.updated_by)


class PublishSerializer(serializers.Serializer):
    change_note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class PublicLegalPageSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(source="page.kind")

    class Meta:
        model = LegalPageVersion
        fields = ["kind", "version", "title", "body", "published_at"]


class ConsentRecordSerializer(serializers.ModelSerializer):
    kind_label = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ConsentRecord
        fields = [
            "id",
            "kind",
            "kind_label",
            "status",
            "status_label",
            "source",
            "source_label",
            "text_version",
            "recorded_at",
            "recorded_by_name",
            "note",
        ]

    def get_kind_label(self, obj):
        labels = self.context.get("kind_labels")
        if labels is None:
            from privacy.services.consent import kind_labels

            labels = kind_labels()
        return labels.get(obj.kind, obj.kind)

    def get_recorded_by_name(self, obj):
        return _person(obj.recorded_by)


class ConsentCreateSerializer(serializers.Serializer):
    member = serializers.IntegerField(required=False)
    parent = serializers.IntegerField(required=False)
    user = serializers.IntegerField(required=False)
    kind = serializers.SlugRelatedField(slug_field="slug", queryset=ConsentKind.objects.all())
    status = serializers.ChoiceField(choices=ConsentRecord.Status.choices)
    text_version = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        # A withdrawal must stay possible after a kind was deactivated; new consents need an active kind.
        if attrs["status"] == ConsentRecord.Status.GRANTED and not attrs["kind"].active:
            raise serializers.ValidationError({"kind": "Diese Einwilligungsart ist deaktiviert."})
        return attrs


class ConsentKindSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentKind
        fields = ["id", "slug", "label", "description", "version", "in_portal", "active", "built_in", "position"]
        read_only_fields = ["id", "version", "built_in"]

    def validate_slug(self, value):
        if self.instance is not None and self.instance.built_in and value != self.instance.slug:
            raise serializers.ValidationError("Die Kennung einer mitgelieferten Einwilligungsart bleibt unverändert.")
        if (
            self.instance is not None
            and value != self.instance.slug
            and ConsentRecord.objects.filter(kind=self.instance.slug).exists()
        ):
            raise serializers.ValidationError(
                "Für diese Art gibt es schon Einwilligungen; die Kennung bleibt unverändert."
            )
        return value
