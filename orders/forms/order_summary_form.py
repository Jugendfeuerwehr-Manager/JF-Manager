from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Row, Column
from ..models import OrderStatus


class OrderSummaryForm(forms.Form):
    """Form für das Senden von Bestellübersichten an den Gerätewart"""
    
    recipient_email = forms.EmailField(
        label='E-Mail-Adresse des Gerätewarts',
        help_text='E-Mail-Adresse der Person, die die Bestellübersicht erhalten soll'
    )
    
    status_filter = forms.ModelMultipleChoiceField(
        queryset=OrderStatus.objects.filter(is_active=True),
        required=False,
        label='Status Filter',
        help_text='Nur Bestellungen mit diesen Status einbeziehen (leer = alle Status)',
        widget=forms.CheckboxSelectMultiple
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Bestelldatum von',
        help_text='Nur Bestellungen ab diesem Datum'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Bestelldatum bis',
        help_text='Nur Bestellungen bis zu diesem Datum'
    )
    
    include_notes = forms.BooleanField(
        required=False,
        initial=True,
        label='Bemerkungen einschließen',
        help_text='Bemerkungen zu Bestellungen und Artikeln in die Übersicht einbeziehen'
    )
    
    group_by_category = forms.BooleanField(
        required=False,
        initial=True,
        label='Nach Kategorien gruppieren',
        help_text='Artikel nach Kategorien gruppieren für einfacheres Einkaufen'
    )
    
    additional_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Zusätzliche Bemerkungen',
        help_text='Zusätzliche Informationen für den Gerätewart'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Empfänger',
                'recipient_email',
            ),
            Fieldset(
                'Filter-Optionen',
                'status_filter',
                Row(
                    Column('date_from', css_class='form-group col-md-6 mb-0'),
                    Column('date_to', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
            ),
            Fieldset(
                'Darstellungsoptionen',
                'include_notes',
                'group_by_category',
                'additional_notes',
            ),
            Submit('send_summary', 'Bestellübersicht senden', css_class='btn btn-primary btn-lg'),
        )
