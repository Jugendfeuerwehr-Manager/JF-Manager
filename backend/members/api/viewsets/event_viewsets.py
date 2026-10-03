"""
EventViewSet and EventTypeViewSet — member lifecycle event tracking.
"""

from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from departments.mixins import DepartmentScopeViewSetMixin
from jf_manager_backend.permissions import DepartmentRoleModelPermissions
from members.api_serializers import EventSerializer, EventTypeSerializer
from members.models import Event, EventType


class EventRolePermissions(DepartmentRoleModelPermissions):
    """Check an event against the departments of its actual member."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        required = self._required_permissions(request, view)
        if required is None:
            return False
        department_ids = set(obj.member.departments.values_list("id", flat=True))
        if not view._user_is_org_wide(user):
            department_ids &= set(view._user_department_ids(user))
        return any(
            all(user.has_perm(name) or name in self._department_role_permissions(request, department_id) for name in required)
            for department_id in department_ids
        )


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
        qs = EventType.objects.annotate(event_count=Count("event"))
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
    permission_classes = [IsAuthenticated, EventRolePermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["member", "type"]
    search_fields = ["member__name", "member__lastname", "notes", "type__name"]
    ordering_fields = ["datetime"]
    ordering = ["-datetime"]

    def get_queryset(self):
        user = self.request.user
        base_qs = Event.objects.select_related("member", "type").prefetch_related("member__departments")
        requested_dept = self._resolve_requested_department(user)
        org_wide = self._user_is_org_wide(user)
        if org_wide and requested_dept is None and user.has_perm("members.view_event"):
            return base_qs

        allowed_ids = {requested_dept} if requested_dept is not None else set(self._user_department_ids(user))
        if org_wide and requested_dept is None:
            allowed_ids = set(user.department_roles.values_list("department_id", flat=True))
        if self.request.method in ("GET", "HEAD", "OPTIONS") and not user.has_perm("members.view_event"):
            permitted_ids = set(
                user.department_roles.filter(
                    groups__permissions__content_type__app_label="members",
                    groups__permissions__codename="view_event",
                ).values_list("department_id", flat=True)
            )
            allowed_ids &= permitted_ids
        return base_qs.filter(member__departments__id__in=allowed_ids).distinct()
