from django.apps import AppConfig


class DepartmentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "departments"
    verbose_name = "Abteilungen"

    def ready(self):
        from django.db.models.signals import post_migrate

        from departments.bootstrap import seed_standard_roles_after_migration

        post_migrate.connect(seed_standard_roles_after_migration, dispatch_uid="departments.seed_standard_roles")
