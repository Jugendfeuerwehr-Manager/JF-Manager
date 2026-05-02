from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("training", "0002_trainingsession_department"),
        ("servicebook", "0006_service_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="training_session",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="servicebook_entry",
                to="training.trainingsession",
                verbose_name="Verknüpfte Ausbildungseinheit",
            ),
        ),
    ]
