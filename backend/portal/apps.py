from django.apps import AppConfig


class PortalConfig(AppConfig):
    name = "portal"
    verbose_name = "Eltern- und Mitgliederportal"

    def ready(self):
        from . import signals  # noqa: F401  (signal receivers)
