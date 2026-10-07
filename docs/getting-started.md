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
pipenv run python dev_env.py ensure
```

`dev_env.py ensure` legt `backend/.env` an bzw. ergänzt fehlende Werte: `DJANGO_SECRET_KEY`,
`FIELD_ENCRYPTION_KEY`, `DEBUG=True` und `REDIS_URL`. Ein vorhandener gültiger Schlüssel wird nie
ersetzt, Werte werden nicht ausgegeben. Von Hand sind mindestens nötig:

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

Alle 16 Standardrollen werden nach der Migration automatisch angelegt. Vorhandene Rollenrechte bleiben erhalten. Neue Rollen und Kopien bestehender Vorlagen werden unter **Rollenvorlagen** verwaltet; siehe [Rollenhandbuch](domains/roles-and-permissions.md).

Administratorkonten müssen beim ersten Login einen Passkey oder eine Authenticator-App (TOTP) einrichten; die Oberfläche führt durch die Einrichtung und zeigt einmalige Wiederherstellungscodes. Mit Passkey ist danach die Anmeldung ohne Passwort möglich ([session-auth.md](operations/session-auth.md#anmeldung-mit-passkey-ohne-passwort)); unter `http://localhost` erlauben Browser Passkeys auch ohne HTTPS.

Die fachliche Einrichtung erfolgt unter **Einstellungen → Einrichtung**; siehe
[Einrichtung und Organisationseinstellungen](domains/configuration.md).

### 3. Frontend einrichten

```bash
cd frontend
npm install
cp .env.example .env
```

`VITE_API_BASE_URL` bleibt `/api/v1`. Ein abweichender Backend-Port wird nur über `VITE_BACKEND_URL` gesetzt.

### 4. Starten

**VS Code:** Startkonfiguration **„JF-Manager: Backend + Frontend“**. Sie startet Redis (oder nutzt ein laufendes), ergänzt fehlende Werte in `backend/.env`, führt Migrationen aus, prüft alle gespeicherten Geheimnisse gegen den Schlüssel, startet den RQ-Worker, Django und Vite und öffnet Chrome unter `http://localhost:5173`. Passen gespeicherte Daten nicht zum Schlüssel, bricht der Start bei **„backend: check keys“** mit einem Hinweis ab, statt später mit `InvalidToken` im Debugger zu stehen.

Backend-Befehle im Terminal am besten über den Helfer starten; dann hat `backend/.env` Vorrang vor
Variablen, die in der Shell noch gesetzt sind:

```bash
cd backend
pipenv run python dev_env.py run python manage.py runserver
pipenv run python dev_env.py check
```

**Terminal:**

```bash
./start-dev.sh
```

Oder einzeln: `cd backend && pipenv run python manage.py runserver` und `cd frontend && npm run dev`, dann `http://localhost:5173` öffnen.

**Mit Beispieldaten statt eigener Datenbank:** VS-Code-Konfiguration **„Demo: Backend + Frontend“** oder wie in der README beschrieben. Die Demo legt eine temporäre Datenbank mit eigenem Wegwerf-Schlüssel an.

### Lokale Daten zurücksetzen und Demodaten laden

VS-Code-Task **„dev: Zurücksetzen und Demodaten“** (oder Startkonfiguration **„Dev: Zurücksetzen und
Demodaten“**) fragt nach und löscht dann die lokale SQLite-Datenbank, `backend/uploads/` und die
Cache-Einträge der Anwendung in Redis, migriert und lädt vollständige fiktive Demodaten. Im Terminal:

```bash
cd backend
pipenv run python dev_env.py reset --confirm ja
```

Die Demodaten (`manage.py seed_demo`) enthalten drei Abteilungen mit Gruppen, Mitgliedern und Eltern,
zehn Konten mit Standardrollen, Dienstbuch mit Anwesenheit, Übungen in allen Status mit Stationen,
Serie und Vorlage, Qualifikationen mit bald ablaufenden Nachweisen, Inventar mit Größen, Beständen und
Ausgaben sowie Bestellungen in allen Status. Alle Daten sind erfunden (`example.invalid`); nichts wird
versendet.

| Konto | Rolle |
|-------|-------|
| `admin` | Superuser |
| `jugendwart` | Jugendwart (Organisation, alle Abteilungen) |
| `leitung.mitte`, `leitung.nord`, `leitung.kinder` | Abteilungsjugendwart |
| `betreuer.mitte`, `betreuer.nord` | Jugendleiter bzw. Betreuer |
| `ausbilder` | Übungsplanung Mitte und Nord, Bibliothek |
| `geraetewart` | Inventar und Bestellungen (alle Abteilungen) |
| `kommunikation` | E-Mail-Versand (alle Abteilungen) |

Alle Konten haben dasselbe Passwort; es steht in `backend/.dev-demo-login` (nur lokal, nicht
versioniert). Konten mit Pflicht-Zwei-Faktor-Anmeldung haben bereits eine Authenticator-App
hinterlegt; den aktuellen Code zeigt der Task **„dev: Anmeldecode (Demo)“** oder
`pipenv run python dev_env.py totp admin` (nur mit `DEBUG=True` und nur für Demokonten).

`seed_demo` verweigert sich bei nicht leerer Datenbank und ohne `DEBUG`. Für ein eigenes
Vorführsystem ohne echte Daten: `python manage.py seed_demo --allow-non-debug`.

### Nicht lesbares SMTP-Passwort in der Entwicklung

Die VS-Code-Konfigurationen verwenden denselben Schlüssel aus `backend/.env` und aktivieren
`DEV_ALLOW_UNREADABLE_SMTP=True` ausschließlich für den lokalen Backend-/Workerstart.
Wenn **nur** das gespeicherte SMTP-Passwort nicht lesbar ist, startet Django im Debugmodus
weiter; jeder E-Mail-Versand schlägt ausdrücklich fehl. Der gespeicherte Wert bleibt erhalten.
Unter **Einstellungen → E-Mail** wird der Fehler angezeigt und das Passwort kann neu
hinterlegt werden. Andere verschlüsselte Daten (MFA, LDAP/OIDC, Sync) bleiben strikt geprüft.

Im Terminal ist dieser begrenzte Modus ebenfalls ausdrücklich einschaltbar:

```bash
cd backend
DEBUG=True DEV_ALLOW_UNREADABLE_SMTP=True pipenv run python manage.py runserver
```

`DEBUG=False` ignoriert die Ausnahme auch bei gesetztem Schalter. Ein neuer zufälliger
Hauptschlüssel repariert keine vorhandene Datenbank: den ursprünglichen Schlüssel erhalten
oder als `FIELD_ENCRYPTION_PREVIOUS_KEYS` ergänzen und mit
`pipenv run python manage.py rotate_field_encryption` zunächst prüfen. Keine Schlüssel in
VS-Code-Dateien eintragen. Ohne passenden alten Schlüssel muss das betroffene SMTP-Passwort
neu eingegeben werden; es wird weder entschlüsselt noch still gelöscht.

### Häufige Probleme

| Symptom | Ursache und Abhilfe |
|---------|---------------------|
| Start bricht mit „FIELD_ENCRYPTION_KEY muss explizit gesetzt sein“ ab | `pipenv run python dev_env.py ensure` ausführen. |
| „backend: check keys“ meldet „Schlüsselprüfung fehlgeschlagen“ oder der Debugger hält bei `InvalidToken` | Lokale Daten wurden mit einem anderen Schlüssel geschrieben. Lokal neu beginnen: „dev: Zurücksetzen und Demodaten“. Daten behalten: alten Schlüssel als `FIELD_ENCRYPTION_PREVIOUS_KEYS` ergänzen. |
| Mehrere lokale Instanzen (Worktrees) teilen einen Redis | Cache-Einträge sind an den Schlüssel gebunden und kollidieren nicht. RQ-Warteschlangen werden aber geteilt: je Instanz eine eigene Redis-Datenbank setzen, z. B. `REDIS_URL=redis://localhost:6379/1`. |
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
| `DEV_ALLOW_UNREADABLE_SMTP` | Lokaler Start trotz unlesbarem SMTP-Passwort, Versand gesperrt; nur mit `DEBUG=True` wirksam | `False` |
| `DEBUG` | Entwicklungsmodus; schaltet `Secure`-Cookies ab | `False` |
| `SECURE_COOKIES` | Erzwingt `Secure`-Cookies unabhängig von `DEBUG` | `true` ohne `DEBUG` |
| `SECURE_SSL_REDIRECT` | Leitet HTTP-Anfragen ans Backend auf HTTPS um (außer `/health/`) | wie `SECURE_COOKIES` |
| `SECURE_HSTS_SECONDS` | Dauer der HSTS-Vorgabe in Sekunden; `0` schaltet sie ab | `31536000` bei `Secure`-Cookies |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD` | HSTS auf Subdomains ausdehnen bzw. Preload anmelden | `false` |
| `TRUST_PROXY_SSL_HEADER` | `X-Forwarded-Proto` des Reverse Proxy als HTTPS-Nachweis vertrauen | `true` |
| `ALLOWED_HOSTS` | Kommagetrennte Hostnamen | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Vertrauenswürdige Herkünfte hinter einem Proxy | leer |
| `REDIS_URL` | Redis-Verbindung | `none` |
| `FRONTEND_URL` | Öffentliche Adresse der Oberfläche; Grundlage für SSO-Weiterleitungen und Passkeys | `http://localhost:5173` |
| `WEBAUTHN_RP_ID`, `WEBAUTHN_ORIGINS` | Abweichende Passkey-RP-ID bzw. erlaubte Herkünfte ([session-auth.md](operations/session-auth.md#passkeys-domain-und-https)) | aus `FRONTEND_URL` |

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

`dev/compose.yml` baut Backend und Frontend aus dem Arbeitsstand und startet sie mit PostgreSQL 17, Redis und Workern, nur an `localhost` gebunden:

```bash
cp dev/.env.example dev/.env
# Pflichtwerte setzen (POSTGRES_PASSWORD, DJANGO_SECRET_KEY, FIELD_ENCRYPTION_KEY)
make dev-up
docker compose -f dev/compose.yml exec backend python manage.py createsuperuser
```

Oberfläche: `http://localhost:8080`. `make dev-logs`, `make dev-down`.

Produktion (Docker Compose mit versionsgebundenen Images oder Debian 13 nativ) läuft ausschließlich über `jfctl`: [Installation](operations/ops-install.md), [Migration bestehender Installationen](operations/ops-migration.md).
