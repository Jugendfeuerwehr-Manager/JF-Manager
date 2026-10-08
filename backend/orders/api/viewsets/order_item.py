"""
Order Item ViewSet
"""

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from departments.mixins import DepartmentScopeViewSetMixin
from inventory.services.booking_idempotency import run_idempotent_booking
from jf_manager_backend.permissions import DepartmentRoleModelPermissions
from orders.api.filters import OrderItemFilter
from orders.api.serializers import (
    OrderItemCreateSerializer,
    OrderItemSerializer,
    OrderItemStatusHistorySerializer,
    OrderItemUpdateSerializer,
)
from orders.models import OrderItem, OrderStatus
from orders.notifications import OrderNotificationService


class OrderItemRolePermissions(DepartmentRoleModelPermissions):
    def _required_permissions(self, request, view):
        if view.action in ("update_status", "bulk_update_status"):
            return ["orders.can_change_order_status"]
        return super()._required_permissions(request, view)

    def has_object_permission(self, request, view, obj):
        return super().has_object_permission(request, view, obj.order)


class OrderItemViewSet(DepartmentScopeViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Order Items

    Provides CRUD operations and status management
    """

    queryset = OrderItem.objects.select_related("order", "item", "status", "order__member").all()
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated, OrderItemRolePermissions]
    department_field = "order__department"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderItemFilter
    search_fields = ["item__name", "order__member__name", "order__member__lastname"]
    ordering_fields = ["order__order_date", "item__name", "status__sort_order"]
    ordering = ["-order__order_date"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method in permissions.SAFE_METHODS:
            return queryset

        required = OrderItemRolePermissions()._required_permissions(self.request, self)
        if not required:
            return queryset.none()
        user = self.request.user
        if self._user_is_org_wide(user) and all(user.has_perm(name) for name in required):
            return queryset
        allowed_ids = set(self._user_department_ids(user))
        for name in required:
            if user.has_perm(name):
                continue
            app_label, codename = name.split(".", 1)
            allowed_ids &= set(
                user.department_roles.filter(
                    groups__permissions__content_type__app_label=app_label,
                    groups__permissions__codename=codename,
                ).values_list("department_id", flat=True)
            )
        return queryset.filter(order__department_id__in=allowed_ids)

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == "create":
            return OrderItemCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return OrderItemUpdateSerializer
        return OrderItemSerializer

    def update(self, request, *args, **kwargs):
        return run_idempotent_booking(
            request,
            lambda: super(OrderItemViewSet, self).update(request, *args, **kwargs),
            replay_allowed=lambda data: self.get_queryset().filter(pk=self.kwargs["pk"]).exists(),
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, OrderItemRolePermissions])
    def update_status(self, request, pk=None):
        return run_idempotent_booking(
            request,
            lambda: self._update_status_impl(request),
            replay_allowed=lambda data: self.get_queryset().filter(pk=self.kwargs["pk"]).exists(),
        )

    def _update_status_impl(self, request):
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
                transaction.on_commit(
                    lambda: OrderNotificationService.send_status_update_notification(
                        order_item, old_status, new_status, request.user, request
                    )
                )

            return Response(OrderItemSerializer(order_item).data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated, OrderItemRolePermissions])
    def bulk_update_status(self, request):
        return run_idempotent_booking(
            request,
            lambda: self._bulk_update_status_impl(request),
            replay_allowed=lambda data: (
                self.get_queryset().filter(pk__in=data.get("updated_ids", [])).count()
                == len(data.get("updated_ids", []))
            ),
        )

    def _bulk_update_status_impl(self, request):
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
                order_items = list(
                    self.get_queryset().select_for_update(of=("self",)).filter(pk__in=item_ids).order_by("pk")
                )
                if len(order_items) != len(item_ids):
                    raise serializers.ValidationError(
                        {"item_ids": "Mindestens eine Bestellposition wurde nicht gefunden."}
                    )
                serializers_to_save = []
                for order_item in order_items:
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
                    serializers_to_save.append((order_item, serializer))

                for order_item, serializer in serializers_to_save:
                    old_status = order_item.status
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
