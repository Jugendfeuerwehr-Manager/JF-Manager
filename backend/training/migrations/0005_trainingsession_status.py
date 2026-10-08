from django.db import migrations, models


def publish_linked_sessions(apps, schema_editor):
    Session = apps.get_model("training", "TrainingSession")
    Service = apps.get_model("servicebook", "Service")
    alias = schema_editor.connection.alias
    linked = Service.objects.using(alias).exclude(training_session_id=None).values("training_session_id")
    Session.objects.using(alias).filter(pk__in=linked).update(status="published")


class Migration(migrations.Migration):
    dependencies = [("training", "0004_trainingsession_revision"), ("servicebook", "0008_staffattendance")]
    operations = [
        migrations.AddField(
            model_name="trainingsession",
            name="status",
            field=models.CharField(
                max_length=12,
                default="draft",
                verbose_name="Status",
                choices=[
                    ("draft", "Entwurf"),
                    ("published", "Veröffentlicht"),
                    ("completed", "Abgeschlossen"),
                    ("cancelled", "Abgesagt"),
                ],
            ),
        ),
        migrations.RunPython(publish_linked_sessions, migrations.RunPython.noop),
    ]
