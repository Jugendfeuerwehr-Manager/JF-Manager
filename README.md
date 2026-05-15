# JF-Manager

JF-Manager ist eine Webanwendung zur einfachen Verwaltung deiner Jugendfeuerwehr.

## 📝 Historie & Beschreibung

Das Projekt wurde von mir im Jahr 2018 begonnen, mit dem Ziel eine einfachere und unkomplizierte Webanwendung zu bauen, um meine Jugendfeuerwehr zu verwalten.

Wir hatten vorher lediglich einige Listen in Excel und andere Verwaltungssoftware war uns zu kompliziert.

Mit dem JF-Manager lässt sich aktuell der Dienstbetrieb einer Jugendfeuerwehr online verwalten.
Es wird stetig weiterentwickelt und um neue Funktionen ergänzt. Wie oben bereits erwähnt ist das ganze ein Hobbyprojekt und erst ganz frisch (2025) als OpenSource verfügbar - Vielleicht kann es ja noch jemand brauchen ...


### 🎯 Hauptfunktionen

- Verwaltung von Mitgliedern
  - Flexible Excel-Exporte mit auswählbaren Spalten
  - Erfassen von Ehrungen, Notizen, Auszeichnungen etc.
- Listen (Anwesenheits- und Aktionslisten) mit Check-Workflow, Notizen und Export
- Gruppen-Editor
  - Fachliche Mitgliedsgruppen (`/groups`)
  - Berechtigungsgruppen (Admin-Gruppenverwaltung unter `/users`)
- Verwaltung von Eltern, inkl. E-Mail und Verknüpfung mit den Mitgliedern
- Kleiderkammer
  - Barcode Scanner
  - Zuordnung zu den Mitgliedern
- Dienstbuch
  - Erfassen von Diensten
  - Dokumentieren von besonderen Vorkommnissen
  - Anwesenheit erfassen und auswerten
- Bestellwesen
  - Bestellungen erstellen und verwalten
  - Status-Workflow mit E-Mail-Benachrichtigungen
- Qualifikationen & Sonderaufgaben
- Zentrales Einstellungsmodul (General, E-Mail, Mitglieder, Dienst, Bestellungen)
- LDAP-Integration inkl. Verbindungs-Test und LDAP→Abteilungsrollen-Mapping
- SSO via OIDC (z. B. Nextcloud/Keycloak) inkl. Gruppen-Mapping
- Abteilungsfähige Mehrmandanten-Logik mit rollenbasierter Daten-Sicht
- Externe Synchronisation von Mitgliedern/Gruppen über Spond
  - inkl. Betriebsmodi und Bereinigungsvorschau
  - erweiterbar für weitere Provider
- REST API zur Anbindung von eigenen Apps und Diensten


## 📦 Tech Stack

| Komponente | Technologie |
|------------|-------------|
| Backend | Django 5.0 + Django REST Framework |
| Frontend | Vue 3 + TypeScript + Pinia + PrimeVue + Vite |
| Datenbank | PostgreSQL (Produktion) / SQLite (Entwicklung) |
| Auth | JWT (djangorestframework-simplejwt) |
| State Management | Pinia (Composition API) |
| Build | Docker Multi-Stage, Vite |

## 🏗️ Projektstruktur

```
JF-Manager/
├── backend/                 # Django REST API
│   ├── api_tests/           # API-Tests
│   ├── inventory/           # Kleiderkammer
│   ├── members/             # Mitglieder & Eltern
│   ├── orders/              # Bestellwesen (Referenz-Implementierung)
│   │   └── api/             # Modulare API-Struktur (ViewSets, Serializers)
│   ├── qualifications/      # Qualifikationen
│   ├── servicebook/         # Dienstbuch
│   ├── settings_manager/    # Einstellungen
│   ├── users/               # Benutzerverwaltung
│   └── jf_manager_backend/  # Django-Projekteinstellungen & REST-URL-Konfiguration
├── frontend/                # Vue 3 SPA
│   └── src/
│       ├── api/             # HTTP-Client (Axios)
│       ├── components/      # Vue-Komponenten (Atomic Design)
│       ├── stores/          # Pinia Stores
│       ├── types/           # TypeScript Interfaces
│       ├── views/           # Seiten-Komponenten
│       └── router/          # Vue Router
├── docker-compose.yml       # Produktion (Backend + Frontend + DB + Redis)
├── docker-compose.dev.yml   # Entwicklung
├── nginx/                   # Nginx-Konfiguration (Reverse Proxy)
└── docs/                    # Dokumentation
```

## 🚀 Installation & Setup

### Lokale Entwicklungsumgebung

**Voraussetzungen:**
- Python 3.10+
- Node.js 20.19+ oder 22.12+
- pipenv (`pip install pipenv`)

1. Repository klonen:
```bash
git clone https://github.com/Jugendfeuerwehr-Manager/JF-Manager.git
cd JF-Manager
```

2. Backend einrichten:
```bash
cd backend
cp example.env .env          # Umgebungsvariablen anpassen
pipenv install
pipenv run python manage.py migrate
pipenv run python manage.py createsuperuser
```

3. Frontend einrichten:
```bash
cd frontend
npm install
```

4. Entwicklungsserver starten:
```bash
# Aus dem Projektroot:
./start-dev.sh

# Oder manuell in zwei Terminals:
# Terminal 1 - Backend (Port 8000):
cd backend && pipenv run python manage.py runserver

# Terminal 2 - Frontend (Port 5173):
cd frontend && npm run dev
```

Nach dem Start:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000/api/v1/
- **Django Admin**: http://localhost:8000/admin/

### Docker-Installation (Produktion)

1. Repository klonen und Umgebungsvariablen konfigurieren:
```bash
git clone https://github.com/Jugendfeuerwehr-Manager/JF-Manager.git
cd JF-Manager
cp backend/example.env .env
# .env anpassen (SECRET_KEY, DB-Passwörter, E-Mail etc.)
```

2. Container bauen und starten:
```bash
docker compose up -d --build
```

Die Anwendung ist unter http://localhost (Port 80) erreichbar.
Das Frontend (Nginx) dient als Reverse Proxy und leitet API-Anfragen an das Backend weiter.

3. Admin-Benutzer erstellen (falls nicht über Umgebungsvariablen):
```bash
docker exec -it jf_manager_backend python manage.py createsuperuser
```

### Umgebungsvariablen

| Variable | Beschreibung | Standard |
|----------|-------------|----------|
| `DJANGO_SECRET_KEY` | Django Secret Key (erforderlich) | - |
| `POSTGRES_DB` | Datenbankname | `jf_manager_backend` |
| `POSTGRES_USER` | Datenbank-Benutzer | `jf_manager` |
| `POSTGRES_PASSWORD` | Datenbank-Passwort | - |
| `DEBUG` | Debug-Modus | `False` |
| `ALLOWED_HOSTS` | Erlaubte Hostnamen | `localhost,127.0.0.1` |
| `EMAIL_HOST` | SMTP-Server | - |
| `EMAIL_PORT` | SMTP-Port | `587` |
| `VITE_API_BASE_URL` | API-URL für Frontend | `/api/v1` |

Vollständige Übersicht: siehe `backend/example.env`

## 🧪 Tests

```bash
# Backend API-Tests
cd backend
pipenv run python manage.py test api_tests --verbosity=2

# Backend Linting
cd backend
pipenv run ruff check .

# Frontend Type-Check
cd frontend
npm run type-check

# Frontend Linting
cd frontend
npm run lint

# Frontend Unit-Tests
cd frontend
npm run test:unit
```

## 📚 Dokumentation

Die vollständige Dokumentation befindet sich im [docs/](docs/) Verzeichnis:

- [Erste Schritte](docs/getting-started.md) – Lokale Entwicklung, Umgebungsvariablen
- [Architektur](docs/architecture/overview.md) – Docker-Architektur, Netzwerk, Sicherheit
- [Abteilungen & Berechtigungen](docs/architecture/departments-and-permissions.md) – Scoping-Modell, aktive Abteilung, Berechtigungsdurchsetzung
- [API Referenz](docs/api/reference.md) – REST API Endpunkte, Authentifizierung
- [Deployment](docs/deployment/docker.md) – Docker Compose, SSL, Backup
- [Portainer](docs/deployment/portainer.md) – Deployment via Portainer
- [Mitglieder, Listen, Gruppen, Excel-Export](docs/domains/members-lists-groups-exports.md) – Neue Listen-/Gruppen- und Exportfunktionen
- [Settings, LDAP, SSO](docs/domains/settings-ldap-sso.md) – Einstellungen und externe Authentifizierung
- [Abteilungen (Operational Guide)](docs/domains/departments.md) – Praxisleitfaden für Abteilungsbetrieb
- [External Sync mit Spond](docs/domains/external-sync-spond.md) – Sync-Jobs und Provider-Erweiterung

## 🤝 Beitragen

Wir freuen uns über Beiträge zur Verbesserung des JF-Managers! Bitte lies dir unsere Beitragsrichtlinien durch, bevor du Änderungen vorschlägst.

## 📄 Lizenz

[GNU AFFERO GENERAL PUBLIC LICENSE](./LICENSE)