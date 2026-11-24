from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from admissions.api.serializers.vouchers import AdmissionVoucherCreateSerializer, AdmissionVoucherSerializer
from admissions.models import AdmissionForm, AdmissionVoucher
from admissions.services import vouchers as voucher_service
from departments.mixins import DepartmentScopeViewSetMixin
from jf_manager_backend.mixins import BasePermissionedViewSet


@extend_schema_view(list=extend_schema(summary="Vouchers of the visible departments (the code itself is never listed)"))
class AdmissionVoucherViewSet(
    DepartmentScopeViewSetMixin,
    BasePermissionedViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = AdmissionVoucher.objects.select_related("form", "application")
    serializer_class = AdmissionVoucherSerializer
    filterset_fields = ["form", "department"]
    search_fields = ["label", "code_hint"]

    @extend_schema(
        summary="Create a voucher; the response is the only place the code appears",
        request=AdmissionVoucherCreateSerializer,
    )
    def create(self, request):
        data = AdmissionVoucherCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        form = get_object_or_404(AdmissionForm, pk=values["form"])
        department_id = form.department_id or values["department"]
        if department_id is None:
            raise ValidationError({"department": "Bitte die Abteilung wählen, an die der Antrag geht."})
        if form.department_id is not None and values["department"] not in (None, form.department_id):
            raise ValidationError({"department": "Dieses Formular gehört zu einer anderen Abteilung."})
        if not self._has_right_in_department(request.user, "admissions.add_admissionvoucher", department_id):
            raise ValidationError({"department": "Keine Berechtigung für diese Abteilung."})
        voucher, code = voucher_service.create_voucher(
            form,
            department_id=department_id,
            label=values["label"] or f"{values['vorname']} {values['nachname']}".strip(),
            prefill={"vorname": values["vorname"], "nachname": values["nachname"]},
            valid_days=values["valid_days"],
            by=request.user,
        )
        body = AdmissionVoucherSerializer(voucher).data
        body["code"] = code
        return Response(body, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Revoke an unused voucher", request=None)
    # Revoking changes the voucher; checked against its own department.
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def revoke(self, request, pk=None):
        voucher = self.get_object()
        if not self._has_right_in_department(request.user, "admissions.change_admissionvoucher", voucher.department_id):
            raise PermissionDenied("Keine Berechtigung zum Widerrufen.")
        return Response(AdmissionVoucherSerializer(voucher_service.revoke(voucher)).data)
