"""
EventViewSet and EventTypeViewSet — member lifecycle event tracking.
"""

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from departments.mixins import DepartmentScopeViewSetMixin
from jf_manager_backend.permissions import DepartmentRoleModelPermissions
from members.api_serializers import EventSerializer, EventTypeSerializer
from members.models import Event, EventType


@extend_schema_view(
    list=extend_schema(summary="List all event types"),
    retrieve=extend_schema(summary="Get event type details"),
    create=extend_schema(summary="Create new event type"),
    update=extend_schema(summary="Update event type"),
    partial_update=extend_schema(summary="Partially update event type"),
    destroy=extend_schema(summary="Delete event type"),
)
class EventTypeViewSet(DepartmentScopeViewSetMixin, viewsets.ModelViewSet):
    queryset = EventType.objects.all()
    serializer_class = EventTypeSerializer
    permission_classes = [IsAuthenticated, DepartmentRoleModelPermissions]
    include_central_records = True
    ordering = ["name"]

    def get_queryset(self):
        """
        Keep global (department=NULL) event types visible even when an org-wide
        user selects a concrete active department.
        """
        user = self.request.user
        qs = EventType.objects.all()
        requested_dept = self._resolve_requested_department(user)

        if self._user_is_org_wide(user):
            if requested_dept is not None:
                return qs.filter(Q(department_id=requested_dept) | Q(department__isnull=True)).order_by("name")
            return qs.order_by("name")

        # Department-scoped users keep central + allowed departments.
        allowed_ids = self._user_department_ids(user)
        if requested_dept is not None:
            return qs.filter(Q(department_id=requested_dept) | Q(department__isnull=True)).order_by("name")

        return qs.filter(Q(department_id__in=allowed_ids) | Q(department__isnull=True)).order_by("name")


@extend_schema_view(
    list=extend_schema(summary="List all events"),
    retrieve=extend_schema(summary="Get event details"),
    create=extend_schema(summary="Create new event"),
    update=extend_schema(summary="Update event"),
    partial_update=extend_schema(summary="Partially update event"),
    destroy=extend_schema(summary="Delete event"),
)
class EventViewSet(DepartmentScopeViewSetMixin, viewsets.ModelViewSet):
    queryset = Event.objects.select_related("member", "type").order_by("-datetime")
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated, DepartmentRoleModelPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["member", "type"]
    search_fields = ["member__name", "member__lastname", "notes", "type__name"]
    ordering_fields = ["datetime"]
    ordering = ["-datetime"]

    def get_queryset(self):
        user = self.request.user
        base_qs = Event.objects.select_related("member", "type").prefetch_related("member__departments")

        if self._user_is_org_wide(user):
            requested_dept = self._resolve_requested_department(user)
            if requested_dept is not None:
                return base_qs.filter(member__departments__id=requested_dept).distinct()
            return base_qs

        requested_dept = self._resolve_requested_department(user)
        if requested_dept is not None:
            return base_qs.filter(member__departments__id=requested_dept).distinct()

        allowed_ids = self._user_department_ids(user)
        return base_qs.filter(member__departments__id__in=allowed_ids).distinct()
