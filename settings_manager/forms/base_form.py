from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from crispy_forms.bootstrap import FormActions
from dynamic_preferences.registries import global_preferences_registry


class BaseSettingsForm(forms.Form):
    """
    Basis-Form für alle Einstellungs-Formulare
    """
    
    def __init__(self, *args, **kwargs):
        self.tabbed_layout = kwargs.pop('tabbed_layout', False)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'settings-form'
        self.helper.form_tag = not self.tabbed_layout  # No form tag in tabbed layout
        self.helper.layout = self.get_layout()
    
    def get_layout(self):
        """
        Überschreibe diese Methode in Unterklassen
        """
        return Layout()
    
    def save(self):
        """
        Speichert die Formular-Daten in den Dynamic Preferences
        """
        if not self.is_valid():
            return False
            
        global_preferences = global_preferences_registry.manager()
        
        for field_name, value in self.cleaned_data.items():
            # Konvertiere field_name zu preference key
            preference_key = self.get_preference_key(field_name)
            if preference_key:
                global_preferences[preference_key] = value
        
        return True
    
    def get_preference_key(self, field_name):
        """
        Konvertiert Formular-Feldname zu Preference-Key
        Überschreibe diese Methode in Unterklassen
        """
        return None