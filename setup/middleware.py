from django.shortcuts import redirect
from django.urls import reverse
from django.db.migrations.executor import MigrationExecutor
from django.db import connections, DEFAULT_DB_ALIAS
from django.contrib.auth import get_user_model
from django.conf import settings

def has_pending_migrations():
    """
    Check if there are any pending migrations.

    Returns:
        bool: True if there are pending migrations, False otherwise.
    """
    try:
        connection = connections[DEFAULT_DB_ALIAS]
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        return bool(plan)
    except Exception:
        # If we can't check migrations (usually because the database isn't created yet)
        return True

def superuser_exists():
    """
    Check if a superuser exists in the database.

    Returns:
        bool: True if a superuser exists, False otherwise.
    """
    User = get_user_model()
    return User.objects.filter(is_superuser=True).exists()

class SetupMiddleware:
    """
    Middleware to redirect to the setup page if there are pending migrations or no superuser exists.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(reverse('setup:user_setup')) and not request.path.startswith(reverse('setup:migrations')):
            if has_pending_migrations() or not superuser_exists():
                return redirect('setup:user_setup')
        response = self.get_response(request)
        return response
