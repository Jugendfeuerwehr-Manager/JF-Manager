import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.response import Response

from departments.assignment_sources import capture_untracked_local, project_sources
from departments.models import RoleGrant, RoleTemplate
from departments.role_assignments import (
    assignable_departments,
    assignment_preview,
    can_assign_template,
    explain_roles,
    is_role_administrator,
)
from users.mfa_policy import mfa_required
from users.step_up import StepUpForWrites

logger = logging.getLogger("security.roles")
User = get_user_model()


class AssignmentInput(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    department_id = serializers.IntegerField(min_value=1, allow_null=True)
    template_id = serializers.IntegerField(min_value=1)
    operation = serializers.ChoiceField(choices=["add", "remove"])
    fingerprint = serializers.CharField(required=False)

    def to_internal_value(self, data):
        if set(data) - set(self.fields):
            raise serializers.ValidationError({"fields": "Nicht unterstützte Zuweisungsfelder."})
        return super().to_internal_value(data)


class AssignmentConflict(APIException):
    status_code = 409
    default_detail = "Die Rechte oder Zuweisungen haben sich geändert. Bitte die Wirkung erneut prüfen."


class RoleAssignmentViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, StepUpForWrites]

    @action(detail=False, methods=["get"])
    def options(self, request):
        actor = request.user
        departments = list(assignable_departments(actor))
        admin = is_role_administrator(actor)
        if not admin and not departments:
            raise PermissionDenied("Keine Berechtigung zur Rollenzuweisung.")
        templates = []
        for template in RoleTemplate.objects.select_related("group").order_by("name"):
            areas = [d.pk for d in departments]
            if admin:
                areas.append(None)
            allowed = [area for area in areas if can_assign_template(actor, template, area)]
            if allowed:
                templates.append(
                    {
                        "id": template.pk,
                        "name": template.name,
                        "description": template.description,
                        "scope": template.scope,
                        "department_ids": allowed,
                    }
                )
        people = (
            User.objects.filter(is_active=True)
            .exclude(username="AnonymousUser")
            .exclude(pk=actor.pk)
            .order_by("username")
        )
        return Response(
            {
                "people": [
                    {"id": person.pk, "name": person.get_full_name() or person.username}
                    for person in people
                    if admin or not mfa_required(person)
                ],
                "departments": [{"id": d.pk, "name": d.name} for d in departments],
                "organization_allowed": admin,
                "roles": templates,
            }
        )

    @action(detail=False, methods=["get"])
    def explain(self, request):
        raw = request.query_params.get("user", request.user.pk)
        try:
            pk = int(raw)
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError({"user": "Ungültige Person."}) from exc
        target = get_object_or_404(User, pk=pk, is_active=True)
        own = target.pk == request.user.pk
        admin = is_role_administrator(request.user)
        departments = assignable_departments(request.user)
        if not own and not admin and not departments.exists():
            raise PermissionDenied("Keine Berechtigung zur Rechteauskunft.")
        return Response(
            {
                "roles": explain_roles(
                    target,
                    None if own or admin else departments.values_list("pk", flat=True),
                    include_global=own or admin,
                )
            }
        )

    def _prepare(self, request, *, lock=False):
        serializer = AssignmentInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if lock:
            list(User.objects.select_for_update().filter(pk__in=[request.user.pk, data["user_id"]]).order_by("pk"))
        target = get_object_or_404(User, pk=data["user_id"])
        templates = RoleTemplate.objects.select_related("group")
        if lock:
            templates = templates.select_for_update(of=("self",))
        template = get_object_or_404(templates, pk=data["template_id"])
        if lock and template.group_id:
            Group.objects.select_for_update().get(pk=template.group_id)
        # Reload the actor, avoiding permission caches from middleware/tests.
        actor = User.objects.get(pk=request.user.pk)
        preview = assignment_preview(actor, target, template, data["department_id"], data["operation"])
        return data, actor, target, template, preview

    @action(detail=False, methods=["post"])
    def preview(self, request):
        return Response(self._prepare(request)[-1])

    @transaction.atomic
    @action(detail=False, methods=["post"])
    def apply(self, request):
        data, actor, target, template, preview = self._prepare(request, lock=True)
        if data.get("fingerprint") != preview["fingerprint"]:
            raise AssignmentConflict()
        department_id = data["department_id"]
        capture_untracked_local(target, department_id)
        lookup = dict(user=target, department_id=department_id, group=template.group, source="local", source_key="")
        if data["operation"] == "add":
            RoleGrant.objects.get_or_create(**lookup)
        else:
            RoleGrant.objects.filter(**lookup).delete()
        project_sources(target, department_id)
        logger.info(
            "role_assignment actor=%s target=%s template=%s department=%s operation=%s result=success",
            actor.pk,
            target.pk,
            template.pk,
            department_id,
            data["operation"],
        )
        return Response(
            {
                "saved": True,
                "roles": explain_roles(
                    target,
                    None
                    if is_role_administrator(actor)
                    else assignable_departments(actor).values_list("pk", flat=True),
                    include_global=is_role_administrator(actor),
                ),
            }
        )
