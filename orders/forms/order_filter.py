from django import forms
from django_filters import FilterSet, DateFromToRangeFilter
from django_filters.widgets import RangeWidget
import django_filters
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML
from members.models import Member
from ..models import Order
from .widgets import Select2Widget


class OrderFilter(FilterSet):
    """Filter für Bestellungen"""
    
    order_date = DateFromToRangeFilter(
        widget=RangeWidget(attrs={'type': 'date'}),
        label='Bestelldatum'
    )
    
    member = django_filters.ModelChoiceFilter(
        queryset=Member.objects.all(),
        widget=Select2Widget(attrs={'data-placeholder': 'Mitglied suchen...'})
    )
    
    class Meta:
        model = Order
        fields = {
            'ordered_by': ['exact'],
            'items__status': ['exact'],
        }


class OrderFilterFormHelper(FormHelper):
    """Helper für das Filterformular"""
    
    form_method = 'GET'
    form_class = 'filter-form'
    layout = Layout(
        Row(
            Column('member', css_class='col-md-3 mb-2'),
            Column('ordered_by', css_class='col-md-3 mb-2'),
            Column('items__status', css_class='col-md-2 mb-2'),
            Column('order_date', css_class='col-md-4 mb-2'),
            css_class='form-row'
        ),
        Row(
            Column(
                Submit('submit', 'Filtern', css_class='btn btn-primary btn-sm mr-2'),
                HTML('<a href="?" class="btn btn-outline-secondary btn-sm">Zurücksetzen</a>'),
                css_class='col-12 text-left'
            ),
            css_class='form-row mt-2'
        )
    )
