"""
ViewSets for Category, Item, and ItemVariant.
"""
from django.db.models import Q, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory.models import Category, Item, ItemVariant, Stock
from jf_manager_backend.mixins import BasePermissionedViewSet

from .serializers import (
    CategorySerializer,
    ItemSerializer,
    ItemVariantSerializer,
    StockSerializer,
)


class CategoryViewSet(BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = Category.objects.all()  # overridden by get_queryset; required for DRF router basename
    serializer_class = CategorySerializer
    search_fields = ["name"]
    filterset_fields = ["name"]

    def get_queryset(self):
        from django.db.models import Count
        return Category.objects.annotate(item_count=Count("item")).all()

    @action(detail=True, methods=["get"], url_path="items")
    def items(self, request, pk=None):
        category = self.get_object()
        items = Item.objects.filter(category=category).select_related("category")
        page = self.paginate_queryset(items)
        serializer = ItemSerializer(page or items, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ItemViewSet(BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = Item.objects.select_related("category").prefetch_related("variants")
    serializer_class = ItemSerializer
    search_fields = ["name", "category__name", "identifier1", "identifier2"]
    filterset_fields = ["category", "is_variant_parent"]

    @action(detail=True, methods=["get"], url_path="variants")
    def variants(self, request, pk=None):
        item = self.get_object()
        qs = item.variants.all().select_related("parent_item__category")
        serializer = ItemVariantSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="stock")
    def stock(self, request, pk=None):
        item = self.get_object()
        stock_qs = Stock.objects.filter(item=item) | Stock.objects.filter(item_variant__parent_item=item)
        stock_qs = stock_qs.select_related("location", "item", "item_variant", "item_variant__parent_item")
        serializer = StockSerializer(stock_qs, many=True)
        total = stock_qs.aggregate(total=Sum("quantity"))['total'] or 0
        return Response({"total": total, "rows": serializer.data})

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response({"results": []})
        items = self.get_queryset().filter(Q(name__icontains=q) | Q(category__name__icontains=q))[:25]
        serializer = self.get_serializer(items, many=True)
        return Response({"results": serializer.data})


class ItemVariantViewSet(BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = ItemVariant.objects.select_related("parent_item__category")
    serializer_class = ItemVariantSerializer
    search_fields = ["parent_item__name", "sku"]
    filterset_fields = ["parent_item", "parent_item__category"]

    @action(detail=True, methods=["get"], url_path="stock")
    def stock(self, request, pk=None):
        variant = self.get_object()
        qs = variant.stock_set.select_related("location").all()
        serializer = StockSerializer(qs, many=True)
        total = qs.aggregate(total=Sum("quantity"))['total'] or 0
        return Response({"total": total, "rows": serializer.data})
