from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "users"

    def ready(self):
        from . import devices  # noqa: F401  (signal receivers)
