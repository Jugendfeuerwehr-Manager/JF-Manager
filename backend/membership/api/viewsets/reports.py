from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from departments.mixins import DepartmentScopeViewSetMixin
from departments.models import Department
from jf_manager_backend.export_audit import ExportAuditMixin
from jf_manager_backend.mixins import BasePermissionedViewSet
from jf_manager_backend.renderers import PassthroughRenderer
from membership.api.serializers.reports import (
    AnnualReportSerializer,
    ManualSerializer,
    ReportQuerySerializer,
    StatisticsProfileSerializer,
)
from membership.models import AnnualReport, StatisticsProfile
from membership.services import annual_report
from membership.services.annual_report_export import build_workbook

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class AnnualReportViewSet(
    ExportAuditMixin,
    DepartmentScopeViewSetMixin,
    BasePermissionedViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = AnnualReport.objects.all()
    serializer_class = AnnualReportSerializer
    filterset_fields = ["department", "year", "state"]
    audited_export_actions = ("export",)

    def _department(self, request, data, permission):
        """The department named in the request, checked against the caller's rights there."""
        query = ReportQuerySerializer(data=data)
        query.is_valid(raise_exception=True)
        department = get_object_or_404(Department, pk=query.validated_data["department"])
        if not self._has_right_in_department(request.user, permission, department.pk):
            raise PermissionDenied("Keine Berechtigung für diese Abteilung.")
        return department, query.validated_data["year"]

    @extend_schema(summary="Report numbers for a department and year (stored if final, else computed)")
    # Reading is checked per requested department (the parameter is not a right on its own).
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def preview(self, request):
        department, year = self._department(request, request.query_params, "membership.view_annualreport")
        report, data = annual_report.report_for(department, year)
        return Response(
            {
                "state": report.state if report else "draft",
                "finalized_at": getattr(report, "finalized_at", None),
                "data": data,
            }
        )

    @extend_schema(summary="Save the values entered by hand (supervisors, activities)", request=ManualSerializer)
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def manual(self, request):
        department, year = self._department(request, request.data, "membership.change_annualreport")
        data = ManualSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        manual = {key: value for key, value in data.validated_data.items() if key not in ("department", "year")}
        annual_report.save_manual(department, year, manual)
        _, numbers = annual_report.report_for(department, year)
        return Response({"state": "draft", "data": numbers})

    @extend_schema(summary="Freeze and seal the report", request=ReportQuerySerializer)
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def finalize(self, request):
        department, year = self._department(request, request.data, "membership.finalize_annualreport")
        report = annual_report.finalize(department, year, by=request.user)
        return Response({"state": report.state, "finalized_at": report.finalized_at, "data": report.data})

    @extend_schema(summary="Excel copy of the report")
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], renderer_classes=[PassthroughRenderer])
    def export(self, request):
        department, year = self._department(request, request.query_params, "membership.view_annualreport")
        self.export_department_ids = [department.pk]
        _, data = annual_report.report_for(department, year)
        response = HttpResponse(build_workbook(data), content_type=XLSX)
        response["Content-Disposition"] = f'attachment; filename="jahresmeldung-{year}-{department.code}.xlsx"'
        return response


class StatisticsProfileViewSet(DepartmentScopeViewSetMixin, BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = StatisticsProfile.objects.select_related("department")
    serializer_class = StatisticsProfileSerializer
    filterset_fields = ["department"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        self._validate_target_department(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validate_target_department(serializer)
        serializer.save()
