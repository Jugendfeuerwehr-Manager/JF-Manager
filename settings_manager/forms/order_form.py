from django import forms
from crispy_forms.layout import Layout, Fieldset, Submit, HTML
from crispy_forms.bootstrap import FormActions
from dynamic_preferences.registries import global_preferences_registry

from .base_form import BaseSettingsForm


class OrderSettingsForm(BaseSettingsForm):
    """
    Formular für Bestellungs-Einstellungen
    """
    equipment_manager_email = forms.EmailField(
        label='Gerätewart E-Mail',
        help_text='E-Mail-Adresse des Gerätewarts für Bestellübersichten',
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Lade aktuelle Werte
        global_preferences = global_preferences_registry.manager()
        self.fields['equipment_manager_email'].initial = global_preferences.get('orders__equipment_manager_email')
    
    def get_preference_key(self, field_name):
        mapping = {
            'equipment_manager_email': 'orders__equipment_manager_email',
        }
        return mapping.get(field_name)
    
    def get_layout(self):
        layout = Layout(
            Fieldset(
                'Bestellungs-Benachrichtigungen',
                'equipment_manager_email',
                HTML('<small class="text-muted">Diese E-Mail-Adresse erhält '
                     'Benachrichtigungen über neue Bestellungen.</small>'),
                css_class='mb-4'
            )
        )
        
        # Add submit button only if not in tabbed layout
        if not self.tabbed_layout:
            layout.append(FormActions(
                Submit('save', 'Speichern', css_class='btn-primary'),
                css_class='text-end'
            ))
        
        return layout