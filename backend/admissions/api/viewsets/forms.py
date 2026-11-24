from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from admissions.api.serializers.forms import (
    AdmissionFormSerializer,
    AdmissionFormVersionSerializer,
    AdmissionTextBlockSerializer,
    PublishSerializer,
)
from admissions.field_catalog import as_payload
from admissions.models import AdmissionForm, AdmissionTextBlock
from admissions.services import forms as form_service
from departments.mixins import DepartmentScopeViewSetMixin
from jf_manager_backend.mixins import BasePermissionedViewSet


@extend_schema_view(
    list=extend_schema(summary="Application forms of the visible departments"),
    create=extend_schema(summary="Create an application form (by default from the youth fire brigade sample)"),
    partial_update=extend_schema(summary="Change settings or save the draft"),
)
class AdmissionFormViewSet(DepartmentScopeViewSetMixin, BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = AdmissionForm.objects.select_related("department", "initial_status").prefetch_related("versions")
    serializer_class = AdmissionFormSerializer
    # No "department" filter: the scope mixin reads ?department= and keeps organisation forms.
    filterset_fields = ["is_active"]
    search_fields = ["title"]
    # Organisation forms (department=NULL) serve every department; changing them needs
    # the right organisation-wide.
    include_central_records = True

    def perform_create(self, serializer):
        self._validate_target_department(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validate_target_department(serializer)
        serializer.save()

    @extend_schema(summary="Field catalog, legal texts and consent kinds for the builder (?form= for its fields)")
    @action(detail=False, methods=["get"])
    def references(self, request):
        department_id = None
        form_id = request.query_params.get("form")
        if form_id and form_id.isdigit():
            form = self.get_queryset().filter(pk=int(form_id)).first()
            department_id = form.department_id if form else None
        return Response({"fields": as_payload(department_id), **form_service.available_references()})

    @extend_schema(summary="Publish the draft as a new version", request=PublishSerializer)
    # Publishing needs its own right in the form's department, not the add right.
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        form = self.get_object()
        if not self._has_right_in_department(request.user, "admissions.publish_admissionform", form.department_id):
            raise PermissionDenied("Keine Berechtigung zum Veröffentlichen.")
        data = PublishSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        version = form_service.publish(form, by=request.user, change_note=data.validated_data["change_note"])
        return Response(AdmissionFormVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Published versions of the form")
    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        form = self.get_object()
        return Response(AdmissionFormVersionSerializer(form.versions.all(), many=True).data)


@extend_schema_view(list=extend_schema(summary="Text blocks (own department and central)"))
class AdmissionTextBlockViewSet(DepartmentScopeViewSetMixin, BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = AdmissionTextBlock.objects.all()
    serializer_class = AdmissionTextBlockSerializer
    search_fields = ["title"]
    # Central blocks are offered to every department; writing stays with the owner.
    include_central_records = True

    def perform_create(self, serializer):
        self._validate_target_department(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validate_target_department(serializer)
        serializer.save()
