from rest_framework import serializers
from .models import OrderStatus, OrderableItem, Order, OrderItem


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = '__all__'


class OrderableItemSerializer(serializers.ModelSerializer):
    sizes_list = serializers.ReadOnlyField(source='get_sizes_list')
    
    class Meta:
        model = OrderableItem
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    item_name = serializers.ReadOnlyField(source='item.name')
    status_name = serializers.ReadOnlyField(source='status.name')
    status_color = serializers.ReadOnlyField(source='status.color')
    
    class Meta:
        model = OrderItem
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source='member.__str__')
    ordered_by_name = serializers.ReadOnlyField(source='ordered_by.__str__')
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = '__all__'
