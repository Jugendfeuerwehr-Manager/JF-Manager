# Arbeitsregeln für die Roadmap

Vor Änderungen an Sicherheit, Rollen, Übungsplanung, Bedienung oder Betrieb zuerst `docs/planning/security-ux-design-roadmap.md` lesen. Den Wiederaufnahmestand, Paketstatus und die letzten Journaleinträge mit Git-Diff und tatsächlichem Code abgleichen.

- Roadmap-Änderungen auf `feat/security-roles-training-operations` integrieren.
- Vor Paketbeginn den Detailblock in Abschnitt 6 mit Abnahme, Abhängigkeiten und stabilen Teilschritt-IDs ausfüllen.
- Jeden abgeschlossenen Teilschritt separat committen. Nur eigene zugehörige Dateien oder Hunks stagen und den Staged-Diff prüfen.
- Im selben Commit Wiederaufnahmeübersicht, Paketstatus und Journal aktualisieren. Prüfergebnisse als bestanden, fehlgeschlagen oder nicht ausgeführt kennzeichnen.
- Bei Unterbrechung einen wiederaufnehmbaren Checkpoint mit offenen Änderungen, Risiken und nächstem Schritt festhalten.
- Vorhandene oder fremde Änderungen nicht zurücksetzen oder als eigene Roadmap-Ergebnisse ausgeben. Keine Geheimnisse oder personenbezogenen Echtdaten ins Journal aufnehmen.

Die vollständigen fachlichen Anforderungen und Prüfregeln stehen in der Roadmap. Eltern-/Mitgliederportal und Teilnahmesteuerung sind in `docs/planning/portal-participation-concept.md` spezifiziert.

# Projektüberblick

JF-Manager verwaltet Jugendfeuerwehren: Mitglieder, Eltern, Inventar, Bestellungen, Qualifikationen, Dienstbuch und Übungsplanung. Seit 2018 intern entwickelt, seit 2025 Open Source.

- **Backend:** Django 5.2, Django REST Framework, PostgreSQL (SQLite für schnelle lokale Tests), Abhängigkeiten über `pipenv` (`backend/Pipfile`).
- **Frontend:** Vue 3, TypeScript, Pinia, PrimeVue, Vite (`frontend/`).
- **Anmeldung:** Cookie-Sitzungen mit CSRF (`users.session_auth.SessionAuthentication`), MFA und Passkeys. Kein JWT.
- **Rechte:** `DEFAULT_PERMISSION_CLASSES = jf_manager_backend.permissions.CustomDefaultPermissions`; Abteilungstrennung und Rollenmodell siehe `docs/architecture/departments-and-permissions.md` und `docs/planning/role-permission-manifest.md`.

## Backend-Struktur

```
backend/{app}/
├── api/              # REST-API (hier entwickeln)
│   ├── serializers/  # fachlich getrennte Serializer
│   ├── viewsets/     # DRF-ViewSets mit Aktionen
│   ├── filters.py    # django-filter-Klassen
│   └── permissions.py
├── views.py          # Altbestand (Django-Templates), keine neuen Endpunkte
├── models/
└── notifications/    # Fachlogik als Services (Beispiel: orders)
```

- Neue Endpunkte immer in `{app}/api/viewsets/`, registriert in `backend/jf_manager_backend/rest_urls.py`. Referenzimplementierung: `backend/orders/api/`.
- Listen-Endpunkte sind paginiert (`LimitOffsetPagination`, `PAGE_SIZE` 100): Antwort `{count, next, previous, results}`.
- Serializer je Aktion über `get_serializer_class()` wählen (Liste schlank, Anlage mit Validierung, Detail vollständig).
- Eigene Endpunkte über `@action(detail=True|False, methods=[...])`.
- Rechte über die vorhandenen Permission-Klassen erzwingen; `permission_classes` nur mit Begründung überschreiben. Rechte und Anmeldung jedes neuen Endpunkts testen (fehlende Rechte, fremde Abteilung).
- Bestellstatus nur über `orders.notifications.OrderWorkflowService` ändern (`get_available_transitions`, `validate_status_change`).
- Schemaänderungen immer mit Migration. OpenAPI-Schema: `pipenv run python manage.py spectacular --file schema.yml`.

## Frontend-Struktur

```
frontend/src/
├── types/<domäne>.ts       # TypeScript-Schnittstellen, PaginatedResponse<T>
├── api/<domäne>.ts         # HTTP-Client auf Basis von api/index.ts (Sitzung, CSRF)
├── stores/<domäne>.ts      # Pinia-Store, Composition API
└── components/<domäne>/
    ├── atoms/
    ├── molecules/
    └── organisms/
```

- Komponenten sind Darstellung; Fachlogik und API-Aufrufe liegen in Pinia-Stores (`defineStore('name', () => { … })` mit `ref`, `computed`, async Aktionen und Lade-/Fehlerzustand).
- Store-Zustand nie direkt aus Komponenten verändern, sondern über Store-Aktionen.
- Bei Listen `response.data.results` übernehmen, nicht `response.data`.
- Keine Mockdaten in Komponenten; echte Daten über Stores laden.
- Props und Emits typisiert (`defineProps<Props>()`, `defineEmits<{ … }>()`).
- Design: DES-01-Tokens, Status nie nur über Farbe, Touchflächen ≥ 44 px, mobil zuerst.

Weitere Details: `docs/architecture/backend-structure.md`, `docs/architecture/frontend-structure.md`, `CONTRIBUTING.md`.

## Entwicklung

- Lokal starten: `./start-dev.sh` (erwartet `backend/.env`, Vorlage `backend/example.env`, siehe `docs/getting-started.md`). Backend `:8000`, Frontend `:5173`, API unter `/api/v1/`.
- Demodaten: Management-Command `seed_demo`. Neue Funktionen ergänzen die Demodaten mit fiktiven Personen.
- Container für Entwicklung: `make dev-up` (`dev/compose.yml`). Produktion ausschließlich über `jfctl` (`docs/operations/ops-jfctl.md`).

## Pflichtprüfungen vor Abschluss jeder Codeänderung

Alle Prüfungen lokal ausführen und jeden Fehler beheben:

- Frontend-Typprüfung: `cd frontend && npm run type-check`
- Frontend-Lint: `cd frontend && npm run lint`
- Frontend-Tests: `cd frontend && npm run test:unit -- --run`
- Backend-Lint/Format: `cd backend && pipenv run ruff check . && pipenv run ruff format --check .`
- Backend-Tests mit expliziten Modulen (`pipenv run python manage.py test <module>`); `manage.py test` ohne Module scheitert am Namenskonflikt `inventory/tests.py` / `inventory/tests/`.
- Bei Modelländerungen: `pipenv run python manage.py makemigrations --check`.

## Allgemeine Regeln

- Keine Markdown-Dateien ohne ausdrücklichen Auftrag anlegen; Ausnahme sind die Roadmap und Planungsdokumente unter `docs/planning/`.
- Code folgt den vorhandenen Mustern und Konventionen des jeweiligen Moduls.
- Für neue Funktionen Tests anlegen (Unit, Integration, bei Bedarf Browser).
