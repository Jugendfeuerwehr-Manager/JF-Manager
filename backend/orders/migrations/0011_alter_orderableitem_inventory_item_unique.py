from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0010_dedupe_orderableitem_inventory_item"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderableitem",
            name="inventory_item",
            field=models.ForeignKey(
                blank=True,
                help_text="Gemeinsamer Inventarartikel für Lagerbestand und Bestellungen.",
                null=True,
                on_delete=models.SET_NULL,
                related_name="orderable_items",
                to="inventory.item",
                unique=True,
                verbose_name="Inventarartikel",
            ),
        ),
    ]
