from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("external_sync", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="syncbinding",
            name="object_type",
            field=models.CharField(
                choices=[
                    ("member", "Mitglied"),
                    ("group", "Gruppe"),
                    ("department", "Abteilung"),
                ],
                max_length=20,
                verbose_name="Objekttyp",
            ),
        ),
    ]
