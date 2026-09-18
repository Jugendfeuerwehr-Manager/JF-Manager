"""
ViewSets for Stock (read-only) and Transaction (full CRUD + discard statistics).
"""

from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction as db_transaction
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory.models import Stock, StorageLocation, Transaction
from jf_manager_backend.mixins import BasePermissionedViewSet
from members.models import Member
from orders.api.serializers.order import OrderCreateSerializer, OrderDetailSerializer
from orders.models import OrderableItem, OrderStatus
from orders.services.inventory_sync import sync_orderable_item

from .access import filter_item_department_queryset_for_user, get_user_department_ids, is_org_wide_user
from .serializers import BatchLoanSerializer, StockSerializer, TransactionSerializer


class StockViewSet(BasePermissionedViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Stock.objects.select_related(
        "item",
        "item_variant",
        "item_variant__parent_item",
        "location",
    )
    serializer_class = StockSerializer
    search_fields = ["item__name", "item_variant__parent_item__name", "location__name"]
    filterset_fields = ["item", "item_variant", "location"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return filter_item_department_queryset_for_user(queryset, self.request.user)


class TransactionViewSet(BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = Transaction.objects.select_related(
        "item",
        "item_variant",
        "item_variant__parent_item",
        "source",
        "target",
        "user",
    )
    serializer_class = TransactionSerializer
    search_fields = ["item__name", "item_variant__parent_item__name", "source__name", "target__name", "note"]
    filterset_fields = ["transaction_type", "item", "item_variant", "source", "target", "discard_reason"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return filter_item_department_queryset_for_user(queryset, self.request.user)

    def perform_create(self, serializer):
        serializer.save()  # user is injected in serializer.create

    @action(detail=False, methods=["post"], url_path="batch-loan")
    def batch_loan(self, request):
        """Issue several already available items to one member atomically."""
        input_serializer = BatchLoanSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        try:
            member = Member.objects.get(pk=data["member"])
        except Member.DoesNotExist:
            return Response({"detail": "Mitglied nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)

        if not is_org_wide_user(request.user):
            allowed_departments = get_user_department_ids(request.user)
            member_departments = set(member.departments.values_list("id", flat=True))
            if not member_departments.intersection(allowed_departments):
                return Response({"detail": "Kein Zugriff auf dieses Mitglied."}, status=status.HTTP_403_FORBIDDEN)

        with db_transaction.atomic():
            member_location = StorageLocation.objects.filter(member=member, is_member=True).first()
            if member_location is None:
                member_location = StorageLocation.objects.create(
                    name=f"{member.name} {member.lastname}",
                    is_member=True,
                    member=member,
                    department=member.departments.first(),
                )

            source_stocks = []
            missing_lines = []
            for line in data["items"]:
                stock_filter = {"item": line.get("item"), "item_variant": line.get("item_variant")}
                stocks = list(
                    Stock.objects.select_for_update()
                    .filter(**stock_filter, quantity__gt=0, location__is_member=False)
                    .select_related("location")
                    .order_by("-quantity", "id")
                )
                available = sum(stock.quantity for stock in stocks)
                if available < line["quantity"]:
                    if not data["order_missing"]:
                        raise serializers.ValidationError(
                            {
                                "items": [
                                    "Nicht genügend Bestand. Für fehlende Artikel muss die Bestellung bestätigt werden."
                                ]
                            }
                        )
                    if available:
                        source_stocks.append(({**line, "quantity": available}, stocks))
                    missing_lines.append({**line, "quantity": line["quantity"] - available})
                    continue
                source_stocks.append((line, stocks))

            order = None
            if missing_lines:
                order_lines = []
                default_order_status = OrderStatus.objects.filter(code="NEW").first()
                if not default_order_status:
                    default_order_status = OrderStatus.objects.filter(code="ORDERED").first()
                if not default_order_status:
                    default_order_status = OrderStatus.objects.first()
                if default_order_status is None:
                    raise serializers.ValidationError({"order": "Kein Bestellstatus ist konfiguriert."})

                for line in missing_lines:
                    inventory_item = line.get("item") or line["item_variant"].parent_item
                    orderable_item = (
                        OrderableItem.objects.filter(inventory_item=inventory_item, is_active=True)
                        .order_by("id")
                        .first()
                    )
                    if orderable_item is None:
                        # Orders always reference an inventory item; provision the bridge row on demand.
                        orderable_item = sync_orderable_item(inventory_item)
                    size = ""
                    if line.get("item_variant"):
                        size = next(iter(line["item_variant"].variant_attributes.values()), "")
                    order_lines.append(
                        {
                            "item": orderable_item.pk,
                            "size": size,
                            "quantity": line["quantity"],
                            "status": default_order_status.pk,
                            "notes": "Vorgemerkte Ausleihe aus der Kleiderkammer",
                        }
                    )

                order_serializer = OrderCreateSerializer(
                    data={
                        "member": member.pk,
                        "department": member.departments.first().pk if member.departments.exists() else None,
                        "notes": data["note"] or "Bestellung für fehlende Ausleihartikel",
                        "items": order_lines,
                    },
                    context={"request": request},
                )
                order_serializer.is_valid(raise_exception=True)
                order = order_serializer.save()

            created_transactions = []
            for line, stocks in source_stocks:
                remaining = line["quantity"]
                for source_stock in stocks:
                    quantity = min(remaining, source_stock.quantity)
                    transaction_serializer = TransactionSerializer(
                        data={
                            "transaction_type": "LOAN",
                            "item": line.get("item").pk if line.get("item") else None,
                            "item_variant": line.get("item_variant").pk if line.get("item_variant") else None,
                            "source": source_stock.location.pk,
                            "target": member_location.pk,
                            "quantity": quantity,
                            "note": data["note"],
                        },
                        context={"request": request},
                    )
                    transaction_serializer.is_valid(raise_exception=True)
                    try:
                        created_transactions.append(transaction_serializer.save())
                    except DjangoValidationError as exc:
                        raise serializers.ValidationError({"items": exc.messages}) from exc
                    remaining -= quantity
                    if remaining == 0:
                        break

        return Response(
            {
                "transactions": TransactionSerializer(created_transactions, many=True).data,
                "order": OrderDetailSerializer(order).data if order else None,
                "missing_count": len(missing_lines),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="discard-statistics")
    def discard_statistics(self, request):
        """Breakdown of discarded items by reason, category, and time period."""
        discard_qs = self.get_queryset().filter(transaction_type="DISCARD")

        by_reason = list(
            discard_qs.values("discard_reason")
            .annotate(count=Count("id"), total_quantity=Sum("quantity"))
            .order_by("-total_quantity")
        )

        by_category_raw = (
            discard_qs.select_related("item__category", "item_variant__parent_item__category")
            .values("item__category__name", "item_variant__parent_item__category__name")
            .annotate(count=Count("id"), total_quantity=Sum("quantity"))
            .order_by("-total_quantity")
        )

        category_stats: dict = {}
        for entry in by_category_raw:
            cat_name = entry["item__category__name"] or entry["item_variant__parent_item__category__name"]
            if cat_name:
                if cat_name not in category_stats:
                    category_stats[cat_name] = {"category": cat_name, "count": 0, "total_quantity": 0}
                category_stats[cat_name]["count"] += entry["count"]
                category_stats[cat_name]["total_quantity"] += entry["total_quantity"] or 0

        now = timezone.now()
        by_time_period = {
            "last_30_days": discard_qs.filter(date__gte=now - timedelta(days=30)).aggregate(
                count=Count("id"), total_quantity=Sum("quantity")
            ),
            "last_6_months": discard_qs.filter(date__gte=now - timedelta(days=180)).aggregate(
                count=Count("id"), total_quantity=Sum("quantity")
            ),
            "all_time": discard_qs.aggregate(count=Count("id"), total_quantity=Sum("quantity")),
        }

        recent_discards = discard_qs.select_related(
            "item", "item_variant", "item_variant__parent_item", "source", "user"
        ).order_by("-date")[:10]

        return Response(
            {
                "by_reason": by_reason,
                "by_category": list(category_stats.values()),
                "by_time_period": by_time_period,
                "recent_discards": TransactionSerializer(recent_discards, many=True).data,
            }
        )

    @action(detail=False, methods=["post"], url_path="clear-former-member-names")
    def clear_former_member_names(self, request):
        """Clear all former member names from transactions (DSGVO compliance).

        Requires the ``inventory.clear_former_member_names`` permission.
        Resets the ``former_member_name`` field on every transaction that has one.
        """
        if not request.user.has_perm("inventory.clear_former_member_names"):
            return Response(
                {"detail": "Keine Berechtigung zum Löschen ehemaliger Mitgliedsnamen."},
                status=status.HTTP_403_FORBIDDEN,
            )
        cleared_count = Transaction.objects.exclude(former_member_name="").update(former_member_name="")
        return Response({"cleared_count": cleared_count})
