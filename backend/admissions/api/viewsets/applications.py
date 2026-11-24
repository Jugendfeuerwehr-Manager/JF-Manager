from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from admissions.api.serializers.applications import (
    ApplicationDetailSerializer,
    ApplicationListSerializer,
    BulkDecisionSerializer,
    CommitteeMeetingSerializer,
    DecisionInputSerializer,
    TakeOverSerializer,
)
from admissions.models import Application, CommitteeMeeting, Seal
from admissions.services import decisions as decision_service
from admissions.services import seal as seal_service
from admissions.services import takeover as takeover_service
from admissions.services.submission import SUBJECT, submission_content
from admissions.services.verification import verify_application
from departments.mixins import DepartmentScopeViewSetMixin
from jf_manager_backend.export_audit import ExportAuditMixin
from jf_manager_backend.mixins import BasePermissionedViewSet


def _decide(application, data, user):
    return decision_service.record_decision(
        application,
        outcome=data["outcome"],
        decided_on=data.get("decided_on") or (data["meeting"].date if data.get("meeting") else None),
        meeting=data.get("meeting"),
        votes=(data.get("votes_yes"), data.get("votes_no"), data.get("votes_abstain")),
        note=data.get("note", ""),
        by=user,
    )


@extend_schema_view(
    list=extend_schema(summary="Applications of the visible departments"),
    retrieve=extend_schema(summary="Application with answers, decisions and files"),
)
class ApplicationViewSet(
    ExportAuditMixin,
    DepartmentScopeViewSetMixin,
    BasePermissionedViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Application.objects.select_related("form_version__form").prefetch_related("decisions", "files")
    filterset_fields = ["department", "status"]
    search_fields = ["applicant_name"]
    audited_export_actions = ("export",)

    def get_serializer_class(self):
        if self.action == "list":
            return ApplicationListSerializer
        return ApplicationDetailSerializer

    def _require(self, application, permission, message):
        if not self._has_right_in_department(self.request.user, permission, application.department_id):
            raise PermissionDenied(message)

    @extend_schema(summary="Re-check all seals of the application")
    @action(detail=True, methods=["get"])
    def verify(self, request, pk=None):
        return Response(verify_application(self.get_object()))

    @extend_schema(summary="Existing parents of the department that match the guardians")
    @action(detail=True, methods=["get"], url_path="parent-suggestions")
    def parent_suggestions(self, request, pk=None):
        return Response(takeover_service.parent_suggestions(self.get_object()))

    @extend_schema(summary="Record the committee's resolution", request=DecisionInputSerializer)
    # Decisions need their own right in the application's department (not add/change).
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def decide(self, request, pk=None):
        application = self.get_object()
        self._require(application, "admissions.record_decision", "Keine Berechtigung, Beschlüsse zu erfassen.")
        data = DecisionInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        _decide(application, data.validated_data, request.user)
        application.refresh_from_db()
        return Response(ApplicationDetailSerializer(application, context=self.get_serializer_context()).data)

    @extend_schema(summary="Create member and guardians from an approved application", request=TakeOverSerializer)
    @action(detail=True, methods=["post"], url_path="take-over", permission_classes=[IsAuthenticated])
    def take_over(self, request, pk=None):
        application = self.get_object()
        self._require(application, "admissions.take_over_application", "Keine Berechtigung zur Übernahme.")
        self._require(application, "members.add_member", "Keine Berechtigung, Mitglieder anzulegen.")
        data = TakeOverSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        member = takeover_service.take_over(application, by=request.user, **data.validated_data)
        return Response({"member": member.pk}, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Sealed export of the application (JSON for the PDF printout)")
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def export(self, request, pk=None):
        application = self.get_object()
        self._require(application, "admissions.export_application", "Keine Berechtigung zum Export.")
        self.export_department_ids = [application.department_id]
        body = ApplicationDetailSerializer(application, context=self.get_serializer_context()).data
        body["seals"] = verify_application(application)["seals"]
        export_seal = seal_service.seal(
            subject_type=SUBJECT,
            subject_id=application.pk,
            kind=Seal.Kind.EXPORT,
            content={"submission": submission_content(application), "exported_by": request.user.pk},
        )
        body["export_seal"] = {
            "public_id": export_seal.public_id,
            "seal_hash": export_seal.seal_hash,
            "sealed_at": export_seal.created_at,
        }
        return Response(body)


@extend_schema_view(list=extend_schema(summary="Committee meetings of the visible departments"))
class CommitteeMeetingViewSet(DepartmentScopeViewSetMixin, BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = CommitteeMeeting.objects.prefetch_related("decisions")
    serializer_class = CommitteeMeetingSerializer
    filterset_fields = ["department"]

    def perform_create(self, serializer):
        self._validate_target_department(serializer)
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        self._validate_target_department(serializer)
        serializer.save()

    def perform_destroy(self, instance):
        if instance.decisions.exists():
            raise ValidationError({"detail": "Eine Sitzung mit Beschlüssen kann nicht gelöscht werden."})
        instance.delete()

    @extend_schema(summary="Decide several applications in this meeting at once", request=BulkDecisionSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def decide(self, request, pk=None):
        meeting = self.get_object()
        if not self._has_right_in_department(request.user, "admissions.record_decision", meeting.department_id):
            raise PermissionDenied("Keine Berechtigung, Beschlüsse zu erfassen.")
        data = BulkDecisionSerializer(data={**request.data, "meeting": meeting.pk})
        data.is_valid(raise_exception=True)
        applications = list(
            Application.objects.filter(pk__in=data.validated_data["applications"], department=meeting.department)
        )
        if len(applications) != len(set(data.validated_data["applications"])):
            raise ValidationError({"applications": "Nicht alle Anträge gehören zur Abteilung der Sitzung."})
        with transaction.atomic():
            for application in applications:
                _decide(application, data.validated_data, request.user)
        return Response({"decided": [application.pk for application in applications]})
