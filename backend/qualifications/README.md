# Qualifikations- und Sonderaufgaben-Management

Ein Django-Modul für die Verwaltung von Qualifikationen und Sonderaufgaben in der Jugendfeuerwehr.

## Funktionen

### Qualifikationen
- **Qualifikationstypen**: Verwaltung verschiedener Qualifikationsarten (Jugendspange, Atemschutz, etc.)
- **Gültigkeitsdauer**: Automatische Berechnung von Ablaufdaten
- **Status-Tracking**: Aktiv, abgelaufen, läuft bald ab
- **Zertifikatsverwaltung**: Erfassung von Zertifikatsnummern und ausstellenden Organisationen

### Sonderaufgaben
- **Aufgabentypen**: Verschiedene Rollen und Verantwortlichkeiten
- **Führungsrollen**: Kennzeichnung von Leitungspositionen
- **Zeiträume**: Start- und Enddaten für Aufgaben
- **Status**: Aktiv/Inaktiv basierend auf Zeiträumen

### Dashboard
- **Übersicht**: Statistiken zu Qualifikationen und Aufgaben
- **Ablaufwarnungen**: Qualifikationen, die bald ablaufen
- **Aktive Aufgaben**: Übersicht über laufende Sonderaufgaben

## Berechtigungen

### Admin
- Vollzugriff auf alle Funktionen
- Verwaltung von Qualifikations- und Aufgabentypen
- Bearbeitung aller Einträge

### Jugendleiter
- Erstellen und Bearbeiten von Qualifikationen und Aufgaben
- Ansicht aller Mitgliederdaten
- Dashboard-Zugriff

### Mitglied
- Nur Lesezugriff auf eigene Qualifikationen und Aufgaben
- Eingeschränkte Dashboard-Ansicht

## Models

### QualificationType
```python
- name: Name der Qualifikation
- description: Beschreibung
- validity_period_months: Gültigkeitsdauer in Monaten (optional)
- is_required: Pflichtqualifikation
```

### Qualification
```python
- member: Verknüpfung zum Mitglied
- qualification_type: Typ der Qualifikation
- issue_date: Ausstellungsdatum
- expiry_date: Ablaufdatum (automatisch berechnet)
- issuing_organization: Ausstellende Organisation
- certificate_number: Zertifikatsnummer
```

### SpecialTaskType
```python
- name: Name der Aufgabe
- description: Beschreibung
- is_leadership_role: Führungsrolle
```

### SpecialTask
```python
- member: Verknüpfung zum Mitglied
- task_type: Typ der Aufgabe
- start_date: Startdatum
- end_date: Enddatum (optional)
- description: Beschreibung
```

## URLs

```
/qualifications/                     # Dashboard
/qualifications/types/               # Qualifikationstypen
/qualifications/list/                # Qualifikationsliste
/qualifications/create/              # Neue Qualifikation
/qualifications/<id>/                # Qualifikationsdetails
/qualifications/<id>/edit/           # Qualifikation bearbeiten
/qualifications/<id>/delete/         # Qualifikation löschen

/qualifications/special-tasks/       # Sonderaufgaben
/qualifications/special-task-types/  # Aufgabentypen
# ... entsprechende CRUD-URLs für Sonderaufgaben
```

## Templates

### Responsive Design
- Bootstrap 5 Styling
- Mobile-first Ansatz
- Responsive Tabellen mit django-tables2

### Dashboard
- Übersichtskarten mit Statistiken
- Warnungen für ablaufende Qualifikationen
- Schnellzugriff auf wichtige Funktionen

### Listen- und Detailansichten
- Filterbare Tabellen
- Export-Funktionen
- Modale Dialoge für Aktionen

## Integration

### Member-Detail erweitert
Das Modul erweitert die Mitglieder-Detailansicht um zwei neue Tabs:
- **Qualifikationen**: Liste aller Qualifikationen des Mitglieds
- **Sonderaufgaben**: Liste aller Aufgaben des Mitglieds

### Navigation
- Hauptmenü-Eintrag "Qualifikationen"
- Dropdown mit Untermenüs für verschiedene Bereiche

## Installation

1. App zu INSTALLED_APPS hinzufügen:
```python
INSTALLED_APPS = [
    # ...
    'qualifications',
    # ...
]
```

2. URLs einbinden:
```python
# urls.py
urlpatterns = [
    # ...
    path('qualifications/', include('qualifications.urls')),
    # ...
]
```

3. Migrationen ausführen:
```bash
python manage.py makemigrations qualifications
python manage.py migrate
```

4. Beispieldaten erstellen (optional):
```bash
python manage.py create_sample_qualifications
```

## Tests

Das Modul enthält umfassende Tests für alle Komponenten:

```bash
python manage.py test qualifications
```

### Test-Coverage
- Model-Validierung und Business Logic
- View-Berechtigungen und Funktionalität
- Form-Validierung und Berechnungen
- URL-Routing und Navigation

## Admin-Interface

Das Django-Admin wurde erweitert um:
- Import/Export-Funktionen
- Erweiterte Suchfunktionen
- Bulk-Aktionen
- Filteroptionen

## Management Commands

### create_sample_qualifications
Erstellt Beispieldaten für Entwicklung und Tests:

```bash
# Beispieldaten erstellen
python manage.py create_sample_qualifications

# Bestehende Daten löschen und neu erstellen
python manage.py create_sample_qualifications --clear
```

## API

Das Modul stellt REST-API Endpoints zur Verfügung:
- Qualifikationen CRUD
- Sonderaufgaben CRUD
- Dashboard-Statistiken
- Export-Funktionen

## Entwicklung

### Code-Struktur
```
qualifications/
├── models/
│   ├── qualification.py    # Qualifikations-Models
│   └── special_task.py     # Sonderaufgaben-Models
├── views/
│   ├── dashboard.py        # Dashboard-Views
│   ├── qualification.py    # Qualifikations-Views
│   └── special_task.py     # Sonderaufgaben-Views
├── forms/
│   ├── qualification.py    # Qualifikations-Forms
│   └── special_task.py     # Sonderaufgaben-Forms
├── templates/qualifications/
│   ├── base.html           # Basis-Template
│   ├── dashboard.html      # Dashboard
│   ├── qualification/      # Qualifikations-Templates
│   └── special_task/       # Sonderaufgaben-Templates
├── tests/
├── management/commands/
└── migrations/
```

### Best Practices
- Verwendung von Class-Based Views
- Permission Mixins für Zugriffskontrolle
- Model-Clean-Methoden für Validierung
- Crispy Forms für einheitliches Styling
- Django Tables2 für konsistente Tabellen

## Erweiterungen

Das Modul ist erweiterbar für:
- E-Mail-Benachrichtigungen bei ablaufenden Qualifikationen
- Automatische Verlängerungen
- Qualifikations-Dependencies
- Reporting und Analytics
- Mobile App Integration
