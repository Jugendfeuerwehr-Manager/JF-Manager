from rest_framework import serializers

from external_sync.models import SyncBinding, SyncJob, SyncRun


class SyncJobListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    has_credentials = serializers.SerializerMethodField()

    class Meta:
        model = SyncJob
        fields = [
            "id",
            "name",
            "provider",
            "scope",
            "department",
            "department_name",
            "run_mode",
            "interval_minutes",
            "deletion_mode",
            "enabled",
            "has_credentials",
            "last_run_at",
            "next_run_at",
            "last_success_at",
            "last_error",
            "last_tested_at",
            "last_test_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_has_credentials(self, obj):
        return bool(obj.credentials)


class SyncJobDetailSerializer(SyncJobListSerializer):
    config = serializers.JSONField(required=False)
    credentials = serializers.JSONField(required=False, write_only=True)
    recent_runs = serializers.SerializerMethodField()

    class Meta(SyncJobListSerializer.Meta):
        fields = [*SyncJobListSerializer.Meta.fields, "config", "credentials", "recent_runs"]
        read_only_fields = [
            "id",
            "department_name",
            "has_credentials",
            "last_run_at",
            "next_run_at",
            "last_success_at",
            "last_error",
            "last_tested_at",
            "last_test_status",
            "created_at",
            "updated_at",
            "recent_runs",
        ]

    def get_recent_runs(self, obj):
        runs = obj.runs.all()[:5]
        return SyncRunSerializer(runs, many=True).data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        user = getattr(request, "user", None)

        scope = attrs.get("scope", getattr(self.instance, "scope", SyncJob.Scope.ORGANIZATION))
        department = attrs.get("department", getattr(self.instance, "department", None))
        provider = attrs.get("provider", getattr(self.instance, "provider", None))
        config = attrs.get("config")
        if config is None and self.instance is not None:
            config = self.instance.config or {}
        config = config or {}

        if provider == SyncJob.Provider.SPOND and not config.get("group_id"):
            raise serializers.ValidationError(
                {"config": "Für Spond muss eine Top-Level-Gruppe ausgewählt werden (config.group_id)."}
            )

        if not user or not user.is_authenticated:
            return attrs

        is_org_wide = user.is_staff or user.is_superuser or user.has_perm("departments.can_access_all_departments")
        allowed_department_ids = set(user.department_roles.values_list("department_id", flat=True))

        if scope == SyncJob.Scope.ORGANIZATION and not is_org_wide:
            raise serializers.ValidationError(
                {"scope": "Organisationsweite Jobs dürfen nur organisationsweit berechtigte Nutzer anlegen."}
            )

        if (
            scope == SyncJob.Scope.DEPARTMENT
            and department is not None
            and not is_org_wide
            and department.id not in allowed_department_ids
        ):
            raise serializers.ValidationError({"department": "Sie können nur Jobs für eigene Abteilungen verwalten."})

        return attrs


class SyncJobActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class SpondGroupsLookupSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(max_length=255)


class SpondTopLevelGroupSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class SyncRunSerializer(serializers.ModelSerializer):
    job_name = serializers.CharField(source="job.name", read_only=True)
    provider = serializers.CharField(source="job.provider", read_only=True)
    department = serializers.PrimaryKeyRelatedField(source="job.department", read_only=True)

    class Meta:
        model = SyncRun
        fields = [
            "id",
            "job",
            "job_name",
            "provider",
            "department",
            "status",
            "trigger",
            "summary",
            "imported_members",
            "imported_groups",
            "updated_members",
            "updated_groups",
            "flagged_for_review",
            "deleted_objects",
            "started_at",
            "finished_at",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields


class SyncBindingSerializer(serializers.ModelSerializer):
    job_name = serializers.CharField(source="job.name", read_only=True)

    class Meta:
        model = SyncBinding
        fields = [
            "id",
            "job",
            "job_name",
            "object_type",
            "external_id",
            "external_name",
            "is_deleted_in_source",
            "pending_garbage_collection",
            "override_local_changes",
            "managed_fields",
            "last_seen_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
