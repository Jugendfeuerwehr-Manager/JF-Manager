from rest_framework import serializers

from admissions.models import AdmissionDecision, Application, CommitteeMeeting
from jf_manager_backend.private_media import private_media_url


class AdmissionDecisionSerializer(serializers.ModelSerializer):
    outcome_label = serializers.CharField(source="get_outcome_display", read_only=True)
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AdmissionDecision
        fields = [
            "id",
            "meeting",
            "body",
            "decided_on",
            "outcome",
            "outcome_label",
            "votes_yes",
            "votes_no",
            "votes_abstain",
            "note",
            "recorded_by_name",
            "recorded_at",
        ]
        read_only_fields = fields

    def get_recorded_by_name(self, decision):
        user = decision.recorded_by
        return (user.get_full_name() or user.username) if user else ""


class ApplicationListSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    form_title = serializers.CharField(source="form_version.title", read_only=True)
    form_version_number = serializers.IntegerField(source="form_version.version", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "department",
            "applicant_name",
            "status",
            "status_label",
            "form_title",
            "form_version_number",
            "submitted_at",
            "member",
        ]
        read_only_fields = fields


class ApplicationDetailSerializer(ApplicationListSerializer):
    schema = serializers.JSONField(source="form_version.schema", read_only=True)
    signature_mode = serializers.CharField(source="form_version.signature_mode", read_only=True)
    decision_body = serializers.CharField(source="form_version.form.decision_body", read_only=True)
    decisions = AdmissionDecisionSerializer(many=True, read_only=True)
    files = serializers.SerializerMethodField()

    class Meta(ApplicationListSerializer.Meta):
        fields = [
            *ApplicationListSerializer.Meta.fields,
            "answers",
            "schema",
            "signature_mode",
            "decision_body",
            "decisions",
            "files",
            "taken_over_at",
        ]
        read_only_fields = fields

    def get_files(self, application):
        request = self.context.get("request")
        return {
            item.key: {
                "kind": item.kind,
                "sha256": item.sha256,
                "url": private_media_url("admission-file", item.pk, request),
            }
            for item in application.files.all()
        }


class DecisionInputSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=AdmissionDecision.Outcome.choices)
    decided_on = serializers.DateField(required=False)
    meeting = serializers.PrimaryKeyRelatedField(
        queryset=CommitteeMeeting.objects.all(), required=False, allow_null=True
    )
    votes_yes = serializers.IntegerField(min_value=0, max_value=999, required=False, allow_null=True)
    votes_no = serializers.IntegerField(min_value=0, max_value=999, required=False, allow_null=True)
    votes_abstain = serializers.IntegerField(min_value=0, max_value=999, required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)

    def validate(self, attrs):
        if not attrs.get("meeting") and not attrs.get("decided_on"):
            raise serializers.ValidationError({"decided_on": "Bitte Sitzung oder Beschlussdatum angeben."})
        return attrs


class BulkDecisionSerializer(DecisionInputSerializer):
    applications = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=100)


class TakeOverSerializer(serializers.Serializer):
    joined = serializers.DateField(required=False)
    parent_links = serializers.DictField(child=serializers.IntegerField(allow_null=True), required=False, default=dict)
    invite_parents = serializers.BooleanField(required=False, default=False)


class CommitteeMeetingSerializer(serializers.ModelSerializer):
    decision_count = serializers.IntegerField(source="decisions.count", read_only=True)

    class Meta:
        model = CommitteeMeeting
        fields = ["id", "department", "body", "date", "protocol_ref", "note", "decision_count", "created_at"]
        read_only_fields = ["id", "decision_count", "created_at"]
