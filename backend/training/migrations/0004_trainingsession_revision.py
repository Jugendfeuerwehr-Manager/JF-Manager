from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("training", "0003_training_management_permissions")]
    operations = [
        migrations.AddField(
            model_name="trainingsession",
            name="revision",
            field=models.PositiveBigIntegerField(default=1, editable=False, verbose_name="Planversion"),
        ),
    ]
