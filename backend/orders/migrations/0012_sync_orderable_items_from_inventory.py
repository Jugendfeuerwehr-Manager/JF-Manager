from django.db import migrations


def sync_orderable_items_from_inventory(apps, schema_editor):
    """Backfill: every existing inventory item gets its OrderableItem bridge row."""
    Item = apps.get_model("inventory", "Item")
    OrderableItem = apps.get_model("orders", "OrderableItem")

    for item in Item.objects.all():
        category_name = item.category.name if item.category_id else "Sonstiges"
        sizes = set()
        if item.is_variant_parent:
            for variant in item.variants.all():
                for value in (variant.variant_attributes or {}).values():
                    if value:
                        sizes.add(str(value))

        OrderableItem.objects.update_or_create(
            inventory_item=item,
            defaults={
                "name": item.name,
                "category": category_name,
                "has_sizes": item.is_variant_parent,
                "available_sizes": ",".join(sorted(sizes)),
                "is_active": True,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0011_alter_orderableitem_inventory_item_unique"),
        ("inventory", "0012_item_is_standard_item"),
    ]

    operations = [
        migrations.RunPython(sync_orderable_items_from_inventory, noop),
    ]
