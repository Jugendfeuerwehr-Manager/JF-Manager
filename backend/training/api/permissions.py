"""Custom permissions for Training API."""

from rest_framework import permissions


class CanManageTraining(permissions.BasePermission):
    """Read: authenticated users. Write: requires training.can_manage_training."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.has_perm('training.can_manage_training')


class CanManageLibrary(permissions.BasePermission):
    """Read: authenticated users. Write: requires training.can_manage_library."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.has_perm('training.can_manage_library')
