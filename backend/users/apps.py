from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "users"

    def ready(self):
        from . import checks, devices  # noqa: F401  (system checks, signal receivers)
