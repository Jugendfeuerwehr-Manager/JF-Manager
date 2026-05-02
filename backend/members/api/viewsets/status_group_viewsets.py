"""
StatusViewSet and GroupViewSet — lookup tables for member categorisation.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
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
