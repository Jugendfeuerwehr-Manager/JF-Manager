"""Validate and optionally re-encrypt every stored secret with the primary key."""

import json

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from jf_manager_backend.encrypted_fields import decrypt_secret


class Command(BaseCommand):
    help = "Prüft Schlüsselring; --apply verschlüsselt Sync-/LDAP-/OIDC-Zugangsdaten und MFA-Geheimnisse atomar neu."
    targets = (
        ("external_sync", "SyncJob", "credentials"),
        ("settings_manager", "LDAPConfig", "bind_password"),
        ("settings_manager", "OIDCConfig", "client_secret"),
        ("users", "MFADevice", "secret"),
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        count = 0
        try:
            for app, name, field_name in self.targets:
                model = apps.get_model(app, name)
                field = model._meta.get_field(field_name)
                # Serialize against concurrent administrative changes.
                ids = list(model.objects.select_for_update().values_list("pk", flat=True))
                table = connection.ops.quote_name(model._meta.db_table)
                column = connection.ops.quote_name(field.column)
                pk_column = connection.ops.quote_name(model._meta.pk.column)
                with connection.cursor() as cursor:
                    for pk in ids:
                        cursor.execute(f"SELECT {column} FROM {table} WHERE {pk_column} = %s", [pk])
                        raw = cursor.fetchone()[0]
                        if raw is None:
                            continue
                        if field_name == "credentials":
                            # SQLite returns encoded JSON; PostgreSQL may return the decoded string.
                            token = json.loads(raw) if raw.startswith('"') else raw
                            value = json.loads(decrypt_secret(token))
                            if not isinstance(value, dict):
                                raise ValueError("Ungültiges JSON-Objekt")
                        else:
                            value = decrypt_secret(raw)
                        if options["apply"]:
                            prepared = field.get_db_prep_save(value, connection)
                            cursor.execute(f"UPDATE {table} SET {column} = %s WHERE {pk_column} = %s", [prepared, pk])
                        count += 1
        except Exception as exc:
            # Do not expose values, provider errors or key material in command output.
            raise CommandError(
                "Umverschlüsselung abgebrochen; Schlüsselring und Datenformat prüfen. Keine Änderungen übernommen."
            ) from exc
        self.stdout.write(f"{count} Geheimnisfelder {'umverschlüsselt' if options['apply'] else 'geprüft'}.")
