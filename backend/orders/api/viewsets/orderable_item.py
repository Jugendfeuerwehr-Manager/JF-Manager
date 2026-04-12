"""
Orderable Item ViewSet
"""

from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from orders.api.filters import OrderableItemFilter
from orders.api.serializers import OrderableItemCreateUpdateSerializer, OrderableItemSerializer
from orders.models import OrderableItem


class OrderableItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Orderable Items (catalog)

    Provides CRUD operations and item information
    """

    queryset = OrderableItem.objects.all()
    serializer_class = OrderableItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderableItemFilter
    search_fields = ['name', 'category', 'description']
    ordering_fields = ['category', 'name', 'created_at']
    ordering = ['category', 'name']

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action in ['create', 'update', 'partial_update']:
            return OrderableItemCreateUpdateSerializer
        return OrderableItemSerializer

    def get_queryset(self):
        """Optimize queryset based on action"""
        queryset = super().get_queryset()

        # For list, only show active items by default
        if self.action == 'list' and not self.request.query_params.get('is_active'):
            queryset = queryset.filter(is_active=True)

        return queryset

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get list of all categories"""
        categories = (
            OrderableItem.objects
            .values_list('category', flat=True)
            .distinct()
            .order_by('category')
        )
        return Response(list(categories))

    @action(detail=True, methods=['get'])
    def sizes(self, request, pk=None):
        """Get available sizes for an item"""
        item = self.get_object()

        return Response({
            'has_sizes': item.has_sizes,
            'sizes': item.get_sizes_list() if item.has_sizes else []
        })

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most frequently ordered items"""

        popular_items = (
            OrderableItem.objects
            .filter(is_active=True)
            .annotate(order_count=Count('orderitem'))
            .filter(order_count__gt=0)
            .order_by('-order_count')[:10]
        )

        serializer = self.get_serializer(popular_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get items grouped by category"""
        category = request.query_params.get('category')

        if not category:
            return Response(
                {'error': 'category parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        items = self.queryset.filter(
            is_active=True,
            category__iexact=category
        )

        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)
