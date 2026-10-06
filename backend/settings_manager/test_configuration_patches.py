from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from dynamic_preferences.models import GlobalPreferenceModel
from dynamic_preferences.registries import global_preferences_registry
from rest_framework.test import APIClient

from jf_manager_backend.email_middleware import EmailConfigMiddleware
from settings_manager.api.viewsets import SettingsViewSet
from settings_manager.secret_preferences import EncryptedPreferenceSerializer


class ConfigurationPatchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-config")
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="settings_manager", codename__in=["view_all_settings", "change_all_settings"]
            )
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_smtp_secret_is_encrypted_in_database_cache_and_write_only_in_api(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                "/api/v1/settings/email/", {"email_host_password": "synthetic-smtp-secret"}, format="json"
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["has_email_host_password"])
        self.assertNotIn("email_host_password", response.data)
        raw = GlobalPreferenceModel.objects.get(section="email", name="email_host_password").raw_value
        self.assertNotIn("synthetic-smtp-secret", raw)
        manager = global_preferences_registry.manager()
        self.assertEqual(manager["email__email_host_password"], "synthetic-smtp-secret")
        self.assertNotEqual(
            manager.cache.get(manager.get_cache_key("email", "email_host_password")), "synthetic-smtp-secret"
        )
        for url in ["/api/v1/settings/email/", "/api/v1/settings/"]:
            self.assertNotIn("synthetic-smtp-secret", str(self.client.get(url).data))

    def test_partial_tls_update_validates_the_existing_state(self):
        response = self.client.patch("/api/v1/settings/email/", {"email_use_ssl": True}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(SettingsViewSet()._get_category_settings("email")["email_use_tls"])
        self.assertFalse(SettingsViewSet()._get_category_settings("email")["email_use_ssl"])

    def test_partial_time_update_validates_the_existing_end(self):
        response = self.client.patch("/api/v1/settings/service/", {"service_start_time": "22:00"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SettingsViewSet()._get_category_settings("service")["service_start_time"], "18:00")

    def test_unknown_fields_are_rejected_without_saving_known_fields(self):
        response = self.client.patch(
            "/api/v1/settings/general/", {"title": "Must not save", "typo": True}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SettingsViewSet()._get_category_settings("general")["title"], "JF Manager")

    def test_failure_rolls_back_database_and_does_not_publish_partial_preference_cache(self):
        original = EncryptedPreferenceSerializer.serialize
        with (
            patch.object(EncryptedPreferenceSerializer, "serialize", side_effect=ValueError("synthetic-write-failure")),
            self.assertRaises(ValueError),
        ):
            self.client.patch(
                "/api/v1/settings/email/",
                {"email_host": "must-not-save.example", "email_host_password": "synthetic"},
                format="json",
            )
        self.assertEqual(SettingsViewSet()._get_category_settings("email")["email_host"], "")
        self.assertEqual(global_preferences_registry.manager()["email__email_host"], "")
        self.assertTrue(original("synthetic"))

    def test_omitting_password_preserves_it_and_explicit_empty_clears_runtime_password(self):
        self.client.patch("/api/v1/settings/email/", {"email_host_password": "synthetic-secret"}, format="json")
        self.client.patch("/api/v1/settings/email/", {"email_port": 2525}, format="json")
        self.assertEqual(SettingsViewSet()._get_category_settings("email")["email_host_password"], "synthetic-secret")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                "/api/v1/settings/email/", {"email_host_password": "", "email_host_user": ""}, format="json"
            )
        self.assertFalse(response.data["has_email_host_password"])
        middleware = EmailConfigMiddleware(lambda request: None)
        middleware.update_email_settings()
        from django.conf import settings

        self.assertEqual(settings.EMAIL_HOST_PASSWORD, "")
        self.assertEqual(settings.EMAIL_HOST_USER, "")

    def test_secret_rotation_checks_smtp_alongside_existing_encrypted_models(self):
        self.client.patch("/api/v1/settings/email/", {"email_host_password": "synthetic-secret"}, format="json")
        call_command("rotate_field_encryption", stdout=StringIO())
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT raw_value FROM dynamic_preferences_globalpreferencemodel WHERE section = %s AND name = %s",
                ["email", "email_host_password"],
            )
            self.assertEqual(EncryptedPreferenceSerializer.deserialize(cursor.fetchone()[0]), "synthetic-secret")

    def test_upgrade_encrypts_legacy_plaintext_and_evicts_the_old_cache(self):
        from importlib import import_module
        from types import SimpleNamespace

        from django.apps import apps

        GlobalPreferenceModel.objects.bulk_create(
            [GlobalPreferenceModel(section="email", name="email_host_password", raw_value="synthetic-legacy-secret")],
            ignore_conflicts=True,
        )
        GlobalPreferenceModel.objects.filter(section="email", name="email_host_password").update(
            raw_value="synthetic-legacy-secret"
        )
        manager = global_preferences_registry.manager()
        manager.cache.set(manager.get_cache_key("email", "email_host_password"), "synthetic-legacy-secret")
        import_module("settings_manager.migrations.0010_encrypt_smtp_preference").encrypt_smtp(
            apps, SimpleNamespace(connection=connection)
        )
        raw = GlobalPreferenceModel.objects.get(section="email", name="email_host_password").raw_value
        self.assertNotEqual(raw, "synthetic-legacy-secret")
        self.assertEqual(manager["email__email_host_password"], "synthetic-legacy-secret")
