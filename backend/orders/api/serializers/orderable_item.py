"""
Orderable Item serializers
"""

from rest_framework import serializers

from orders.models import OrderableItem


class OrderableItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderableItem with computed fields"""

    sizes_list = serializers.ReadOnlyField(source='get_sizes_list')

    class Meta:
        model = OrderableItem
        fields = [
            'id',
            'name',
            'category',
            'description',
            'has_sizes',
            'available_sizes',
            'sizes_list',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'sizes_list']


class OrderableItemMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for nested use"""

    class Meta:
        model = OrderableItem
        fields = ['id', 'name', 'category', 'has_sizes']


class OrderableItemCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating orderable items"""

    class Meta:
        model = OrderableItem
        fields = [
            'name',
            'category',
            'description',
            'has_sizes',
            'available_sizes',
            'is_active'
        ]

    def validate_available_sizes(self, value):
        """Validate sizes format"""
        if value:
            sizes = [s.strip() for s in value.split(',')]
            if not all(sizes):
                raise serializers.ValidationError(
                    "Sizes must be comma-separated non-empty strings"
                )
        return value
