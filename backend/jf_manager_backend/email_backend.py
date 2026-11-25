"""Use DB SMTP configuration for workers and commands as well as web requests."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.smtp import EmailBackend
from dynamic_preferences.registries import global_preferences_registry


def default_from_email():
    """Configured sender address; read from the DB because workers never run the email middleware."""
    configured = global_preferences_registry.manager()["email__default_from_email"]
    if configured:
        return configured
    return settings.DEFAULT_FROM_EMAIL


class ConfiguredSMTPBackend(EmailBackend):
    def open(self):
        preferences = global_preferences_registry.manager()
        # Always fail closed on unreadable credentials, even with fail_silently.
        password = preferences["email__email_host_password"]
        host = preferences["email__email_host"]
        tls = preferences["email__email_use_tls"]
        ssl = preferences["email__email_use_ssl"]
        if tls and ssl:
            raise ImproperlyConfigured(
                "SMTP: STARTTLS und direkte TLS-Verbindung dürfen nicht gleichzeitig aktiv sein."
            )
        if not host:
            raise ImproperlyConfigured("SMTP ist nicht eingerichtet; E-Mail-Versand gesperrt.")
        self.host = host
        self.port = preferences["email__email_port"]
        self.username = preferences["email__email_host_user"]
        self.password = password
        self.use_tls = tls
        self.use_ssl = ssl
        # EmailBackend caches the SSL context; configuration can change between jobs.
        self.__dict__.pop("ssl_context", None)
        return super().open()

    def send_messages(self, email_messages):
        # Messages built outside a request (RQ worker, commands) carry the static fallback sender
        # from settings; SMTP servers reject it, so substitute the configured sender address.
        sender = default_from_email()
        for message in email_messages:
            if message.from_email in (None, "", settings.DEFAULT_FROM_EMAIL):
                message.from_email = sender
        return super().send_messages(email_messages)
