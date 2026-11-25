"""Training capabilities are evaluated in the real session department."""

from django.db.models import Q
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError

from departments.role_assignments import scoped_permission
from jf_manager_backend.permissions import DepartmentRoleModelPermissions


def can_manage_training_department(user, department_id):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return scoped_permission(user, "training.can_manage_training", department_id)


def filter_training_queryset(request, queryset, prefix=""):
    user = request.user
    department_field = f"{prefix}department_id"
    status_field = f"{prefix}status"
    organization = user.has_perm("departments.can_access_all_departments")
    assigned = set(user.department_roles.values_list("department_id", flat=True))
    raw = request.query_params.get("department")
    if raw:
        try:
            department_id = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"department": "Ungültige Abteilung."}) from exc
        if not organization and department_id not in assigned:
            raise PermissionDenied("Keine Berechtigung für diese Abteilung.")
        queryset = queryset.filter(**{department_field: department_id})
    if not organization:
        queryset = queryset.filter(**{department_field + "__in": assigned})
    if request.method not in permissions.SAFE_METHODS or user.is_superuser:
        return queryset
    model_name = queryset.model._meta.model_name
    read = f"training.view_{model_name}"
    if not user.has_perm(read):
        app, code = read.split(".")
        readable = user.department_roles.filter(
            groups__permissions__content_type__app_label=app, groups__permissions__codename=code
        ).values_list("department_id", flat=True)
        queryset = queryset.filter(**{department_field + "__in": readable})
    if user.has_perm("training.can_manage_training") and organization:
        return queryset
    planners = [pk for pk in assigned if can_manage_training_department(user, pk)]
    # Ordinary readers see released exercises and their retained history.
    return queryset.filter(~Q(**{status_field: "draft"}) | Q(**{department_field + "__in": planners})).distinct()


class CanManageTraining(DepartmentRoleModelPermissions):
    def _get_model(self, view):
        from training.models import TrainingBlock, TrainingSession

        return TrainingBlock if "block" in (getattr(view, "basename", "") or "") else TrainingSession

    def _required_permissions(self, request, view):
        model = self._get_model(view)
        if request.method in permissions.SAFE_METHODS:
            return [f"training.view_{model._meta.model_name}"]
        if request.method == "DELETE":
            if model._meta.model_name == "trainingsession":
                # Planning includes deleting an exercise (NOTIF-02, user decision 11.10.2026): it removes
                # planning data only, never personal master data, so no separate delete right is needed.
                return ["training.can_manage_training"]
            return ["training.can_manage_training", f"training.delete_{model._meta.model_name}"]
        if request.method in ("POST", "PUT", "PATCH"):
            return ["training.can_manage_training"]
        return None

    def has_object_permission(self, request, view, obj):
        owner = obj.session if hasattr(obj, "session_id") else obj
        if request.method in permissions.SAFE_METHODS:
            if not super().has_object_permission(request, view, owner):
                return False
            return owner.status != "draft" or can_manage_training_department(request.user, owner.department_id)
        return super().has_object_permission(request, view, owner) and can_manage_training_department(
            request.user, owner.department_id
        )


LIBRARY_PERMISSION = "training.can_manage_library"


def holds_library_permission_in_department(user):
    """The shared library has no owning department; any department role may contribute to it."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    app, code = LIBRARY_PERMISSION.split(".")
    return user.department_roles.filter(
        groups__permissions__content_type__app_label=app, groups__permissions__codename=code
    ).exists()


class CanManageLibrary(permissions.BasePermission):
    """Shared library reads; global editors manage everything.

    Holders of the library right from a department role may add blocks and edit the
    blocks they created. Editing foreign blocks, deleting and importing (which overwrites
    existing blocks) stay with the global editorial right.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if user.has_perm(LIBRARY_PERMISSION):
            if request.method != "DELETE":
                return True
            model = view.get_queryset().model
            return user.has_perm(f"training.delete_{model._meta.model_name}")
        if request.method == "DELETE" or getattr(view, "action", None) == "import_blocks":
            return False
        return holds_library_permission_in_department(user)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.has_perm(LIBRARY_PERMISSION):
            return True
        return getattr(obj, "created_by_id", None) == request.user.pk
