from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Row, Column
from ..models import OrderItem, OrderStatus


class BulkStatusUpdateForm(forms.Form):
    """Form für Bulk-Status-Updates von Bestellartikeln"""
    
    order_items = forms.ModelMultipleChoiceField(
        queryset=OrderItem.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label='Artikel auswählen'
    )
    
    new_status = forms.ModelChoiceField(
        queryset=OrderStatus.objects.filter(is_active=True),
        label='Neuer Status'
    )
    
    update_dates = forms.BooleanField(
        required=False,
        label='Datumsfelder automatisch setzen',
        help_text='Setze Eingangsdatum bei Status "Eingegangen" oder Ausgabedatum bei Status "Ausgegeben"'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Bemerkungen',
        help_text='Diese Bemerkung wird zu allen ausgewählten Artikeln hinzugefügt'
    )

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop('queryset', OrderItem.objects.none())
        super().__init__(*args, **kwargs)
        self.fields['order_items'].queryset = queryset
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Bulk Status-Update',
                'order_items',
                Row(
                    Column('new_status', css_class='form-group col-md-6 mb-0'),
                    Column('update_dates', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                'notes',
            ),
            Submit('submit', 'Status für ausgewählte Artikel aktualisieren', css_class='btn btn-primary'),
        )
