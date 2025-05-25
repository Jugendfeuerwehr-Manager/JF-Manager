from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from dynamic_preferences.registries import global_preferences_registry


class EmailSettingsForm(forms.Form):
    """Form for managing email settings in a single interface"""
    email_host = forms.CharField(
        label='SMTP Server',
        required=False,
        help_text='Hostname oder IP-Adresse des SMTP-Servers (z.B. smtp.gmail.com)'
    )
    email_port = forms.IntegerField(
        label='SMTP Port',
        required=False,
        help_text='Port des SMTP-Servers (z.B. 587 für TLS, 465 für SSL)'
    )
    email_host_user = forms.CharField(
        label='SMTP Benutzername',
        required=False,
        help_text='Benutzername für die Authentifizierung beim SMTP-Server'
    )
    email_host_password = forms.CharField(
        label='SMTP Passwort',
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text='Passwort für die Authentifizierung beim SMTP-Server'
    )
    email_use_tls = forms.BooleanField(
        label='TLS verwenden',
        required=False,
        help_text='TLS-Verschlüsselung für die E-Mail-Verbindung verwenden'
    )
    email_use_ssl = forms.BooleanField(
        label='SSL verwenden',
        required=False,
        help_text='SSL-Verschlüsselung für die E-Mail-Verbindung verwenden (nicht zusammen mit TLS)'
    )
    default_from_email = forms.EmailField(
        label='Absender E-Mail',
        required=False,
        help_text='E-Mail-Adresse, die als Absender verwendet wird'
    )

    def clean(self):
        """Validate that TLS and SSL are not both enabled"""
        cleaned_data = super().clean()
        email_use_tls = cleaned_data.get('email_use_tls')
        email_use_ssl = cleaned_data.get('email_use_ssl')

        if email_use_tls and email_use_ssl:
            raise forms.ValidationError(
                "TLS und SSL können nicht gleichzeitig aktiviert sein. Bitte wähle nur eine Verschlüsselungsmethode."
            )
        
        return cleaned_data


class EmailSettingsAdmin(admin.ModelAdmin):
    """
    Admin class for a dedicated email settings page.
    This doesn't correspond to an actual model but provides a UI.
    """
    model = None  # No actual model
    template_name = 'admin/email_settings.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_site.admin_view(self.email_settings_view), name='email_settings'),
            path('test/', self.admin_site.admin_view(self.test_email_view), name='test_email'),
        ]
        return custom_urls + urls

    def email_settings_view(self, request):
        """View for managing email settings"""
        # Get the global preferences manager
        global_preferences = global_preferences_registry.manager()
        
        if request.method == 'POST':
            form = EmailSettingsForm(request.POST)
            if form.is_valid():
                # Save values to dynamic preferences
                for field_name, value in form.cleaned_data.items():
                    pref_key = f'email__{field_name}'
                    global_preferences[pref_key] = value
                
                # Show success message
                messages.success(request, 'E-Mail Einstellungen wurden erfolgreich gespeichert.')
                
                # Redirect to the same page to refresh settings
                return HttpResponseRedirect(reverse('admin:email_settings'))
        else:
            # Initialize form with current values from preferences
            initial_data = {
                'email_host': global_preferences.get('email__email_host'),
                'email_port': global_preferences.get('email__email_port'),
                'email_host_user': global_preferences.get('email__email_host_user'),
                'email_host_password': global_preferences.get('email__email_host_password'),
                'email_use_tls': global_preferences.get('email__email_use_tls'),
                'email_use_ssl': global_preferences.get('email__email_use_ssl'),
                'default_from_email': global_preferences.get('email__default_from_email'),
            }
            form = EmailSettingsForm(initial=initial_data)
        
        # Current settings from Django's settings (after middleware has applied preferences)
        current_settings = {
            'EMAIL_HOST': settings.EMAIL_HOST,
            'EMAIL_PORT': settings.EMAIL_PORT,
            'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
            'EMAIL_HOST_PASSWORD': '*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else '',
            'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
            'EMAIL_USE_SSL': settings.EMAIL_USE_SSL,
            'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        }
        
        context = {
            'title': 'E-Mail Einstellungen',
            'form': form,
            'current_settings': current_settings,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request),
            'opts': self.model._meta if self.model else None,
            'app_label': 'email_settings',
        }
        
        return render(request, self.template_name, context)

    def test_email_view(self, request):
        """View for testing email settings"""
        # Reuse the existing test email view
        from .email_admin import CustomGlobalPreferenceAdmin
        
        # Create an instance of the custom admin to use its test email view
        admin_instance = CustomGlobalPreferenceAdmin(model=None, admin_site=admin.site)
        return admin_instance.test_email_view(request)
    
    def has_add_permission(self, request):
        """No adding allowed as this isn't a real model"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Always allow changes if user can access admin"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """No deletion allowed as this isn't a real model"""
        return False


# Create a dummy class for admin registration
class EmailSettingsAdminSite:
    """Dummy class to use with EmailSettingsAdmin"""
    pass


# Create a dummy model for admin registration
email_settings_site = EmailSettingsAdminSite()
email_settings_site._meta = type('_meta', (object,), {'app_label': 'email_settings', 'model_name': 'settings'})


# Set up the admin URL for email settings
admin.site.register_view(
    path='email-settings/', 
    view=EmailSettingsAdmin(model=email_settings_site, admin_site=admin.site).email_settings_view,
    name='Email Settings'
)

# Add a view for testing email
admin.site.register_view(
    path='email-settings/test/', 
    view=EmailSettingsAdmin(model=email_settings_site, admin_site=admin.site).test_email_view,
    name='Test Email'
)

# Add the email settings to the admin index
original_app_list = admin.site.get_app_list

def custom_app_list(request):
    app_list = original_app_list(request)
    
    # Add email settings to app list
    email_app = {
        'name': 'E-Mail',
        'app_label': 'email_settings',
        'app_url': '/admin/email-settings/',
        'has_module_perms': True,
        'models': [
            {
                'name': 'E-Mail Einstellungen',
                'object_name': 'EmailSettings',
                'perms': {'add': False, 'change': True, 'delete': False, 'view': True},
                'admin_url': '/admin/email-settings/',
            }
        ],
    }
    
    app_list.append(email_app)
    return app_list

# Override the app list method
admin.site.get_app_list = custom_app_list