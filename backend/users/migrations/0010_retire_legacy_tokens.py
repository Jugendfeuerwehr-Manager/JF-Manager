"""Retire JWT and DRF token credentials and end every existing session (SEC-07.7).

Browser logins now use server-side sessions only. Tokens issued before this
release must stop working even if the packages remain installed, and sessions
created under the old rules (without MFA) are discarded. Irreversible by design.
"""

from django.db import migrations

LEGACY_TABLES = (
    "token_blacklist_blacklistedtoken",
    "token_blacklist_outstandingtoken",
    "authtoken_token",
)
LEGACY_APPS = ("authtoken", "token_blacklist")


def retire_legacy_credentials(apps, schema_editor):
    connection = schema_editor.connection
    existing = set(connection.introspection.table_names())
    with connection.cursor() as cursor:
        for table in LEGACY_TABLES:
            if table in existing:
                cursor.execute(f"DROP TABLE {connection.ops.quote_name(table)}")
        cursor.execute("DELETE FROM django_migrations WHERE app IN (%s, %s)", LEGACY_APPS)
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label__in=LEGACY_APPS).delete()
    Session = apps.get_model("sessions", "Session")
    Session.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0009_mfa_devices"),
        ("sessions", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(retire_legacy_credentials, migrations.RunPython.noop)]
