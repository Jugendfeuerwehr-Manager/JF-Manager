from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML
from members.models import Member
from ..models import OrderableItem
from .widgets import Select2Widget


class QuickOrderForm(forms.Form):
    """Schnelle Bestellung für häufig bestellte Artikel"""
    
    member = forms.ModelChoiceField(
        queryset=Member.objects.all(),
        label='Mitglied',
        widget=Select2Widget(attrs={'data-placeholder': 'Mitglied suchen...'})
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
                # Filter out empty sizes
                sizes = [s for s in sizes if s.strip()]
                
                self.fields[size_field_name] = forms.ChoiceField(
                    choices=[('', 'Größe auswählen...')] + [(s, s) for s in sizes],
                    required=False,
                    label=f'Größe',
                    widget=forms.Select(attrs={
                        'class': 'form-control',
                        'data-item-id': item.id
                    })
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
