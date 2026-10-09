from django.apps import AppConfig


class ParticipationConfig(AppConfig):
    name = "participation"
    verbose_name = "Teilnahme an Diensten"

    def ready(self):
        from . import conflict_receivers, receivers  # noqa: F401
