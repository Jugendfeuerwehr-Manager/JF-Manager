from django import forms
from crispy_forms.layout import Layout, Fieldset, Submit, HTML
from crispy_forms.bootstrap import FormActions
from dynamic_preferences.registries import global_preferences_registry

from .base_form import BaseSettingsForm


class MemberSettingsForm(BaseSettingsForm):
    """
    Formular für Mitglieder-Einstellungen
    """
    alert_threshold = forms.IntegerField(
        label='Alarm: Schwellenwert nicht Anwesend',
        help_text='Definiert den Schwellenwert wann ein Ausrufezeichen angezeigt wird',
        min_value=1,
        initial=3,
        required=False
    )
    
    alert_threshold_last_entries = forms.IntegerField(
        label='Alarm: Intervallgröße',
        help_text='Definiert die Anzahl an Diensten die rückwärtig betrachtet werden',
        min_value=1,
        initial=10,
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Lade aktuelle Werte
        global_preferences = global_preferences_registry.manager()
        self.fields['alert_threshold'].initial = global_preferences.get('members__alert_threshold')
        self.fields['alert_threshold_last_entries'].initial = global_preferences.get('members__alert_threshold_last_entries')
    
    def get_preference_key(self, field_name):
        mapping = {
            'alert_threshold': 'members__alert_threshold',
            'alert_threshold_last_entries': 'members__alert_threshold_last_entries',
        }
        return mapping.get(field_name)
    
    def get_layout(self):
        layout = Layout(
            Fieldset(
                'Anwesenheits-Alarme',
                'alert_threshold',
                'alert_threshold_last_entries',
                HTML('<small class="text-muted">Diese Einstellungen bestimmen, wann Mitglieder '
                     'als häufig abwesend markiert werden.</small>'),
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