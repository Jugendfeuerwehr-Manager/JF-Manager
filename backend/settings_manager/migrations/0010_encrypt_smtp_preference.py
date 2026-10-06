from django.db import migrations


def encrypt_smtp(apps, schema_editor):
    from dynamic_preferences.registries import global_preferences_registry
    from settings_manager.secret_preferences import EncryptedPreferenceSerializer

    Preference = apps.get_model("dynamic_preferences", "GlobalPreferenceModel")
    rows = Preference.objects.using(schema_editor.connection.alias).filter(section="email", name="email_host_password")
    for row in rows:
        rows.filter(pk=row.pk).update(raw_value=EncryptedPreferenceSerializer.serialize(row.raw_value or ""))
    manager = global_preferences_registry.manager()
    manager.cache.delete(manager.get_cache_key("email", "email_host_password"))


class Migration(migrations.Migration):
    dependencies = [
        ("settings_manager", "0009_settings_write_lock"),
        ("dynamic_preferences", "0006_auto_20191001_2236"),
    ]
    operations = [migrations.RunPython(encrypt_smtp)]
