"""
Order Status ViewSet
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from jf_manager_backend.permissions import DepartmentRoleModelPermissions, OrgWideWritePermission
from orders.api.filters import OrderStatusFilter
from orders.api.serializers import OrderStatusSerializer
from orders.models import OrderStatus


class OrderStatusViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order Status management

    Provides CRUD operations and workflow information
    """

    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer
    permission_classes = [permissions.IsAuthenticated, DepartmentRoleModelPermissions, OrgWideWritePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderStatusFilter
    search_fields = ["name", "code", "description"]
    ordering_fields = ["sort_order", "name", "code"]
    ordering = ["sort_order", "name"]

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get only active statuses"""
        statuses = self.queryset.filter(is_active=True).order_by("sort_order")
        serializer = self.get_serializer(statuses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def next_statuses(self, request, pk=None):
        """Get allowed next statuses from this status"""
        status = self.get_object()

        # Get statuses with higher sort_order
        next_statuses = OrderStatus.objects.filter(is_active=True, sort_order__gt=status.sort_order).order_by(
            "sort_order"
        )[:3]

        serializer = self.get_serializer(next_statuses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def workflow(self, request):
        """Get complete workflow information"""
        from orders.notifications import OrderWorkflowService

        workflow = OrderWorkflowService.get_workflow_graph()
        return Response(workflow)
