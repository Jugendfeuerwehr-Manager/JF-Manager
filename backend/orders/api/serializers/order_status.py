"""
Enhanced serializers for Orders API

These serializers provide comprehensive functionality for the Vue frontend:
- Nested serializers for related objects
- Computed fields for UI display
- Validation for business rules
- Separate read/write serializers for optimal performance
"""

from rest_framework import serializers

from orders.models import OrderStatus


class OrderStatusSerializer(serializers.ModelSerializer):
    """Serializer for OrderStatus"""

    class Meta:
        model = OrderStatus
        fields = [
            'id',
            'name',
            'code',
            'description',
            'color',
            'is_active',
            'sort_order'
        ]
        read_only_fields = ['id']


class OrderStatusMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for nested use"""

    class Meta:
        model = OrderStatus
        fields = ['id', 'name', 'code', 'color']
