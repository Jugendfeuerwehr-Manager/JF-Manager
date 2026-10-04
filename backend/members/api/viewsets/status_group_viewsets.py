"""
StatusViewSet and GroupViewSet — lookup tables for member categorisation.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from departments.mixins import DepartmentScopeViewSetMixin
from jf_manager_backend.permissions import DepartmentRoleModelPermissions
from members.api_serializers import GroupSerializer, StatusSerializer
from members.models import Group, Status


@extend_schema_view(
    list=extend_schema(summary="List all statuses"),
    retrieve=extend_schema(summary="Get status details"),
    create=extend_schema(summary="Create new status"),
    update=extend_schema(summary="Update status"),
    partial_update=extend_schema(summary="Partially update status"),
    destroy=extend_schema(summary="Delete status"),
)
class StatusViewSet(viewsets.ModelViewSet):
    queryset = Status.objects.all()
    serializer_class = StatusSerializer
    permission_classes = [IsAuthenticated, DepartmentRoleModelPermissions]
    ordering = ["name"]


@extend_schema_view(
    list=extend_schema(summary="List all groups"),
    retrieve=extend_schema(summary="Get group details"),
    create=extend_schema(summary="Create new group"),
    update=extend_schema(summary="Update group"),
    partial_update=extend_schema(summary="Partially update group"),
    destroy=extend_schema(summary="Delete group"),
)
class GroupViewSet(DepartmentScopeViewSetMixin, viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, DepartmentRoleModelPermissions]
    ordering = ["name"]

    def _validate_target_department(self, serializer):
        if "department" in serializer.validated_data:
            department = serializer.validated_data["department"]
            department_id = department.pk if department is not None else None
        elif serializer.instance is not None:
            department_id = serializer.instance.department_id
        else:
            department_id = self._resolve_requested_department(self.request.user)
            if department_id is None and not self._user_is_org_wide(self.request.user):
                assigned_ids = self._user_department_ids(self.request.user)
                if len(assigned_ids) == 1:
                    department_id = assigned_ids[0]

        permission = DepartmentRoleModelPermissions()
        if department_id is None:
            required = permission._required_permissions(self.request, self)
            allowed = required is not None and self._user_is_org_wide(self.request.user) and all(
                self.request.user.has_perm(name) for name in required
            )
        else:
            allowed = permission.has_object_permission(
                self.request, self, Group(department_id=department_id)
            )
        if not allowed:
            raise ValidationError({"department": "Keine Schreibberechtigung für die Zielabteilung."})

    def perform_create(self, serializer):
        self._validate_target_department(serializer)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._validate_target_department(serializer)
        super().perform_update(serializer)
