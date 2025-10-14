"""
Order serializers with nested items and computed fields
"""

from rest_framework import serializers
from django.db.models import Count, Q
from orders.models import Order
from .order_item import OrderItemSerializer, OrderItemMinimalSerializer, OrderItemCreateSerializer
from .order_status import OrderStatusMinimalSerializer


class OrderSerializer(serializers.ModelSerializer):
    """Read serializer with full order details"""
    
    member_name = serializers.CharField(source='member.get_full_name', read_only=True)
    member_group = serializers.CharField(source='member.group.name', read_only=True)
    ordered_by_name = serializers.CharField(source='ordered_by.get_full_name', read_only=True)
    
    items = OrderItemMinimalSerializer(many=True, read_only=True)
    
    # Computed fields
    items_count = serializers.SerializerMethodField()
    common_status = serializers.SerializerMethodField()
    status_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'member',
            'member_name',
            'member_group',
            'ordered_by',
            'ordered_by_name',
            'order_date',
            'notes',
            'items',
            'items_count',
            'common_status',
            'status_summary'
        ]
        read_only_fields = ['id', 'order_date', 'ordered_by', 'member_name', 
                           'member_group', 'ordered_by_name', 'items', 
                           'items_count', 'common_status', 'status_summary']
    
    def get_items_count(self, obj):
        """Get total number of items"""
        return obj.items.count()
    
    def get_common_status(self, obj):
        """Get most common status"""
        status = obj.get_common_status()
        if status:
            return OrderStatusMinimalSerializer(status).data
        return None
    
    def get_status_summary(self, obj):
        """Get breakdown of items by status"""
        summary = obj.items.values(
            'status__id',
            'status__name',
            'status__code',
            'status__color'
        ).annotate(count=Count('id'))
        
        return [
            {
                'status_id': item['status__id'],
                'status_name': item['status__name'],
                'status_code': item['status__code'],
                'status_color': item['status__color'],
                'count': item['count']
            }
            for item in summary
        ]


class OrderDetailSerializer(OrderSerializer):
    """Detailed serializer with full item details"""
    
    items = OrderItemSerializer(many=True, read_only=True)


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders with nested items"""
    
    items = OrderItemCreateSerializer(many=True)
    
    class Meta:
        model = Order
        fields = [
            'member',
            'notes',
            'items'
        ]
    
    def validate_items(self, value):
        """Ensure at least one item"""
        if not value:
            raise serializers.ValidationError("Order must contain at least one item")
        return value
    
    def create(self, validated_data):
        """Create order with nested items"""
        items_data = validated_data.pop('items')
        
        # Get user from context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['ordered_by'] = request.user
        
        # Create order
        order = Order.objects.create(**validated_data)
        
        # Create items
        from orders.models import OrderStatus
        default_status = OrderStatus.objects.filter(code='NEW').first()
        if not default_status:
            default_status = OrderStatus.objects.filter(code='ORDERED').first()
        if not default_status:
            default_status = OrderStatus.objects.first()
        
        for item_data in items_data:
            if 'status' not in item_data and default_status:
                item_data['status'] = default_status
            
            from orders.models import OrderItem
            OrderItem.objects.create(order=order, **item_data)
        
        return order


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating orders"""
    
    class Meta:
        model = Order
        fields = [
            'member',
            'notes'
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    
    member_name = serializers.CharField(source='member.get_full_name', read_only=True)
    member_group = serializers.CharField(source='member.group.name', read_only=True)
    ordered_by_name = serializers.CharField(source='ordered_by.get_full_name', read_only=True)
    items_count = serializers.SerializerMethodField()
    items_summary = serializers.SerializerMethodField()
    common_status = serializers.SerializerMethodField()
    status_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'member',
            'member_name',
            'member_group',
            'ordered_by',
            'ordered_by_name',
            'order_date',
            'items_count',
            'items_summary',
            'common_status',
            'status_summary'
        ]
    
    def get_items_count(self, obj):
        """Get total number of items"""
        # Use prefetch_related count if available
        if hasattr(obj, '_items_count'):
            return obj._items_count
        return obj.items.count()
    
    def get_items_summary(self, obj):
        """Get summary of items with quantities"""
        items = obj.items.select_related('item').all()
        return [
            {
                'item_id': item.item.id,
                'item_name': item.item.name,
                'size': item.size or '',
                'quantity': item.quantity
            }
            for item in items
        ]
    
    def get_common_status(self, obj):
        """Get most common status"""
        status = obj.get_common_status()
        if status:
            return {
                'id': status.id,
                'name': status.name,
                'code': status.code,
                'color': status.color
            }
        return None
    
    def get_status_summary(self, obj):
        """Get breakdown of items by status"""
        summary = obj.items.values(
            'status__id',
            'status__name',
            'status__code',
            'status__color'
        ).annotate(count=Count('id'))
        
        return [
            {
                'status_id': item['status__id'],
                'status_name': item['status__name'],
                'status_code': item['status__code'],
                'status_color': item['status__color'],
                'count': item['count']
            }
            for item in summary
        ]
