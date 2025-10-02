from rest_framework import serializers

from inventory.models import (
    Category,
    Item,
    ItemVariant,
    StorageLocation,
    Stock,
    Transaction,
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
            "total_stock",
            "variants",
        ]


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
            "full_path",
        ]

    def get_full_path(self, obj):  # pragma: no cover - simple helper
        return obj.get_full_path()


class StockSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    variant_display = serializers.CharField(source="item_variant.__str__", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    category_id = serializers.SerializerMethodField()

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
        ]

    def get_category_id(self, obj):  # pragma: no cover
        return obj.get_category().id if obj.get_category() else None


class TransactionSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="get_item_name", read_only=True)
    source_name = serializers.CharField(source="source.name", read_only=True)
    target_name = serializers.CharField(source="target.name", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Transaction
        read_only_fields = ["date", "user"]
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
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data.setdefault("user", request.user)
        return super().create(validated_data)
