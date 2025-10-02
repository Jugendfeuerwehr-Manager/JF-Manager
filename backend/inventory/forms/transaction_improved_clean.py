from django import forms
from django.db.models import Q
from ..models import Transaction, Item, ItemVariant, StorageLocation, Stock
from members.models import Member


class ImprovedTransactionForm(forms.ModelForm):
    """Simplified Transaction Form with better field handling"""
    
    class Meta:
        model = Transaction
        fields = ['transaction_type', 'item', 'item_variant', 'source', 'target', 'quantity', 'note']
        widgets = {
            'transaction_type': forms.Select(attrs={
                'class': 'form-control form-select'
            }),
            'note': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'Optionale Notizen...', 
                'class': 'form-control'
            }),
            'quantity': forms.NumberInput(attrs={
                'min': '1', 
                'step': '1', 
                'placeholder': 'Anzahl', 
                'class': 'form-control',
                'value': '1'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Extract initial values from kwargs
        self.user = kwargs.pop('user', None)
        self.initial_location = kwargs.pop('initial_location', None)
        self.initial_target = kwargs.pop('initial_target', None)
        self.initial_item = kwargs.pop('initial_item', None)
        self.initial_variant = kwargs.pop('initial_variant', None)
        self.initial_transaction_type = kwargs.pop('initial_transaction_type', None)
        
        super().__init__(*args, **kwargs)
        
        # Setup fields
        self.setup_fields()
        
        # Apply initial values
        self.apply_initial_values()

    def setup_fields(self):
        """Setup form fields with proper querysets and widgets"""
        
        # Transaction type choices
        TRANSACTION_CHOICES = [
            ('', '--- Transaktionstyp wählen ---'),
            ('IN', 'Eingang'),
            ('OUT', 'Ausgang'),
            ('MOVE', 'Umlagerung'),
            ('LOAN', 'Ausleihe'),
            ('RETURN', 'Rückgabe'),
            ('DISCARD', 'Aussortierung'),
        ]
        self.fields['transaction_type'].choices = TRANSACTION_CHOICES
        
        # Item field - regular ModelChoiceField
        self.fields['item'] = forms.ModelChoiceField(
            queryset=Item.objects.select_related('category').all(),
            required=False,
            empty_label="--- Artikel wählen ---",
            widget=forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Artikel suchen...'
            })
        )
        
        # Item variant field
        self.fields['item_variant'] = forms.ModelChoiceField(
            queryset=ItemVariant.objects.select_related('parent_item').all(),
            required=False,
            empty_label="--- Variante wählen ---",
            widget=forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Variante suchen...'
            })
        )
        
        # Location fields
        self.fields['source'] = forms.ModelChoiceField(
            queryset=StorageLocation.objects.all(),
            required=False,
            empty_label="--- Quellort wählen ---",
            widget=forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Quellort suchen...'
            })
        )
        
        self.fields['target'] = forms.ModelChoiceField(
            queryset=StorageLocation.objects.all(),
            required=False,
            empty_label="--- Zielort wählen ---",
            widget=forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Zielort suchen...'
            })
        )

    def apply_initial_values(self):
        """Apply initial values from URL parameters or context"""
        
        if self.initial_transaction_type:
            self.fields['transaction_type'].initial = self.initial_transaction_type
            
        if self.initial_item:
            try:
                item = Item.objects.get(pk=self.initial_item)
                self.fields['item'].initial = item
            except (Item.DoesNotExist, ValueError):
                pass
                
        if self.initial_variant:
            try:
                variant = ItemVariant.objects.get(pk=self.initial_variant)
                self.fields['item_variant'].initial = variant
                # Also set the parent item
                if variant.parent_item:
                    self.fields['item'].initial = variant.parent_item
            except (ItemVariant.DoesNotExist, ValueError):
                pass
                
        if self.initial_location:
            try:
                location = StorageLocation.objects.get(pk=self.initial_location)
                self.fields['source'].initial = location
            except (StorageLocation.DoesNotExist, ValueError):
                pass
                
        if self.initial_target:
            try:
                target = StorageLocation.objects.get(pk=self.initial_target)
                self.fields['target'].initial = target
            except (StorageLocation.DoesNotExist, ValueError):
                pass

    def clean(self):
        """Custom validation"""
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        source = cleaned_data.get('source')
        target = cleaned_data.get('target')
        item = cleaned_data.get('item')
        item_variant = cleaned_data.get('item_variant')
        
        # Basic validation
        if not transaction_type:
            self.add_error('transaction_type', 'Transaktionstyp ist erforderlich.')
            
        if not item and not item_variant:
            self.add_error('item', 'Artikel oder Variante ist erforderlich.')
            
        # Transaction type specific validation
        if transaction_type in ['OUT', 'DISCARD', 'LOAN'] and not source:
            self.add_error('source', f'Quellort ist für {transaction_type} erforderlich.')
            
        if transaction_type in ['IN', 'MOVE', 'RETURN'] and not target:
            self.add_error('target', f'Zielort ist für {transaction_type} erforderlich.')
            
        if transaction_type == 'MOVE' and not source:
            self.add_error('source', 'Quellort ist für Umlagerung erforderlich.')
            
        if source == target and source is not None:
            self.add_error('target', 'Quell- und Zielort dürfen nicht identisch sein.')
            
        return cleaned_data
