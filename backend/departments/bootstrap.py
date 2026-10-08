"""Install missing standard templates after Django has created all permissions."""

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.db import connections, router
from django.db.migrations.recorder import MigrationRecorder


def seed_standard_roles_after_migration(sender, using="default", **kwargs):
    if not getattr(settings, "ROLE_SEED_ON_MIGRATE", True):
        return
    # post_migrate runs once per app. Wait for the final model app so permissions
    # from training, orders and settings exist even on a completely fresh DB.
    model_apps = [config for config in apps.get_app_configs() if config.models_module is not None]
    if not model_apps or sender != model_apps[-1] or not router.allow_migrate(using, "departments"):
        return
    recorder = MigrationRecorder(connections[using])
    if not recorder.migration_qs.filter(app="departments", name="0005_alter_roletemplate_options_and_more").exists():
        return  # A deliberate rollback to a pre-role schema must stay possible.
    call_command("seed_role_templates", database=using, stdout=kwargs.get("stdout"))
