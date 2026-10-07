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

Vorhandene Zeitangaben werden bei der Versionsmigration nicht verändert. Ungültige Altzeiten müssen vor dem nächsten Speichern korrigiert werden. Der Vertrag gilt auch für Django-Admin-Formulare: erwartete Planversion, Zeit-/Gruppenprüfung und ausdrückliche Bestätigung dokumentierter Dienste. Terminänderungen und Blockänderungen/-löschungen erhöhen die Planversion; veraltete Adminformulare werden abgewiesen. Massenlöschung von Bausteinen ist deaktiviert, damit dokumentierte Dienste über den ausdrücklich bestätigten Planeditor geändert werden.

## Status und Dienstbuch

`status` ist `draft`, `published`, `completed` oder `cancelled`. Neue Termine beginnen als Entwurf und erzeugen keinen regulären Dienst. Veröffentlichen erzeugt einen Dienst oder aktualisiert dessen bestehende Identität; Abschluss und Absage behalten den verknüpften Dienst einschließlich Anwesenheiten und Dokumentation. Ein verknüpfter Termin kann nicht wieder zum Entwurf werden; ein unveröffentlichter Termin kann nicht abgeschlossen werden. Migration 0005 übernimmt bereits verknüpfte Termine als veröffentlicht und erzeugt keine Serien neu.

`can_manage_plan` zeigt die tatsächliche Schreibberechtigung für diese Übungsabteilung; reine Leser erhalten im Frontend Details ohne Bearbeitungsaktionen.

`requires_service_confirmation` zeigt, ob der Dienst begonnen hat, Vorkommnisse oder Anwesenheiten enthält. Jede Planänderung verlangt dann ausdrücklich `session.confirm_service_change: true` (bei einzelnen Termin-/Blockänderungen im Anfrageobjekt). Die Bestätigung gilt nur für diese Speicheraktion. Fehlende Bestätigung liefert HTTP 400 ohne Änderung. Die Abteilung eines dokumentierten Dienstes bleibt unveränderlich. Eine ausdrückliche Löschoption entfernt nur zukünftige und undokumentierte Dienste; historische oder dokumentierte Dienste werden beim Löschen der Übung erhalten und entkoppelt. Dienstlisten liefern `training_status`, damit Absagen auch im Dienstbuch erkennbar bleiben.

## Serien (TRAIN-03)

Jeder Serientermin trägt `series_uuid` (stabile Serienidentität) und `original_date` (ursprünglicher Serientermin, auch nach Verschieben). Die Wiederholungsregel liegt ausschließlich am Serienursprung: `{"frequency": "WEEKLY|BIWEEKLY|MONTHLY", "end_date": "YYYY-MM-DD"}`. Unbekannte Frequenzen, zusätzliche Schlüssel und ein Ende vor dem ursprünglichen Termin werden mit HTTP 400 abgewiesen. Monatsserien rechnen jedes Vorkommen vom ursprünglichen Tag aus: 31.01. → 28./29.02. → 31.03.

`GET /api/v1/training/sessions/{id}/series_preview/?window_start=&window_end=` (von jedem Serientermin aus) liefert die vollständige Vorschau ohne Änderung: je Vorkommen `action` `new` (wird als eigenständiger Entwurf mit dem aktuell gespeicherten Ablauf einschließlich unabhängiger Medien-/Anhangkopien angelegt), `preserved` (vorhandener, ggf. verschobener Termin bleibt unverändert), `skipped` (bereits begonnener Termin wird nicht nachträglich erzeugt) oder `conflict` (mehrfache oder nicht bearbeitbare Zuordnung, bleibt unverändert). `warnings` nennt Überschneidungen mit anderen Übungen derselben Abteilung. Ohne Fenster beginnt die Vorschau beim späteren von ursprünglichem Termin und heute und endet nach höchstens 24 Monaten; ein längeres Fenster und mehr als 200 Vorkommen werden abgewiesen.

`POST .../generate_series/` mit `preview_token` (und demselben Fenster) legt ausschließlich die `new`-Vorkommen an. Bestehende Termine, Pläne, Dienste und Anwesenheiten werden nie gelöscht oder neu erzeugt. Hat sich Serie, Planversion oder ein Vorkommen seit der Vorschau geändert, antwortet der Server mit HTTP 409, `code: series_preview_changed` und der aktuellen Vorschau unter `preview`; nichts wird angelegt. Serienaktionen sperren zuerst den Ursprung, dann die Vorkommen nach ID. Neue Vorkommen sind Entwürfe ohne Dienst. Migration 0006 vergibt Altserien eine Identität, ohne Termine neu zu erzeugen; doppelte Altdaten am selben Datum erhalten kein `original_date` und werden als Konflikt nicht angetastet.

### Dieser und folgende

„Dieser Termin“ ist die normale Planbearbeitung. „Dieser und folgende“ überträgt den **gespeicherten** Stand eines Serientermins (Titel, Beschreibung, Zeiten, Ort, Notizen, Gruppen, Ablauf mit unabhängigen Medien-/Anhangkopien) auf alle Termine mit späterem ursprünglichem Datum. `POST .../propagation_preview/` mit optional `include_deviating: [ids]` liefert je Folgetermin `action`: `update`, `unchanged`, `deviating` (seit Erzeugung/letzter Übertragung individuell geändert oder verschoben; bleibt standardmäßig erhalten, `overridable: true`), `history` (begonnen, abgeschlossen, abgesagt oder dokumentierter Dienst; nie änderbar) oder `conflict` (nicht bearbeitbar oder andere Abteilung). `changes` beschreibt konkret, was sich ändert. Nur abweichende, änderbare Termine dürfen in `include_deviating` stehen. `POST .../propagate_series/` mit `preview_token` übernimmt genau diese Vorschau; jede Änderung an Quelle, Folgeterminen oder Auswahl seit der Vorschau führt zu HTTP 409 `series_preview_changed` mit aktueller Vorschau. Geänderte Termine erhalten eine neue Planversion; veröffentlichte Termine behalten ihre Dienstidentität, deren Zeiten/Titel synchronisiert werden. Status und Datum der Folgetermine bleiben unverändert. Abweichung wird über einen Inhalts-Fingerabdruck (ohne Status/Datum, mit Medien-/Anhangs-IDs) gegenüber dem zuletzt vereinbarten Stand und über `date != original_date` erkannt; Altserien ohne Fingerabdruck gelten konservativ als abweichend.

## Vorlagen und Kopien (TRAIN-03.3)

Alle Übernahmen erzeugen eigenständige Stände: Inhalte werden kopiert und bereinigt, Bilder und Anhänge als eigene Dateien des Ziels angelegt; eingebettete Bild-URLs zeigen auf die Kopien. Spätere Änderungen oder das Löschen der Quelle (Übung, Vorlage, Bibliotheksbaustein einschließlich ihrer Dateien) verändern oder beschädigen die Kopie nicht.

- `POST /api/v1/training/sessions/{id}/copy/` `{date, title?}`: unabhängiger Entwurf am neuen Datum, ohne Dienst und ohne Serienzugehörigkeit.
- `POST /api/v1/training/sessions/{id}/save_as_template/` `{title?}`: speichert den gespeicherten Plan als Übungsvorlage (`TrainingTemplate` mit `TrainingTemplateBlock`).
- `GET/PATCH/DELETE /api/v1/training/templates/{id}/`: nur Planer der Vorlagenabteilung. Änderbar sind Name und Beschreibung; Inhalte ändern sich durch erneutes Speichern als Vorlage. Löschen entfernt die eigenen Datei-Datensätze der Vorlage, nie die daraus erstellten Übungen.
- `POST /api/v1/training/templates/{id}/instantiate/` `{date, title?}`: neuer Entwurf in der Vorlagenabteilung; Gruppen, die inzwischen zu einer anderen Abteilung gehören, werden nicht übernommen.
- `GET /api/v1/training/template-blocks/`: schreibgeschützte Eigentümersicht; regelt den Zugriff auf Vorlagenbilder (`private-media`) und -anhänge (`attachments`).

Bausteine aus der Bibliothek (`library_block` bei neuen Bausteinen, auch im vollständigen Planvertrag) erhalten beim Anlegen eigene Kopien der im Inhalt referenzierten Bibliotheksbilder und aller Bibliotheksanhänge. Die Referenz `library_block` bleibt nur als Herkunftsangabe erhalten; Bibliotheksänderungen wirken nicht automatisch auf geplante Übungen. Bei einem Fehler innerhalb der Kopieraktion werden bereits geschriebene Kopien entfernt.

## Stationen, Ausbilder und Material (TRAIN-02)

Jeder Baustein im Planvertrag kann zusätzlich `kind` (`block`, `station`, `transition` = Wechsel, `break` = Pause, `free` = freie Runde), `location`, `learning_objective`, `safety_notes`, `instructor_ids` und `materials` enthalten. Bei Stationen ist `content` der Ablauf und `duration_minutes` die Stationsdauer. Lesend liefern Bausteine `instructors` (`id`, `name`) und `materials` (`id`, `item`, `variant`, `quantity`, `label`).

- Ausbilder: nur aktive Konten mit Rolle in der Übungsabteilung (gleicher Personenkreis wie Dienstbuch-Personal). `GET .../sessions/{id}/instructor_options/` liefert diese Auswahl minimal (`id`, `name`), nur für Planer der Abteilung.
- Material: `{item?, variant?, quantity ≥ 1, label?}`. Eine Variante bestimmt ihren Artikel; ein abweichender Artikel ist ungültig. Ohne Artikel ist `label` Pflicht (Freitextbedarf); mit Artikel wird `label` aus Artikel/Variante übernommen und bleibt als Anzeigename erhalten, auch wenn der Artikel später entfernt wird. Erlaubt sind Artikel der Übungsabteilung und abteilungsübergreifende Artikel. Höchstens 50 Positionen je Baustein. `GET .../sessions/{id}/material_options/?search=` liefert höchstens 30 Artikel mit Varianten, nur für Planer. Materialbedarf bucht, reserviert oder ändert keinen Bestand.
- `materials` ersetzt beim Speichern die Positionen des Bausteins vollständig; ausgelassen (Einzel-PATCH) bleiben sie unverändert.

Serie, Kopie, Vorlage und „dieser und folgende“ übernehmen Art, Ort, Lernziel, Sicherheitshinweise, Ausbilder und Material als eigene Datensätze. Beim Anlegen aus einer Vorlage werden nur Ausbilder übernommen, die weiterhin eine Rolle in der Abteilung haben. Materialänderungen gelten im Fingerabdruck als Ablaufänderung.

### Planungswarnungen und Veröffentlichung

`POST .../sessions/{id}/check_plan/` nimmt einen vollständigen, ungespeicherten Entwurf (`session`, `blocks` wie beim Speichern) und liefert `warnings` ohne Änderung; ungültige Entwürfe werden wie beim Speichern mit HTTP 400 abgewiesen. `GET .../sessions/{id}/conflicts/` prüft den gespeicherten Plan. Beide nur für Planer der Abteilung. Jede Warnung: `code` (`group`, `instructor`, `location`, `material`), `message`, `blocks` (gespeicherte IDs bzw. `neu-<Position>` für ungespeicherte Bausteine) und `other_session` (nur bei sichtbaren fremden Übungen).

- Gruppen: zeitlich überlappende Bausteine mit gemeinsamer Gruppe; Bausteine ohne Gruppen gelten für alle Gruppen.
- Ausbilder: dieselbe Person gleichzeitig in zwei Bausteinen oder in einer anderen Übung desselben Tages.
- Ort: gleiche normalisierte Ortsangabe (Groß-/Kleinschreibung, Leerraum) gleichzeitig in dieser oder einer anderen Übung.
- Material: an jedem Bausteinbeginn gleichzeitiger Bedarf eines Artikels/einer Variante über alle nicht abgesagten Übungen des Tages gegen Bestand außerhalb von Mitgliederlagerorten (Artikel ohne Variante: einschließlich aller Varianten). Rechnerisch, keine Reservierung; Freitextbedarf wird nicht gezählt.
- Übungen, die die Person nicht planen darf, erscheinen nur als „einer anderen Übung (nicht sichtbar)“ ohne Titel oder ID.

Warnungen blockieren das Speichern nicht. Der Übergang zu `published` (Planvertrag oder Einzeländerung) verlangt bei Warnungen `publish_justification`; sonst HTTP 400 mit `publish_justification` und den Warntexten unter `warnings`. Gespeichert werden Begründung und Warntexte (`publish_warnings`, schreibgeschützt). Weitere Speicherungen einer bereits veröffentlichten Übung fragen nicht erneut. Ungültige Zeiten und fehlende Rechte blockieren weiterhin.

### Rotationsassistent

Der Rotationsassistent im Planer erzeugt ausschließlich lokale Entwurfsbausteine (kein eigener Endpunkt); gespeichert wird wie jeder Entwurf über den vollständigen Planvertrag. Eingaben: Gruppen, Stationen in Reihenfolge (Titel, Ort, Ausbilder), Beginn, Stationsdauer, Wechselzeit und optional eine Pause zwischen zwei Runden. Runden = max(Gruppen, Stationen); in Runde r besucht Gruppe g die Position (g + r) mod Runden. Positionen ohne Station werden als `free` („Freie Runde“) für diese Gruppe angelegt, unbesetzte Stationen erscheinen in der Vorschau. Zwischen den Runden entstehen `transition`-Bausteine bzw. ein `break`; nehmen alle Gruppen teil, gelten sie für alle Gruppen. Überschreitet der Ablauf den Terminrahmen, ist die Übernahme gesperrt. Die vollständige Vorschau (Runden × Gruppen mit Uhrzeiten) wird als ein rückgängig machbarer Schritt übernommen.

#### Bibliotheksbausteine und verknüpfte Stationen (TRAIN-02.3b)

Je Station kann ein Bibliotheksbaustein gewählt werden; Titel, Inhalt, Farbe und Beschreibung (als Lernziel) werden übernommen, der Server kopiert beim Speichern referenzierte Bilder und Anhänge in den geplanten Baustein (`library_block`). Alle Bausteine einer Station erhalten dasselbe optionale Feld `station_key` (UUID, auch in Vorlagenbausteinen, Kopien und Serien erhalten). Der Planer übernimmt Änderungen an Titel, Ablauf, Art, Ort, Lernziel, Sicherheitshinweisen, Farbe, Nextcloud-Link, Ausbildern und Material eines Bausteins in alle Bausteine mit demselben Schlüssel im Entwurf, als ein Rückgängig-Schritt; Zeiten und Gruppen bleiben je Baustein. Weil Gruppen meist Altersgruppen mit eigener Ansprache sind, kann ein Baustein mit „Nur für diese Gruppe ändern“ gelöst werden (`station_key: null`). Der Server erzwingt keine Gleichheit; der Schlüssel ist nur ein Planungsmerkmal.

## Durchführung (TRAIN-04.2)

Die Durchführungsansicht `/training/sessions/{id}/run` liest nur `GET .../sessions/{id}/plan/` (Leserecht genügt) und schreibt nichts. Der Plan wird an jedem Bausteinbeginn in Abschnitte geteilt; Lücken bis zum nächsten Beginn sind eigene Abschnitte („Übergang“), Abschnitte mit Stationen sind Runden. Die Gerätezeit bestimmt den aktuellen Abschnitt; Abschnitte lassen sich ohne Speichern blättern. Je Station: Gruppe jetzt und in der nächsten Runde (über `station_key`, sonst Titel und Ort), Ort, Ausbilder. „Meine Station“ zeigt ab dem angezeigten Abschnitt die Bausteine, in denen die angemeldete Person Ausbilder ist, mit Lernziel, Ablauf, Sicherheit und Material. Die Materialabhakliste liegt nur im Browserspeicher dieses Geräts. Die Ansicht lädt jede Minute und nach Wiederverbindung neu, meldet eine neue Planversion und zeigt ohne Verbindung den Stand der letzten Aktualisierung. `publish_justification` und `publish_warnings` liefert der Planendpunkt nur Personen, die den Plan bearbeiten dürfen, weil die Warntexte für die Sichtbarkeit der veröffentlichenden Person erstellt wurden.
