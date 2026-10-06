# Getting Started

## Voraussetzungen

- Python 3.12+ und pipenv
- Node.js 20.19+ oder 22.12+
- Redis (lokal, z. B. `brew install redis`) für Hintergrundaufgaben und Drosselung
- Docker (optional, für den Produktionsweg)

## Lokale Entwicklung

Oberfläche und API laufen im Browser unter **einer** Herkunft: Die App wird immer über `http://localhost:5173` geöffnet, Vite leitet `/api`, `/admin` und `/static` an Django auf Port 8000 weiter. Nur so funktionieren Sitzungs- und CSRF-Cookies. `http://localhost:8000` direkt im Browser ist nur für `/admin/` gedacht.

### 1. Repository klonen

```bash
git clone https://github.com/Jugendfeuerwehr-Manager/JF-Manager.git
cd JF-Manager
```

### 2. Backend einrichten

```bash
cd backend
pipenv install
cp example.env .env
```

In `backend/.env` für die lokale Entwicklung mindestens setzen:

```bash
DEBUG=True
DJANGO_SECRET_KEY=<zufälliger langer Wert>
# Pflicht: Schlüssel für verschlüsselte Felder (MFA, LDAP/OIDC/Sync-Zugangsdaten)
FIELD_ENCRYPTION_KEY=<Ausgabe des folgenden Befehls>
```

```bash
pipenv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Den Schlüssel aufbewahren: Mit ihm verschlüsselte Daten sind ohne ihn nicht mehr lesbar. `backend/.env` ist in Git ignoriert und darf nicht eingecheckt werden. `pipenv run` sowie die VS-Code-Konfigurationen lesen die Datei automatisch.

```bash
pipenv run python manage.py migrate
pipenv run python manage.py createsuperuser
```

Administratorkonten müssen beim ersten Login eine Authenticator-App (TOTP) einrichten; die Oberfläche führt durch die Einrichtung und zeigt einmalige Wiederherstellungscodes.

### 3. Frontend einrichten

```bash
cd frontend
npm install
cp .env.example .env
```

`VITE_API_BASE_URL` bleibt `/api/v1`. Ein abweichender Backend-Port wird nur über `VITE_BACKEND_URL` gesetzt.

### 4. Starten

**VS Code:** Startkonfiguration **„JF-Manager: Backend + Frontend“**. Sie startet Redis (oder nutzt ein laufendes), führt Migrationen aus, startet den RQ-Worker, Django und Vite und öffnet Chrome unter `http://localhost:5173`.

**Terminal:**

```bash
./start-dev.sh
```

Oder einzeln: `cd backend && pipenv run python manage.py runserver` und `cd frontend && npm run dev`, dann `http://localhost:5173` öffnen.

**Mit Beispieldaten statt eigener Datenbank:** VS-Code-Konfiguration **„Demo: Backend + Frontend“** oder wie in der README beschrieben. Die Demo legt eine temporäre Datenbank mit eigenem Wegwerf-Schlüssel an.

### Häufige Probleme

| Symptom | Ursache und Abhilfe |
|---------|---------------------|
| Start bricht mit „FIELD_ENCRYPTION_KEY muss explizit gesetzt sein“ ab | Schlüssel in `backend/.env` eintragen (siehe oben). |
| Login meldet „Gespeicherte Zugangsdaten können nicht entschlüsselt werden“ | Die Datenbank wurde mit einem anderen Schlüssel beschrieben. Den ursprünglichen Schlüssel eintragen; bei Schlüsselwechsel den alten in `FIELD_ENCRYPTION_PREVIOUS_KEYS` angeben. |
| Login klappt, aber jede Anfrage ist sofort wieder abgemeldet | App nicht über `http://localhost:5173` geöffnet oder `DEBUG=True` fehlt (dann sind Cookies `Secure` und werden über http nicht gesendet). |
| `npm run dev` liefert für `/api/...` HTML statt JSON | Veraltete `frontend/vite.config.js` vorhanden; maßgeblich ist nur `vite.config.ts`. |

## Umgebungsvariablen

### Backend

| Variable | Bedeutung | Standard |
|----------|-----------|----------|
| `DJANGO_SECRET_KEY` | Django-Geheimnis | *Pflicht* |
| `FIELD_ENCRYPTION_KEY` | Fernet-Schlüssel für verschlüsselte Felder | *Pflicht* |
| `FIELD_ENCRYPTION_PREVIOUS_KEYS` | Kommagetrennte alte Schlüssel für die Rotation | leer |
| `DEBUG` | Entwicklungsmodus; schaltet `Secure`-Cookies ab | `False` |
| `SECURE_COOKIES` | Erzwingt `Secure`-Cookies unabhängig von `DEBUG` | `true` ohne `DEBUG` |
| `SECURE_SSL_REDIRECT` | Leitet HTTP-Anfragen ans Backend auf HTTPS um (außer `/health/`) | wie `SECURE_COOKIES` |
| `SECURE_HSTS_SECONDS` | Dauer der HSTS-Vorgabe in Sekunden; `0` schaltet sie ab | `31536000` bei `Secure`-Cookies |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD` | HSTS auf Subdomains ausdehnen bzw. Preload anmelden | `false` |
| `TRUST_PROXY_SSL_HEADER` | `X-Forwarded-Proto` des Reverse Proxy als HTTPS-Nachweis vertrauen | `true` |
| `ALLOWED_HOSTS` | Kommagetrennte Hostnamen | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Vertrauenswürdige Herkünfte hinter einem Proxy | leer |
| `REDIS_URL` | Redis-Verbindung | `none` |

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | API-Pfad im Browser; muss dieselbe Herkunft wie die Oberfläche haben (Sitzungs-/CSRF-Cookies) | `/api/v1` |
| `VITE_BACKEND_URL` | Nur Entwicklung: Ziel des Vite-Proxys für `/api`, `/admin`, `/static` | `http://localhost:8000` |

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Vue.js Frontend (via Nginx in production) |
| `/admin/` | Django Admin |
| `/api/v1/` | REST API |
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | ReDoc API docs |
| `/health/` | Health check |

## Docker (nur Entwicklung)

Die `docker-compose.yml` im Projektwurzelverzeichnis baut die Images aus dem Quellcode und dient nur der Entwicklung:

```bash
cp .env.example .env
# Pflichtwerte setzen (DJANGO_SECRET_KEY, FIELD_ENCRYPTION_KEY, POSTGRES_PASSWORD)
make dev-up
docker compose exec backend python manage.py createsuperuser
```

Produktion (Docker Compose mit versionsgebundenen Images oder Debian 13 nativ) läuft ausschließlich über `jfctl`: [Installation](operations/ops-install.md), [Migration bestehender Installationen](operations/ops-migration.md).
