from django.apps import AppConfig


class ServicebookConfig(AppConfig):
    name = 'servicebook'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        import servicebook.signals
