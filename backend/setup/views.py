from django.views.generic.edit import FormView
from django.views.generic import TemplateView
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.migrations.executor import MigrationExecutor
from django.db import connections, DEFAULT_DB_ALIAS
from django import forms
from django.urls import reverse_lazy
from django.conf import settings
from django.shortcuts import redirect
from django.template.context_processors import request
from django.db.utils import OperationalError

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

def initialize_database():
    """
    Apply all migrations to initialize the database.

    Returns:
        bool: True if the database was initialized successfully, False otherwise.
    """
    try:
        # Simple migrate without trying to be too clever
        call_command('migrate', verbosity=0)
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False

def superuser_exists():
    """
    Check if a superuser exists in the database.

    Returns:
        bool: True if a superuser exists, False otherwise.
    """
    User = get_user_model()
    try:
        return User.objects.filter(is_superuser=True).exists()
    except OperationalError:
        # If the table does not exist, return False
        return False

class SetupForm(forms.ModelForm):
    """
    Form for creating the initial superuser.
    """
    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
        widgets = {
            'password': forms.PasswordInput(),
        }

class MigrationView(TemplateView):
    """
    View to handle database migrations.

    Template:
        setup/migrations.html
    """
    template_name = 'setup/migrations.html'

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests. Check for pending migrations and initialize the database if necessary.

        Args:
            request: The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The HTTP response object.
        """
        if superuser_exists():
            return redirect('admin:index')
        try:
            connection = connections[DEFAULT_DB_ALIAS]
            connection.ensure_connection()
            initialize_database()
            if not has_pending_migrations():
                return redirect('setup:user_setup')
        except Exception:
            # Database doesn't exist or can't connect, initialize it
            initialize_database()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests. Apply all migrations and redirect to the user setup page.

        Args:
            request: The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The HTTP response object.
        """
        if superuser_exists():
            return redirect('admin:index')
        try:
            initialize_database()
            return redirect('setup:user_setup')
        except Exception as e:
            return self.render_to_response(
                self.get_context_data(error=str(e))
            )

class SetupView(FormView):
    """
    View to handle the initial superuser setup.

    Template:
        setup/setup.html
    """
    template_name = 'setup/setup.html'
    form_class = SetupForm
    success_url = reverse_lazy('admin:index')

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests. Check for pending migrations and redirect to the migration view if necessary.

        Args:
            request: The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            HttpResponse: The HTTP response object.
        """
        if superuser_exists():
            return redirect('admin:index')
        if has_pending_migrations():
            return redirect('setup:migrations')
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        """
        Handle valid form submissions. Create the initial superuser.

        Args:
            form: The submitted form.

        Returns:
            HttpResponse: The HTTP response object.
        """
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            user = form.save(commit=False)
            user.is_superuser = True
            user.is_staff = True
            user.set_password(form.cleaned_data['password'])
            user.save()
            settings.SETUP_REQUIRED = False
        return super().form_valid(form)
