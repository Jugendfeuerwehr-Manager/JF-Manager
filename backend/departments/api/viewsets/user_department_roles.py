from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from departments.api.serializers.department import UserDepartmentRoleSerializer
from departments.models import UserDepartmentRole
from users.api.permissions import IdentityModelPermissions
from users.step_up import StepUpForWrites


class UserDepartmentRoleViewSet(viewsets.ModelViewSet):
    """
    Manage user-department role assignments.  Admin only.
    """

    queryset = UserDepartmentRole.objects.all()
    serializer_class = UserDepartmentRoleSerializer
    permission_classes = [permissions.IsAuthenticated, IdentityModelPermissions, StepUpForWrites]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["user", "department"]
    ordering = ["department__name", "user__username"]

    def get_queryset(self):
        return UserDepartmentRole.objects.select_related("user", "department").prefetch_related("groups").all()

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        from departments.assignment_sources import set_local_groups
        from departments.models import RoleGrant

        if instance.user_id == self.request.user.pk:
            raise PermissionDenied("Eigene Rollenzuweisungen können nicht geändert werden.")
        set_local_groups(instance.user, instance.department_id, [])
        if not RoleGrant.objects.filter(user=instance.user, department_id=instance.department_id).exists():
            instance.delete()
