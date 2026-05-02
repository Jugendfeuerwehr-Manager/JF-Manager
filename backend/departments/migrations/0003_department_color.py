from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("departments", "0002_replace_role_field_with_groups_m2m"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="color",
            field=models.CharField(
                default="#2563EB",
                help_text="Hex-Farbe zur visuellen Kennzeichnung (z.B. #2563EB)",
                max_length=7,
                verbose_name="Farbe",
            ),
        ),
    ]
