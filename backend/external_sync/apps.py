from django.apps import AppConfig


class ExternalSyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "external_sync"
    verbose_name = "External Sync"
