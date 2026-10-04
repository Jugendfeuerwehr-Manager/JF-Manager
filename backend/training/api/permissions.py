"""Custom permissions for Training API."""

from rest_framework import permissions


def can_manage_training_department(user, department_id):
    """A global training right is limited to assigned departments without org scope."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.has_perm("training.can_manage_training"):
        return False
    if user.has_perm("departments.can_access_all_departments"):
        return True
    return department_id is not None and user.department_roles.filter(department_id=department_id).exists()


class CanManageTraining(permissions.BasePermission):
    """Read: authenticated users. Write: requires training.can_manage_training."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.has_perm("training.can_manage_training")

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        department_id = (
            obj.session.department_id if hasattr(obj, "session_id") else getattr(obj, "department_id", None)
        )
        return can_manage_training_department(request.user, department_id)


class CanManageLibrary(permissions.BasePermission):
    """Read: authenticated users. Write: requires training.can_manage_library."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.has_perm("training.can_manage_library")
