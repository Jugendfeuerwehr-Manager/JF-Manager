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
        """Initialize form, capture provided initial context and run setup helpers."""
        # Extract additional keyword arguments before calling parent
        self.user = kwargs.pop('user', None)
        self.initial_location = kwargs.pop('initial_location', None)
        self.initial_target = kwargs.pop('initial_target', None)
        self.initial_item = kwargs.pop('initial_item', None)
        self.initial_variant = kwargs.pop('initial_variant', None)
        self.initial_transaction_type = kwargs.pop('initial_transaction_type', None)

        super().__init__(*args, **kwargs)

        # Setup dynamic fields and apply initial / auto logic
        self.setup_fields()
        self.apply_initial_values()
        self.auto_assign_source_location()

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
            # Handle both object and ID
            if isinstance(self.initial_item, Item):
                self.fields['item'].initial = self.initial_item
            else:
                try:
                    item = Item.objects.get(pk=self.initial_item)
                    self.fields['item'].initial = item
                except (Item.DoesNotExist, ValueError):
                    pass
            # Clear variant if item is set
            self.fields['item_variant'].initial = None
                
        if self.initial_variant:
            # Handle both object and ID
            if isinstance(self.initial_variant, ItemVariant):
                self.fields['item_variant'].initial = self.initial_variant
            else:
                try:
                    variant = ItemVariant.objects.get(pk=self.initial_variant)
                    self.fields['item_variant'].initial = variant
                except (ItemVariant.DoesNotExist, ValueError):
                    pass
            # Clear item if variant is set (mutual exclusion)
            self.fields['item'].initial = None
                
        if self.initial_location:
            # Handle both object and ID
            if isinstance(self.initial_location, StorageLocation):
                self.fields['source'].initial = self.initial_location
            else:
                try:
                    location = StorageLocation.objects.get(pk=self.initial_location)
                    self.fields['source'].initial = location
                except (StorageLocation.DoesNotExist, ValueError):
                    pass
                
        if self.initial_target:
            # Handle both object and ID
            if isinstance(self.initial_target, StorageLocation):
                self.fields['target'].initial = self.initial_target
            else:
                try:
                    target = StorageLocation.objects.get(pk=self.initial_target)
                    self.fields['target'].initial = target
                except (StorageLocation.DoesNotExist, ValueError):
                    pass

    def clean(self):
        """Custom validation with better error messages and stock checking"""
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        source = cleaned_data.get('source')
        target = cleaned_data.get('target')
        item = cleaned_data.get('item')
        item_variant = cleaned_data.get('item_variant')
        quantity = cleaned_data.get('quantity', 0)
        
        # Basic validation
        if not transaction_type:
            self.add_error('transaction_type', 'Transaktionstyp ist erforderlich.')
            
        # Item/Variant validation with better messages
        if not item and not item_variant:
            self.add_error('item', 'Wählen Sie entweder einen Artikel oder eine Artikel-Variante aus.')
            self.add_error('item_variant', 'Wählen Sie entweder einen Artikel oder eine Artikel-Variante aus.')
            
        if item and item_variant:
            self.add_error('item', 'Wählen Sie nur einen Artikel ODER eine Variante, nicht beide.')
            self.add_error('item_variant', 'Wählen Sie nur einen Artikel ODER eine Variante, nicht beide.')
            
        # Transaction type specific validation
        if transaction_type in ['OUT', 'DISCARD', 'LOAN'] and not source:
            self.add_error('source', f'Quellort ist für {self.get_transaction_type_display(transaction_type)} erforderlich.')
            
        if transaction_type in ['IN', 'MOVE', 'RETURN'] and not target:
            self.add_error('target', f'Zielort ist für {self.get_transaction_type_display(transaction_type)} erforderlich.')
            
        if transaction_type == 'MOVE' and not source:
            self.add_error('source', 'Quellort ist für Umlagerung erforderlich.')
            
        if source == target and source is not None:
            self.add_error('target', 'Quell- und Zielort dürfen nicht identisch sein.')
            
        # Stock availability check for outbound transactions
        if (transaction_type in ['OUT', 'DISCARD', 'LOAN', 'MOVE'] and 
            source and quantity > 0 and (item or item_variant)):
            
            stock_available = self.check_stock_availability(item, item_variant, source, quantity)
            if stock_available is not None and stock_available < quantity:
                item_name = item.name if item else str(item_variant)
                error_msg = (f'Nicht genügend Bestand vorhanden! '
                           f'Verfügbar: {stock_available}, '
                           f'Benötigt: {quantity} '
                           f'von "{item_name}" am Lagerort "{source.name}"')
                
                self.add_error('quantity', error_msg)
                self.add_error('source', f'Zu wenig Bestand am gewählten Quellort.')
            
        return cleaned_data

    def auto_assign_source_location(self):
        """Setzt automatisch den Quell-Lagerort, falls eindeutig ableitbar.

        Regeln:
        - Nur wenn Formular noch nicht gebunden ist (GET Aufruf ohne POST Daten)
        - Nur wenn noch kein source initial gesetzt wurde
        - Falls genau EIN Lagerort positiven Bestand für gewähltes Item/Variante hat
        - Gilt für alle Transaktionstypen; auch bei RETURN hilfreich zur Übersicht
        """
        if self.is_bound:
            return  # User hat bereits Eingaben gemacht
        if self.fields['source'].initial:
            return

        item = self.fields['item'].initial
        variant = self.fields['item_variant'].initial
        if not item and not variant:
            return

        stock_qs = Stock.objects.filter(quantity__gt=0)
        if item:
            stock_qs = stock_qs.filter(item=item, item_variant__isnull=True)
        if variant:
            stock_qs = stock_qs.filter(item_variant=variant, item__isnull=True)

        locations = list({s.location for s in stock_qs.select_related('location')})
        if len(locations) == 1:
            self.fields['source'].initial = locations[0]
    
    def check_stock_availability(self, item, item_variant, location, required_quantity):
        """Check if enough stock is available at the given location"""
        from inventory.models.stock import Stock
        
        try:
            stock_params = {'location': location}
            if item:
                stock_params.update({'item': item, 'item_variant': None})
            elif item_variant:
                stock_params.update({'item': None, 'item_variant': item_variant})
            else:
                return None
                
            stock = Stock.objects.get(**stock_params)
            return stock.quantity
            
        except Stock.DoesNotExist:
            return 0  # No stock available
    
    def get_transaction_type_display(self, transaction_type):
        """Get human readable transaction type"""
        type_map = {
            'IN': 'Eingang',
            'OUT': 'Ausgang', 
            'MOVE': 'Umlagerung',
            'LOAN': 'Ausleihe',
            'RETURN': 'Rückgabe',
            'DISCARD': 'Aussortierung'
        }
        return type_map.get(transaction_type, transaction_type)
