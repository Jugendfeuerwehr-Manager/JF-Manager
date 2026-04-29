from django.apps import AppConfig


class TrainingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'training'
    verbose_name = 'Ausbildungsplanung'

    def ready(self):
        pass
