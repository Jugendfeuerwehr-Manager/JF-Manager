"""Staffing templates API (PART-04.5).

Department templates belong to the planners of that department; organisation templates
(``department`` null) are read by every planner and changed only by organisation-wide planners.
"""

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from departments.models import Department
from departments.role_assignments import ORG_SCOPE
from training.api.permissions import can_manage_training_department
from training.api.viewsets.template import manageable_department_ids
from training.models import TrainingSession, TrainingTemplate

from . import service, templates
from .models import StaffingTemplate, TemplateParticipation
from .rules import Names, summarize
from .service import ParticipationError
from .staff_views import StaffView, config_payload, error_response, no_markup
from .views import may_plan_anywhere


def can_manage_org_templates(user):
    return user.is_superuser or (user.has_perm("training.can_manage_training") and user.has_perm(ORG_SCOPE))


def can_write(user, department_id):
    if department_id is None:
        return can_manage_org_templates(user)
    return can_manage_training_department(user, department_id)


def visible_templates(user):
    queryset = StaffingTemplate.objects.select_related("department", "created_by")
    if user.is_superuser:
        return queryset
    return queryset.filter(Q(department__isnull=True) | Q(department_id__in=manageable_department_ids(user)))


def template_payload(template, *, full=False):
    body = template.body or {}
    rule = body.get("eligibility") or {}
    out = {
        "id": template.pk,
        "name": template.name,
        "description": template.description,
        "department": template.department_id,
        "department_name": template.department.name if template.department_id else None,
        "scope": "department" if template.department_id else "organization",
        "version": template.version,
        "archived": template.archived_at is not None,
        "archived_at": template.archived_at,
        "updated_at": template.updated_at,
        "mode": body.get("mode"),
        "slots": [{"label": s.get("label"), "min": s.get("min"), "max": s.get("max")} for s in body.get("slots", [])],
        "summary": _safe_summary(rule),
    }
    if full:
        out["body"] = body
    return out


def _safe_summary(rule):
    if not rule or not rule.get("rules"):
        return None
    try:
        return summarize(rule, Names.for_rule(rule))
    except (KeyError, TypeError):
        return None


class TemplateInput(serializers.Serializer):
    name = serializers.CharField(max_length=120, validators=[no_markup])
    description = serializers.CharField(max_length=1000, allow_blank=True, required=False, default="")
    department = serializers.IntegerField(allow_null=True, required=False, default=None)
    session = serializers.IntegerField(required=False, allow_null=True, default=None)
    body = serializers.JSONField(required=False, allow_null=True, default=None)
    version = serializers.IntegerField(required=False, min_value=1)

    def validate_description(self, value):
        return no_markup(value)

    def validate_body(self, value):
        if value is None:
            return None
        errors = templates.validate_body(value)
        if errors:
            raise serializers.ValidationError(errors)
        return value


def _department(value):
    if value is None:
        return None
    if not Department.objects.filter(pk=value).exists():
        raise serializers.ValidationError({"department": "Unbekannte Abteilung."})
    return value


class TemplateListView(StaffView):
    def get(self, request):
        if not may_plan_anywhere(request.user):
            raise PermissionDenied("Keine Berechtigung zur Dienstplanung.")
        queryset = visible_templates(request.user)
        if request.query_params.get("archived") != "1":
            queryset = queryset.filter(archived_at__isnull=True)
        department = request.query_params.get("department")
        if department and department.isdigit():
            # templates usable for a service of that department: its own and organisation ones
            queryset = queryset.filter(Q(department_id=int(department)) | Q(department__isnull=True))
        return Response(
            {
                "results": [template_payload(t) for t in queryset[:200]],
                "can_manage_organization": can_manage_org_templates(request.user),
            }
        )

    def post(self, request):
        data = TemplateInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        department_id = _department(values["department"])
        if not can_write(request.user, department_id):
            raise PermissionDenied("Keine Berechtigung, Vorlagen für diesen Bereich anzulegen.")
        if values["session"] is not None:
            session = get_object_or_404(TrainingSession, pk=values["session"])
            if not can_manage_training_department(request.user, session.department_id):
                raise PermissionDenied("Keine Berechtigung für diesen Dienst.")
            body = templates.snapshot(service.participation_for(session)[0])
        elif values["body"] is not None:
            body = values["body"]
        else:
            raise serializers.ValidationError({"body": "Dienst oder Inhalt angeben."})
        template = StaffingTemplate.objects.create(
            name=values["name"].strip(),
            description=values["description"].strip(),
            department_id=department_id,
            body=body,
            created_by=request.user,
        )
        return Response(template_payload(template, full=True), status=status.HTTP_201_CREATED)


class TemplateDetailView(StaffView):
    def template_for(self, request, pk, *, write):
        template = visible_templates(request.user).filter(pk=pk).first()
        if template is None:
            raise NotFound("Vorlage nicht gefunden.")
        if write and not can_write(request.user, template.department_id):
            raise PermissionDenied("Keine Berechtigung, diese Vorlage zu ändern.")
        return template

    def get(self, request, pk):
        return Response(template_payload(self.template_for(request, pk, write=False), full=True))

    def put(self, request, pk):
        self.template_for(request, pk, write=True)
        data = TemplateInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        with transaction.atomic():
            template = StaffingTemplate.objects.select_for_update().get(pk=pk)
            if values.get("version") != template.version:
                return Response(
                    {
                        "code": "stale",
                        "detail": "Die Vorlage wurde inzwischen geändert.",
                        "current": template_payload(template, full=True),
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            department_id = _department(values["department"])
            if department_id != template.department_id and not can_write(request.user, department_id):
                raise PermissionDenied("Keine Berechtigung für diesen Bereich.")
            template.name = values["name"].strip()
            template.description = values["description"].strip()
            template.department_id = department_id
            if values["body"] is not None:
                template.body = values["body"]
            template.version += 1
            template.save()
        return Response(template_payload(template, full=True))


class TemplateArchiveView(StaffView):
    archive = True

    def post(self, request, pk):
        template = TemplateDetailView().template_for(request, pk, write=True)
        template.archived_at = timezone.now() if self.archive else None
        template.version += 1
        template.save(update_fields=["archived_at", "version", "updated_at"])
        return Response(template_payload(template, full=True))


class TemplateUnarchiveView(TemplateArchiveView):
    archive = False


class ApplyInput(serializers.Serializer):
    template = serializers.IntegerField()
    revision = serializers.IntegerField(min_value=0)


class ApplyTemplateView(StaffView):
    """Copy a staffing template into a service (independent copy, warnings for removed ids)."""

    def post(self, request, session_id):
        self.session_for(request, session_id, write=True)
        data = ApplyInput(data=request.data)
        data.is_valid(raise_exception=True)
        template = visible_templates(request.user).filter(pk=data.validated_data["template"]).first()
        with transaction.atomic():
            session = (
                TrainingSession.objects.select_for_update(of=("self",)).select_related("department").get(pk=session_id)
            )
            if template is None or template.department_id not in (None, session.department_id):
                raise NotFound("Vorlage nicht gefunden.")
            participation, _ = service.participation_for(session)
            if data.validated_data["revision"] != participation.revision:
                return error_response(
                    ParticipationError(
                        "stale",
                        "Die Konfiguration wurde inzwischen geändert.",
                        status=409,
                        current=config_payload(session, participation),
                    )
                )
            try:
                participation, warnings = templates.apply_to_session(session, template.body, template=template)
            except ParticipationError as error:
                return error_response(error)
            service.promote_waitlist(session, participation)
        body = config_payload(session, participation)
        body["warnings"] = warnings
        body["template_source"] = {"id": template.pk, "name": template.name}
        return Response(body)


class TrainingTemplateInput(serializers.Serializer):
    staffing_template = serializers.IntegerField(allow_null=True)


class TrainingTemplateParticipationView(StaffView):
    """Carry a staffing template into an exercise template (TRAIN-03); copies the body."""

    def training_template(self, request, pk):
        template = get_object_or_404(TrainingTemplate, pk=pk)
        if not can_manage_training_department(request.user, template.department_id):
            raise PermissionDenied("Keine Berechtigung für diese Übungsvorlage.")
        return template

    def payload(self, row):
        if row is None:
            return {"staffing_template": None, "name": None, "slots": [], "mode": None}
        body = row.body or {}
        return {
            "staffing_template": row.staffing_template_id,
            "name": row.staffing_template.name if row.staffing_template_id else None,
            "mode": body.get("mode"),
            "slots": [
                {"label": s.get("label"), "min": s.get("min"), "max": s.get("max")} for s in body.get("slots", [])
            ],
        }

    def get(self, request, pk):
        template = self.training_template(request, pk)
        return Response(self.payload(TemplateParticipation.objects.filter(template=template).first()))

    def put(self, request, pk):
        template = self.training_template(request, pk)
        data = TrainingTemplateInput(data=request.data)
        data.is_valid(raise_exception=True)
        staffing_id = data.validated_data["staffing_template"]
        if staffing_id is None:
            TemplateParticipation.objects.filter(template=template).delete()
            return Response(self.payload(None))
        staffing = visible_templates(request.user).filter(pk=staffing_id, archived_at__isnull=True).first()
        if staffing is None or staffing.department_id not in (None, template.department_id):
            raise NotFound("Vorlage nicht gefunden.")
        body, _warnings = templates.clean_body(staffing.body)
        row, _ = TemplateParticipation.objects.update_or_create(
            template=template, defaults={"body": body, "staffing_template": staffing}
        )
        return Response(self.payload(row))
