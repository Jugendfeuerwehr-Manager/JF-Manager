"""
Order ViewSet with comprehensive functionality
"""

import csv
from datetime import datetime, timedelta

from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from orders.api.filters import OrderFilter
from orders.api.permissions import CanManageOrders
from orders.api.serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    OrderSerializer,
    OrderUpdateSerializer,
)
from orders.models import Order, OrderItem, OrderStatus
from orders.notifications import OrderNotificationService


class OrderViewSet(viewsets.ModelViewSet):
    """
    Comprehensive ViewSet for Order management

    Provides:
    - Full CRUD operations
    - Filtering, searching, ordering
    - Statistics and analytics
    - Bulk operations
    - Export functionality
    """

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageOrders]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderFilter
    search_fields = ['member__name', 'member__lastname', 'notes', 'items__item__name']
    ordering_fields = ['order_date', 'member__name', 'member__lastname']
    ordering = ['-order_date']

    def get_queryset(self):
        """Optimize queryset with prefetch"""
        queryset = Order.objects.select_related(
            'member',
            'member__group',
            'ordered_by'
        ).prefetch_related(
            'items__item',
            'items__status'
        )

        # For list view, add count annotation
        if self.action == 'list':
            queryset = queryset.annotate(_items_count=Count('items'))

        return queryset

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return OrderListSerializer
        elif self.action == 'retrieve':
            return OrderDetailSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return OrderUpdateSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        """Create order and send notification"""
        order = serializer.save()

        # Send notification
        OrderNotificationService.send_order_created_notification(
            order, self.request
        )

    @action(detail=True, methods=['get'])
    def detail_with_history(self, request, pk=None):
        """Get order with full item history"""
        order = self.get_object()
        serializer = OrderDetailSerializer(order)

        # Add status history for all items
        data = serializer.data
        for item_data in data['items']:
            item = OrderItem.objects.get(id=item_data['id'])
            history = item.status_history.all().order_by('-changed_at')
            from orders.api.serializers import OrderItemStatusHistorySerializer
            item_data['history'] = OrderItemStatusHistorySerializer(
                history, many=True
            ).data

        return Response(data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get comprehensive order statistics"""
        # Apply filters
        queryset = self.filter_queryset(self.get_queryset())

        # Basic counts
        total_orders = queryset.count()
        total_items = OrderItem.objects.filter(order__in=queryset).count()

        # Status breakdown
        status_breakdown = (
            OrderItem.objects
            .filter(order__in=queryset)
            .values('status__name', 'status__code', 'status__color')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Category breakdown
        category_breakdown = (
            OrderItem.objects
            .filter(order__in=queryset)
            .values('item__category')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Member statistics
        member_stats = (
            queryset
            .values('member__id', 'member__name', 'member__lastname')
            .annotate(order_count=Count('id'))
            .order_by('-order_count')[:10]
        )

        # Monthly trend (last 12 months)
        today = timezone.now().date()
        monthly_data = []
        for i in range(12):
            month_start = (today.replace(day=1) - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            count = queryset.filter(
                order_date__date__gte=month_start,
                order_date__date__lte=month_end
            ).count()

            monthly_data.append({
                'month': month_start.strftime('%Y-%m'),
                'count': count
            })

        monthly_data.reverse()

        return Response({
            'total_orders': total_orders,
            'total_items': total_items,
            'status_breakdown': list(status_breakdown),
            'category_breakdown': list(category_breakdown),
            'top_members': list(member_stats),
            'monthly_trend': monthly_data,
            'pending_items': OrderItem.objects.filter(
                order__in=queryset,
                status__code__in=['NEW', 'ORDERED']
            ).count(),
            'delivered_items': OrderItem.objects.filter(
                order__in=queryset,
                status__code='DELIVERED'
            ).count(),
        })

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent orders"""
        limit = int(request.query_params.get('limit', 10))

        recent_orders = (
            self.get_queryset()
            .order_by('-order_date')[:limit]
        )

        serializer = OrderListSerializer(recent_orders, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get orders with pending items"""
        delivered_status = OrderStatus.objects.filter(code='DELIVERED').first()
        cancelled_status = OrderStatus.objects.filter(code='CANCELLED').first()

        exclude_statuses = []
        if delivered_status:
            exclude_statuses.append(delivered_status.pk)
        if cancelled_status:
            exclude_statuses.append(cancelled_status.pk)

        pending_orders = (
            self.get_queryset()
            .exclude(items__status__pk__in=exclude_statuses)
            .distinct()
        )

        serializer = OrderListSerializer(pending_orders, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_member(self, request):
        """Get orders for a specific member"""
        member_id = request.query_params.get('member_id')

        if not member_id:
            return Response(
                {'error': 'member_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        orders = (
            self.get_queryset()
            .filter(member__id=member_id)
            .order_by('-order_date')
        )

        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def quick_create(self, request):
        """Quick order creation for common items"""
        member_id = request.data.get('member')
        item_ids = request.data.get('items', [])  # List of {item_id, size, quantity}
        notes = request.data.get('notes', 'Quick order')

        if not member_id or not item_ids:
            return Response(
                {'error': 'member and items are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build order data
        order_data = {
            'member': member_id,
            'notes': notes,
            'items': []
        }

        # Get default status
        default_status = OrderStatus.objects.filter(code='NEW').first()
        if not default_status:
            default_status = OrderStatus.objects.filter(code='ORDERED').first()
        if not default_status:
            default_status = OrderStatus.objects.first()

        for item_data in item_ids:
            order_data['items'].append({
                'item': item_data.get('item_id'),
                'size': item_data.get('size', ''),
                'quantity': item_data.get('quantity', 1),
                'status': default_status.id if default_status else None
            })

        # Create using serializer
        serializer = OrderCreateSerializer(data=order_data, context={'request': request})

        if serializer.is_valid():
            order = serializer.save()

            # Send notification
            OrderNotificationService.send_order_created_notification(order, request)

            return Response(
                OrderDetailSerializer(order).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export orders to CSV"""
        # Apply filters
        queryset = self.filter_queryset(self.get_queryset())

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="orders_{timestamp}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Order ID', 'Member', 'Group', 'Order Date', 'Ordered By',
            'Item', 'Category', 'Size', 'Quantity', 'Status',
            'Received Date', 'Delivered Date', 'Notes'
        ])

        for order in queryset:
            for item in order.items.all():
                writer.writerow([
                    order.pk,
                    order.member.get_full_name(),
                    order.member.group.name if order.member.group else '',
                    order.order_date.strftime('%Y-%m-%d %H:%M'),
                    order.ordered_by.get_full_name() if order.ordered_by else '',
                    item.item.name,
                    item.item.category,
                    item.size or '',
                    item.quantity,
                    item.status.name,
                    item.received_date.strftime('%Y-%m-%d %H:%M') if item.received_date else '',
                    item.delivered_date.strftime('%Y-%m-%d %H:%M') if item.delivered_date else '',
                    item.notes or ''
                ])

        return response

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def send_summary(self, request):
        """Send order summary to Gerätewart - for NEW orders only"""
        from django.db import transaction

        # Get parameters
        recipient_email = request.data.get('recipient_email')
        include_notes = request.data.get('include_notes', True)
        group_by_category = request.data.get('group_by_category', True)
        additional_notes = request.data.get('additional_notes', '')

        if not recipient_email:
            return Response(
                {'error': 'recipient_email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get NEW status
        try:
            new_status = OrderStatus.objects.get(code='NEW')
        except OrderStatus.DoesNotExist:
            return Response(
                {'error': 'NEW status not found in system'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build queryset - only orders with NEW items
        orders_queryset = Order.objects.filter(
            items__status=new_status
        ).distinct().order_by('-order_date')

        # Check if there are any NEW orders
        if not orders_queryset.exists():
            return Response(
                {'error': 'Keine neuen Bestellungen gefunden'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prepare filter context
        filters = {
            'status_filter': [new_status.id],
            'include_notes': include_notes,
            'group_by_category': group_by_category,
            'additional_notes': additional_notes,
        }

        try:
            # Send email
            success = OrderNotificationService.send_order_summary_notification(
                recipient_email=recipient_email,
                orders=orders_queryset,
                filters=filters,
                request=request
            )

            if success:
                # Update status from NEW to ORDERED
                with transaction.atomic():
                    try:
                        new_status = OrderStatus.objects.get(code='NEW')
                        ordered_status = OrderStatus.objects.get(code='ORDERED')

                        new_items = OrderItem.objects.filter(
                            order__in=orders_queryset,
                            status=new_status
                        )

                        updated_count = 0
                        for item in new_items:
                            item.status = ordered_status
                            item.save()
                            updated_count += 1

                        return Response({
                            'success': True,
                            'message': f'Bestellübersicht wurde erfolgreich an {recipient_email} gesendet',
                            'orders_count': orders_queryset.count(),
                            'items_updated': updated_count
                        })
                    except OrderStatus.DoesNotExist:
                        return Response({
                            'success': True,
                            'message': f'Bestellübersicht wurde erfolgreich an {recipient_email} gesendet',
                            'orders_count': orders_queryset.count(),
                            'items_updated': 0,
                            'warning': 'Status konnte nicht aktualisiert werden'
                        })
            else:
                return Response(
                    {'error': 'Fehler beim Versenden der E-Mail'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
