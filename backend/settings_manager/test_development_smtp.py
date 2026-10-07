from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.test import TestCase, override_settings
from dynamic_preferences.models import GlobalPreferenceModel
from dynamic_preferences.registries import global_preferences_registry
from rest_framework.test import APIClient

from jf_manager_backend.email_middleware import EmailConfigMiddleware
from jf_manager_backend.encrypted_fields import decrypt_secret
from settings_manager.secret_preferences import EncryptedPreferenceSerializer


class DevelopmentSMTPTests(TestCase):
    def setUp(self):
        self.token = Fernet(Fernet.generate_key()).encrypt(b"synthetic-old-password").decode()
        GlobalPreferenceModel.objects.bulk_create(
            [
                GlobalPreferenceModel(section="email", name="email_host_password", raw_value=self.token),
            ],
            ignore_conflicts=True,
        )
        GlobalPreferenceModel.objects.filter(section="email", name="email_host_password").update(raw_value=self.token)
        manager = global_preferences_registry.manager()
        manager.cache.delete(manager.get_cache_key("email", "email_host_password"))

    @override_settings(
        DEBUG=True, DEV_ALLOW_UNREADABLE_SMTP=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_local_start_preserves_ciphertext_and_blocks_even_silent_delivery(self):
        with self.assertLogs("jf_manager_backend.email_middleware", level="WARNING") as logs:
            middleware = EmailConfigMiddleware(lambda request: None)
        self.assertNotIn(self.token, " ".join(logs.output))
        self.assertEqual(settings.EMAIL_HOST_PASSWORD, "")
        for silent in [False, True]:
            with self.assertRaisesMessage(ImproperlyConfigured, "E-Mail-Versand gesperrt"):
                send_mail("synthetic", "synthetic", "from@example.com", ["to@example.com"], fail_silently=silent)
        self.assertEqual(
            GlobalPreferenceModel.objects.get(section="email", name="email_host_password").raw_value, self.token
        )
        with self.assertRaises(ImproperlyConfigured):
            decrypt_secret(self.token)
        middleware.update_email_settings()

    @override_settings(DEBUG=False, DEV_ALLOW_UNREADABLE_SMTP=True)
    def test_production_still_refuses_invalid_credentials(self):
        with self.assertRaises(ImproperlyConfigured):
            EmailConfigMiddleware(lambda request: None)

    @override_settings(DEBUG=True, DEV_ALLOW_UNREADABLE_SMTP=False)
    def test_development_exception_requires_explicit_opt_in(self):
        with self.assertRaises(ImproperlyConfigured):
            EmailConfigMiddleware(lambda request: None)

    @override_settings(
        DEBUG=True, DEV_ALLOW_UNREADABLE_SMTP=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_read_and_repair_through_settings_without_losing_opaque_secret_on_unrelated_patch(self):
        user = get_user_model().objects.create_user(username="synthetic-smtp-repair")
        user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="settings_manager",
                codename__in=["view_email_settings", "change_email_settings"],
            )
        )
        client = APIClient()
        client.force_authenticate(user)
        middleware = EmailConfigMiddleware(lambda request: None)
        response = client.get("/api/v1/settings/email/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["email_credentials_unavailable"])
        self.assertTrue(response.data["has_email_host_password"])
        self.assertNotIn("email_host_password", response.data)
        self.assertEqual(client.patch("/api/v1/settings/email/", {"email_port": 2525}, format="json").status_code, 200)
        self.assertEqual(
            GlobalPreferenceModel.objects.get(section="email", name="email_host_password").raw_value, self.token
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = client.patch(
                "/api/v1/settings/email/", {"email_host_password": "synthetic-replacement"}, format="json"
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["email_credentials_unavailable"])
        middleware.update_email_settings()
        self.assertEqual(settings.EMAIL_BACKEND, "django.core.mail.backends.locmem.EmailBackend")
        raw = GlobalPreferenceModel.objects.get(section="email", name="email_host_password").raw_value
        self.assertEqual(EncryptedPreferenceSerializer.deserialize(raw), "synthetic-replacement")

    def test_worker_smtp_backend_blocks_wrong_key_without_web_middleware(self):
        from unittest.mock import patch

        from jf_manager_backend.email_backend import ConfiguredSMTPBackend

        backend = ConfiguredSMTPBackend(fail_silently=True)
        with patch("django.core.mail.backends.smtp.EmailBackend.open") as network:
            with self.assertRaises(ImproperlyConfigured):
                backend.open()
            network.assert_not_called()

    def test_worker_smtp_backend_uses_current_database_credentials(self):
        from unittest.mock import patch

        from jf_manager_backend.email_backend import ConfiguredSMTPBackend

        preferences = global_preferences_registry.manager()
        GlobalPreferenceModel.objects.filter(section="email", name="email_host_password").update(
            raw_value=EncryptedPreferenceSerializer.serialize("synthetic-repaired")
        )
        preferences.cache.delete(preferences.get_cache_key("email", "email_host_password"))
        preferences["email__email_host"] = "smtp.synthetic.example"
        preferences["email__email_port"] = 2525
        preferences["email__email_host_user"] = "synthetic-smtp"
        backend = ConfiguredSMTPBackend()
        with patch("django.core.mail.backends.smtp.EmailBackend.open", return_value=True) as network:
            self.assertTrue(backend.open())
            network.assert_called_once()
        self.assertEqual(backend.host, "smtp.synthetic.example")
        self.assertEqual(backend.port, 2525)
        self.assertEqual(backend.username, "synthetic-smtp")
        self.assertEqual(backend.password, "synthetic-repaired")
