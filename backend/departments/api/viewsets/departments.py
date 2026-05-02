from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from departments.api.filters import DepartmentFilter
from departments.api.serializers.department import DepartmentSerializer
from departments.models import Department


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    Manage departments.

    - Staff / users with can_manage_all_departments: full CRUD.
    - All authenticated users: list and retrieve their own accessible departments.
    """

    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DepartmentFilter
    search_fields = ["name", "code"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        user = self.request.user
        # Staff and users with org-wide permission see all departments
        if user.is_staff or user.has_perm("departments.can_access_all_departments"):
            return Department.objects.all()
        # Otherwise only departments the user is assigned to
        return Department.objects.filter(user_roles__user=user).distinct()

    def perform_destroy(self, instance):
        # Only staff / org-wide managers may delete
        user = self.request.user
        if not (user.is_staff or user.has_perm("departments.can_manage_all_departments")):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Nur Administratoren können Abteilungen löschen.")
        instance.delete()

    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_staff or user.has_perm("departments.can_manage_all_departments")):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Nur Administratoren können Abteilungen anlegen.")
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if not (user.is_staff or user.has_perm("departments.can_manage_all_departments")):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Nur Administratoren können Abteilungen bearbeiten.")
        serializer.save()
