"""
Shared base classes for DRF ViewSets used across all apps.

Usage
-----
Most apps only need authentication, not full model-level permissions::

    from jf_manager_backend.mixins import BaseFilterMixin

    class MyViewSet(BaseFilterMixin, viewsets.ModelViewSet):
        ...

For stricter model-level permission enforcement (view/add/change/delete)::

    from jf_manager_backend.mixins import BasePermissionedViewSet

    class MyViewSet(BasePermissionedViewSet, viewsets.ModelViewSet):
        ...
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated

from jf_manager_backend.permissions import DepartmentRoleModelPermissions


class BaseFilterMixin:
    """Adds standard filter, search, and ordering backends to a ViewSet."""

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class BaseAuthViewSet:
    """Requires authentication; adds standard filter backends."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class BasePermissionedViewSet:
    """
    Requires authentication AND enforces model-level permissions
    (view/add/change/delete) via ``DepartmentRoleModelPermissions``.

    Used in inventory and any app that needs granular role-based access control.
    """

    permission_classes = [IsAuthenticated, DepartmentRoleModelPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
