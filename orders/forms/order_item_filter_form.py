from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from members.models import Member
from ..models import OrderStatus, OrderableItem
from .widgets import Select2Widget


class OrderItemFilterForm(forms.Form):
    """Form für erweiterte Filterung von Bestellartikeln"""
    
    status = forms.ModelChoiceField(
        queryset=OrderStatus.objects.filter(is_active=True),
        required=False,
        label='Status',
        empty_label='Alle Status'
    )
    
    item_category = forms.ChoiceField(
        required=False,
        label='Kategorie',
        choices=[('', 'Alle Kategorien')]
    )
    
    member = forms.ModelChoiceField(
        queryset=Member.objects.all(),
        required=False,
        label='Mitglied',
        empty_label='Alle Mitglieder',
        widget=Select2Widget(attrs={'data-placeholder': 'Mitglied suchen...'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Bestelldatum von'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Bestelldatum bis'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate category choices from existing items
        categories = OrderableItem.objects.filter(is_active=True).values_list('category', flat=True).distinct()
        category_choices = [('', 'Alle Kategorien')] + [(cat, cat) for cat in categories]
        self.fields['item_category'].choices = category_choices
        
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'form-inline'
        self.helper.layout = Layout(
            Row(
                Column('status', css_class='form-group col-md-2 mb-0'),
                Column('item_category', css_class='form-group col-md-2 mb-0'),
                Column('member', css_class='form-group col-md-2 mb-0'),
                Column('date_from', css_class='form-group col-md-2 mb-0'),
                Column('date_to', css_class='form-group col-md-2 mb-0'),
                Column(
                    Submit('filter', 'Filtern', css_class='btn btn-primary'),
                    css_class='form-group col-md-2 mb-0'
                ),
                css_class='form-row'
            )
        )
