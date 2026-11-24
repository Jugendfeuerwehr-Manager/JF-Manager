from rest_framework import serializers

from admissions.models import AdmissionForm, AdmissionFormVersion, AdmissionTextBlock
from admissions.schema import check_structure
from admissions.services import forms as form_service
from jf_manager_backend.html_safety import sanitize_rich_html
from members.models import Status

INITIAL_CATEGORIES = (Status.Category.APPLICANT, Status.Category.TRIAL, Status.Category.ACTIVE)


class AdmissionFormVersionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionFormVersion
        fields = ["id", "version", "title", "schema_hash", "change_note", "published_at"]


class AdmissionFormVersionSerializer(AdmissionFormVersionSummarySerializer):
    class Meta(AdmissionFormVersionSummarySerializer.Meta):
        fields = [*AdmissionFormVersionSummarySerializer.Meta.fields, "intro", "signature_mode", "schema"]


class AdmissionFormSerializer(serializers.ModelSerializer):
    from_template = serializers.BooleanField(write_only=True, required=False, default=True)
    current_version = AdmissionFormVersionSummarySerializer(read_only=True)
    draft_issues = serializers.SerializerMethodField()
    has_unpublished_changes = serializers.SerializerMethodField()

    class Meta:
        model = AdmissionForm
        fields = [
            "id",
            "department",
            "title",
            "intro",
            "initial_status",
            "signature_mode",
            "decision_body",
            "is_active",
            "access",
            "public_slug",
            "public_departments",
            "draft_schema",
            "draft_issues",
            "has_unpublished_changes",
            "current_version",
            "from_template",
            "updated_at",
        ]
        read_only_fields = ["id", "public_slug", "updated_at"]
        extra_kwargs = {
            "draft_schema": {"required": False},
            # Explicit: null is an organisation form, never a guessed department.
            "department": {"required": True, "allow_null": True},
            "public_departments": {"required": False},
        }

    def get_draft_issues(self, form):
        return form_service.draft_issues(form)

    def get_has_unpublished_changes(self, form):
        version = form.current_version
        if version is None:
            return True
        frozen, _ = form_service.snapshot(form.draft_schema, form.department_id)
        content = {"title": form.title, "intro": form.intro, "signature_mode": form.signature_mode, "schema": frozen}
        return form_service.canonical_hash(content) != version.schema_hash

    def validate_draft_schema(self, schema):
        errors = check_structure(schema)
        if errors:
            raise serializers.ValidationError(errors)
        return form_service.sanitize_draft(schema)

    def validate(self, attrs):
        department = attrs["department"] if "department" in attrs else getattr(self.instance, "department", None)
        if any(not choice.is_active for choice in attrs.get("public_departments") or []):
            raise serializers.ValidationError({"public_departments": "Nur aktive Abteilungen sind auswählbar."})
        if department is not None and attrs.get("public_departments"):
            # A department form always delivers to its own department.
            attrs["public_departments"] = []
        status = attrs.get("initial_status")
        if status is None:
            return attrs
        if status.category not in INITIAL_CATEGORIES:
            raise serializers.ValidationError({"initial_status": "Nur Antrag, Probezeit oder Aktiv sind möglich."})
        if status.department_id not in (None, getattr(department, "pk", None)):
            raise serializers.ValidationError({"initial_status": "Der Status gehört zu einer anderen Abteilung."})
        return attrs

    def create(self, validated_data):
        from_template = validated_data.pop("from_template", True)
        public_departments = validated_data.pop("public_departments", None)
        form = form_service.create_form(
            department=validated_data.pop("department"),
            title=validated_data.pop("title"),
            from_template=from_template,
            by=self.context["request"].user,
        )
        if public_departments is not None:
            validated_data["public_departments"] = public_departments
        return self.update(form, validated_data) if validated_data else form

    def update(self, instance, validated_data):
        validated_data.pop("from_template", None)
        validated_data["updated_by"] = self.context["request"].user
        form = super().update(instance, validated_data)
        if form.access == AdmissionForm.Access.PUBLIC and not form.public_slug:
            form.public_slug = form_service.new_public_slug(form.title)
            form.save(update_fields=["public_slug"])
        return form


class PublishSerializer(serializers.Serializer):
    change_note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class AdmissionTextBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionTextBlock
        fields = ["id", "department", "title", "body", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def validate_body(self, body):
        return sanitize_rich_html(body)
