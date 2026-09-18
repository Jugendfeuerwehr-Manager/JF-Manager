from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0012_item_is_standard_item"),
        ("orders", "0008_add_email_layout_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderableitem",
            name="inventory_item",
            field=models.ForeignKey(
                blank=True,
                help_text="Gemeinsamer Inventarartikel für Lagerbestand und Bestellungen.",
                null=True,
                on_delete=models.SET_NULL,
                related_name="orderable_items",
                to="inventory.item",
                verbose_name="Inventarartikel",
            ),
        ),
    ]
