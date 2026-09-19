"""
Order Item serializers with status tracking and validation
"""

from django.db import transaction as db_transaction
from rest_framework import serializers

from inventory.api.access import (
    can_manage_department,
    get_user_department_ids,
    is_location_allowed_for_item_department,
    is_org_wide_user,
)
from inventory.models import ItemVariant, Stock, StorageLocation, Transaction
from orders.models import OrderItem, OrderItemStatusHistory
from orders.notifications import OrderWorkflowService

from .order_status import OrderStatusMinimalSerializer
from .orderable_item import OrderableItemMinimalSerializer


class OrderItemStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for status history"""

    changed_by_display = serializers.CharField(source="changed_by.get_full_name", read_only=True)
    old_status = serializers.IntegerField(source="from_status.id", read_only=True)
    old_status_name = serializers.CharField(source="from_status.name", read_only=True)
    new_status = serializers.IntegerField(source="to_status.id", read_only=True)
    new_status_name = serializers.CharField(source="to_status.name", read_only=True)

    class Meta:
        model = OrderItemStatusHistory
        fields = [
            "id",
            "old_status",
            "old_status_name",
            "new_status",
            "new_status_name",
            "changed_by",
            "changed_by_display",
            "changed_at",
            "notes",
        ]
        read_only_fields = ["id", "changed_at", "changed_by"]


class OrderItemSerializer(serializers.ModelSerializer):
    """Read serializer with full details"""

    item_details = OrderableItemMinimalSerializer(source="item", read_only=True)
    status_details = OrderStatusMinimalSerializer(source="status", read_only=True)

    # Backward compatibility fields
    item_name = serializers.CharField(source="item.name", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)
    status_code = serializers.CharField(source="status.code", read_only=True)
    status_color = serializers.CharField(source="status.color", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order",
            "item",
            "item_details",
            "item_name",
            "size",
            "quantity",
            "status",
            "status_details",
            "status_name",
            "status_code",
            "status_color",
            "received_date",
            "receipt_transaction",
            "loan_transaction",
            "delivered_date",
            "notes",
        ]
        read_only_fields = [
            "id",
            "item_details",
            "item_name",
            "status_details",
            "status_name",
            "status_color",
            "receipt_transaction",
            "loan_transaction",
        ]


class OrderItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating order items"""

    class Meta:
        model = OrderItem
        fields = ["item", "size", "quantity", "status", "notes"]

    def validate_quantity(self, value):
        """Ensure quantity is positive"""
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value

    def validate(self, attrs):
        """Validate size for items that have sizes"""
        item = attrs.get("item")
        size = attrs.get("size", "")

        if item and item.has_sizes and not size:
            raise serializers.ValidationError({"size": "Size is required for this item"})

        return attrs


class OrderItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order items with status transition validation"""

    receipt_location = serializers.PrimaryKeyRelatedField(
        queryset=StorageLocation.objects.filter(is_member=False), required=False, write_only=True
    )
    create_loan = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = OrderItem
        fields = ["size", "quantity", "status", "notes", "receipt_location", "create_loan"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Die Menge muss mindestens 1 sein.")
        return value

    def validate_status(self, value):
        """Validate status transitions"""
        if self.instance:
            old_status = self.instance.status
            new_status = value

            if old_status != new_status and not OrderWorkflowService.can_transition_to(old_status, new_status):
                raise serializers.ValidationError(f'Cannot transition from "{old_status.name}" to "{new_status.name}"')

        return value

    def update(self, instance, validated_data):
        """Record receipt and status together, once per order item."""
        request = self.context.get("request")
        user = request.user if request else None
        location = validated_data.pop("receipt_location", None)
        create_loan = validated_data.pop("create_loan", False)
        with db_transaction.atomic():
            instance = (
                OrderItem.objects.select_for_update()
                .select_related("status", "item__inventory_item")
                .get(pk=instance.pk)
            )
            new_status = validated_data.get("status", instance.status)
            if new_status != instance.status and not OrderWorkflowService.can_transition_to(
                instance.status, new_status
            ):
                raise serializers.ValidationError({"status": "Dieser Statuswechsel ist nicht erlaubt."})
            if instance.receipt_transaction_id and any(
                key in validated_data and validated_data[key] != getattr(instance, key) for key in ("size", "quantity")
            ):
                raise serializers.ValidationError(
                    "Ein bereits gebuchter Wareneingang kann nicht nachträglich geändert werden."
                )

            receiving = new_status.code.upper() == "RECEIVED" and instance.status_id != new_status.pk
            if receiving and instance.item.inventory_item_id:
                if validated_data.get("quantity", instance.quantity) < 1:
                    raise serializers.ValidationError({"quantity": "Die Menge muss mindestens 1 sein."})
                if instance.receipt_transaction_id:
                    raise serializers.ValidationError(
                        {"status": "Für diese Position wurde der Eingang bereits gebucht."}
                    )
                if location is None:
                    raise serializers.ValidationError(
                        {"receipt_location": "Bitte einen Lagerort für den Wareneingang wählen."}
                    )
                inventory_item = instance.item.inventory_item
                if not can_manage_department(user, inventory_item.department_id) or (
                    not is_org_wide_user(user)
                    and not is_location_allowed_for_item_department(location, inventory_item.department_id)
                ):
                    raise serializers.ValidationError({"receipt_location": "Kein Zugriff auf diesen Lagerort."})
                size = validated_data.get("size", instance.size)
                if inventory_item.is_variant_parent:
                    variants = list(ItemVariant.objects.filter(parent_item=inventory_item))
                    matches = [
                        variant
                        for variant in variants
                        if size and str(size) in {str(value) for value in (variant.variant_attributes or {}).values()}
                    ]
                    if len(matches) != 1:
                        raise serializers.ValidationError(
                            {"size": "Die Größe muss genau einer Inventarvariante entsprechen."}
                        )
                    stock_identity = {"item_variant": matches[0]}
                else:
                    if size:
                        raise serializers.ValidationError({"size": "Dieser Inventarartikel hat keine Größenvarianten."})
                    stock_identity = {"item": inventory_item}
                receipt = Transaction.objects.create(
                    transaction_type="IN",
                    target=location,
                    quantity=validated_data.get("quantity", instance.quantity),
                    note=f"Wareneingang Bestellung #{instance.order_id}, Position #{instance.pk}",
                    user=user,
                    **stock_identity,
                )
                instance.receipt_transaction = receipt

            if create_loan:
                if new_status.code.upper() != "DELIVERED":
                    raise serializers.ValidationError({"create_loan": "Eine Ausleihe ist nur bei Ausgabe möglich."})
                if instance.item.inventory_item_id and not instance.loan_transaction_id:
                    receipt = instance.receipt_transaction
                    if receipt is None:
                        raise serializers.ValidationError(
                            {"create_loan": "Für diese Position muss zuerst ein Wareneingang gebucht sein."}
                        )
                    inventory_item = instance.item.inventory_item
                    if not can_manage_department(user, inventory_item.department_id):
                        raise serializers.ValidationError({"create_loan": "Kein Zugriff auf diesen Artikel."})
                    member = instance.order.member
                    if not is_org_wide_user(user) and not set(
                        member.departments.values_list("id", flat=True)
                    ).intersection(get_user_department_ids(user)):
                        raise serializers.ValidationError({"create_loan": "Kein Zugriff auf dieses Mitglied."})
                    source = receipt.target
                    if source is None or source.is_member:
                        raise serializers.ValidationError(
                            {"create_loan": "Der Wareneingang hat keinen gültigen Lagerort."}
                        )
                    stock_identity = {"item": receipt.item, "item_variant": receipt.item_variant}
                    source_stock = Stock.objects.select_for_update().filter(location=source, **stock_identity).first()
                    if source_stock is None or source_stock.quantity < instance.quantity:
                        raise serializers.ValidationError(
                            {"create_loan": "Am Lagerort des Wareneingangs ist nicht genügend Bestand vorhanden."}
                        )
                    member_location, _ = StorageLocation.objects.get_or_create(
                        member=member,
                        defaults={
                            "name": f"{member.name} {member.lastname}",
                            "is_member": True,
                            "department": member.departments.filter(pk=inventory_item.department_id).first()
                            or member.departments.first(),
                        },
                    )
                    if not member_location.is_member:
                        raise serializers.ValidationError({"create_loan": "Der Lagerort des Mitglieds ist ungültig."})
                    if not is_org_wide_user(user) and not is_location_allowed_for_item_department(
                        source, inventory_item.department_id
                    ):
                        raise serializers.ValidationError({"create_loan": "Kein Zugriff auf den Quelllagerort."})
                    if not is_org_wide_user(user) and not is_location_allowed_for_item_department(
                        member_location, inventory_item.department_id
                    ):
                        raise serializers.ValidationError({"create_loan": "Kein Zugriff auf den Mitglieds-Lagerort."})
                    instance.loan_transaction = Transaction.objects.create(
                        transaction_type="LOAN",
                        source=source,
                        target=member_location,
                        quantity=instance.quantity,
                        note=f"Ausleihe aus Bestellung #{instance.order_id}, Position #{instance.pk}",
                        user=user,
                        **stock_identity,
                    )

            for key, value in validated_data.items():
                setattr(instance, key, value)
            instance.save(changed_by=user)
            return instance


class OrderItemMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for nested use in orders"""

    item_name = serializers.CharField(source="item.name", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)
    status_color = serializers.CharField(source="status.color", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "item", "item_name", "size", "quantity", "status", "status_name", "status_color"]
