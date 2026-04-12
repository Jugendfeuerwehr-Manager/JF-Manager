from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Only allow superusers or staff with user management permissions."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.is_staff
