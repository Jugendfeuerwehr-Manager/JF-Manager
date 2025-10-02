from django.db.models import Sum, Count, Q
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from jf_manager_backend.permissions import CustomDefaultPermissions
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from inventory.models import (
    Category,
    Item,
    ItemVariant,
    StorageLocation,
    Stock,
    Transaction,
)
from .serializers import (
    CategorySerializer,
    ItemSerializer,
    ItemVariantSerializer,
    StorageLocationSerializer,
    StockSerializer,
    TransactionSerializer,
)


class BaseAuthMixin:
    # Enforce both authentication AND model-level perms (view/add/change/delete)
    permission_classes = [IsAuthenticated, CustomDefaultPermissions]
    filter_backends = [DjangoFilterBackend, SearchFilter]


class CategoryViewSet(BaseAuthMixin, viewsets.ModelViewSet):
    queryset = Category.objects.annotate(item_count=Count("item")).all()
    serializer_class = CategorySerializer
    search_fields = ["name"]
    filterset_fields = ["name"]

    @action(detail=True, methods=["get"], url_path="items")
    def items(self, request, pk=None):
        category = self.get_object()
        items = Item.objects.filter(category=category).select_related("category")
        page = self.paginate_queryset(items)
        serializer = ItemSerializer(page or items, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ItemViewSet(BaseAuthMixin, viewsets.ModelViewSet):
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


class ItemVariantViewSet(BaseAuthMixin, viewsets.ModelViewSet):
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


class StorageLocationViewSet(BaseAuthMixin, viewsets.ModelViewSet):
    queryset = StorageLocation.objects.select_related("parent", "member")
    serializer_class = StorageLocationSerializer
    search_fields = ["name", "parent__name", "member__name", "member__lastname"]
    filterset_fields = ["parent", "is_member", "member"]

    @action(detail=True, methods=["get"], url_path="stock")
    def stock(self, request, pk=None):
        location = self.get_object()
        qs = location.stock_set.select_related(
            "item",
            "item_variant",
            "item_variant__parent_item",
            "location",
        )
        serializer = StockSerializer(qs, many=True)
        total = qs.aggregate(total=Sum("quantity"))['total'] or 0
        return Response({"total": total, "rows": serializer.data})


class StockViewSet(BaseAuthMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Stock.objects.select_related(
        "item",
        "item_variant",
        "item_variant__parent_item",
        "location",
    )
    serializer_class = StockSerializer
    search_fields = ["item__name", "item_variant__parent_item__name", "location__name"]
    filterset_fields = ["item", "item_variant", "location"]


class TransactionViewSet(BaseAuthMixin, viewsets.ModelViewSet):
    queryset = Transaction.objects.select_related(
        "item",
        "item_variant",
        "item_variant__parent_item",
        "source",
        "target",
        "user",
    )
    serializer_class = TransactionSerializer
    search_fields = [
        "item__name",
        "item_variant__parent_item__name",
        "source__name",
        "target__name",
        "note",
    ]
    filterset_fields = [
        "transaction_type",
        "item",
        "item_variant",
        "source",
        "target",
    ]

    def perform_create(self, serializer):
        serializer.save()  # user injected in serializer.create
