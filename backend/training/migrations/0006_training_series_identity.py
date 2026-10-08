import uuid
from django.db import migrations, models


def preserve_existing_series(apps, schema_editor):
    Session = apps.get_model("training", "TrainingSession")
    manager = Session.objects.using(schema_editor.connection.alias)
    parents = manager.filter(series_children__isnull=False).distinct().order_by("pk")
    for parent in parents:
        if parent.series_uuid:
            continue
        identity = uuid.uuid4()
        used = set()
        for session in manager.filter(models.Q(pk=parent.pk) | models.Q(series_parent_id=parent.pk)).order_by("pk"):
            session.series_uuid = identity
            session.original_date = session.date if session.date not in used else None
            used.add(session.date)
            session.save(update_fields=["series_uuid", "original_date"])
    # No baseline hash: existing independent plans are conservatively preserved.


class Migration(migrations.Migration):
    dependencies = [("training", "0005_trainingsession_status")]
    operations = [
        migrations.AddField(
            model_name="trainingsession",
            name="series_uuid",
            field=models.UUIDField(null=True, blank=True, db_index=True, editable=False),
        ),
        migrations.AddField(
            model_name="trainingsession",
            name="original_date",
            field=models.DateField(null=True, blank=True, editable=False),
        ),
        migrations.AddField(
            model_name="trainingsession",
            name="series_baseline_hash",
            field=models.CharField(max_length=64, blank=True, editable=False),
        ),
        migrations.RunPython(preserve_existing_series, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="trainingsession",
            constraint=models.UniqueConstraint(
                fields=("series_uuid", "original_date"), name="unique_training_series_occurrence"
            ),
        ),
    ]
