from django import forms
from crispy_forms.layout import Layout, Fieldset, Field, Submit, HTML
from crispy_forms.bootstrap import FormActions
from dynamic_preferences.registries import global_preferences_registry

from .base_form import BaseSettingsForm


class GeneralSettingsForm(BaseSettingsForm):
    """
    Formular für allgemeine Einstellungen
    """
    title = forms.CharField(
        label='Website Titel',
        max_length=200,
        help_text='Der Titel der Website, der im Browser-Tab angezeigt wird',
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Lade aktuelle Werte
        global_preferences = global_preferences_registry.manager()
        self.fields['title'].initial = global_preferences.get('general__title')
    
    def get_preference_key(self, field_name):
        mapping = {
            'title': 'general__title',
        }
        return mapping.get(field_name)
    
    def get_layout(self):
        layout = Layout(
            Fieldset(
                'Allgemeine Einstellungen',
                Field('title', css_class='form-control'),
                HTML('<hr>'),
                HTML('<small class="text-muted">Diese Einstellungen gelten für die gesamte Anwendung.</small>'),
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