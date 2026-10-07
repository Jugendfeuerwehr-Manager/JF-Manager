import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend
from django.utils.deprecation import MiddlewareMixin
from dynamic_preferences.registries import global_preferences_registry


class EmailConfigMiddleware(MiddlewareMixin):
    """
    Middleware that updates Django's email settings from dynamic preferences.
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response
        blocked_backend = "jf_manager_backend.email_middleware.UnavailableSMTPBackend"
        if blocked_backend != settings.EMAIL_BACKEND:
            UnavailableSMTPBackend.configured_backend = settings.EMAIL_BACKEND
        self._email_backend = UnavailableSMTPBackend.configured_backend
        self._smtp_unavailable = False
        self.update_email_settings()

    def process_request(self, request):
        """
        Update email settings on each request to ensure they're always current.
        """
        self.update_email_settings()
        return None

    def update_email_settings(self):
        """
        Update Django email settings from dynamic preferences.
        """
        global_preferences = global_preferences_registry.manager()

        try:
            email_host_password = global_preferences.get("email__email_host_password")
        except ImproperlyConfigured:
            if not (settings.DEBUG and getattr(settings, "DEV_ALLOW_UNREADABLE_SMTP", False)):
                raise
            settings.EMAIL_HOST_PASSWORD = ""
            settings.EMAIL_HOST = ""
            settings.EMAIL_BACKEND = "jf_manager_backend.email_middleware.UnavailableSMTPBackend"
            if not self._smtp_unavailable:
                logging.getLogger(__name__).warning(
                    "Lokale SMTP-Zugangsdaten nicht entschlüsselbar. E-Mail-Versand gesperrt; "
                    "ursprünglichen Schlüssel ergänzen oder SMTP-Passwort in den Einstellungen neu eingeben."
                )
            self._smtp_unavailable = True
            return
        if self._smtp_unavailable:
            settings.EMAIL_BACKEND = self._email_backend
            self._smtp_unavailable = False

        # Publish connection settings only after credentials were decrypted.
        email_host = global_preferences.get("email__email_host")
        settings.EMAIL_HOST = email_host

        # Port is stored as integer
        email_port = global_preferences.get("email__email_port")
        if email_port:
            settings.EMAIL_PORT = email_port

        # TLS and SSL settings (boolean)
        settings.EMAIL_USE_TLS = global_preferences.get("email__email_use_tls")
        settings.EMAIL_USE_SSL = global_preferences.get("email__email_use_ssl")

        # Auth settings
        email_host_user = global_preferences.get("email__email_host_user")
        settings.EMAIL_HOST_USER = email_host_user

        settings.EMAIL_HOST_PASSWORD = email_host_password

        # From email
        default_from_email = global_preferences.get("email__default_from_email")
        if default_from_email:
            settings.DEFAULT_FROM_EMAIL = default_from_email


class UnavailableSMTPBackend(BaseEmailBackend):
    """Never fall back to unauthenticated or silently successful email delivery."""

    configured_backend = "django.core.mail.backends.smtp.EmailBackend"

    def send_messages(self, email_messages):
        raise ImproperlyConfigured(
            "E-Mail-Versand gesperrt: gespeichertes SMTP-Passwort nicht entschlüsselbar. "
            "Schlüsselring prüfen oder das SMTP-Passwort neu eingeben."
        )
