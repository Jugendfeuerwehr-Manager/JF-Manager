"""
Order Item ViewSet
"""

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from jf_manager_backend.permissions import DepartmentRoleModelPermissions
from orders.api.filters import OrderItemFilter
from orders.api.permissions import CanChangeOrderStatus
from orders.api.serializers import (
    OrderItemCreateSerializer,
    OrderItemSerializer,
    OrderItemStatusHistorySerializer,
    OrderItemUpdateSerializer,
)
from orders.models import OrderItem, OrderStatus
from orders.notifications import OrderNotificationService


class OrderItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order Items

    Provides CRUD operations and status management
    """

    queryset = OrderItem.objects.select_related("order", "item", "status", "order__member").all()
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated, DepartmentRoleModelPermissions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderItemFilter
    search_fields = ["item__name", "order__member__name", "order__member__lastname"]
    ordering_fields = ["order__order_date", "item__name", "status__sort_order"]
    ordering = ["-order__order_date"]

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == "create":
            return OrderItemCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return OrderItemUpdateSerializer
        return OrderItemSerializer

    @action(detail=True, methods=["post"], permission_classes=[CanChangeOrderStatus])
    def update_status(self, request, pk=None):
        """Update status of a single order item"""
        order_item = self.get_object()
        status_id = request.data.get("status")
        request.data.get("notes", "")

        if not status_id:
            return Response({"error": "status is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_status = OrderStatus.objects.get(id=status_id)
        except OrderStatus.DoesNotExist:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        old_status = order_item.status

        # Use the serializer for validation
        serializer = OrderItemUpdateSerializer(
            order_item,
            data={
                key: request.data[key]
                for key in ("status", "receipt_location", "create_loan", "notes")
                if key in request.data
            },
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            order_item = serializer.save()

            # Send notification if status changed
            if old_status != new_status:
                OrderNotificationService.send_status_update_notification(
                    order_item, old_status, new_status, request.user, request
                )

            return Response(OrderItemSerializer(order_item).data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], permission_classes=[CanChangeOrderStatus])
    def bulk_update_status(self, request):
        """Update status for multiple order items"""
        item_ids = request.data.get("item_ids", [])
        status_id = request.data.get("status")
        request.data.get("notes", "")

        if not item_ids or not status_id:
            return Response({"error": "item_ids and status are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_status = OrderStatus.objects.get(id=status_id)
        except OrderStatus.DoesNotExist:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(item_ids, list) or len(item_ids) != len(set(map(str, item_ids))):
            return Response({"item_ids": "Bitte eindeutige Bestellpositionen angeben."}, status=400)

        updated_items = []
        try:
            with transaction.atomic():
                order_items = list(OrderItem.objects.select_for_update().filter(pk__in=item_ids).order_by("pk"))
                if len(order_items) != len(item_ids):
                    raise serializers.ValidationError(
                        {"item_ids": "Mindestens eine Bestellposition wurde nicht gefunden."}
                    )
                for order_item in order_items:
                    old_status = order_item.status
                    update_data = {"status": status_id}
                    if request.data.get("receipt_location") is not None:
                        update_data["receipt_location"] = request.data["receipt_location"]
                    if "create_loan" in request.data:
                        update_data["create_loan"] = request.data["create_loan"]
                    serializer = OrderItemUpdateSerializer(
                        order_item,
                        data=update_data,
                        partial=True,
                        context={"request": request},
                    )
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    updated_items.append(order_item.id)
                    if old_status != new_status:
                        transaction.on_commit(
                            lambda item=order_item, previous=old_status: (
                                OrderNotificationService.send_status_update_notification(
                                    item, previous, new_status, request.user, request
                                )
                            )
                        )
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        return Response({"updated": len(updated_items), "updated_ids": updated_items, "errors": []})

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """Get status change history for an order item"""
        order_item = self.get_object()
        history = order_item.status_history.all().order_by("-changed_at")
        serializer = OrderItemStatusHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """Get statistics for order items"""
        from django.db.models import Count, Q

        # Filter by query params
        queryset = self.filter_queryset(self.get_queryset())

        stats = {
            "total": queryset.count(),
            "by_status": list(
                queryset.values("status__name", "status__code", "status__color")
                .annotate(count=Count("id"))
                .order_by("-count")
            ),
            "by_category": list(queryset.values("item__category").annotate(count=Count("id")).order_by("-count")),
            "pending": queryset.filter(Q(status__code="NEW") | Q(status__code="ORDERED")).count(),
            "delivered": queryset.filter(status__code="DELIVERED").count(),
        }

        return Response(stats)
