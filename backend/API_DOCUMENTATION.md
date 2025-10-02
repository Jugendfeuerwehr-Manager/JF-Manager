# JF-Manager REST API Dokumentation

## Basis-URL
- Lokal: `http://localhost:8000/api/v1/`
- Production: `https://your-domain.com/api/v1/`

## Authentifizierung

### JWT-Authentifizierung (Empfohlen für SPA)

#### Login
```
POST /api/auth/login/
```
**Body:**
```json
{
    "username": "benutzername",
    "password": "passwort"
}
```
**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Token Refresh
```
POST /api/auth/refresh/
```
**Body:**
```json
{
    "refresh": "refresh_token_here"
}
```

#### Token Verify
```
POST /api/auth/verify/
```
**Body:**
```json
{
    "token": "access_token_here"
}
```

### Verwendung
Fügen Sie den Access Token in den Authorization Header ein:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Benutzer-Endpoints

### Aktuelle Benutzerinformationen
```
GET /api/v1/users/me/
```
**Response:**
```json
{
    "id": 1,
    "username": "max.mustermann",
    "email": "max@example.com",
    "first_name": "Max",
    "last_name": "Mustermann",
    "phone": "+4912345678",
    "mobile_phone": "+491234567890",
    "street": "Musterstraße 1",
    "zip_code": "12345",
    "city": "Musterstadt",
    "avatar": "http://localhost:8000/media/avatars/user1.jpg",
    "date_joined": "2023-01-01T10:00:00Z",
    "last_login": "2023-09-21T08:30:00Z",
    "is_active": true,
    "is_staff": false
}
```

### Profil aktualisieren
```
PATCH /api/v1/users/me/
```
**Body (partial updates möglich):**
```json
{
    "first_name": "Max",
    "last_name": "Mustermann",
    "email": "new-email@example.com",
    "phone": "+4912345678",
    "mobile_phone": "+491234567890",
    "street": "Neue Straße 2",
    "zip_code": "54321",
    "city": "Neue Stadt"
}
```

### Passwort ändern
```
POST /api/v1/users/change-password/
```
**Body:**
```json
{
    "old_password": "altes_passwort",
    "new_password": "neues_passwort",
    "confirm_password": "neues_passwort"
}
```

## Mitglieder-Endpoints

### Liste aller Mitglieder
```
GET /api/v1/members/
```
**Query Parameter:**
- `search`: Suche nach Name, E-Mail etc.
- `limit`: Anzahl pro Seite (default: 100)
- `offset`: Offset für Pagination

### Einzelnes Mitglied
```
GET /api/v1/members/{id}/
```

### Neues Mitglied erstellen
```
POST /api/v1/members/
```

### Mitglied aktualisieren
```
PUT /api/v1/members/{id}/
PATCH /api/v1/members/{id}/
```

### Mitglied löschen
```
DELETE /api/v1/members/{id}/
```

## Eltern-Endpoints

### Liste aller Eltern
```
GET /api/v1/parents/
```

### Einzelner Elternteil
```
GET /api/v1/parents/{id}/
```

### Neuen Elternteil erstellen
```
POST /api/v1/parents/
```

### Elternteil aktualisieren
```
PUT /api/v1/parents/{id}/
PATCH /api/v1/parents/{id}/
```

### Elternteil löschen
```
DELETE /api/v1/parents/{id}/
```

## Inventar-Endpoints

### Artikel
```
GET /api/v1/inventory/items/          # Liste aller Artikel
GET /api/v1/inventory/items/{id}/     # Einzelner Artikel
POST /api/v1/inventory/items/         # Neuen Artikel erstellen
PUT /api/v1/inventory/items/{id}/     # Artikel aktualisieren
PATCH /api/v1/inventory/items/{id}/   # Artikel teilweise aktualisieren
DELETE /api/v1/inventory/items/{id}/  # Artikel löschen
```

### Kategorien
```
GET /api/v1/inventory/categories/          # Liste aller Kategorien
GET /api/v1/inventory/categories/{id}/     # Einzelne Kategorie
POST /api/v1/inventory/categories/         # Neue Kategorie erstellen
PUT /api/v1/inventory/categories/{id}/     # Kategorie aktualisieren
PATCH /api/v1/inventory/categories/{id}/   # Kategorie teilweise aktualisieren
DELETE /api/v1/inventory/categories/{id}/  # Kategorie löschen
```

### Artikel-Varianten
```
GET /api/v1/inventory/variants/          # Liste aller Varianten
GET /api/v1/inventory/variants/{id}/     # Einzelne Variante
POST /api/v1/inventory/variants/         # Neue Variante erstellen
PUT /api/v1/inventory/variants/{id}/     # Variante aktualisieren
PATCH /api/v1/inventory/variants/{id}/   # Variante teilweise aktualisieren
DELETE /api/v1/inventory/variants/{id}/  # Variante löschen
```

### Lagerorte
```
GET /api/v1/inventory/locations/          # Liste aller Lagerorte
GET /api/v1/inventory/locations/{id}/     # Einzelner Lagerort
POST /api/v1/inventory/locations/         # Neuen Lagerort erstellen
PUT /api/v1/inventory/locations/{id}/     # Lagerort aktualisieren
PATCH /api/v1/inventory/locations/{id}/   # Lagerort teilweise aktualisieren
DELETE /api/v1/inventory/locations/{id}/  # Lagerort löschen
```

### Lagerbestände
```
GET /api/v1/inventory/stocks/          # Liste aller Bestände
GET /api/v1/inventory/stocks/{id}/     # Einzelner Bestand
POST /api/v1/inventory/stocks/         # Neuen Bestand erstellen
PUT /api/v1/inventory/stocks/{id}/     # Bestand aktualisieren
PATCH /api/v1/inventory/stocks/{id}/   # Bestand teilweise aktualisieren
DELETE /api/v1/inventory/stocks/{id}/  # Bestand löschen
```

### Transaktionen
```
GET /api/v1/inventory/transactions/          # Liste aller Transaktionen
GET /api/v1/inventory/transactions/{id}/     # Einzelne Transaktion
POST /api/v1/inventory/transactions/         # Neue Transaktion erstellen
PUT /api/v1/inventory/transactions/{id}/     # Transaktion aktualisieren
PATCH /api/v1/inventory/transactions/{id}/   # Transaktion teilweise aktualisieren
DELETE /api/v1/inventory/transactions/{id}/  # Transaktion löschen
```

## Dienstbuch-Endpoints

### Dienste
```
GET /api/v1/servicebook/services/          # Liste aller Dienste
GET /api/v1/servicebook/services/{id}/     # Einzelner Dienst
POST /api/v1/servicebook/services/         # Neuen Dienst erstellen
PUT /api/v1/servicebook/services/{id}/     # Dienst aktualisieren
PATCH /api/v1/servicebook/services/{id}/   # Dienst teilweise aktualisieren
DELETE /api/v1/servicebook/services/{id}/  # Dienst löschen
```

### Anwesenheiten
```
GET /api/v1/servicebook/attandances/          # Liste aller Anwesenheiten
GET /api/v1/servicebook/attandances/{id}/     # Einzelne Anwesenheit
POST /api/v1/servicebook/attandances/         # Neue Anwesenheit erstellen
PUT /api/v1/servicebook/attandances/{id}/     # Anwesenheit aktualisieren
PATCH /api/v1/servicebook/attandances/{id}/   # Anwesenheit teilweise aktualisieren
DELETE /api/v1/servicebook/attandances/{id}/  # Anwesenheit löschen
```

## Bestellungen-Endpoints

### Bestellungen
```
GET /api/v1/orders/          # Liste aller Bestellungen
GET /api/v1/orders/{id}/     # Einzelne Bestellung
POST /api/v1/orders/         # Neue Bestellung erstellen
PUT /api/v1/orders/{id}/     # Bestellung aktualisieren
PATCH /api/v1/orders/{id}/   # Bestellung teilweise aktualisieren
DELETE /api/v1/orders/{id}/  # Bestellung löschen
```

### Bestellartikel
```
GET /api/v1/orders/items/          # Liste aller Bestellartikel
GET /api/v1/orders/items/{id}/     # Einzelner Bestellartikel
POST /api/v1/orders/items/         # Neuen Bestellartikel erstellen
PUT /api/v1/orders/items/{id}/     # Bestellartikel aktualisieren
PATCH /api/v1/orders/items/{id}/   # Bestellartikel teilweise aktualisieren
DELETE /api/v1/orders/items/{id}/  # Bestellartikel löschen
```

### Bestellbare Artikel
```
GET /api/v1/orders/orderable-items/          # Liste aller bestellbaren Artikel
GET /api/v1/orders/orderable-items/{id}/     # Einzelner bestellbarer Artikel
POST /api/v1/orders/orderable-items/         # Neuen bestellbaren Artikel erstellen
PUT /api/v1/orders/orderable-items/{id}/     # Bestellbaren Artikel aktualisieren
PATCH /api/v1/orders/orderable-items/{id}/   # Bestellbaren Artikel teilweise aktualisieren
DELETE /api/v1/orders/orderable-items/{id}/  # Bestellbaren Artikel löschen
```

### Bestellstatus
```
GET /api/v1/orders/statuses/          # Liste aller Bestellstatus
GET /api/v1/orders/statuses/{id}/     # Einzelner Bestellstatus
POST /api/v1/orders/statuses/         # Neuen Bestellstatus erstellen
PUT /api/v1/orders/statuses/{id}/     # Bestellstatus aktualisieren
PATCH /api/v1/orders/statuses/{id}/   # Bestellstatus teilweise aktualisieren
DELETE /api/v1/orders/statuses/{id}/  # Bestellstatus löschen
```

## Qualifikationen-Endpoints

### Qualifikationstypen
```
GET /api/v1/qualifications/types/          # Liste aller Qualifikationstypen
GET /api/v1/qualifications/types/{id}/     # Einzelner Qualifikationstyp
POST /api/v1/qualifications/types/         # Neuen Qualifikationstyp erstellen
PUT /api/v1/qualifications/types/{id}/     # Qualifikationstyp aktualisieren
PATCH /api/v1/qualifications/types/{id}/   # Qualifikationstyp teilweise aktualisieren
DELETE /api/v1/qualifications/types/{id}/  # Qualifikationstyp löschen
```

### Qualifikationen
```
GET /api/v1/qualifications/          # Liste aller Qualifikationen
GET /api/v1/qualifications/{id}/     # Einzelne Qualifikation
POST /api/v1/qualifications/         # Neue Qualifikation erstellen
PUT /api/v1/qualifications/{id}/     # Qualifikation aktualisieren
PATCH /api/v1/qualifications/{id}/   # Qualifikation teilweise aktualisieren
DELETE /api/v1/qualifications/{id}/  # Qualifikation löschen
```

### Sonderaufgaben-Typen
```
GET /api/v1/specialtasks/types/          # Liste aller Sonderaufgaben-Typen
GET /api/v1/specialtasks/types/{id}/     # Einzelner Sonderaufgaben-Typ
POST /api/v1/specialtasks/types/         # Neuen Sonderaufgaben-Typ erstellen
PUT /api/v1/specialtasks/types/{id}/     # Sonderaufgaben-Typ aktualisieren
PATCH /api/v1/specialtasks/types/{id}/   # Sonderaufgaben-Typ teilweise aktualisieren
DELETE /api/v1/specialtasks/types/{id}/  # Sonderaufgaben-Typ löschen
```

### Sonderaufgaben
```
GET /api/v1/specialtasks/          # Liste aller Sonderaufgaben
GET /api/v1/specialtasks/{id}/     # Einzelne Sonderaufgaben
POST /api/v1/specialtasks/         # Neue Sonderaufgaben erstellen
PUT /api/v1/specialtasks/{id}/     # Sonderaufgaben aktualisieren
PATCH /api/v1/specialtasks/{id}/   # Sonderaufgaben teilweise aktualisieren
DELETE /api/v1/specialtasks/{id}/  # Sonderaufgaben löschen
```

## Allgemeine API-Funktionen

### Pagination
Alle Listen-Endpoints unterstützen Pagination:
```json
{
    "count": 150,
    "next": "http://localhost:8000/api/v1/members/?limit=100&offset=100",
    "previous": null,
    "results": [...]
}
```

### Filtering
Die meisten Endpoints unterstützen Filtering:
```
GET /api/v1/members/?search=max
GET /api/v1/inventory/items/?category=1
```

### Ordering
Sortierung mit dem `ordering` Parameter:
```
GET /api/v1/members/?ordering=last_name
GET /api/v1/members/?ordering=-created_at
```

## Fehlerbehandlung

### HTTP Status Codes
- `200` - OK (Erfolgreiche GET, PUT, PATCH Requests)
- `201` - Created (Erfolgreiches POST)
- `204` - No Content (Erfolgreiches DELETE)
- `400` - Bad Request (Validierungsfehler)
- `401` - Unauthorized (Nicht authentifiziert)
- `403` - Forbidden (Keine Berechtigung)
- `404` - Not Found (Ressource nicht gefunden)
- `500` - Internal Server Error

### Fehler-Response Format
```json
{
    "error": "Fehlerbeschreibung",
    "details": {
        "field_name": ["Spezifische Feldvalidierungsfehler"]
    }
}
```

## Vue.js Integration Beispiele

### API Service Setup
```javascript
// api.js
import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1/',
  timeout: 10000
})

// Request Interceptor für JWT Token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response Interceptor für Token Refresh
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post('/api/auth/refresh/', {
            refresh: refreshToken
          })
          localStorage.setItem('access_token', response.data.access)
          // Retry original request
          return api.request(error.config)
        } catch (refreshError) {
          // Redirect to login
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api
```

### Login Service
```javascript
// auth.js
import api from './api'

export const authService = {
  async login(username, password) {
    const response = await api.post('/api/auth/login/', {
      username,
      password
    })
    
    localStorage.setItem('access_token', response.data.access)
    localStorage.setItem('refresh_token', response.data.refresh)
    
    return response.data
  },

  async getCurrentUser() {
    const response = await api.get('/users/me/')
    return response.data
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }
}
```

### Mitglieder Service
```javascript
// members.js
import api from './api'

export const membersService = {
  async getMembers(params = {}) {
    const response = await api.get('/members/', { params })
    return response.data
  },

  async getMember(id) {
    const response = await api.get(`/members/${id}/`)
    return response.data
  },

  async createMember(memberData) {
    const response = await api.post('/members/', memberData)
    return response.data
  },

  async updateMember(id, memberData) {
    const response = await api.patch(`/members/${id}/`, memberData)
    return response.data
  },

  async deleteMember(id) {
    await api.delete(`/members/${id}/`)
  }
}
```