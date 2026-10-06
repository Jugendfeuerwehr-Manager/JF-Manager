from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response

from departments.api.serializers.role_template import RoleTemplateReadSerializer
from departments.delegation import approval_digest, can_approve_delegation
from departments.models import RoleTemplate
from departments.role_comparison import compare_role_template
from users.step_up import StepUpForWrites


class StaleRoleComparison(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Die Rollenvorlage wurde seit dem Vergleich geändert. Bitte erneut vergleichen."


class CanManageRoleTemplates(permissions.BasePermission):
    required_by_action = {
        "list": ("departments.view_roletemplate",),
        "retrieve": ("departments.view_roletemplate",),
        "compare": ("departments.view_roletemplate",),
        "partial_update": ("departments.change_roletemplate",),
        "archive": ("departments.change_roletemplate",),
        "apply_permissions": ("departments.change_roletemplate", "auth.change_group"),
        "delegation": ("departments.change_roletemplate", "departments.can_assign_roles"),
        "duplicate": ("departments.add_roletemplate", "auth.add_group"),
    }

    def has_permission(self, request, view):
        required = self.required_by_action.get(view.action)
        return bool(request.user and request.user.is_authenticated and required and request.user.has_perms(required))


class RoleTemplateViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = RoleTemplateReadSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageRoleTemplates, StepUpForWrites]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return RoleTemplate.objects.select_related("group").order_by("key")

    @action(detail=True, methods=["get"])
    def compare(self, request, pk=None):
        template = self.get_object()
        return Response({**self.get_serializer(template).data, **compare_role_template(template)})

    def _locked_template(self):
        template = get_object_or_404(
            RoleTemplate.objects.select_for_update(of=("self",)).select_related("group"), pk=self.kwargs["pk"]
        )
        if template.group_id:
            Group.objects.select_for_update().get(pk=template.group_id)
        return template

    @staticmethod
    def _check_fingerprint(request, template):
        supplied = request.data.get("fingerprint")
        if not isinstance(supplied, str) or not supplied:
            raise ValidationError({"fingerprint": "Ein aktueller Vergleich ist erforderlich."})
        if supplied != compare_role_template(template)["fingerprint"]:
            raise StaleRoleComparison()

    @staticmethod
    def _check_fields(request, allowed):
        unknown = set(request.data) - allowed
        if unknown:
            raise ValidationError({"fields": f"Nicht unterstützte Felder: {', '.join(sorted(unknown))}"})

    @staticmethod
    def _check_active(template):
        if template.is_archived:
            raise ValidationError({"is_archived": "Archivierte Vorlagen können nicht geändert werden."})

    @staticmethod
    def _check_not_own_group(request, template):
        if template.group_id and (
            template.group.user_set.filter(pk=request.user.pk).exists()
            or template.group.department_assignments.filter(user=request.user).exists()
        ):
            raise PermissionDenied("Eigene Rollengruppen können nicht geändert werden.")

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        self._check_fields(request, {"fingerprint", "name", "description", "is_delegable"})
        changes = {
            field: request.data[field] for field in ("name", "description", "is_delegable") if field in request.data
        }
        if not changes:
            raise ValidationError({"fields": "Mindestens ein Änderungsfeld ist erforderlich."})
        for field in ("name", "description"):
            if field in changes and not isinstance(changes[field], str):
                raise ValidationError({field: "Ein Textwert ist erforderlich."})
        if "is_delegable" in changes and type(changes["is_delegable"]) is not bool:
            raise ValidationError({"is_delegable": "Ein boolescher Wert ist erforderlich."})
        template = self._locked_template()
        self._check_fingerprint(request, template)
        self._check_active(template)
        self._check_not_own_group(request, template)
        if "is_delegable" in changes:
            template.delegation_approval = ""
            changes["delegation_approval"] = ""
        for field, value in changes.items():
            setattr(template, field, value)
        try:
            template.save(update_fields=[*changes, "updated_at"])
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict) from exc
        return Response(self.get_serializer(template).data)

    @staticmethod
    def _resolve_permissions(names):
        if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
            raise ValidationError({"permissions": "Eine Liste vollqualifizierter Permission-Namen ist erforderlich."})
        if len(set(names)) != len(names):
            raise ValidationError({"permissions": "Doppelte Permission-Namen sind nicht erlaubt."})
        resolved = []
        for name in names:
            parts = name.split(".")
            if len(parts) != 2 or not all(parts):
                raise ValidationError({"permissions": f"Ungültiger Permission-Name: {name}"})
            matches = list(Permission.objects.filter(content_type__app_label=parts[0], codename=parts[1]))
            if len(matches) != 1:
                raise ValidationError({"permissions": f"Permission fehlt oder ist mehrdeutig: {name}"})
            resolved.append(matches[0])
        return resolved

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="apply-permissions")
    def apply_permissions(self, request, pk=None):
        self._check_fields(request, {"fingerprint", "permissions"})
        template = self._locked_template()
        self._check_fingerprint(request, template)
        self._check_active(template)
        self._check_not_own_group(request, template)
        if template.group_id is None:
            raise ValidationError({"group": "Die Vorlage ist keiner Django-Gruppe zugeordnet."})
        if template.scope == RoleTemplate.Scope.BOTH:
            raise ValidationError({"scope": "Für Änderungen ist ein eindeutiger Bereich erforderlich."})
        selected = self._resolve_permissions(request.data.get("permissions"))
        names = set(request.data["permissions"])
        organization_scope = "departments.can_access_all_departments"
        if (organization_scope in names) != (template.scope == RoleTemplate.Scope.ORGANIZATION):
            raise ValidationError({"permissions": "Organisationsberechtigung passt nicht zum Vorlagenbereich."})
        template.group.permissions.set(selected)
        template.delegation_approval = ""
        template.save(update_fields=["delegation_approval", "updated_at"])
        return Response({**self.get_serializer(template).data, **compare_role_template(template)})

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def delegation(self, request, pk=None):
        self._check_fields(request, {"fingerprint", "approved"})
        template = self._locked_template()
        self._check_fingerprint(request, template)
        self._check_not_own_group(request, template)
        approved = request.data.get("approved")
        if type(approved) is not bool:
            raise ValidationError({"approved": "Ein boolescher Wert ist erforderlich."})
        if approved and not can_approve_delegation(template):
            raise ValidationError(
                {
                    "approved": "Nur aktive delegierbare Abteilungsrollen ohne privilegierte Rechte können freigegeben werden."
                }
            )
        template.delegation_approval = approval_digest(template) if approved else ""
        template.save(update_fields=["delegation_approval", "updated_at"])
        return Response(self.get_serializer(template).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        self._check_fields(request, {"fingerprint"})
        template = self._locked_template()
        self._check_fingerprint(request, template)
        self._check_not_own_group(request, template)
        if not template.is_archived:
            template.is_archived = True
            template.save(update_fields=["is_archived", "updated_at"])
        return Response(self.get_serializer(template).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        self._check_fields(request, {"fingerprint", "key", "name", "description", "is_delegable"})
        source = self._locked_template()
        self._check_fingerprint(request, source)
        self._check_active(source)
        if source.group_id is None or source.scope == RoleTemplate.Scope.BOTH:
            raise ValidationError({"group": "Nur gebundene Vorlagen mit eindeutigem Bereich können kopiert werden."})
        key = request.data.get("key")
        name = request.data.get("name")
        is_delegable = request.data.get("is_delegable", False)
        if not isinstance(key, str) or not isinstance(name, str):
            raise ValidationError({"key": "Ein neuer Schlüssel und Anzeigename sind erforderlich."})
        description = request.data.get("description", source.description)
        if not isinstance(description, str):
            raise ValidationError({"description": "Ein Textwert ist erforderlich."})
        if type(is_delegable) is not bool:
            raise ValidationError({"is_delegable": "Ein boolescher Wert ist erforderlich."})
        group_name = f"jf_role__{key}"
        if Group.objects.filter(name=group_name).exists():
            raise ValidationError({"key": "Eine Gruppe mit diesem technischen Namen existiert bereits."})
        group = Group.objects.create(name=group_name)
        group.permissions.set(source.group.permissions.all())
        try:
            duplicate = RoleTemplate.objects.create(
                key=key,
                group=group,
                name=name,
                description=description,
                template_version=1,
                scope=source.scope,
                is_delegable=is_delegable,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict) from exc
        return Response(self.get_serializer(duplicate).data, status=status.HTTP_201_CREATED)
