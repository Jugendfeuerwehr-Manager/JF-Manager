import json

from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from external_sync.api.serializers import (
    SpondGroupsLookupSerializer,
    SpondTopLevelGroupSerializer,
    SyncBindingSerializer,
    SyncJobActionSerializer,
    SyncJobDetailSerializer,
    SyncJobListSerializer,
    SyncRunSerializer,
)
from external_sync.models import SyncJob, SyncRun
from external_sync.services import ProviderNotImplementedError, get_provider
from jf_manager_backend.permissions import DepartmentRoleModelPermissions


class ExternalSyncScopeMixin:
    def _user_is_org_wide(self, user):
        return user.is_staff or user.is_superuser or user.has_perm("departments.can_access_all_departments")

    def _user_department_ids(self, user):
        return list(user.department_roles.values_list("department_id", flat=True))


class SyncJobViewSet(ExternalSyncScopeMixin, viewsets.ModelViewSet):
    queryset = SyncJob.objects.select_related("department", "created_by").prefetch_related("runs")
    lookup_value_regex = r"\d+"
    permission_classes = [IsAuthenticated, DepartmentRoleModelPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["provider", "scope", "department", "run_mode", "enabled", "deletion_mode"]
    search_fields = ["name", "provider"]
    ordering_fields = ["name", "created_at", "updated_at", "last_run_at", "next_run_at"]
    ordering = ["name"]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if self._user_is_org_wide(user):
            department_id = self.request.query_params.get("department")
            if department_id:
                return queryset.filter(department_id=department_id)
            return queryset

        allowed_department_ids = self._user_department_ids(user)
        return queryset.filter(department_id__in=allowed_department_ids)

    def get_serializer_class(self):
        if self.action in {"list"}:
            return SyncJobListSerializer
        if self.action in {"spond_top_level_groups"}:
            return SpondGroupsLookupSerializer
        if self.action in {"run_now", "test_connection", "garbage_collection_preview", "garbage_collect"}:
            return SyncJobActionSerializer
        return SyncJobDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def _json_safe_summary(self, payload):
        """Convert provider payload to JSON-safe data for JSONField storage."""
        return json.loads(json.dumps(payload, cls=DjangoJSONEncoder))

    def _record_failed_run(self, job, user, trigger, error_message):
        now = timezone.now()
        run = SyncRun.objects.create(
            job=job,
            triggered_by=user,
            status=SyncRun.Status.FAILED,
            trigger=trigger,
            started_at=now,
            finished_at=now,
            error_message=error_message,
            summary={"provider": job.provider, "implemented": False},
        )
        job.last_run_at = now
        job.last_error = error_message
        job.save(update_fields=["last_run_at", "last_error", "updated_at"])
        return run

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        job = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job.last_tested_at = timezone.now()

        try:
            provider = get_provider(job.provider)
            result = provider.test_connection(job)
            job.last_test_status = bool(result.get("ok"))
            job.last_error = "" if job.last_test_status else result.get("message", "")
            job.save(update_fields=["last_tested_at", "last_test_status", "last_error", "updated_at"])
            return Response(result)
        except ProviderNotImplementedError as exc:
            job.last_test_status = False
            job.last_error = str(exc)
            job.save(update_fields=["last_tested_at", "last_test_status", "last_error", "updated_at"])
            return Response({"ok": False, "detail": str(exc)}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=["post"])
    def run_now(self, request, pk=None):
        job = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            provider = get_provider(job.provider)
            result = provider.run(job=job, triggered_by=request.user)
            summary = self._json_safe_summary(result)
            run = SyncRun.objects.create(
                job=job,
                triggered_by=request.user,
                status=SyncRun.Status.SUCCEEDED,
                trigger="manual",
                started_at=result.get("started_at", timezone.now()),
                finished_at=result.get("finished_at", timezone.now()),
                summary=summary,
                imported_members=result.get("imported_members", 0),
                imported_groups=result.get("imported_groups", 0),
                updated_members=result.get("updated_members", 0),
                updated_groups=result.get("updated_groups", 0),
                flagged_for_review=result.get("flagged_for_review", 0),
                deleted_objects=result.get("deleted_objects", 0),
            )
            job.last_run_at = run.finished_at
            job.last_success_at = run.finished_at
            job.last_error = ""
            job.save(update_fields=["last_run_at", "last_success_at", "last_error", "updated_at"])
            return Response(SyncRunSerializer(run).data, status=status.HTTP_201_CREATED)
        except ProviderNotImplementedError as exc:
            run = self._record_failed_run(job, request.user, "manual", str(exc))
            return Response(SyncRunSerializer(run).data, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=False, methods=["post"], url_path="spond-top-level-groups")
    def spond_top_level_groups(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            provider = get_provider("spond")
            groups = provider.list_top_level_groups(credentials=serializer.validated_data)
            return Response({"results": SpondTopLevelGroupSerializer(groups, many=True).data})
        except ProviderNotImplementedError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=True, methods=["get"], url_path="garbage-collection-preview")
    def garbage_collection_preview(self, request, pk=None):
        job = self.get_object()
        bindings = job.bindings.filter(is_deleted_in_source=True, pending_garbage_collection=True).order_by(
            "object_type", "external_name", "external_id"
        )
        return Response(
            {
                "job": job.id,
                "pending_count": bindings.count(),
                "items": SyncBindingSerializer(bindings[:100], many=True).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="garbage-collect")
    def garbage_collect(self, request, pk=None):
        job = self.get_object()
        bindings = job.bindings.filter(is_deleted_in_source=True, pending_garbage_collection=True)
        deleted_count = bindings.count()
        bindings.delete()
        return Response({"job": job.id, "deleted_count": deleted_count})


class SyncRunViewSet(ExternalSyncScopeMixin, viewsets.ReadOnlyModelViewSet):
    queryset = SyncRun.objects.select_related("job", "job__department", "triggered_by")
    lookup_value_regex = r"\d+"
    serializer_class = SyncRunSerializer
    permission_classes = [IsAuthenticated, DepartmentRoleModelPermissions]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["job", "status", "trigger", "job__provider", "job__department"]
    ordering_fields = ["created_at", "started_at", "finished_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if self._user_is_org_wide(user):
            return queryset

        allowed_department_ids = self._user_department_ids(user)
        return queryset.filter(job__department_id__in=allowed_department_ids)
