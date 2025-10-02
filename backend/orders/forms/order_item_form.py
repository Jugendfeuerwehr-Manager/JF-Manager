from django import forms
from django.forms import inlineformset_factory
from ..models import Order, OrderItem, OrderableItem


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
        
        # Custom widget für das Item-Feld mit data-Attributen
        items = OrderableItem.objects.filter(is_active=True)
        choices = [('', '---------')]
        
        for item in items:
            # Create option with data attributes
            choice_attrs = {
                'data-has-sizes': 'true' if item.has_sizes else 'false',
                'data-sizes': ','.join(item.get_sizes_list()) if item.has_sizes else ''
            }
            choices.append((item.pk, f'{item.category} - {item.name}'))
        
        # Custom Select widget mit option_attrs
        class ItemSelectWidget(forms.Select):
            def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
                option = super().create_option(name, value, label, selected, index, subindex, attrs)
                if value:  # Skip empty option
                    try:
                        item = OrderableItem.objects.get(pk=value)
                        option['attrs']['data-has-sizes'] = 'true' if item.has_sizes else 'false'
                        option['attrs']['data-sizes'] = ','.join(item.get_sizes_list()) if item.has_sizes else ''
                    except OrderableItem.DoesNotExist:
                        pass
                return option
        
        self.fields['item'].widget = ItemSelectWidget()
        
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
