from django.db import migrations


def dedupe_inventory_item_links(apps, schema_editor):
    """Keep only the first OrderableItem per inventory item; unlink the rest without deleting data."""
    OrderableItem = apps.get_model("orders", "OrderableItem")
    seen_inventory_item_ids = set()
    for orderable_item in OrderableItem.objects.exclude(inventory_item__isnull=True).order_by("id"):
        if orderable_item.inventory_item_id in seen_inventory_item_ids:
            orderable_item.inventory_item_id = None
            orderable_item.save(update_fields=["inventory_item"])
        else:
            seen_inventory_item_ids.add(orderable_item.inventory_item_id)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0009_orderableitem_inventory_item"),
    ]

    operations = [
        migrations.RunPython(dedupe_inventory_item_links, noop),
    ]
