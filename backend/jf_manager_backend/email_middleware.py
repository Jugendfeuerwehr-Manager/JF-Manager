from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from dynamic_preferences.registries import global_preferences_registry


class EmailConfigMiddleware(MiddlewareMixin):
    """
    Middleware that updates Django's email settings from dynamic preferences.
    """
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response
        self.update_email_settings()

    def process_request(self, request):
        """
        Update email settings on each request to ensure they're always current.
        """
        self.update_email_settings()
        return None

    def update_email_settings(self):
        """
        Update Django email settings from dynamic preferences.
        """
        global_preferences = global_preferences_registry.manager()
        
        # Only set values if they're provided in preferences
        email_host = global_preferences.get('email__email_host')
        if email_host:
            settings.EMAIL_HOST = email_host
            
        # Port is stored as integer
        email_port = global_preferences.get('email__email_port')
        if email_port:
            settings.EMAIL_PORT = email_port
            
        # TLS and SSL settings (boolean)
        settings.EMAIL_USE_TLS = global_preferences.get('email__email_use_tls')
        settings.EMAIL_USE_SSL = global_preferences.get('email__email_use_ssl')
        
        # Auth settings
        email_host_user = global_preferences.get('email__email_host_user')
        if email_host_user:
            settings.EMAIL_HOST_USER = email_host_user
            
        email_host_password = global_preferences.get('email__email_host_password')
        if email_host_password:
            settings.EMAIL_HOST_PASSWORD = email_host_password
            
        # From email
        default_from_email = global_preferences.get('email__default_from_email')
        if default_from_email:
            settings.DEFAULT_FROM_EMAIL = default_from_email
