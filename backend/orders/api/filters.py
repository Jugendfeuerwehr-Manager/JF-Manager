"""
Django filters for Orders API
"""

from django.db.models import Q
from django_filters import rest_framework as filters

from orders.models import Order, OrderableItem, OrderItem, OrderStatus


class OrderFilter(filters.FilterSet):
    """Filter for orders"""

    member = filters.NumberFilter(field_name='member__id')
    member_name = filters.CharFilter(method='filter_member_name')
    ordered_by = filters.NumberFilter(field_name='ordered_by__id')
    date_from = filters.DateFilter(field_name='order_date__date', lookup_expr='gte')
    date_to = filters.DateFilter(field_name='order_date__date', lookup_expr='lte')
    status = filters.NumberFilter(method='filter_by_status')
    has_status = filters.CharFilter(method='filter_has_status')

    class Meta:
        model = Order
        fields = ['member', 'ordered_by', 'date_from', 'date_to', 'status']

    def filter_member_name(self, queryset, name, value):
        """Filter by member name (first or last)"""
        return queryset.filter(
            Q(member__name__icontains=value) |
            Q(member__lastname__icontains=value)
        )

    def filter_by_status(self, queryset, name, value):
        """Filter orders that have items with specific status"""
        return queryset.filter(items__status__id=value).distinct()

    def filter_has_status(self, queryset, name, value):
        """Filter orders that have items with specific status code"""
        return queryset.filter(items__status__code=value).distinct()


class OrderItemFilter(filters.FilterSet):
    """Filter for order items"""

    order = filters.NumberFilter(field_name='order__id')
    member = filters.NumberFilter(field_name='order__member__id')
    status = filters.NumberFilter(field_name='status__id')
    status_code = filters.CharFilter(field_name='status__code')
    item = filters.NumberFilter(field_name='item__id')
    item_category = filters.CharFilter(field_name='item__category')
    date_from = filters.DateFilter(field_name='order__order_date__date', lookup_expr='gte')
    date_to = filters.DateFilter(field_name='order__order_date__date', lookup_expr='lte')
    has_size = filters.BooleanFilter(method='filter_has_size')

    class Meta:
        model = OrderItem
        fields = ['order', 'member', 'status', 'status_code', 'item',
                 'item_category', 'date_from', 'date_to']

    def filter_has_size(self, queryset, name, value):
        """Filter items that have/don't have size specified"""
        if value:
            return queryset.exclude(size='')
        else:
            return queryset.filter(size='')


class OrderableItemFilter(filters.FilterSet):
    """Filter for orderable items"""

    category = filters.CharFilter(lookup_expr='iexact')
    has_sizes = filters.BooleanFilter()
    is_active = filters.BooleanFilter()
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = OrderableItem
        fields = ['category', 'has_sizes', 'is_active']

    def filter_search(self, queryset, name, value):
        """Search in name, category, and description"""
        return queryset.filter(
            Q(name__icontains=value) |
            Q(category__icontains=value) |
            Q(description__icontains=value)
        )


class OrderStatusFilter(filters.FilterSet):
    """Filter for order statuses"""

    is_active = filters.BooleanFilter()
    code = filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = OrderStatus
        fields = ['is_active', 'code']
