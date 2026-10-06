from django.apps import AppConfig


class SettingsManagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "settings_manager"
    verbose_name = "Einstellungen"

    def ready(self):
        # Import signal handlers
        from . import role_mapping_signals  # noqa: F401
