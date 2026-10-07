"""Attendance evaluation for members and team (UX-04.2)."""

from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from departments.mixins import DepartmentScopeViewSetMixin
from servicebook.attendance_report import attendance_report, default_period
from servicebook.models import Service

from ..attendance_permissions import permitted_departments

ATTENDANCE_PERMISSIONS = ("servicebook.view_attendance", "servicebook.change_attendance")
MAX_PERIOD_DAYS = 5 * 366


class ReportPeriodSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        default_from, default_to = default_period()
        attrs.setdefault("date_to", default_to)
        attrs.setdefault("date_from", default_from)
        if attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError({"date_from": "Der Beginn muss vor dem Ende liegen."})
        if (attrs["date_to"] - attrs["date_from"]).days > MAX_PERIOD_DAYS:
            raise serializers.ValidationError({"date_from": "Der Zeitraum darf höchstens fünf Jahre umfassen."})
        return attrs


class AttendanceReportViewSet(DepartmentScopeViewSetMixin, viewsets.GenericViewSet):
    """Read-only evaluation over services the caller may see attendance for."""

    permission_classes = [IsAuthenticated]
    queryset = Service.objects.all()

    def list(self, request):
        period = ReportPeriodSerializer(data=request.query_params)
        period.is_valid(raise_exception=True)
        return Response(
            attendance_report(
                self._attendance_services(request.user),
                period.validated_data["date_from"],
                period.validated_data["date_to"],
            )
        )

    def _attendance_services(self, user):
        services = self.get_queryset()
        if user.is_superuser or any(user.has_perm(name) for name in ATTENDANCE_PERMISSIONS):
            return services
        allowed = set()
        for name in ATTENDANCE_PERMISSIONS:
            allowed.update(permitted_departments(user, name))
        if not allowed:
            raise PermissionDenied("Keine Berechtigung zum Anzeigen der Anwesenheit.")
        return services.filter(Q(department_id__in=allowed))
