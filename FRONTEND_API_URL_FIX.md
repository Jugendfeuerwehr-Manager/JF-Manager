# Frontend API URL Fix

## Problem

Das Frontend wurde mit einer hardcodierten API URL (`http://localhost:8000/api/v1`) gebaut, was zu CORS-Fehlern führt, wenn es auf dem Server läuft:

```
XMLHttpRequest cannot load http://localhost:8000/api/v1/auth/login/ due to access control checks.
```

Zusätzlich gibt es CSRF-Fehler beim Django Admin Login:

```
Verboten (403)
CSRF-Verifizierung fehlgeschlagen. Anfrage abgebrochen.
```

## Ursache

Vite-Umgebungsvariablen werden zur **Build-Zeit** in den Code eingebaut, nicht zur Laufzeit. Das Dockerfile hat die `VITE_API_BASE_URL` Umgebungsvariable nicht gesetzt, sodass der Fallback-Wert verwendet wurde.

## Lösung

### 1. Dockerfile angepasst

Die `VITE_API_BASE_URL` wird jetzt als Build-Argument akzeptiert und zur Build-Zeit gesetzt:

```dockerfile
# Add build arguments
ARG VITE_API_BASE_URL=/api/v1

# Build the application with environment variable
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build-only
```

### 2. docker-compose.yml erweitert

Das Build-Argument wird in der docker-compose.yml übergeben:

```yaml
frontend:
  build:
    args:
      VITE_API_BASE_URL: ${VITE_API_BASE_URL:-/api/v1}
```

### 3. .env.example aktualisiert

Die `.env.example` enthält jetzt die Frontend-Konfiguration:

```bash
# Frontend Configuration
# For production behind nginx reverse proxy, use relative path:
VITE_API_BASE_URL=/api/v1
# For development or direct access, use full URL:
# VITE_API_BASE_URL=https://yourdomain.com/api/v1
```

## Deployment

### Für Produktion (hinter nginx Reverse Proxy)

1. In `.env` setzen (ersetze `yourdomain.com` mit deiner echten Domain):
   ```bash
   # Frontend API Configuration
   VITE_API_BASE_URL=/api/v1
   
   # Django Security Settings (WICHTIG!)
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,localhost
   # CSRF_TRUSTED_ORIGINS muss das KOMPLETTE URL-Schema enthalten!
   CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   ```

2. Frontend neu bauen:
   ```bash
   docker-compose build --no-cache frontend
   docker-compose up -d frontend
   ```

3. Backend neu starten (um neue CSRF Settings zu laden):
   ```bash
   docker-compose restart backend
   ```

Der relative Pfad `/api/v1` funktioniert, weil nginx alle `/api/*` Anfragen an das Backend proxied (siehe `frontend/conf.d/default.conf`).

### Für direkten Zugriff (ohne Reverse Proxy)

Falls das Frontend direkt (nicht über nginx) erreichbar sein soll:

```bash
VITE_API_BASE_URL=https://jfl.feuerwehr-laudenbach.de/api/v1
```

## Verifikation

Nach dem Neubauen im Browser-DevTools Console prüfen:

```javascript
// In der Netzwerk-Tab sollten API-Requests zu /api/v1/* gehen
// NICHT zu http://localhost:8000/api/v1/*
```

Django Admin Login testen:
```
https://yourdomain.com/admin/
```

Oder im gebauten JavaScript nach der URL suchen:
```bash
docker exec jf_manager_frontend grep -r "localhost:8000" /usr/share/nginx/html/assets/
# Sollte NICHTS finden
```

Backend Logs für CSRF-Fehler prüfen:
```bash
docker-compose logs backend | grep -i csrf
```

## Entwicklung

Für lokale Entwicklung bleibt die `frontend/.env` unverändert:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Der Dev-Server verwendet diese URL direkt.

## Nginx Konfiguration

Die nginx-Konfiguration (`frontend/conf.d/default.conf`) proxied API-Requests korrekt:

```nginx
location /api/ {
    proxy_pass http://backend;
    # ... headers ...
}
```

Das bedeutet:
- Browser macht Request zu `https://jfl.feuerwehr-laudenbach.de/api/v1/auth/login/`
- nginx leitet weiter zu `http://backend:8000/api/v1/auth/login/`
- Keine CORS-Probleme, da alles von derselben Domain kommt

## Häufige Probleme

### CSRF-Fehler beim Admin Login

**Symptom**: `Verboten (403) CSRF-Verifizierung fehlgeschlagen`

**Lösung**: 
1. Sicherstellen, dass `CSRF_TRUSTED_ORIGINS` in `.env` das **komplette** URL-Schema enthält:
   ```bash
   # ✅ RICHTIG
   CSRF_TRUSTED_ORIGINS=https://jfl.feuerwehr-laudenbach.de
   
   # ❌ FALSCH - fehlendes https://
   CSRF_TRUSTED_ORIGINS=jfl.feuerwehr-laudenbach.de
   ```

2. Backend neu starten nach `.env` Änderungen:
   ```bash
   docker-compose restart backend
   ```

### API Requests gehen zu localhost

**Symptom**: Netzwerk-Tab zeigt Requests zu `http://localhost:8000/api/v1/*`

**Lösung**: Frontend mit korrekter `VITE_API_BASE_URL` neu bauen (siehe oben)
