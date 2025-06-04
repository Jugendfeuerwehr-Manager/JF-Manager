from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Row, Column, HTML, Div
from ..models import Order
from .widgets import Select2Widget


class OrderForm(forms.ModelForm):
    """Form für die Erstellung von Bestellungen"""
    
    class Meta:
        model = Order
        fields = ['member', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'member': Select2Widget(attrs={'data-placeholder': 'Mitglied suchen...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Neue Bestellung',
                Row(
                    Column('member', css_class='form-group col-md-8 mb-0'),
                    css_class='form-row'
                ),
                'notes',
            ),

            Div(
                Submit('submit', 'Bestellung erstellen', css_class='btn btn-primary'),
                HTML('<a href="{% url "orders:list" %}" class="btn btn-secondary ml-2">Abbrechen</a>'),
                css_class='form-actions'
            )
        )
