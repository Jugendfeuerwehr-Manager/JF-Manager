"""
ViewSets for Category, Item, and ItemVariant.
"""

from django.db import transaction
from django.db.models import Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from departments.mixins import DepartmentScopeViewSetMixin
from inventory.api.access import (
    can_manage_department,
    can_view_item_department,
    is_org_wide_user,
    visible_item_department_ids,
)
from inventory.models import Category, Item, ItemVariant, Stock
from jf_manager_backend.mixins import BasePermissionedViewSet

from .serializers import (
    CategorySerializer,
    ItemSerializer,
    ItemVariantBulkCreateSerializer,
    ItemVariantSerializer,
    StockSerializer,
)


class CategoryWritePermission(BasePermission):
    """Global categories require global model rights and organization scope."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        action = {"POST": "add", "PUT": "change", "PATCH": "change", "DELETE": "delete"}.get(request.method)
        if action is None:
            return False
        return is_org_wide_user(request.user) and request.user.has_perm(f"inventory.{action}_category")


class CategoryViewSet(BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = Category.objects.all()  # overridden by get_queryset; required for DRF router basename
    serializer_class = CategorySerializer
    permission_classes = [*BasePermissionedViewSet.permission_classes, CategoryWritePermission]
    search_fields = ["name"]
    filterset_fields = ["name"]

    def get_queryset(self):
        from django.db.models import Count

        allowed_ids = visible_item_department_ids(self.request.user, "inventory.view_item")
        if allowed_ids is None:
            return Category.objects.annotate(item_count=Count("item"))
        visible = Q(item__department_id__in=allowed_ids) | Q(item__department__isnull=True)
        return Category.objects.annotate(item_count=Count("item", filter=visible if allowed_ids else Q(pk__isnull=True)))

    @action(detail=True, methods=["get"], url_path="items")
    def items(self, request, pk=None):
        category = self.get_object()
        items = Item.objects.filter(category=category).select_related("category")
        allowed_ids = visible_item_department_ids(request.user, "inventory.view_item")
        if allowed_ids is not None:
            items = items.filter(Q(department_id__in=allowed_ids) | Q(department__isnull=True)) if allowed_ids else items.none()
        page = self.paginate_queryset(items)
        serializer = ItemSerializer(page or items, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ItemViewSet(DepartmentScopeViewSetMixin, BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = Item.objects.select_related("category", "department").prefetch_related("variants")
    serializer_class = ItemSerializer
    include_central_records = True
    search_fields = ["name", "category__name", "identifier1", "identifier2"]
    filterset_fields = ["category", "is_variant_parent", "is_standard_item"]

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in SAFE_METHODS:
            codename = "delete" if request.method == "DELETE" else "change"
            if not can_manage_department(request.user, obj.department_id, f"inventory.{codename}_item"):
                raise PermissionDenied("Keine Berechtigung für diesen Artikel.")

    @action(detail=True, methods=["get"], url_path="variants")
    def variants(self, request, pk=None):
        item = self.get_object()
        qs = item.variants.all().select_related("parent_item__category")
        serializer = ItemVariantSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="stock")
    def stock(self, request, pk=None):
        item = self.get_object()
        if not can_view_item_department(request.user, item.department_id, "inventory.view_stock"):
            raise PermissionDenied("Kein Leserecht für den Artikelbestand.")
        stock_qs = Stock.objects.filter(item=item) | Stock.objects.filter(item_variant__parent_item=item)
        stock_qs = stock_qs.select_related("location", "item", "item_variant", "item_variant__parent_item")
        serializer = StockSerializer(stock_qs, many=True)
        total = stock_qs.aggregate(total=Sum("quantity"))["total"] or 0
        return Response({"total": total, "rows": serializer.data})

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response({"results": []})
        items = self.get_queryset().filter(Q(name__icontains=q) | Q(category__name__icontains=q))[:25]
        serializer = self.get_serializer(items, many=True)
        return Response({"results": serializer.data})


class ItemVariantViewSet(DepartmentScopeViewSetMixin, BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = ItemVariant.objects.select_related("parent_item__category")
    serializer_class = ItemVariantSerializer
    department_field = "parent_item__department"
    include_central_records = True
    search_fields = ["parent_item__name", "sku"]
    filterset_fields = ["parent_item", "parent_item__category"]

    def perform_create(self, serializer):
        # The parent item determines the department; it is not a variant field.
        serializer.save()

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in SAFE_METHODS:
            codename = "delete" if request.method == "DELETE" else "change"
            permission = f"inventory.{codename}_itemvariant"
            if not can_manage_department(request.user, obj.parent_item.department_id, permission):
                raise PermissionDenied("Keine Berechtigung für Varianten dieses Artikels.")

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        """Create missing variants for a list of attribute values in one atomic step."""
        payload = ItemVariantBulkCreateSerializer(data=request.data, context={"request": request})
        payload.is_valid(raise_exception=True)
        parent_item = payload.validated_data["parent_item"]
        attribute = payload.validated_data["attribute"]

        with transaction.atomic():
            Item.objects.select_for_update().filter(pk=parent_item.pk).first()
            existing = {
                str(attrs.get(attribute, "")).strip().casefold()
                for attrs in parent_item.variants.values_list("variant_attributes", flat=True)
                if isinstance(attrs, dict)
            }
            created, skipped = [], []
            for value in payload.validated_data["values"]:
                if value.casefold() in existing:
                    skipped.append(value)
                    continue
                created.append(
                    ItemVariant.objects.create(parent_item=parent_item, variant_attributes={attribute: value})
                )
            if created and not parent_item.is_variant_parent:
                parent_item.is_variant_parent = True
                parent_item.save(update_fields=["is_variant_parent"])

        serializer = ItemVariantSerializer(created, many=True, context={"request": request})
        return Response({"created": serializer.data, "skipped": skipped}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="stock")
    def stock(self, request, pk=None):
        variant = self.get_object()
        if not can_view_item_department(
            request.user, variant.parent_item.department_id, "inventory.view_stock"
        ):
            raise PermissionDenied("Kein Leserecht für den Variantenbestand.")
        qs = variant.stock_set.select_related("location").all()
        serializer = StockSerializer(qs, many=True)
        total = qs.aggregate(total=Sum("quantity"))["total"] or 0
        return Response({"total": total, "rows": serializer.data})
