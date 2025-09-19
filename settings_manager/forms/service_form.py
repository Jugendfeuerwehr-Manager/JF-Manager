from django import forms
from crispy_forms.layout import Layout, Fieldset, Submit, HTML, Row, Column
from crispy_forms.bootstrap import FormActions
from dynamic_preferences.registries import global_preferences_registry

from .base_form import BaseSettingsForm


class ServiceSettingsForm(BaseSettingsForm):
    """
    Formular für Dienst-Einstellungen
    """
    service_start_time = forms.TimeField(
        label='Standard Start Zeit',
        help_text='Standard-Startzeit für neue Dienste',
        widget=forms.TimeInput(attrs={'type': 'time'}),
        required=False
    )
    
    service_end_time = forms.TimeField(
        label='Standard Ende Zeit',
        help_text='Standard-Endzeit für neue Dienste',
        widget=forms.TimeInput(attrs={'type': 'time'}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Lade aktuelle Werte und konvertiere sie zu Time-Objekten
        global_preferences = global_preferences_registry.manager()
        
        start_time_str = global_preferences.get('service__service_start_time')
        if start_time_str:
            from datetime import datetime
            try:
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
                self.fields['service_start_time'].initial = start_time
            except ValueError:
                pass
        
        end_time_str = global_preferences.get('service__service_end_time')
        if end_time_str:
            from datetime import datetime
            try:
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
                self.fields['service_end_time'].initial = end_time
            except ValueError:
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('service_start_time')
        end_time = cleaned_data.get('service_end_time')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise forms.ValidationError('Die Startzeit muss vor der Endzeit liegen.')
        
        return cleaned_data
    
    def get_preference_key(self, field_name):
        mapping = {
            'service_start_time': 'service__service_start_time',
            'service_end_time': 'service__service_end_time',
        }
        return mapping.get(field_name)
    
    def save(self):
        """
        Überschreibt die save-Methode um Zeit-Objekte in Strings zu konvertieren
        """
        if not self.is_valid():
            return False
            
        global_preferences = global_preferences_registry.manager()
        
        for field_name, value in self.cleaned_data.items():
            preference_key = self.get_preference_key(field_name)
            if preference_key and value:
                # Konvertiere Time-Objekte zu Strings
                if hasattr(value, 'strftime'):
                    value = value.strftime('%H:%M')
                global_preferences[preference_key] = value
        
        return True
    
    def get_layout(self):
        layout = Layout(
            Fieldset(
                'Standard Dienstzeiten',
                Row(
                    Column('service_start_time', css_class='form-group col-md-6'),
                    Column('service_end_time', css_class='form-group col-md-6'),
                ),
                HTML('<small class="text-muted">Diese Zeiten werden als Vorauswahl '
                     'für neue Dienste verwendet.</small>'),
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