# AGENTS.md – Arbeitsregeln für Coding-Agents im JF-Manager

Diese Datei gilt für alle Agents (Claude Code, Copilot, Codex …). Sie beschreibt, **wie** im Projekt gearbeitet wird und **welche Architekturregeln nicht verhandelbar sind**. Details stehen in `docs/architecture/`; bei Widerspruch zwischen dieser Datei, der Doku und dem Code zuerst den Code prüfen und die Abweichung im PR benennen, statt still einer Seite zu folgen.

## Projekt in einem Absatz

JF-Manager verwaltet Jugendfeuerwehren und vergleichbare Organisationen (Vereine, Einsatzabteilungen): Mitglieder, Eltern, Portal, Teilnahme, Inventar, Bestellungen, Qualifikationen, Dienstbuch und Übungsplanung. Die Anwendung läuft öffentlich im Internet und verarbeitet sensible Daten von Minderjährigen. Mehrere Abteilungen teilen sich eine Installation und sind strikt voneinander getrennt.

- **Backend:** Django 5.2, DRF, PostgreSQL (SQLite nur für schnelle lokale Tests), RQ-Worker über Redis, `pipenv` (`backend/Pipfile`).
- **Frontend:** Vue 3, TypeScript (strict), Pinia (Composition API), PrimeVue, Vite (`frontend/`).
- **Betrieb:** ausschließlich über `jfctl` (`docs/operations/ops-jfctl.md`).

## Architektur-Leitplanken (verbindlich)

### 1. Das Backend entscheidet über Rechte – immer

- Jeder Endpunkt prüft Anmeldung **und** Recht serverseitig. Das Frontend blendet nur aus; es ist nie die Sicherheitsgrenze.
- Standard: `jf_manager_backend.permissions.CustomDefaultPermissions` (Django-Modellrechte plus Abteilungsrollen). `permission_classes` nur mit Begründung im Code überschreiben.
- Abteilungsdaten laufen über `departments.mixins.DepartmentScopeViewSetMixin` bzw. eigene Queryset-Helfer nach dem Muster `inventory/api/access.py`.
- **Sichtbarkeit darf breiter sein als Änderbarkeit:** zentrale Datensätze (`department=NULL`) dürfen sichtbar sein, Schreiben bleibt bei der besitzenden Abteilung.
- Organisationsweiter Zugriff (`can_access_all_departments`) erteilt **keine** Modellrechte; Abteilungsrollen wirken nur in ihrer Abteilung; `is_staff` allein gewährt nichts.
- Der `department`-Parameter aus dem Frontend ist Kontext, keine Rechteaussage. Fehlende oder manipulierte Parameter dürfen nie mehr Rechte ergeben.
- Jeder neue oder geänderte Endpunkt bekommt Tests für: anonym, fehlendes Recht, fremde Abteilung, berechtigter Fall.
- Referenz: `docs/architecture/departments-and-permissions.md`, `docs/planning/role-permission-manifest.md`.

### 2. Anmeldung: nur Cookie-Sitzungen

- Sitzung + CSRF (`users.session_auth.SessionAuthentication`), MFA und Passkeys. **Kein JWT, keine Token-Anmeldung, keine API-Keys** – auch nicht „nur für einen Test“ oder ein Skript.

### 3. Backend-Schichten

```
backend/{app}/
├── api/
│   ├── viewsets/      # dünne DRF-ViewSets: Rechte, Serializer, Aufruf der Fachlogik
│   ├── serializers/   # je Aktion passende Serializer
│   ├── filters.py
│   └── permissions.py
├── services/          # Fachlogik, Zustandsübergänge, Transaktionen
├── models/
└── tests/
```

- ViewSets bleiben dünn. Fachregeln, Zustandsübergänge und alles, was mehrere Modelle in einer Transaktion ändert, gehören in Services bzw. Fachmodule, nicht in ViewSets oder Serializer.
- Zustandsautomaten nur über ihren Service ändern (z. B. Bestellstatus über `orders.notifications.OrderWorkflowService`).
- Neue Endpunkte: ViewSet in `{app}/api/viewsets/`, Basis `BasePermissionedViewSet` (`jf_manager_backend/mixins.py`), Registrierung in `jf_manager_backend/rest_urls.py`, eigene Aktionen per `@action`. Referenzimplementierung: `backend/orders/api/`.
- Listen sind paginiert (`LimitOffsetPagination`, `{count, next, previous, results}`).
- Seiteneffekte (E-Mail, Push, Sync) laufen asynchron über den RQ-Worker bzw. die vorhandenen Producer/Dispatcher in `notifications/`, nicht synchron im Request.
- **Bestehende Abweichungen:** `portal/`, `participation/` und `notifications/` nutzen `APIView`s in `*views.py` und eigene `urls.py`. Dort im vorhandenen Stil weiterarbeiten und nicht in derselben Änderung umbauen. Neue Apps folgen dem obigen Schema.
- `views.py` mit Django-Templates ist Altbestand: keine neuen Template-Views.
- Jede Modelländerung mit Migration; Migrationen nicht von Hand editieren. Kein OpenAPI-Schema ins Repository einchecken (wird zur Laufzeit erzeugt).

### 4. Frontend-Schichten

```
frontend/src/
├── types/<domäne>.ts        # Schnittstellen, PaginatedResponse<T>
├── api/<domäne>.ts          # HTTP über api/index.ts (Sitzung, CSRF, Abteilungskontext)
├── stores/<domäne>.ts       # Pinia, defineStore('x', () => { … }), Lade-/Fehlerzustand
├── composables/             # wiederverwendbare UI-Logik ohne eigenen Datenbesitz
├── utils/                   # reine Hilfsfunktionen
├── views/                   # Routenseiten, setzen Organismen zusammen
└── components/<domäne>/{atoms,molecules,organisms}/
```

- Datenfluss: Komponente → Store-Aktion → `api/` → Backend. **Neue Komponenten rufen `api/` nicht direkt auf**; bestehende Direktaufrufe (Altbestand) nicht vermehren, beim Anfassen gern in den Store ziehen.
- Store-Zustand nur über Store-Aktionen ändern. Bei Listen `response.data.results` übernehmen.
- Typisierte Props/Emits (`defineProps<Props>()`, `defineEmits<{…}>()`); kein `any` außer an Integrationsgrenzen.
- Keine Mockdaten in Komponenten.

Muster (Referenz: `frontend/src/api/orders.ts`, `frontend/src/stores/orders.ts`):

```typescript
// api/orders.ts – nur HTTP, keine Logik
export const ordersApi = {
  list: (params?: OrderListParams) =>
    apiClient.get<PaginatedResponse<Order>>('/orders/', { params }),
}

// stores/orders.ts – Zustand, Laden, Fehler
export const useOrdersStore = defineStore('orders', () => {
  const orders = ref<Order[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchOrders(params?: OrderListParams) {
    loading.value = true
    error.value = null
    try {
      orders.value = (await ordersApi.list(params)).data.results // nicht .data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Bestellungen konnten nicht geladen werden') // utils/apiError.ts
    } finally {
      loading.value = false
    }
  }
  return { orders, loading, error, fetchOrders }
})
```
