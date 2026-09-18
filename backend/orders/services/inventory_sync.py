"""Keeps the OrderableItem catalog in sync with inventory.Item.

OrderableItem is a technical bridge only. Articles are managed exclusively in the
Inventory module; this module derives/updates the matching OrderableItem so that
orders can always reference an inventory item without manual duplicate upkeep.
"""

from orders.models import OrderableItem


def _sizes_from_variants(inventory_item):
    sizes = set()
    for variant in inventory_item.variants.all():
        for value in (variant.variant_attributes or {}).values():
            if value:
                sizes.add(str(value))
    return ",".join(sorted(sizes))


def sync_orderable_item(inventory_item):
    """Create or update the OrderableItem bridge row for one inventory item."""
    category_name = inventory_item.category.name if inventory_item.category_id else "Sonstiges"
    orderable_item, _created = OrderableItem.objects.update_or_create(
        inventory_item=inventory_item,
        defaults={
            "name": inventory_item.name,
            "category": category_name,
            "has_sizes": inventory_item.is_variant_parent,
            "available_sizes": _sizes_from_variants(inventory_item) if inventory_item.is_variant_parent else "",
            "is_active": True,
        },
    )
    return orderable_item
