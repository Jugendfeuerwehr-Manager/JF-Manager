from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"

    def ready(self):
        from . import producers, signals  # noqa: F401  (NOTIF-01.5b: participation events)
