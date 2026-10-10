import importlib
import json
from io import StringIO

from cryptography.fernet import Fernet, InvalidToken
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, override_settings

from external_sync.models import SyncJob
from jf_manager_backend.encryption_config import cache_key_prefix, encryption_keys
from settings_manager.models import LDAPConfig, OIDCConfig


class EncryptionConfigTests(SimpleTestCase):
    def test_missing_or_invalid_primary_is_rejected(self):
        for environment in (
            {},
            {"FIELD_ENCRYPTION_KEY": "invalid"},
            {"FIELD_ENCRYPTION_PREVIOUS_KEYS": Fernet.generate_key().decode()},
        ):
            with self.assertRaises(ImproperlyConfigured):
                encryption_keys(environment)

    def test_explicit_rotation_ring(self):
        first, previous = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        self.assertEqual(
            encryption_keys({"FIELD_ENCRYPTION_KEY": first, "FIELD_ENCRYPTION_PREVIOUS_KEYS": previous}),
            [first, previous],
        )

    def test_cache_prefix_is_bound_to_the_primary_key(self):
        first, second = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        self.assertEqual(cache_key_prefix([first, second]), cache_key_prefix([first]))
        self.assertNotEqual(cache_key_prefix([first]), cache_key_prefix([second]))
        self.assertTrue(cache_key_prefix([first]).startswith("jf_manager_backend:"))
        self.assertNotIn(first, cache_key_prefix([first]))


class StoredEncryptionTests(TestCase):
    def raw(self, model, pk, field):
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT "{field}" FROM "{model._meta.db_table}" WHERE id = %s', [pk])
            value = cursor.fetchone()[0]
        return value

    def test_sync_roundtrip_ciphertext_and_wrong_key(self):
        job = SyncJob.objects.create(
            name="Encryption test", provider="spond", credentials={"password": "synthetic-password"}
        )
        raw = self.raw(SyncJob, job.pk, "credentials")
        self.assertNotIn("synthetic-password", raw)
        self.assertEqual(SyncJob.objects.get(pk=job.pk).credentials, {"password": "synthetic-password"})
        with (
            override_settings(FIELD_ENCRYPTION_KEY=[Fernet.generate_key().decode()]),
            self.assertRaises(ImproperlyConfigured),
        ):
            SyncJob.objects.get(pk=job.pk)

    def test_rotation_all_fields_and_remove_old_key(self):
        old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        with override_settings(FIELD_ENCRYPTION_KEY=[old]):
            job = SyncJob.objects.create(name="Rotate", provider="spond", credentials={"password": "synthetic"})
            ldap = LDAPConfig.objects.create(bind_password="synthetic-ldap")
            oidc = OIDCConfig.objects.create(client_secret="synthetic-oidc")
        original = self.raw(SyncJob, job.pk, "credentials")
        with override_settings(FIELD_ENCRYPTION_KEY=[new, old]):
            call_command("rotate_field_encryption", stdout=StringIO())
            self.assertEqual(self.raw(SyncJob, job.pk, "credentials"), original)
            call_command("rotate_field_encryption", apply=True, stdout=StringIO())
        with override_settings(FIELD_ENCRYPTION_KEY=[new]):
            self.assertEqual(SyncJob.objects.get(pk=job.pk).credentials["password"], "synthetic")
            self.assertEqual(LDAPConfig.objects.get(pk=ldap.pk).bind_password, "synthetic-ldap")
            self.assertEqual(OIDCConfig.objects.get(pk=oidc.pk).client_secret, "synthetic-oidc")
        with self.assertRaises(InvalidToken):
            Fernet(old).decrypt(json.loads(self.raw(SyncJob, job.pk, "credentials")).encode())

    def test_failed_rotation_rolls_back_preceding_updates(self):
        job = SyncJob.objects.create(name="Atomic", provider="spond", credentials={"password": "synthetic"})
        ldap = LDAPConfig.objects.create(bind_password="synthetic")
        original = self.raw(SyncJob, job.pk, "credentials")
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE settings_manager_ldapconfig SET bind_password = %s WHERE id = %s", ["invalid-token", ldap.pk]
            )
        with self.assertRaises(CommandError):
            call_command("rotate_field_encryption", apply=True, stdout=StringIO())
        self.assertEqual(self.raw(SyncJob, job.pk, "credentials"), original)
        with self.assertRaises(ImproperlyConfigured):
            LDAPConfig.objects.get(pk=ldap.pk)

    def test_historical_plain_json_migration_and_atomic_failure(self):
        apps = (
            MigrationExecutor(connection)
            .loader.project_state([("external_sync", "0002_syncbinding_department_object_type")])
            .apps
        )
        OldJob = apps.get_model("external_sync", "SyncJob")
        old = OldJob.objects.create(name="Legacy", provider="spond", credentials={"password": "synthetic-legacy"})
        bad = OldJob.objects.create(name="Invalid", provider="spond", credentials="not-an-object")
        migrate = importlib.import_module("external_sync.migrations.0003_encrypt_credentials").encrypt_existing
        from types import SimpleNamespace

        with self.assertRaises(ValueError), transaction.atomic():
            migrate(apps, SimpleNamespace(connection=connection))
        self.assertIn("synthetic-legacy", self.raw(SyncJob, old.pk, "credentials"))
        OldJob.objects.filter(pk=bad.pk).delete()
        migrate(apps, SimpleNamespace(connection=connection))
        self.assertNotIn("synthetic-legacy", self.raw(SyncJob, old.pk, "credentials"))
        self.assertEqual(SyncJob.objects.get(pk=old.pk).credentials["password"], "synthetic-legacy")
