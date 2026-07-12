"""
ViewSets for Stock (read-only) and Transaction (full CRUD + discard statistics).
"""

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory.models import Stock, Transaction
from jf_manager_backend.mixins import BasePermissionedViewSet

from .access import filter_item_department_queryset_for_user
from .serializers import StockSerializer, TransactionSerializer


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
