from rest_framework import serializers

from jf_manager_backend.html_safety import SanitizedHTMLField
from privacy.consent_kinds import CONSENT_KINDS
from privacy.models import ConsentRecord, LegalPage, LegalPageVersion


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
        return CONSENT_KINDS.get(obj.kind, obj.kind)

    def get_recorded_by_name(self, obj):
        return _person(obj.recorded_by)


class ConsentCreateSerializer(serializers.Serializer):
    member = serializers.IntegerField(required=False)
    parent = serializers.IntegerField(required=False)
    user = serializers.IntegerField(required=False)
    kind = serializers.ChoiceField(choices=list(CONSENT_KINDS))
    status = serializers.ChoiceField(choices=ConsentRecord.Status.choices)
    text_version = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
