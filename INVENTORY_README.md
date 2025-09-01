# Inventar- und Lagerhaltungssystem

Ein vollständiges Django-basiertes Inventar- und Lagerhaltungssystem für die Jugendfeuerwehr.

## Features

### 🎯 Kernfunktionen
- **Artikel-Verwaltung** mit Kategorien und variablen Attributen
- **Lagerorte** inklusive Mitglieder-Zuordnung
- **Bestandsverfolgung** in Echtzeit
- **Transaktions-Management** mit automatischer Bestandsaktualisierung
- **Rechte-Management** mit Django Permissions

### 📊 Transaktionstypen
- **IN** - Wareneingänge ins Lager
- **OUT** - Warenausgänge aus dem Lager
- **LOAN** - Ausleihen an Mitglieder
- **RETURN** - Rückgaben von Mitgliedern
- **MOVE** - Umlagerungen zwischen Standorten
- **DISCARD** - Aussortierung defekter/alter Artikel

### 🔐 Berechtigungen
- **Admin**: Vollzugriff auf alles, inkl. Aussortieren und Löschen
- **Jugendleiter**: Artikel verwalten, Transaktionen erstellen (außer DISCARD)
- **Mitglied**: Nur eigene Ausleihen einsehen

## Installation & Setup

### 1. Models migrieren
```bash
pipenv run python manage.py migrate inventory
```

### 2. Beispieldaten erstellen (optional)
```bash
pipenv run python manage.py create_inventory_sample_data
```

### 3. URLs einbinden
Die URLs sind bereits in `inventory/urls.py` definiert und sollten in der Haupt-URLconf eingebunden werden:

```python
# jf_manager_backend/urls.py
path('inventory/', include('inventory.urls')),
```

## Datenmodell

### Category
- `name` - Name der Kategorie
- `schema` - JSON-Schema für variable Attribute

### Item
- `name` - Artikelname
- `category` - Zugehörige Kategorie
- `base_unit` - Grundeinheit (Stück, Liter, etc.)
- `attributes` - JSON-Attribute (Größe, Farbe, etc.)

### StorageLocation
- `name` - Name des Lagerorts
- `is_member` - Ob es sich um einen Mitglieder-Lagerort handelt
- `member` - Verknüpftes Mitglied (optional)

### Stock
- `item` - Artikel
- `location` - Lagerort
- `quantity` - Menge (automatisch verwaltet)

### Transaction
- `transaction_type` - Art der Transaktion
- `item` - Betroffener Artikel
- `source` - Quell-Lagerort
- `target` - Ziel-Lagerort
- `quantity` - Menge
- `user` - Ausführender Benutzer
- `note` - Notiz

## URLs & Views

### Hauptseiten
- `/inventory/` - Dashboard mit Übersicht
- `/inventory/items/` - Artikel-Liste
- `/inventory/stocks/` - Bestandsübersicht
- `/inventory/transactions/` - Transaktions-Historie

### Aktionen
- `/inventory/items/new/` - Neuer Artikel
- `/inventory/transactions/new/` - Neue Transaktion
- `/inventory/my-loans/` - Eigene Ausleihen (Mitglieder)

## Templates

Alle Templates verwenden Bootstrap 4 (entsprechend dem Projekt-Standard) und sind responsive:

- `inventory/dashboard.html` - Hauptdashboard
- `inventory/item_list.html` - Artikel-Übersicht
- `inventory/item_form.html` - Artikel erstellen/bearbeiten
- `inventory/transaction_form.html` - Transaktion erstellen
- `inventory/stock_list.html` - Bestandsübersicht
- `inventory/member_loans.html` - Mitglieder-Ausleihen

## Permission-System

### Standard Django Permissions
- `inventory.view_item` - Artikel anzeigen
- `inventory.add_item` - Artikel hinzufügen
- `inventory.change_item` - Artikel bearbeiten
- `inventory.delete_item` - Artikel löschen
- `inventory.view_stock` - Bestände anzeigen
- `inventory.view_transaction` - Transaktionen anzeigen
- `inventory.add_transaction` - Transaktionen erstellen

### Custom Permissions
- `inventory.discard_items` - Artikel aussortieren (nur Admins)

### Template-Verwendung
```html
{% if perms.inventory.add_item %}
<a href="{% url 'inventory:item_create' %}" class="btn btn-success">
    Neuer Artikel
</a>
{% endif %}
```

## Forms & Validierung

### TransactionForm
- **Dynamische Transaktionstypen** basierend auf Benutzerrechten
- **Context-sensitive Validierung** je nach Transaktionstyp
- **JavaScript-Integration** für bessere UX

### Beispiel für rechtbasierte Formfelder:
```python
def get_allowed_transaction_types(self):
    if self.user.has_perm('inventory.discard_items'):
        # Admin kann alle Typen
        return Transaction.TRANSACTION_TYPES
    elif self.user.has_perm('inventory.change_item'):
        # Jugendleiter kann fast alles außer DISCARD
        return [('IN', 'Eingang'), ('LOAN', 'Ausleihe'), ...]
    # etc.
```

## Admin Interface

Vollständig konfiguriertes Admin-Interface mit:
- **Kategorien** mit Schema-Editor
- **Artikel** mit Fieldsets und Autocomplete
- **Lagerorte** mit Mitglieder-Zuordnung
- **Bestände** (readonly, werden automatisch verwaltet)
- **Transaktionen** mit Filterung und Suche

## Management Commands

### create_inventory_sample_data
Erstellt Beispieldaten für Entwicklung und Tests:

```bash
# Beispieldaten erstellen
pipenv run python manage.py create_inventory_sample_data

# Bestehende Daten löschen und neue erstellen
pipenv run python manage.py create_inventory_sample_data --clear
```

## API Integration

Das System integriert sich nahtlos in die bestehende DRF-API:
- `ItemViewSet` - Erweitert um neue Felder
- `CategoryViewSet` - Mit Schema-Unterstützung

## Best Practices

### 1. Transaktionen verwenden
Alle Bestandsänderungen **immer** über Transaktionen, nie direkt am Stock-Model:

```python
# ✅ Richtig
Transaction.objects.create(
    transaction_type='IN',
    item=item,
    target=location,
    quantity=10,
    user=request.user
)

# ❌ Falsch
Stock.objects.create(item=item, location=location, quantity=10)
```

### 2. Permissions prüfen
In Templates und Views immer Permissions verwenden:

```python
# Views
class ItemCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'inventory.add_item'

# Templates
{% if perms.inventory.add_item %}
    <!-- Inhalt nur für berechtigte User -->
{% endif %}
```

### 3. Atomic Transactions
Bei kritischen Operationen `@transaction.atomic` verwenden:

```python
from django.db import transaction

@transaction.atomic
def complex_inventory_operation():
    # Mehrere zusammenhängende Transaktionen
    pass
```

## Erweiterungen

### Zukünftige Features
- **Barcode-Scanner** Integration
- **QR-Code** Generation für Artikel
- **E-Mail-Benachrichtigungen** für überfällige Rückgaben
- **Inventur-Modus** für regelmäßige Bestandskontrollen
- **Reporting** mit Charts und Statistiken

### Custom Attribute Types
Das Schema-System kann erweitert werden:

```json
{
  "größe": {
    "type": "choice",
    "options": ["XS", "S", "M", "L", "XL"]
  },
  "farbe": {
    "type": "color",
    "default": "#000000"
  },
  "gewicht": {
    "type": "number",
    "unit": "kg",
    "min": 0
  }
}
```

## Troubleshooting

### Migration-Probleme
Falls Migrations-Konflikte auftreten:
```bash
pipenv run python manage.py migrate inventory --fake-initial
```

### Performance-Optimierung
Bei vielen Artikeln `select_related` und `prefetch_related` verwenden:
```python
queryset = Item.objects.select_related('category').prefetch_related('stock_set__location')
```

### Debug-Modus
Transaktions-Debugging aktivieren:
```python
# settings.py
LOGGING = {
    'loggers': {
        'inventory.models': {
            'level': 'DEBUG',
        }
    }
}
```

## Support

Bei Fragen oder Problemen:
1. Überprüfen Sie die Django-Logs
2. Nutzen Sie das Admin-Interface für direkten Datenzugriff
3. Verwenden Sie das Management-Command für Testdaten

Das System ist vollständig in das bestehende JF-Manager-Projekt integriert und nutzt alle vorhandenen Infrastrukturen (Bootstrap, Crispy Forms, Django Guardian, etc.).
