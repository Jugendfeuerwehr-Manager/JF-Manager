from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from departments.api.serializers.department import UserDepartmentRoleSerializer
from departments.models import UserDepartmentRole


class UserDepartmentRoleViewSet(viewsets.ModelViewSet):
    """
    Manage user-department role assignments.  Admin only.
    """

    serializer_class = UserDepartmentRoleSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["user", "department"]
    ordering = ["department__name", "user__username"]

    def get_queryset(self):
        return UserDepartmentRole.objects.select_related("user", "department").prefetch_related("groups").all()
