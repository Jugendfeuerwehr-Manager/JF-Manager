# Bugfix - VariableDoesNotExist: n_attended_services

## Datum: 1. Oktober 2025

### Problem
```
VariableDoesNotExist: Failed lookup for key [n_attended_services]
```

Der Server stürzte beim Laden der Dienstbuch-Seite (`/servicebook/`) ab, weil das Template `service_table.html` die Variable `{{ n_attended_services }}` verwendete, die nicht im Context definiert war.

### Ursache
Im Template wurden doppelte Badge-Anzeigen in den Top-Listen verwendet:

```html
<!-- FALSCH - doppeltes Badge -->
<li class="list-group-item d-flex justify-content-between align-items-center">
    {{ forloop.counter }}. {{ item.person__name }} {{ item.person__lastname }}:
    <span class="badge badge-primary badge-pill">{{ item.num_services }}</span>
    <span class="badge badge-primary badge-pill">{{ n_attended_services }}</span>  ← Diese Variable existiert nicht!
</li>
```

Die Variable `n_attended_services` wurde nie in der View `ServiceTableView.get_context_data()` übergeben und war ein Copy-Paste-Fehler aus einem anderen Template (wahrscheinlich `member_detail.html`).

### Lösung
Die nicht existierende Variable wurde aus allen drei Top-Listen entfernt:

1. **"Am meisten anwesend"** (top_present)
2. **"Am meisten entschuldigt"** (top_e)  
3. **"Am meisten fehlend"** (top_f)

```html
<!-- RICHTIG - nur ein Badge mit der korrekten Anzahl -->
<li class="list-group-item d-flex justify-content-between align-items-center">
    {{ forloop.counter }}. {{ item.person__name }} {{ item.person__lastname }}:
    <span class="badge badge-primary badge-pill">{{ item.num_services }}</span>
</li>
```

### Betroffene Datei
- `servicebook/templates/service_table.html` (Zeilen 357, 372, 388)

### Änderungen
- ❌ Entfernt: 3 Vorkommen von `{{ n_attended_services }}`
- ✅ Behalten: `{{ item.num_services }}` (zeigt die korrekte Anzahl der Dienste)

### Testen
```bash
# Check auf Fehler
python manage.py check
# ✅ System check identified no issues (0 silenced).

# Server starten
python manage.py runserver
# ✅ Server läuft ohne Fehler

# Dienstbuch-Seite aufrufen
# ✅ /servicebook/ lädt ohne Fehler
```

### Kontext
Die Variable `n_attended_services` wird nur in den Member-Detail-Templates (`member_detail.html`, `member_detail_complete.html`) verwendet, wo sie im Context der jeweiligen View bereitgestellt wird. Sie hat nichts in der Service-Table-View zu suchen.

### Status
✅ **BEHOBEN** - Die Seite lädt jetzt fehlerfrei.
