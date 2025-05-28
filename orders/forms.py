from django import forms
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Row, Column, HTML, Div
from crispy_forms.bootstrap import InlineRadios
from django_filters import FilterSet, DateFromToRangeFilter
from django_filters.widgets import RangeWidget

from members.models import Member
from .models import Order, OrderItem, OrderableItem, OrderStatus


class OrderForm(forms.ModelForm):
    """Form für die Erstellung von Bestellungen"""
    
    class Meta:
        model = Order
        fields = ['member', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
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


class OrderItemForm(forms.ModelForm):
    """Form für einzelne Bestellartikel"""
    
    class Meta:
        model = OrderItem
        fields = ['item', 'size', 'quantity', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
            'quantity': forms.NumberInput(attrs={'min': 1, 'value': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item'].queryset = OrderableItem.objects.filter(is_active=True)
        self.fields['size'].required = False
        
        # Größenfeld nur anzeigen wenn Item ausgewählt und Größen hat
        try:
            if self.instance.pk and self.instance.item and self.instance.item.has_sizes:
                sizes = self.instance.item.get_sizes_list()
                if sizes:
                    self.fields['size'].widget = forms.Select(choices=[('', '---------')] + [(s, s) for s in sizes])
        except (AttributeError, OrderableItem.DoesNotExist):
            # New instance or item doesn't exist yet
            pass


# Formset für OrderItems
OrderItemFormSet = inlineformset_factory(
    Order, 
    OrderItem,
    form=OrderItemForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
    fields=['item', 'size', 'quantity', 'notes']
)


class OrderStatusUpdateForm(forms.ModelForm):
    """Form für Status-Updates von Bestellartikeln"""
    
    class Meta:
        model = OrderItem
        fields = ['status', 'received_date', 'delivered_date', 'notes']
        widgets = {
            'received_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'delivered_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'status',
            Row(
                Column('received_date', css_class='form-group col-md-6 mb-0'),
                Column('delivered_date', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'notes',
            Submit('submit', 'Status aktualisieren', css_class='btn btn-primary'),
        )


class OrderFilter(FilterSet):
    """Filter für Bestellungen"""
    
    order_date = DateFromToRangeFilter(
        widget=RangeWidget(attrs={'type': 'date'}),
        label='Bestelldatum'
    )
    
    class Meta:
        model = Order
        fields = {
            'member': ['exact'],
            'ordered_by': ['exact'],
            'items__status': ['exact'],
        }


class OrderFilterFormHelper(FormHelper):
    """Helper für das Filterformular"""
    
    form_method = 'GET'
    form_class = 'form-inline'
    layout = Layout(
        Row(
            Column('member', css_class='form-group col-md-3 mb-0'),
            Column('ordered_by', css_class='form-group col-md-3 mb-0'),
            Column('items__status', css_class='form-group col-md-2 mb-0'),
            Column('order_date', css_class='form-group col-md-3 mb-0'),
            Column(
                Submit('submit', 'Filtern', css_class='btn btn-primary'),
                css_class='form-group col-md-1 mb-0'
            ),
            css_class='form-row'
        )
    )


class QuickOrderForm(forms.Form):
    """Schnelle Bestellung für häufig bestellte Artikel"""
    
    member = forms.ModelChoiceField(
        queryset=Member.objects.all(),
        label='Mitglied'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamische Felder für häufig bestellte Artikel
        common_items = OrderableItem.objects.filter(
            is_active=True, 
            category__in=['Uniform', 'Schutzausrüstung']
        ).order_by('category', 'name')
        
        for item in common_items:
            field_name = f'item_{item.id}'
            self.fields[field_name] = forms.BooleanField(
                required=False,
                label=f'{item.category} - {item.name}'
            )
            
            if item.has_sizes and item.get_sizes_list():
                size_field_name = f'size_{item.id}'
                sizes = item.get_sizes_list()
                self.fields[size_field_name] = forms.ChoiceField(
                    choices=[('', 'Keine Größe')] + [(s, s) for s in sizes],
                    required=False,
                    label=f'Größe für {item.name}'
                )
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'member',
            HTML('<hr><h5>Artikel auswählen</h5>'),
            HTML('<div class="row">'),
            *[HTML(f'<div class="col-md-6 mb-2">{{% field form.{field_name} %}}{{% if form.size_{field_name.split("_")[1]} %}}<br>{{% field form.size_{field_name.split("_")[1]} %}}{{% endif %}}</div>') 
              for field_name, field in self.fields.items() if field_name != 'member' and not field.label.startswith('Größe')],
            HTML('</div>'),
            Submit('submit', 'Schnellbestellung erstellen', css_class='btn btn-success mt-3'),
        )


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
        empty_label='Alle Mitglieder'
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
