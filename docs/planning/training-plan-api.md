# TRAIN-01: atomarer Planvertrag

`GET /api/v1/training/sessions/{id}/plan/` liefert Terminmetadaten, Planversion `revision` und alle Bausteine gemeinsam. `PUT` ersetzt den vollständigen Plan:

```json
{
  "expected_revision": 1,
  "session": {
    "title": "Übung",
    "date": "2030-01-01",
    "start_time": "18:00:00",
    "end_time": "20:00:00",
    "department": 1,
    "group_ids": [1]
  },
  "blocks": [
    {"id": 1, "title": "Einführung", "duration_minutes": 15,
     "start_offset_minutes": 0, "group_ids": []},
    {"title": "Neuer Baustein", "duration_minutes": 30,
     "start_offset_minutes": 15, "group_ids": [1]}
  ]
}
```

Bestehende IDs behalten Identität und zugehörige Bilder/Anhänge. Neue Bausteine haben keine ID. Nicht mehr aufgeführte Bausteine einschließlich ihrer generischen Medien-/Anhangdatensätze werden entfernt. Doppelte oder fremde IDs sind ungültig. Höchstens 1000 Bausteine pro Anfrage. Die Terminmetadaten benötigen Titel, Datum, Beginn und Ende; optional ausgelassene Termin-/Blockfelder folgen dem bestehenden Serializervertrag. Clients senden für bearbeitete Blöcke den vollständigen beschreibbaren Zustand, einschließlich `group_ids`, Inhalt und Vorlagenreferenz.

Alle Zeit- und Zielrelationen werden vor der ersten Speicherung geprüft. Eine Transaktion übernimmt Termin, Gruppen, Blöcke, Version und die statusabhängige Dienstsynchronisierung gemeinsam. Ende liegt am selben Tag nach Beginn; Blockdauern sind positiv, Offsets nicht negativ und das Blockende liegt höchstens am Terminende. Überschneidungen sind zulässig und werden in TRAIN-02 als Warnungen behandelt.

Bei einer veralteten Version: HTTP 409 mit `code: plan_revision_conflict` und dem vollständigen aktuellen Plan unter `current`. Der lokale Entwurf darf dabei nicht verworfen werden. Fehler 400/403 verändern den Plan nicht. Erfolgreiches Speichern liefert den vollständigen neuen Stand mit genau einmal erhöhter Version. Bisherige Einzeländerungen an Termin-/Blockdaten sperren ebenfalls die Terminzeile und erhöhen deren Version, damit sie einen geladenen Plan nicht unbemerkt ändern können. Ein Wechsel eines Blocks zwischen Terminen erhöht beide Versionen; die beiden Terminzeilen werden nach ID sortiert gesperrt.

Die API nutzt die bestehenden Trainingsrechte und Abteilungs-/Gruppenzielprüfungen. Sie aktiviert keine abteilungsgebundenen Rollenvorlagen; deren Rechtevertrag bleibt SEC-01/02/ROLE-01. Statusabhängige Dienstanlage und Veröffentlichungsregeln sind in TRAIN-01.5b umgesetzt. Medien-/Anhang-Uploads sind gesonderte sofortige Aktionen und gehören nicht zum Planentwurf; neue lokale Bausteine müssen dafür zuerst gespeichert werden.

Vorhandene Zeitangaben werden bei der Versionsmigration nicht verändert. Ungültige Altzeiten müssen vor dem nächsten Speichern korrigiert werden. Der aktuelle Vertrag gilt für API-Schreibwege; Django-Admin-Formulare erhöhen die Version noch nicht. Diese Grenze bleibt vor TRAIN-01-Paketabnahme zu schließen.

## Status und Dienstbuch

`status` ist `draft`, `published`, `completed` oder `cancelled`. Neue Termine beginnen als Entwurf und erzeugen keinen regulären Dienst. Veröffentlichen erzeugt einen Dienst oder aktualisiert dessen bestehende Identität; Abschluss und Absage behalten den verknüpften Dienst einschließlich Anwesenheiten und Dokumentation. Ein verknüpfter Termin kann nicht wieder zum Entwurf werden; ein unveröffentlichter Termin kann nicht abgeschlossen werden. Migration 0005 übernimmt bereits verknüpfte Termine als veröffentlicht und erzeugt keine Serien neu.

`requires_service_confirmation` zeigt, ob der Dienst begonnen hat, Vorkommnisse oder Anwesenheiten enthält. Jede Planänderung verlangt dann ausdrücklich `session.confirm_service_change: true` (bei einzelnen Termin-/Blockänderungen im Anfrageobjekt). Die Bestätigung gilt nur für diese Speicheraktion. Fehlende Bestätigung liefert HTTP 400 ohne Änderung. Die Abteilung eines dokumentierten Dienstes bleibt unveränderlich. Eine ausdrückliche Löschoption entfernt nur zukünftige und undokumentierte Dienste; historische oder dokumentierte Dienste werden beim Löschen der Übung erhalten und entkoppelt. Dienstlisten liefern `training_status`, damit Absagen auch im Dienstbuch erkennbar bleiben.
