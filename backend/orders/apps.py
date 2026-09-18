from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orders"
    verbose_name = "Bestellungen"

    def ready(self):
        from . import signals  # noqa: F401  (registers post_save/post_delete receivers)
