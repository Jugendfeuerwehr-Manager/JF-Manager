"""Service viewsets with statistics and filtering."""

from django.core.cache import cache
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from departments.mixins import DepartmentScopeViewSetMixin
from jf_manager_backend.permissions import DepartmentRoleModelPermissions
from portal.permissions import StaffAccountRequired
from servicebook.models import Attendance, Service
from servicebook.selectors import get_top_lists_by_state

from ..attendance_permissions import filter_by_permission, has_department_permission
from ..serializers import (
    ServiceCreateSerializer,
    ServiceDetailSerializer,
    ServiceListSerializer,
    ServiceUpdateSerializer,
)


class ServiceViewSet(DepartmentScopeViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing services with attendance tracking.

    Provides:
    - Standard CRUD operations
    - Filtering by topic, place, date range, operations_manager
    - Search by topic, description, place
    - Statistics endpoints for attendance summaries
    """

    permission_classes = [IsAuthenticated, DepartmentRoleModelPermissions]
    queryset = Service.objects.all()  # Base queryset for router registration
    serializer_class = ServiceDetailSerializer  # Default serializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # Range lookups drive the upcoming/past split and the today card in the list view.
    filterset_fields = {
        "topic": ["exact"],
        "place": ["exact"],
        "operations_manager": ["exact"],
        "start": ["exact", "gte", "lte"],
        "end": ["exact", "gte", "lte"],
    }
    search_fields = ["topic", "description", "events", "place"]
    ordering_fields = ["start", "end", "topic"]
    ordering = ["-start"]

    def get_queryset(self):
        """Get services filtered by department scope."""
        self.queryset = Service.objects.select_related("training_session").prefetch_related("operations_manager")
        queryset = super().get_queryset()
        if self.action in ("attendance_board", "staff_statistics", "registrations", "apply_excused"):
            # These actions enforce attendance rights instead of service rights.
            return queryset
        permission = {
            "create": "servicebook.add_service",
            "update": "servicebook.change_service",
            "partial_update": "servicebook.change_service",
            "destroy": "servicebook.delete_service",
        }.get(self.action, "servicebook.view_service")
        return filter_by_permission(queryset, self.request.user, permission)

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            return ServiceListSerializer
        elif self.action == "create":
            return ServiceCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ServiceUpdateSerializer
        return ServiceDetailSerializer

    def create(self, request, *args, **kwargs):
        """Create service and return detailed response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from rest_framework.exceptions import PermissionDenied

        department = serializer.validated_data.get("department")
        department_id = department.pk if department else self._resolve_requested_department(request.user)
        if department_id is None and not self._user_is_org_wide(request.user):
            assigned = self._user_department_ids(request.user)
            department_id = assigned[0] if len(assigned) == 1 else None
        if not has_department_permission(request.user, "servicebook.add_service", department_id):
            raise PermissionDenied("Keine Berechtigung zum Anlegen in dieser Abteilung.")
        if department is None and department_id is not None:
            from departments.models import Department

            serializer.validated_data["department"] = Department.objects.get(pk=department_id)
        service = self.perform_create(serializer)

        # Use DetailSerializer for response to include all fields including id
        detail_serializer = ServiceDetailSerializer(service)
        headers = self.get_success_headers(detail_serializer.data)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """
        Get overall servicebook statistics.

        Returns:
        - Total services count
        - Recent services summary
        - Top attendance lists (most present, excused, absent)
        """
        services = self.get_queryset()
        services_count = services.count()
        recent_services = services.order_by("-start")[:5]

        # Get top lists
        top_present = get_top_lists_by_state("A", max_entries=7, services=services)
        top_excused = get_top_lists_by_state("E", max_entries=7, services=services)
        top_absent = get_top_lists_by_state("F", max_entries=7, services=services)

        return Response(
            {
                "total_services": services_count,
                "recent_services": ServiceListSerializer(recent_services, many=True).data,
                "top_lists": {
                    "most_present": list(top_present),
                    "most_excused": list(top_excused),
                    "most_absent": list(top_absent),
                },
            }
        )

    @action(detail=False, methods=["get"])
    def attendance_chart(self, request):
        """
        Get attendance data for chart visualization.

        Returns time-series data of attendance across services.
        """
        from servicebook.selectors import get_attendance_over_time_data

        chart_data = get_attendance_over_time_data(services=self.get_queryset())
        return Response(chart_data)

    @action(detail=True, methods=["get"])
    def attendance_summary(self, request, pk=None):
        """
        Get detailed attendance summary for a specific service.

        Returns:
        - Counts by state (A, E, F)
        - List of attendees with their status
        """
        service = self.get_object()

        # Get attendance summary
        attendance_counts = Attendance.objects.filter(service=service).values("state").annotate(count=Count("id"))
        counts = {"A": 0, "E": 0, "F": 0}
        for item in attendance_counts:
            counts[item["state"]] = item["count"]

        # Get all attendees with status
        attendances = Attendance.objects.filter(service=service).select_related("person")
        attendees = [
            {
                "id": att.person.id,
                "name": att.person.name,
                "lastname": att.person.lastname,
                "full_name": att.person.get_full_name(),
                "state": att.state,
                "state_display": att.get_state_display(),
                "attendance_id": att.id,
            }
            for att in attendances
        ]

        return Response(
            {
                "summary": {
                    "present": counts["A"],
                    "excused": counts["E"],
                    "absent": counts["F"],
                    "total": sum(counts.values()),
                },
                "attendees": attendees,
            }
        )

    @action(detail=True, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def attendance_board(self, request, pk=None):
        from rest_framework.exceptions import PermissionDenied

        from ..attendance_board import board_response, update_board

        service = self.get_object()
        if not (
            has_department_permission(request.user, "servicebook.view_attendance", service.department_id)
            or has_department_permission(request.user, "servicebook.change_attendance", service.department_id)
        ):
            raise PermissionDenied("Keine Berechtigung zum Anzeigen der Anwesenheit.")
        if request.method == "PATCH":
            return update_board(request, service)
        return board_response(service)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated, StaffAccountRequired, DepartmentRoleModelPermissions],
    )
    def overview(self, request):
        """Mobile list: today, the next 14 days and past services with incomplete attendance."""
        from ..registrations import overview_payload

        return Response(overview_payload(self.get_queryset()))

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated, StaffAccountRequired])
    def registrations(self, request, pk=None):
        from ..registrations import registrations_payload

        service = self.get_object()
        if not (
            has_department_permission(request.user, "servicebook.view_attendance", service.department_id)
            or has_department_permission(request.user, "servicebook.change_attendance", service.department_id)
        ):
            raise PermissionDenied("Keine Berechtigung zum Anzeigen der Anwesenheit.")
        return Response(registrations_payload(service, request.user))

    @action(
        detail=True,
        methods=["post"],
        url_path="registrations/apply-excused",
        permission_classes=[IsAuthenticated, StaffAccountRequired],
    )
    def apply_excused(self, request, pk=None):
        from ..registrations import ApplyExcusedSerializer, apply_excused

        service = self.get_object()
        if not has_department_permission(request.user, "servicebook.change_attendance", service.department_id):
            raise PermissionDenied("Keine Berechtigung zum Bearbeiten der Anwesenheit.")
        data = ApplyExcusedSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(
            apply_excused(
                service, dry_run=data.validated_data["dry_run"], member_ids=data.validated_data.get("member_ids")
            )
        )

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def staff_statistics(self, request):
        from rest_framework.exceptions import PermissionDenied

        from ..attendance_board import staff_report

        if not (
            request.user.is_superuser
            or request.user.has_perm("servicebook.view_attendance")
            or request.user.has_perm("servicebook.change_attendance")
            or request.user.department_roles.filter(
                groups__permissions__content_type__app_label="servicebook",
                groups__permissions__codename__in=["view_attendance", "change_attendance"],
            ).exists()
        ):
            raise PermissionDenied("Keine Berechtigung zum Anzeigen der Anwesenheit.")
        from rest_framework import serializers

        class DateRange(serializers.Serializer):
            date_from = serializers.DateField(required=False)
            date_to = serializers.DateField(required=False)

        dates = DateRange(data=request.query_params)
        dates.is_valid(raise_exception=True)
        services = self.filter_queryset(self.get_queryset())
        if not request.user.is_superuser and not request.user.has_perm("servicebook.view_attendance") and not request.user.has_perm("servicebook.change_attendance"):
            from django.db.models import Q

            allowed = request.user.department_roles.filter(
                groups__permissions__codename__in=["view_attendance", "change_attendance"],
                groups__permissions__content_type__app_label="servicebook",
            ).values_list("department_id", flat=True)
            services = services.filter(Q(department_id__in=allowed))
        if dates.validated_data.get("date_from"):
            services = services.filter(start__date__gte=dates.validated_data["date_from"])
        if dates.validated_data.get("date_to"):
            services = services.filter(start__date__lte=dates.validated_data["date_to"])
        return staff_report(services)

    def perform_create(self, serializer):
        """Handle service creation and clear cache."""
        service = serializer.save()
        # Clear attendance cache when new service is created
        cache.delete("attendance_over_time_data")
        return service

    def perform_update(self, serializer):
        """Handle service update and clear cache."""
        from rest_framework.exceptions import PermissionDenied

        department = serializer.validated_data.get("department", serializer.instance.department)
        if not has_department_permission(self.request.user, "servicebook.change_service", department.pk if department else None):
            raise PermissionDenied("Keine Berechtigung zum Verschieben in diese Abteilung.")
        service = serializer.save()
        # Clear attendance cache when service is updated
        cache.delete("attendance_over_time_data")
        return service

    def perform_destroy(self, instance):
        """Handle service deletion and clear cache."""
        instance.delete()
        # Clear attendance cache when service is deleted
        cache.delete("attendance_over_time_data")
