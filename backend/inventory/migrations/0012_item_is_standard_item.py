from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0011_add_former_member_name_to_transaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="is_standard_item",
            field=models.BooleanField(
                default=False,
                help_text="Artikel, der bei einer Ersteinkleidung standardmäßig benötigt wird.",
                verbose_name="Standardartikel",
            ),
        ),
    ]
