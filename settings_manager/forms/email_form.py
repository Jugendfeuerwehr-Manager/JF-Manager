from django import forms
from crispy_forms.layout import Layout, Fieldset, Submit, HTML, Row, Column
from crispy_forms.bootstrap import FormActions
from dynamic_preferences.registries import global_preferences_registry

from .base_form import BaseSettingsForm


class EmailSettingsForm(BaseSettingsForm):
    """
    Formular für E-Mail Einstellungen
    """
    email_host = forms.CharField(
        label='SMTP Server',
        max_length=200,
        help_text='Hostname oder IP-Adresse des SMTP-Servers (z.B. smtp.gmail.com)',
        required=False
    )
    
    email_port = forms.IntegerField(
        label='SMTP Port',
        help_text='Port des SMTP-Servers (z.B. 587 für TLS, 465 für SSL)',
        min_value=1,
        max_value=65535,
        initial=587,
        required=False
    )
    
    email_use_tls = forms.BooleanField(
        label='TLS verwenden',
        help_text='TLS-Verschlüsselung für die E-Mail-Verbindung verwenden',
        required=False
    )
    
    email_use_ssl = forms.BooleanField(
        label='SSL verwenden',
        help_text='SSL-Verschlüsselung für die E-Mail-Verbindung verwenden (nicht zusammen mit TLS)',
        required=False
    )
    
    email_host_user = forms.CharField(
        label='SMTP Benutzername',
        max_length=200,
        help_text='Benutzername für die Authentifizierung beim SMTP-Server',
        required=False
    )
    
    email_host_password = forms.CharField(
        label='SMTP Passwort',
        widget=forms.PasswordInput(render_value=True),
        help_text='Passwort für die Authentifizierung beim SMTP-Server',
        required=False
    )
    
    default_from_email = forms.EmailField(
        label='Absender E-Mail',
        help_text='E-Mail-Adresse, die als Absender verwendet wird',
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Lade aktuelle Werte
        global_preferences = global_preferences_registry.manager()
        self.fields['email_host'].initial = global_preferences.get('email__email_host')
        self.fields['email_port'].initial = global_preferences.get('email__email_port')
        self.fields['email_use_tls'].initial = global_preferences.get('email__email_use_tls')
        self.fields['email_use_ssl'].initial = global_preferences.get('email__email_use_ssl')
        self.fields['email_host_user'].initial = global_preferences.get('email__email_host_user')
        self.fields['email_host_password'].initial = global_preferences.get('email__email_host_password')
        self.fields['default_from_email'].initial = global_preferences.get('email__default_from_email')
    
    def get_preference_key(self, field_name):
        mapping = {
            'email_host': 'email__email_host',
            'email_port': 'email__email_port',
            'email_use_tls': 'email__email_use_tls',
            'email_use_ssl': 'email__email_use_ssl',
            'email_host_user': 'email__email_host_user',
            'email_host_password': 'email__email_host_password',
            'default_from_email': 'email__default_from_email',
        }
        return mapping.get(field_name)
    
    def get_layout(self):
        layout = Layout(
            Fieldset(
                'SMTP Server Einstellungen',
                Row(
                    Column('email_host', css_class='form-group col-md-8'),
                    Column('email_port', css_class='form-group col-md-4'),
                ),
                Row(
                    Column('email_use_tls', css_class='form-group col-md-6'),
                    Column('email_use_ssl', css_class='form-group col-md-6'),
                ),
                css_class='mb-4'
            ),
            Fieldset(
                'Authentifizierung',
                'email_host_user',
                'email_host_password',
                css_class='mb-4'
            ),
            Fieldset(
                'Absender Einstellungen',
                'default_from_email',
                css_class='mb-4'
            ),
            HTML('<div class="alert alert-info"><i class="fas fa-info-circle"></i> '
                 '<strong>Wichtig:</strong> Nach dem Speichern können Sie die Einstellungen '
                 'mit einer Test-E-Mail überprüfen.</div>')
        )
        
        # Add submit button only if not in tabbed layout
        if not self.tabbed_layout:
            layout.append(FormActions(
                Submit('save', 'Speichern', css_class='btn-primary me-2'),
                HTML('<a href="{% url \'admin:test_email\' %}" class="btn btn-outline-success">'
                     '<i class="fas fa-paper-plane"></i> Test E-Mail senden</a>'),
                css_class='text-end'
            ))
        
        return layout