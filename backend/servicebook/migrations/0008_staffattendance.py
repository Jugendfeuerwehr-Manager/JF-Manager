from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("servicebook", "0007_service_training_session"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffAttendance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "state",
                    models.CharField(
                        choices=[("A", "Anwesend"), ("E", "Entschuldigt"), ("F", "Fehlend")], max_length=1
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_attendances",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="staff_attendances",
                        to="servicebook.service",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("person", "service"), name="unique_staff_service_attendance")
                ]
            },
        ),
    ]
