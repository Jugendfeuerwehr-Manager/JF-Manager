from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from ..models import Item


class LegacyItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ('category', 'size', 'identifier1', 'identifier2', 'rented_by')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', 'Speichern'))
        self.helper.add_input(Submit('cancel', 'Abbrechen', css_class='btn-danger', formnovalidate='formnovalidate'))
