from rest_framework import serializers

from inventory.models import (
    Category,
    Item,
    ItemVariant,
    Stock,
    StorageLocation,
    Transaction,
)

from .access import (
    can_manage_department,
    is_location_allowed_for_item_department,
    is_org_wide_user,
)


class CategorySerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "schema", "item_count"]


class ItemVariantSerializer(serializers.ModelSerializer):
    parent_item_name = serializers.CharField(source="parent_item.name", read_only=True)
    category_id = serializers.IntegerField(source="parent_item.category_id", read_only=True)
    category_name = serializers.CharField(source="parent_item.category.name", read_only=True)
    total_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = ItemVariant
        fields = [
            "id",
            "parent_item",
            "parent_item_name",
            "category_id",
            "category_name",
            "sku",
            "variant_attributes",
            "total_stock",
        ]


class ItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    variants = ItemVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = [
            "id",
            "name",
            "category",
            "category_name",
            "base_unit",
            "attributes",
            "is_variant_parent",
            # legacy fields (kept for backward compat of forms)
            "size",
            "identifier1",
            "identifier2",
            "rented_by",
            "department",
            "total_stock",
            "variants",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or getattr(request, "method", "GET") in ("GET", "HEAD", "OPTIONS"):
            return attrs

        department = attrs.get("department", getattr(self.instance, "department", None))
        department_id = getattr(department, "id", None)

        if not can_manage_department(user, department_id):
            raise serializers.ValidationError(
                {"department": "Artikel dürfen nur in der eigenen Abteilung verwaltet werden."}
            )

        return attrs


class StorageLocationSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    full_path = serializers.SerializerMethodField()

    class Meta:
        model = StorageLocation
        fields = [
            "id",
            "name",
            "parent",
            "parent_name",
            "is_member",
            "member",
            "department",
            "full_path",
        ]

    def get_full_path(self, obj):  # pragma: no cover - simple helper
        return obj.get_full_path()

    def validate(self, attrs):
        attrs = super().validate(attrs)

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or getattr(request, "method", "GET") in ("GET", "HEAD", "OPTIONS"):
            return attrs

        department = attrs.get("department", getattr(self.instance, "department", None))
        department_id = getattr(department, "id", None)

        if not can_manage_department(user, department_id):
            raise serializers.ValidationError(
                {"department": "Lagerorte dürfen nur in der eigenen Abteilung verwaltet werden."}
            )

        return attrs


class StockSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True, allow_null=True)
    variant_display = serializers.SerializerMethodField()
    location_name = serializers.CharField(source="location.name", read_only=True)
    category_id = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            "id",
            "item",
            "item_name",
            "item_variant",
            "variant_display",
            "location",
            "location_name",
            "quantity",
            "category_id",
            "category_name",
            "display_name",
        ]

    def get_variant_display(self, obj):
        if obj.item_variant:
            return str(obj.item_variant)
        return None

    def get_category_id(self, obj):
        category = obj.get_category()
        return category.id if category else None

    def get_category_name(self, obj):
        category = obj.get_category()
        return category.name if category else None

    def get_display_name(self, obj):
        """Returns a unified display name for the stock item"""
        return obj.get_item_name()


class TransactionSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="get_item_name", read_only=True)
    source_name = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()
    user_username = serializers.CharField(source="user.username", read_only=True)
    discard_reason_display = serializers.CharField(source="get_discard_reason_display", read_only=True)

    class Meta:
        model = Transaction
        read_only_fields = ["date", "user", "former_member_name"]
        fields = [
            "id",
            "transaction_type",
            "item",
            "item_variant",
            "source",
            "target",
            "quantity",
            "date",
            "note",
            "user",
            "item_name",
            "source_name",
            "target_name",
            "user_username",
            "discard_reason",
            "discard_reason_display",
            "former_member_name",
        ]

    def get_source_name(self, obj):
        if obj.source:
            return obj.source.name
        if obj.former_member_name:
            return f"[{obj.former_member_name}]"
        return None

    def get_target_name(self, obj):
        if obj.target:
            return obj.target.name
        if obj.former_member_name:
            return f"[{obj.former_member_name}]"
        return None

    def validate(self, attrs):
        """Custom validation for transaction data"""
        request = self.context.get("request")
        user = getattr(request, "user", None)

        transaction_type = attrs.get("transaction_type")
        discard_reason = attrs.get("discard_reason")

        # Validate discard_reason for DISCARD transactions
        if transaction_type == "DISCARD" and not discard_reason:
            raise serializers.ValidationError(
                {"discard_reason": "Aussortierungsgrund ist erforderlich für DISCARD-Transaktionen."}
            )

        if transaction_type != "DISCARD" and discard_reason:
            raise serializers.ValidationError(
                {"discard_reason": "Aussortierungsgrund kann nur bei DISCARD-Transaktionen angegeben werden."}
            )

        item = attrs.get("item", getattr(self.instance, "item", None))
        item_variant = attrs.get("item_variant", getattr(self.instance, "item_variant", None))
        source = attrs.get("source", getattr(self.instance, "source", None))
        target = attrs.get("target", getattr(self.instance, "target", None))

        item_department_id = None
        if item is not None:
            item_department_id = item.department_id
        elif item_variant is not None:
            item_department_id = item_variant.parent_item.department_id

        if user and not is_org_wide_user(user):
            if not can_manage_department(user, item_department_id):
                raise serializers.ValidationError(
                    {"item": "Transaktionen sind nur für Artikel der eigenen Abteilung erlaubt."}
                )

            for field_name, location in (("source", source), ("target", target)):
                if location is None:
                    continue
                if not is_location_allowed_for_item_department(location, item_department_id):
                    raise serializers.ValidationError({field_name: "Quelle/Ziel muss zur Artikel-Abteilung gehören."})

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data.setdefault("user", request.user)
        return super().create(validated_data)
