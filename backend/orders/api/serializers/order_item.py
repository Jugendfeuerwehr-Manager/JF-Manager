"""
Order Item serializers with status tracking and validation
"""

from rest_framework import serializers

from orders.models import OrderItem, OrderItemStatusHistory
from orders.notifications import OrderWorkflowService

from .order_status import OrderStatusMinimalSerializer
from .orderable_item import OrderableItemMinimalSerializer


class OrderItemStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for status history"""

    changed_by_display = serializers.CharField(source="changed_by.get_full_name", read_only=True)
    old_status = serializers.IntegerField(source="from_status.id", read_only=True)
    old_status_name = serializers.CharField(source="from_status.name", read_only=True)
    new_status = serializers.IntegerField(source="to_status.id", read_only=True)
    new_status_name = serializers.CharField(source="to_status.name", read_only=True)

    class Meta:
        model = OrderItemStatusHistory
        fields = [
            "id",
            "old_status",
            "old_status_name",
            "new_status",
            "new_status_name",
            "changed_by",
            "changed_by_display",
            "changed_at",
            "notes",
        ]
        read_only_fields = ["id", "changed_at", "changed_by"]


class OrderItemSerializer(serializers.ModelSerializer):
    """Read serializer with full details"""

    item_details = OrderableItemMinimalSerializer(source="item", read_only=True)
    status_details = OrderStatusMinimalSerializer(source="status", read_only=True)

    # Backward compatibility fields
    item_name = serializers.CharField(source="item.name", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)
    status_color = serializers.CharField(source="status.color", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order",
            "item",
            "item_details",
            "item_name",
            "size",
            "quantity",
            "status",
            "status_details",
            "status_name",
            "status_color",
            "received_date",
            "delivered_date",
            "notes",
        ]
        read_only_fields = ["id", "item_details", "item_name", "status_details", "status_name", "status_color"]


class OrderItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating order items"""

    class Meta:
        model = OrderItem
        fields = ["item", "size", "quantity", "status", "notes"]

    def validate_quantity(self, value):
        """Ensure quantity is positive"""
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value

    def validate(self, attrs):
        """Validate size for items that have sizes"""
        item = attrs.get("item")
        size = attrs.get("size", "")

        if item and item.has_sizes and not size:
            raise serializers.ValidationError({"size": "Size is required for this item"})

        return attrs


class OrderItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order items with status transition validation"""

    class Meta:
        model = OrderItem
        fields = ["size", "quantity", "status", "notes"]

    def validate_status(self, value):
        """Validate status transitions"""
        if self.instance:
            old_status = self.instance.status
            new_status = value

            if old_status != new_status and not OrderWorkflowService.can_transition_to(old_status, new_status):
                raise serializers.ValidationError(f'Cannot transition from "{old_status.name}" to "{new_status.name}"')

        return value

    def update(self, instance, validated_data):
        """Update with status tracking"""
        old_status = instance.status
        new_status = validated_data.get("status", old_status)

        # Get user from context
        request = self.context.get("request")
        user = request.user if request else None

        # Update instance
        instance = super().update(instance, validated_data)

        # Track status change
        if old_status != new_status and user:
            OrderItemStatusHistory.objects.create(
                order_item=instance,
                from_status=old_status,
                to_status=new_status,
                changed_by=user,
                notes="Status updated via API",
            )

        return instance


class OrderItemMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for nested use in orders"""

    item_name = serializers.CharField(source="item.name", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)
    status_color = serializers.CharField(source="status.color", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "item", "item_name", "size", "quantity", "status", "status_name", "status_color"]
