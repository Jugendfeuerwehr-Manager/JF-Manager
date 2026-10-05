import json

from django.db import migrations
from jf_manager_backend.encrypted_fields import EncryptedJSONField, crypter


def encrypt_existing(apps, schema_editor):
    Job = apps.get_model("external_sync", "SyncJob")
    for job in Job.objects.using(schema_editor.connection.alias).all().iterator():
        if not isinstance(job.credentials, dict):
            raise ValueError("Sync-Zugangsdaten sind kein JSON-Objekt; Migration abgebrochen.")
        token = crypter().encrypt(json.dumps(job.credentials).encode("utf-8")).decode("ascii")
        Job.objects.using(schema_editor.connection.alias).filter(pk=job.pk).update(credentials=token)


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("external_sync", "0002_syncbinding_department_object_type")]
    operations = [
        migrations.RunPython(encrypt_existing),
        migrations.AlterField(model_name="syncjob", name="credentials", field=EncryptedJSONField(default=dict, blank=True, verbose_name="Zugangsdaten")),
    ]
