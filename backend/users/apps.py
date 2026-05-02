from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "users"

    def ready(self):
        # Configure TokenAdmin fields after apps are loaded to avoid
        # importing auth token models at module import time which can
        # trigger app-loading errors when INSTALLED_APPS isn't ready.
        try:
            from rest_framework.authtoken.admin import TokenAdmin

            TokenAdmin.raw_id_fields = ["user"]
        except Exception:
            # If authtoken isn't available in the environment yet, skip
            # the customization — Django will still function and the
            # admin will use defaults.
            pass
