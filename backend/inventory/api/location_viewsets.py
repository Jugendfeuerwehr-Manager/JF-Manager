"""
ViewSets for StorageLocation — including member equipment lookups.
"""
from django.db.models import Q, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory.models import Stock, StorageLocation, Transaction
from jf_manager_backend.mixins import BasePermissionedViewSet

from .serializers import StockSerializer, StorageLocationSerializer, TransactionSerializer


class StorageLocationViewSet(BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = StorageLocation.objects.select_related("parent", "member")
    serializer_class = StorageLocationSerializer
    search_fields = ["name", "parent__name", "member__name", "member__lastname"]
    filterset_fields = ["parent", "is_member", "member"]

    @action(detail=True, methods=["get"], url_path="stock")
    def stock(self, request, pk=None):
        location = self.get_object()
        qs = location.stock_set.select_related(
            "item", "item_variant", "item_variant__parent_item", "location",
        )
        serializer = StockSerializer(qs, many=True)
        total = qs.aggregate(total=Sum("quantity"))['total'] or 0
        return Response({"total": total, "rows": serializer.data})

    @action(detail=False, methods=["get", "post"], url_path="for-member/(?P<member_id>[^/.]+)")
    def for_member(self, request, member_id=None):
        """
        GET/POST: Return (or auto-create) the storage location for a member.
        Auto-creation avoids manual location management for member equipment.
        """
        from members.models import Member

        try:
            member = Member.objects.get(pk=member_id)
        except Member.DoesNotExist:
            return Response(
                {"detail": f"Member with ID {member_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            location = member.personal_storage_location
            serializer = self.get_serializer(location)
            return Response(serializer.data)
        except StorageLocation.DoesNotExist:
            pass

        location = StorageLocation.objects.create(
            name=f"{member.name} {member.lastname}",
            is_member=True,
            member=member,
            parent=None,
        )
        serializer = self.get_serializer(location)
        return_status = status.HTTP_201_CREATED if request.method == "POST" else status.HTTP_200_OK
        return Response(serializer.data, status=return_status)

    @action(detail=False, methods=["get"], url_path="member-equipment/(?P<member_id>[^/.]+)")
    def member_equipment(self, request, member_id=None):
        """Return all equipment currently loaned to a specific member."""
        from members.models import Member

        try:
            member = Member.objects.get(pk=member_id)
        except Member.DoesNotExist:
            return Response(
                {"detail": f"Member with ID {member_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            location = member.personal_storage_location
        except StorageLocation.DoesNotExist:
            return Response({
                "member_id": int(member_id),
                "member_name": f"{member.name} {member.lastname}",
                "location_id": None,
                "equipment": [],
                "total_items": 0,
                "recent_transactions": [],
            })

        stock_qs = Stock.objects.filter(
            location=location, quantity__gt=0
        ).select_related("item", "item_variant", "item_variant__parent_item", "location")
        total_items = sum(s.quantity for s in stock_qs)

        transactions_qs = Transaction.objects.filter(
            Q(source=location) | Q(target=location)
        ).select_related(
            "item", "item_variant", "item_variant__parent_item", "source", "target", "user"
        ).order_by("-date")[:20]

        return Response({
            "member_id": int(member_id),
            "member_name": f"{member.name} {member.lastname}",
            "location_id": location.id,
            "equipment": StockSerializer(stock_qs, many=True).data,
            "total_items": total_items,
            "recent_transactions": TransactionSerializer(transactions_qs, many=True).data,
        })
