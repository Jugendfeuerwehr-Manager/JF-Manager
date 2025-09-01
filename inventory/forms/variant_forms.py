from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Field, Row, Column, HTML, Fieldset
from crispy_forms.bootstrap import InlineRadios
import json

from ..models import Item, ItemVariant


class ItemVariantForm(forms.ModelForm):
    """Form für einzelne Artikel-Variante"""
    class Meta:
        model = ItemVariant
        fields = ['parent_item', 'sku', 'variant_attributes']
        widgets = {
            'variant_attributes': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.parent_item = kwargs.pop('parent_item', None)
        super().__init__(*args, **kwargs)
        
        if self.parent_item:
            self.fields['parent_item'].initial = self.parent_item
            self.fields['parent_item'].widget = forms.HiddenInput()

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'parent_item',
            'sku',
            HTML('<div id="variant-attributes-container"></div>'),
            'variant_attributes',
            Div(
                Submit('submit', 'Speichern', css_class='btn btn-primary'),
                HTML('<a href="#" onclick="history.back()" class="btn btn-secondary ms-2">Abbrechen</a>'),
                css_class='d-flex gap-2'
            ),
        )


class BulkVariantCreationForm(forms.Form):
    """Form für Bulk-Erstellung von Artikelvarianten"""
    
    # Häufige Größen für verschiedene Artikel
    SIZE_CHOICES = [
        ('164', '164'),
        ('176', '176'), 
        ('188', '188'),
        ('XS', 'XS'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
        ('XXXL', 'XXXL'),
    ]
    
    COLOR_CHOICES = [
        ('blau', 'Blau'),
        ('rot', 'Rot'),
        ('gelb', 'Gelb'),
        ('grün', 'Grün'),
        ('schwarz', 'Schwarz'),
        ('weiß', 'Weiß'),
        ('orange', 'Orange'),
        ('grau', 'Grau'),
    ]
    
    # Varianten-Typ
    creation_type = forms.ChoiceField(
        choices=[
            ('sizes', 'Größen'),
            ('colors', 'Farben'),
            ('sizes_colors', 'Größen und Farben'),
            ('custom', 'Benutzerdefiniert'),
        ],
        label='Art der Varianten',
        widget=forms.RadioSelect,
        initial='sizes'
    )
    
    # Größenauswahl
    sizes = forms.MultipleChoiceField(
        choices=SIZE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Größen auswählen'
    )
    
    # Farbauswahl
    colors = forms.MultipleChoiceField(
        choices=COLOR_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Farben auswählen'
    )
    
    # Benutzerdefinierte Größen
    custom_sizes = forms.CharField(
        max_length=500,
        required=False,
        label='Benutzerdefinierte Größen',
        help_text='Komma-getrennt, z.B.: 110, 122, 134, 146',
        widget=forms.TextInput(attrs={'placeholder': '110, 122, 134, 146'})
    )
    
    # Benutzerdefinierte Farben
    custom_colors = forms.CharField(
        max_length=500,
        required=False,
        label='Benutzerdefinierte Farben',
        help_text='Komma-getrennt, z.B.: navy, dunkelblau, hellblau',
        widget=forms.TextInput(attrs={'placeholder': 'navy, dunkelblau, hellblau'})
    )
    
    # SKU-Präfix für automatische Generierung
    sku_prefix = forms.CharField(
        max_length=20,
        required=False,
        label='SKU-Präfix',
        help_text='Optional: Präfix für automatische SKU-Generierung, z.B. "HOSE"',
        widget=forms.TextInput(attrs={'placeholder': 'HOSE'})
    )
    
    # Zusätzliche Attribute
    additional_attributes = forms.CharField(
        required=False,
        label='Erweiterte Attribute (JSON, optional)',
        help_text='Optional: JSON-Format für weitere Attribute, die nicht als Custom Fields verfügbar sind, z.B.: {"material": "Baumwolle", "waschbar": true}',
        widget=forms.Textarea(attrs={
            'placeholder': '{"material": "Baumwolle", "waschbar": true}',
            'rows': 3
        })
    )

    def __init__(self, *args, **kwargs):
        self.parent_item = kwargs.pop('parent_item', None)
        super().__init__(*args, **kwargs)
        
        # Dynamisch verfügbare Optionen basierend auf dem Hauptartikel bestimmen
        available_choices = self._get_available_creation_types()
        self.fields['creation_type'].choices = available_choices
        
        # Wenn nur eine Option verfügbar ist, diese vorauswählen
        if len(available_choices) == 1:
            self.fields['creation_type'].initial = available_choices[0][0]
        
        # Dynamische Custom Fields basierend auf Parent Item hinzufügen
        self._add_dynamic_custom_fields()
        
        # Felder ausblenden, die nicht relevant sind
        self._configure_field_visibility()
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Varianten-Erstellung',
                HTML('<p class="text-muted">Erstellen Sie mehrere Varianten gleichzeitig für diesen Artikel.</p>'),
                *self._get_dynamic_layout(),
            ),
            
            Div(
                Submit('submit', 'Varianten erstellen', css_class='btn btn-primary'),
                HTML('<a href="#" onclick="history.back()" class="btn btn-secondary ms-2">Abbrechen</a>'),
                css_class='d-flex gap-2'
            ),
        )

    def _get_available_creation_types(self):
        """Bestimmt welche Erstellungstypen basierend auf dem Hauptartikel verfügbar sind"""
        if not self.parent_item:
            return [('custom', 'Benutzerdefiniert')]
        
        choices = []
        has_size_attributes = self._parent_has_size_attributes()
        has_color_attributes = self._parent_has_color_attributes()
        
        if has_size_attributes:
            choices.append(('sizes', 'Größen'))
            
        if has_color_attributes:
            choices.append(('colors', 'Farben'))
            
        if has_size_attributes and has_color_attributes:
            choices.append(('sizes_colors', 'Größen und Farben'))
        
        # Benutzerdefiniert ist immer verfügbar
        choices.append(('custom', 'Benutzerdefiniert'))
        
        return choices

    def _parent_has_size_attributes(self):
        """Überprüft ob der Hauptartikel größenrelevante Attribute hat"""
        if not self.parent_item:
            return False
            
        # Legacy size field
        if self.parent_item.size:
            return True
        
        # Check category schema for size-related fields
        if self.parent_item.category and self.parent_item.category.schema:
            size_keys = ['size', 'größe', 'groesse', 'sizes', 'größen']
            for key in self.parent_item.category.schema.keys():
                if key.lower() in size_keys:
                    return True
            
        # Check attributes JSON for size-related fields
        if self.parent_item.attributes:
            size_keys = ['size', 'größe', 'groesse', 'sizes', 'größen']
            for key in self.parent_item.attributes.keys():
                if key.lower() in size_keys:
                    return True
                    
        # Check if it's already a variant parent with size variants
        if self.parent_item.is_variant_parent:
            for variant in self.parent_item.get_variants():
                if variant.variant_attributes:
                    for key in variant.variant_attributes.keys():
                        if key.lower() in ['size', 'größe', 'groesse']:
                            return True
        
        return False

    def _parent_has_color_attributes(self):
        """Überprüft ob der Hauptartikel farbrelevante Attribute hat"""
        if not self.parent_item:
            return False
        
        # Check category schema for color-related fields
        if self.parent_item.category and self.parent_item.category.schema:
            color_keys = ['color', 'colour', 'farbe', 'colors', 'farben']
            for key in self.parent_item.category.schema.keys():
                if key.lower() in color_keys:
                    return True
            
        # Check attributes JSON for color-related fields
        if self.parent_item.attributes:
            color_keys = ['color', 'colour', 'farbe', 'colors', 'farben']
            for key in self.parent_item.attributes.keys():
                if key.lower() in color_keys:
                    return True
                    
        # Check if it's already a variant parent with color variants
        if self.parent_item.is_variant_parent:
            for variant in self.parent_item.get_variants():
                if variant.variant_attributes:
                    for key in variant.variant_attributes.keys():
                        if key.lower() in ['color', 'colour', 'farbe']:
                            return True
        
        return False

    def _add_dynamic_custom_fields(self):
        """Fügt dynamische Felder für alle verfügbaren Custom Attributes des Parent Items hinzu"""
        if not self.parent_item:
            return
            
        custom_fields = self._get_parent_custom_fields()
        
        for field_name, field_info in custom_fields.items():
            field_key = f'custom_field_{field_name}'
            field_type_raw = field_info.get('type', field_info.get('field_type', 'string'))
            
            # Robuste Feldtyp-Behandlung
            field_type = self._normalize_field_type(field_type_raw)
            
            # Nur unterstützte Feldtypen verarbeiten
            if not self._is_bulk_creation_supported(field_type):
                continue
                
            # Besserer Hilfetext basierend auf Quelle
            source_info = {
                'category_schema': 'aus Kategorie-Schema',
                'parent_attributes': 'aus Artikel-Attributen',
                'existing_variants': 'aus bestehenden Varianten'
            }
            source_text = source_info.get(field_info.get('source'), '')
            
            # Erstelle Feld basierend auf Typ - nur Text und Zahlen
            if field_type in ['number', 'integer', 'int', 'float', 'decimal']:
                # Number: Range-Eingabe (von-bis)
                range_field_from = f'{field_key}_from'
                range_field_to = f'{field_key}_to'
                
                self.fields[range_field_from] = forms.CharField(
                    required=False,
                    label=f'{field_info.get("display_name", field_name)} - Von',
                    help_text=f'Startwert für numerische Varianten ({source_text})',
                    widget=forms.TextInput(attrs={
                        'placeholder': '1',
                        'class': 'form-control',
                        'type': 'number'
                    })
                )
                
                self.fields[range_field_to] = forms.CharField(
                    required=False,
                    label=f'{field_info.get("display_name", field_name)} - Bis',
                    help_text=f'Endwert für numerische Varianten ({source_text})',
                    widget=forms.TextInput(attrs={
                        'placeholder': '10',
                        'class': 'form-control',
                        'type': 'number'
                    })
                )
            else:
                # Text-Feld: Kommagetrennte Eingabe (Standard)
                self.fields[field_key] = forms.CharField(
                    required=False,
                    label=field_info.get("display_name", field_name),
                    help_text=f'Kommagetrennte Werte ({source_text}), z.B.: Rot, Blau, Grün',
                    widget=forms.TextInput(attrs={
                        'placeholder': 'Wert1, Wert2, Wert3',
                        'class': 'form-control'
                    })
                )

    def _get_parent_custom_fields(self):
        """Ermittelt alle verfügbaren Custom Fields des Parent Items"""
        all_custom_fields = {}
        
        if not self.parent_item:
            return all_custom_fields
            
        # Standard-Felder ausschließen (diese werden separat behandelt)
        excluded_keys = ['size', 'größe', 'groesse', 'sizes', 'größen', 
                        'color', 'colour', 'farbe', 'colors', 'farben']
        
        # Aus Kategorie-Schema
        if self.parent_item.category and self.parent_item.category.schema:
            for key, field_type in self.parent_item.category.schema.items():
                if key.lower() not in excluded_keys:
                    all_custom_fields[key] = {
                        'display_name': key.title(),
                        'field_type': field_type,
                        'source': 'category_schema',
                        'example': self._generate_example_values(key),
                        'bulk_supported': self._is_bulk_creation_supported(field_type)
                    }
        
        # Aus Parent Item Attributen
        if self.parent_item.attributes:
            for key, value in self.parent_item.attributes.items():
                if key.lower() not in excluded_keys:
                    all_custom_fields[key] = {
                        'display_name': key.title(),
                        'current_value': value,
                        'field_type': 'string',  # Assume string for existing attributes
                        'source': 'parent_attributes',
                        'example': self._generate_example_values(key, value),
                        'bulk_supported': self._is_bulk_creation_supported('string')
                    }
        
        # Aus bestehenden Varianten (falls vorhanden)
        if self.parent_item.is_variant_parent:
            for variant in self.parent_item.get_variants():
                if variant.variant_attributes:
                    for key, value in variant.variant_attributes.items():
                        if key.lower() not in excluded_keys and key not in all_custom_fields:
                            all_custom_fields[key] = {
                                'display_name': key.title(),
                                'current_value': value,
                                'field_type': 'string',  # Assume string for existing variants
                                'source': 'existing_variants',
                                'example': self._generate_example_values(key, value),
                                'bulk_supported': self._is_bulk_creation_supported('string')
                            }
        
        # Filtere nur unterstützte Felder für die Rückgabe
        return {k: v for k, v in all_custom_fields.items() if v['bulk_supported']}

    def _is_bulk_creation_supported(self, field_type):
        """Prüft ob ein Feldtyp für Bulk-Creation geeignet ist"""
        supported_types = [
            'string', 'text', 'varchar', 'char',  # Text-Felder
            'number', 'integer', 'int', 'float', 'decimal'  # Zahlen-Felder
        ]
        
        field_type_normalized = self._normalize_field_type(field_type)
        
        # Nur explizit unterstützte Typen erlauben
        return field_type_normalized in supported_types

    def _get_all_custom_fields_with_info(self):
        """Gibt alle Custom Fields zurück, auch nicht-unterstützte, mit Info-Status"""
        all_fields = {}
        
        if not self.parent_item:
            return all_fields
            
        excluded_keys = ['size', 'größe', 'groesse', 'sizes', 'größen', 
                        'color', 'colour', 'farbe', 'colors', 'farben']
        
        # Aus Kategorie-Schema
        if self.parent_item.category and self.parent_item.category.schema:
            for key, field_type in self.parent_item.category.schema.items():
                if key.lower() not in excluded_keys:
                    all_fields[key] = {
                        'display_name': key.title(),
                        'field_type': field_type,
                        'source': 'category_schema',
                        'bulk_supported': self._is_bulk_creation_supported(field_type),
                        'reason': self._get_unsupported_reason(field_type)
                    }
        
        return all_fields

    def _get_unsupported_reason(self, field_type):
        """Gibt den Grund zurück, warum ein Feldtyp nicht unterstützt wird"""
        field_type_lower = str(field_type).lower()
        
        reasons = {
            'boolean': 'Boolean-Felder haben nur zwei Werte (true/false)',
            'bool': 'Boolean-Felder haben nur zwei Werte (true/false)',
            'date': 'Datum-Felder sind selten für Varianten relevant',
            'datetime': 'Datum-Zeit-Felder sind selten für Varianten relevant',
            'time': 'Zeit-Felder sind selten für Varianten relevant',
            'timestamp': 'Zeitstempel-Felder sind selten für Varianten relevant',
            'number': 'Numerische Felder sind noch nicht unterstützt (geplant)',
            'integer': 'Numerische Felder sind noch nicht unterstützt (geplant)',
            'int': 'Numerische Felder sind noch nicht unterstützt (geplant)',
            'float': 'Numerische Felder sind noch nicht unterstützt (geplant)',
            'decimal': 'Numerische Felder sind noch nicht unterstützt (geplant)',
        }
        
        return reasons.get(field_type_lower, 'Feldtyp nicht unterstützt')

    def _generate_example_values(self, field_name, current_value=None):
        """Generiert Beispielwerte für ein Custom Field"""
        field_lower = field_name.lower()
        
        # Spezifische Beispiele für bekannte Feldtypen
        examples = {
            'geschmack': 'erdbeere, vanille, schokolade',
            'material': 'baumwolle, polyester, mischgewebe', 
            'typ': 'standard, premium, deluxe',
            'type': 'standard, premium, deluxe',
            'hersteller': 'adidas, nike, puma',
            'manufacturer': 'adidas, nike, puma',
            'marke': 'adidas, nike, puma',
            'brand': 'adidas, nike, puma',
            'saison': 'frühjahr, sommer, herbst',
            'season': 'spring, summer, autumn',
            'stil': 'casual, formal, sport',
            'style': 'casual, formal, sport',
            'qualität': 'basic, standard, premium',
            'quality': 'basic, standard, premium',
            'kategorie': 'A, B, C',
            'category': 'A, B, C',
            'modell': 'classic, modern, vintage',
            'model': 'classic, modern, vintage',
            'ausführung': 'einfach, erweitert, komplett',
            'version': 'v1, v2, v3',
            'zustand': 'neu, gebraucht, repariert',
            'condition': 'new, used, refurbished',
        }
        
        # Prüfe auf bekannte Muster
        for pattern, example in examples.items():
            if pattern in field_lower:
                return example
                
        # Fallback: basierend auf aktuellem Wert
        if current_value:
            if isinstance(current_value, str):
                return f'{current_value}1, {current_value}2, {current_value}3'
            else:
                return f'wert1, wert2, wert3'
        
        # Default
        return f'{field_name.lower()}1, {field_name.lower()}2, {field_name.lower()}3'

    def _normalize_field_type(self, field_type_raw):
        """Normalisiert verschiedene Feldtyp-Formate zu einem einheitlichen String"""
        if isinstance(field_type_raw, str):
            return field_type_raw.lower()
        elif isinstance(field_type_raw, dict):
            # Wenn field_type ein Dict ist, schaue nach 'type' Key
            if 'type' in field_type_raw:
                return str(field_type_raw['type']).lower()
            elif 'kind' in field_type_raw:
                return str(field_type_raw['kind']).lower()
            elif 'dataType' in field_type_raw:
                return str(field_type_raw['dataType']).lower()
            else:
                # Fallback: nimm den ersten Wert oder 'string'
                values = list(field_type_raw.values())
                return str(values[0]).lower() if values else 'string'
        else:
            # Fallback für andere Typen
            return str(field_type_raw).lower() if field_type_raw else 'string'

    def _configure_field_visibility(self):
        """Konfiguriert die Sichtbarkeit von Feldern basierend auf verfügbaren Optionen"""
        available_types = [choice[0] for choice in self._get_available_creation_types()]
        
        # Wenn Größen nicht verfügbar sind, Größenfelder ausblenden
        if 'sizes' not in available_types and 'sizes_colors' not in available_types:
            self.fields['sizes'].widget = forms.HiddenInput()
            self.fields['custom_sizes'].widget = forms.HiddenInput()
            
        # Wenn Farben nicht verfügbar sind, Farbfelder ausblenden
        if 'colors' not in available_types and 'sizes_colors' not in available_types:
            self.fields['colors'].widget = forms.HiddenInput()
            self.fields['custom_colors'].widget = forms.HiddenInput()

    def _get_dynamic_layout(self):
        """Erstellt ein dynamisches Layout basierend auf verfügbaren Optionen"""
        available_types = [choice[0] for choice in self._get_available_creation_types()]
        
        layout_elements = []
        
        # Radio-Buttons immer anzeigen (auch bei nur einer Option)
        layout_elements.append(InlineRadios('creation_type'))
        layout_elements.append(HTML('<hr>'))
        
        # Größen-Sektion nur anzeigen wenn verfügbar
        if 'sizes' in available_types or 'sizes_colors' in available_types:
            layout_elements.extend([
                HTML('<div id="sizes-section">'),
                HTML('<h6>Größenauswahl</h6>'),
                Row(
                    Column('sizes', css_class='col-md-8'),
                    Column('custom_sizes', css_class='col-md-4'),
                ),
                HTML('</div>'),
            ])
        
        # Farben-Sektion nur anzeigen wenn verfügbar
        if 'colors' in available_types or 'sizes_colors' in available_types:
            layout_elements.extend([
                HTML('<div id="colors-section">'),
                HTML('<h6>Farbauswahl</h6>'),
                Row(
                    Column('colors', css_class='col-md-8'),
                    Column('custom_colors', css_class='col-md-4'),
                ),
                HTML('</div>'),
            ])
        
        # Benutzerdefinierte Attribute für alle Typen
        custom_fields = self._get_parent_custom_fields()
        all_fields_info = self._get_all_custom_fields_with_info()
        unsupported_fields = {k: v for k, v in all_fields_info.items() if not v['bulk_supported']}
        
        if custom_fields:
            layout_elements.extend([
                HTML('<div id="custom-fields-section">'),
                HTML('<h6>Benutzerdefinierte Felder für Bulk-Creation</h6>'),
                HTML('<p class="text-muted small">Verfügbare Felder basierend auf Kategorie-Schema, Artikel-Attributen und bestehenden Varianten.</p>'),
                HTML('<div class="alert alert-info py-2 mb-3">'),
                HTML('<small><strong>Tipp:</strong> Je nach Feldtyp stehen verschiedene Eingabemöglichkeiten zur Verfügung.</small>'),
                HTML('</div>'),
            ])
            
            # Gruppiere Felder nach Typ für bessere Darstellung
            string_fields = []
            number_fields = []
            unsupported_fields = {}
            
            for field_name, field_info in custom_fields.items():
                field_type = self._normalize_field_type(field_info.get('type', field_info.get('field_type', 'string')))
                field_key = f'custom_field_{field_name}'
                
                if self._is_bulk_creation_supported(field_type):
                    if field_type in ['number', 'integer', 'int', 'float', 'decimal']:
                        number_fields.append((field_key, field_name))
                    else:
                        string_fields.append(field_key)
                else:
                    # Sammle nicht-unterstützte Felder für Info-Anzeige
                    unsupported_fields[field_name] = {
                        'display_name': field_info.get('display_name', field_name),
                        'field_type': field_type,
                        'reason': 'Bulk-Creation nicht implementiert'
                    }
            
            # String-Felder
            if string_fields:
                layout_elements.extend([
                    HTML('<h6 class="mt-3">Text-Felder</h6>'),
                    HTML('<p class="small text-muted">Kommagetrennte Werte eingeben</p>'),
                ])
                for field_key in string_fields:
                    layout_elements.append(Field(field_key))
            
            # Number-Felder
            if number_fields:
                layout_elements.extend([
                    HTML('<h6 class="mt-3">Numerische Felder</h6>'),
                    HTML('<p class="small text-muted">Bereich eingeben (von-bis)</p>'),
                ])
                for field_key, field_name in number_fields:
                    layout_elements.extend([
                        HTML(f'<div class="row mb-3">'),
                        HTML(f'<div class="col-md-12"><strong>{field_name.title()}</strong></div>'),
                        HTML(f'<div class="col-md-6">'),
                        Field(f'{field_key}_from'),
                        HTML(f'</div>'),
                        HTML(f'<div class="col-md-6">'),
                        Field(f'{field_key}_to'),
                        HTML(f'</div>'),
                        HTML(f'</div>'),
                    ])
            
            layout_elements.append(HTML('</div>'))
        
        # Info über nicht-unterstützte Felder
        if unsupported_fields:
            layout_elements.extend([
                HTML('<div id="unsupported-fields-info">'),
                HTML('<h6 class="mt-3">Nicht unterstützte Felder</h6>'),
                HTML('<div class="alert alert-warning py-2">'),
                HTML('<small><i class="fas fa-info-circle me-1"></i><strong>Folgende Felder sind für Bulk-Creation nicht geeignet:</strong></small>'),
            ])
            
            for field_name, field_info in unsupported_fields.items():
                layout_elements.append(
                    HTML(f'<div class="small mt-1"><strong>{field_info["display_name"]}</strong> ({field_info["field_type"]}): {field_info["reason"]}</div>')
                )
            
            layout_elements.extend([
                HTML('<div class="small mt-2"><em>Diese Felder können bei der individuellen Varianten-Erstellung gesetzt werden.</em></div>'),
                HTML('</div>'),
                HTML('</div>'),
            ])
        
        # Fallback wenn gar keine Custom Fields verfügbar sind
        if not custom_fields and not unsupported_fields:
            layout_elements.extend([
                HTML('<div id="no-custom-fields-info">'),
                HTML('<div class="alert alert-warning py-2">'),
                HTML('<small><i class="fas fa-info-circle me-1"></i><strong>Hinweis:</strong> Keine Custom Fields verfügbar. Definieren Sie Schema-Felder in der Kategorie oder Attribute im Artikel für mehr Optionen.</small>'),
                HTML('</div>'),
                HTML('</div>'),
            ])
        
        # Fallback für JSON-Attribute
        layout_elements.extend([
            HTML('<div id="json-section">'),
            HTML('<h6>Erweiterte Attribute (optional)</h6>'),
            HTML('<p class="text-muted small">Nur für spezielle Attribute verwenden, die nicht als Custom Fields verfügbar sind.</p>'),
            'additional_attributes',
            HTML('</div>'),
        ])
        
        # Weitere Optionen
        layout_elements.extend([
            HTML('<hr>'),
            Row(
                Column('sku_prefix', css_class='col-md-6'),
                Column(HTML(''), css_class='col-md-6'),  # Platzhalter
            ),
        ])
        
        return layout_elements

    def clean(self):
        cleaned_data = super().clean()
        creation_type = cleaned_data.get('creation_type')
        sizes = cleaned_data.get('sizes', [])
        colors = cleaned_data.get('colors', [])
        custom_sizes = cleaned_data.get('custom_sizes', '')
        custom_colors = cleaned_data.get('custom_colors', '')
        additional_attributes = cleaned_data.get('additional_attributes', '')
        
        # Validierung basierend auf creation_type
        if creation_type == 'sizes':
            if not sizes and not custom_sizes:
                raise ValidationError('Bitte wählen Sie mindestens eine Größe aus oder geben Sie benutzerdefinierte Größen ein.')
        elif creation_type == 'colors':
            if not colors and not custom_colors:
                raise ValidationError('Bitte wählen Sie mindestens eine Farbe aus oder geben Sie benutzerdefinierte Farben ein.')
        elif creation_type == 'sizes_colors':
            if (not sizes and not custom_sizes) or (not colors and not custom_colors):
                raise ValidationError('Bitte wählen Sie mindestens eine Größe und eine Farbe aus.')
        elif creation_type == 'custom':
            # Prüfe ob entweder unterstützte Custom Fields oder JSON-Attribute definiert sind
            has_custom_fields = self._has_any_custom_field_values()
            
            if not has_custom_fields and not additional_attributes:
                supported_fields = list(self._get_parent_custom_fields().keys())
                if supported_fields:
                    field_names = ', '.join(supported_fields)
                    raise ValidationError(f'Bitte geben Sie Werte für mindestens ein unterstütztes Feld ein ({field_names}) oder verwenden Sie JSON-Attribute.')
                else:
                    raise ValidationError('Bitte definieren Sie zusätzliche Attribute im JSON-Format oder fügen Sie unterstützte Felder zur Kategorie hinzu.')

    def _has_any_custom_field_values(self):
        """Prüft ob irgendwelche Custom Field Werte eingegeben wurden"""
        custom_fields_info = self._get_parent_custom_fields()
        
        for field_name, field_info in custom_fields_info.items():
            field_type = self._normalize_field_type(field_info.get('type', field_info.get('field_type', 'string')))
            field_key = f'custom_field_{field_name}'
            
            # Nur unterstützte Feldtypen prüfen
            if not self._is_bulk_creation_supported(field_type):
                continue
                
            if field_type in ['number', 'integer', 'int', 'float', 'decimal']:
                # Number: Prüfe ob von/bis Werte vorhanden sind
                from_val = self.cleaned_data.get(f'{field_key}_from', '')
                to_val = self.cleaned_data.get(f'{field_key}_to', '')
                if from_val or to_val:
                    return True
            else:
                # String/Text: Prüfe ob Werte vorhanden sind
                values = self.cleaned_data.get(field_key, '')
                if values and values.strip():
                    return True
        
        return False
        
        # JSON-Validierung für zusätzliche Attribute (nur wenn vorhanden)
        if additional_attributes:
            try:
                json.loads(additional_attributes)
            except json.JSONDecodeError:
                raise ValidationError('Zusätzliche Attribute müssen im gültigen JSON-Format eingegeben werden.')
        
        return cleaned_data
    
    def get_size_list(self):
        """Kombiniert ausgewählte und benutzerdefinierte Größen"""
        sizes = list(self.cleaned_data.get('sizes', []))
        custom_sizes = self.cleaned_data.get('custom_sizes', '')
        
        if custom_sizes:
            custom_list = [s.strip() for s in custom_sizes.split(',') if s.strip()]
            sizes.extend(custom_list)
        
        return sizes
    
    def get_color_list(self):
        """Kombiniert ausgewählte und benutzerdefinierte Farben"""
        colors = list(self.cleaned_data.get('colors', []))
        custom_colors = self.cleaned_data.get('custom_colors', '')
        
        if custom_colors:
            custom_list = [c.strip() for c in custom_colors.split(',') if c.strip()]
            colors.extend(custom_list)
        
        return colors
    
    def get_additional_attributes_dict(self):
        """Konvertiert JSON-String zu Dictionary"""
        additional_attributes = self.cleaned_data.get('additional_attributes', '')
        if additional_attributes:
            try:
                return json.loads(additional_attributes)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def create_variants(self):
        """Erstellt die Varianten basierend auf den Formulareingaben"""
        if not self.parent_item:
            raise ValueError("Parent item is required")
        
        creation_type = self.cleaned_data['creation_type']
        sku_prefix = self.cleaned_data.get('sku_prefix', '')
        additional_attrs = self.get_additional_attributes_dict()
        created_variants = []
        
        if creation_type == 'sizes':
            sizes = self.get_size_list()
            for size in sizes:
                variant_attrs = {'größe': size}
                variant_attrs.update(additional_attrs)
                
                sku = f"{sku_prefix}-{size}" if sku_prefix else ""
                
                variant = ItemVariant.objects.create(
                    parent_item=self.parent_item,
                    variant_attributes=variant_attrs,
                    sku=sku
                )
                created_variants.append(variant)
        
        elif creation_type == 'colors':
            colors = self.get_color_list()
            for color in colors:
                variant_attrs = {'farbe': color}
                variant_attrs.update(additional_attrs)
                
                sku = f"{sku_prefix}-{color}" if sku_prefix else ""
                
                variant = ItemVariant.objects.create(
                    parent_item=self.parent_item,
                    variant_attributes=variant_attrs,
                    sku=sku
                )
                created_variants.append(variant)
        
        elif creation_type == 'sizes_colors':
            sizes = self.get_size_list()
            colors = self.get_color_list()
            
            for size in sizes:
                for color in colors:
                    variant_attrs = {'größe': size, 'farbe': color}
                    variant_attrs.update(additional_attrs)
                    
                    sku = f"{sku_prefix}-{size}-{color}" if sku_prefix else ""
                    
                    variant = ItemVariant.objects.create(
                        parent_item=self.parent_item,
                        variant_attributes=variant_attrs,
                        sku=sku
                    )
                    created_variants.append(variant)
        
        elif creation_type == 'custom':
            # Für benutzerdefinierte Attribute mit Custom Fields
            custom_field_combinations = self.get_custom_field_combinations()
            
            if custom_field_combinations:
                # Erstelle Varianten für alle Kombinationen
                for combination in custom_field_combinations:
                    variant_attrs = combination.copy()
                    variant_attrs.update(additional_attrs)
                    
                    # SKU aus Kombinationswerten generieren
                    sku_parts = [sku_prefix] if sku_prefix else []
                    sku_parts.extend([str(v)[:10] for v in combination.values()])  # Max 10 Zeichen pro Wert
                    sku = "-".join(sku_parts) if sku_parts else ""
                    
                    variant = ItemVariant.objects.create(
                        parent_item=self.parent_item,
                        variant_attributes=variant_attrs,
                        sku=sku
                    )
                    created_variants.append(variant)
            else:
                # Fallback: Eine Variante mit nur additional_attributes
                variant_attrs = additional_attrs
                sku = sku_prefix if sku_prefix else ""
                
                variant = ItemVariant.objects.create(
                    parent_item=self.parent_item,
                    variant_attributes=variant_attrs,
                    sku=sku
                )
                created_variants.append(variant)
        
        return created_variants

    def get_custom_field_combinations(self):
        """Erzeugt alle Kombinationen der Custom Field Werte"""
        custom_fields = self._get_parent_custom_fields()
        bulk_supported_fields = {
            name: field for name, field in custom_fields.items() 
            if self._is_bulk_creation_supported(field.get('type', field.get('field_type', 'string')))
        }
        
        if not bulk_supported_fields:
            return [{}]
        
        combinations = [{}]
        
        for field_name, field_info in bulk_supported_fields.items():
            field_type = self._normalize_field_type(field_info.get('type', field_info.get('field_type', 'string')))
            
            if field_type in ['number', 'integer', 'int', 'float', 'decimal']:
                # Number: Bereich aus cleaned_data verwenden
                from_val = self.cleaned_data.get(f'custom_field_{field_name}_from')
                to_val = self.cleaned_data.get(f'custom_field_{field_name}_to')
                if from_val and to_val:
                    try:
                        start = int(from_val)
                        end = int(to_val)
                        new_combinations = []
                        for combo in combinations:
                            for num_val in range(start, end + 1):
                                new_combo = combo.copy()
                                new_combo[field_name] = str(num_val)
                                new_combinations.append(new_combo)
                        combinations = new_combinations
                    except (ValueError, TypeError):
                        pass  # Ungültige Zahlen ignorieren
                        
            else:
                # String/Text: kommagetrennte Werte
                values_input = self.cleaned_data.get(f'custom_field_{field_name}', '')
                if values_input:
                    values = [v.strip() for v in values_input.split(',') if v.strip()]
                    if values:
                        new_combinations = []
                        for combo in combinations:
                            for value in values:
                                new_combo = combo.copy()
                                new_combo[field_name] = value
                                new_combinations.append(new_combo)
                        combinations = new_combinations
        
        return combinations
