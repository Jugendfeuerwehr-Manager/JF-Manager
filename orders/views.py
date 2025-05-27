from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from .models import Order, OrderableItem, OrderStatus, OrderItem
from .serializers import OrderSerializer, OrderableItemSerializer, OrderStatusSerializer, OrderItemSerializer
from .selectors import get_order_list, get_orderable_item_list, get_order_status_list


# Temporäre View für Phase 1 - wird in Phase 2 erweitert
class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    
    def get_queryset(self):
        return Order.objects.select_related('member', 'ordered_by')


############################ API ################################################

class OrderViewSet(viewsets.ModelViewSet):
    """
    API Endpoint für Bestellungen
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_order_list()
    serializer_class = OrderSerializer
    filterset_fields = ['member', 'ordered_by', 'order_date']
    search_fields = ['member__name', 'member__lastname', 'notes']


class OrderableItemViewSet(viewsets.ModelViewSet):
    """
    API Endpoint für bestellbare Artikel
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_orderable_item_list()
    serializer_class = OrderableItemSerializer
    filterset_fields = ['category', 'has_sizes', 'is_active']
    search_fields = ['name', 'category', 'description']


class OrderStatusViewSet(viewsets.ModelViewSet):
    """
    API Endpoint für Bestellstatus
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = get_order_status_list()
    serializer_class = OrderStatusSerializer
    filterset_fields = ['is_active']
    search_fields = ['name', 'code']


class OrderItemViewSet(viewsets.ModelViewSet):
    """
    API Endpoint für Bestellartikel
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    queryset = OrderItem.objects.select_related('order', 'item', 'status')
    serializer_class = OrderItemSerializer
    filterset_fields = ['order', 'item', 'status', 'size']
    search_fields = ['item__name', 'notes']
