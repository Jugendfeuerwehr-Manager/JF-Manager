# TRAIN-01.5c: Browserabnahme

Geprüft am 06.10.2026 mit synthetischer SQLite-Datenbank unter `/private/tmp`, separatem Django-Testserver und Vite-Testport; keine Anwendungsechtdaten geändert. Chrome, Desktop und mobile Breite 390 × 844 CSS-Pixel. Technische Testkonten und Dienste existieren ausschließlich in dieser Wegwerf-Datenbank.

| Ablauf | Ergebnis |
| --- | --- |
| Entwurf laden | bestanden: Status Entwurf, Version 1, kein Dienstlink |
| Veröffentlichung lokal übernehmen und speichern | bestanden: Status veröffentlicht, Version 2 und neuer Dienstlink |
| Baustein über benannte Aktion anlegen | bestanden: Formular ohne Ziehen erreichbar; Bilder/Anhänge erst nach Speicherung |
| Titel, Inhalt und Beginn bearbeiten | bestanden: zusammenhängender Entwurf; nach Speicherung Version 3, gespeicherter Beginn Minute 20 und Inhalt |
| Tastatur und Rückgängig | bestanden: Pfeil nach unten verschiebt fünf Minuten; Rückgängig stellt alten Beginn wieder her |
| Veraltete Planversion speichern | bestanden: Konflikt mit Serverversion 4, lokal Minute 25 erhalten, Server Minute 20 und abweichender Titel sichtbar |
| Serverstand ausdrücklich laden | bestanden: nach Bestätigung Serverversion 4, kein ungespeicherter Entwurf; Browsersteuerung beim Bestätigungsdialog zeitweise blockiert, anschließend nativer Zustand geprüft |
| Handout | bestanden: gespeicherter Status, Version, Gruppen, Ablauf und Inhalte sichtbar |
| PDF | bestanden: Datei im Browser erzeugt; Version 4 und Status enthalten; erste Seite mit PDFKit gerendert und visuell geprüft, Umlaute und Tabellen lesbar |
| Mobile Durchführung | bestanden: Status, Version, Dienstlink, Gruppen und Bausteine sichtbar; Dokumentbreite und Scrollbreite jeweils 390 Pixel |
| Mobile Bearbeitung | bestanden: ausdrücklicher Wechsel zum Planer; Bausteinformular mit beschrifteten Feldern, Breite 366 Pixel, kein horizontaler Überlauf |
| Reines Leserecht | bestanden: keine Status-, Speicher-, Entfernen- oder Bearbeitungsaktionen; Enter zeigt Bausteininhalt als Details |
| Offline-Speichern / Verlassensschutz | automatisierte Store-/Router-/Beforeunload-Regressionen bestanden; manueller Offline- oder echter Touch-Hardwarelauf nicht ausgeführt |

Die Teststeuerung für den PDF-Download meldete einen Timeout, obwohl Chrome die Datei erfolgreich heruntergeladen hatte. Dateizeit, synthetischer Inhalt und gerenderte Seite wurden anschließend direkt geprüft. Das ist kein Nachweis eines fehlgeschlagenen Exports.

## Weitere Prüfungen und Grenzen

- Alle TRAIN-Backendtests einschließlich konkurrierender Speicherungen und Admin-Versionsschutz auf PostgreSQL 15: siehe aktuellen Roadmap-Checkpoint.
- Frontendtests, Typecheck, gezieltes ESLint und Produktionsbuild: siehe aktuellen Roadmap-Checkpoint.
- Ein vorheriger Backend-Gesamtlauf: 700 Tests, ein fehlgeschlagener ROLE-Test (`UserDepartmentRoleAdminTest.test_staff_can_list_roles`). Alle TRAIN-Tests im Lauf bestanden. Der gleichzeitig geänderte ROLE-Stand ist getrennt erneut abzunehmen.
- Seriengenerierung und virtuelle Kalendertermine werden erst in TRAIN-03 ersetzt; Stationen-/Ressourcenwarnungen und Nachbereitung gehören zu TRAIN-02/04. Die TRAIN-01-Abnahme stellt deren Fertigstellung nicht dar.

# TRAIN-03.4: Browserabnahme Serien, Vorlagen und Kopien

Geprüft am 06.10.2026 mit frisch migrierter synthetischer SQLite-Datenbank und Mediendateien im Sitzungs-Scratchpad, separatem Django-Testserver (18081) und Vite (15183; 15173 war durch eine andere Sitzung belegt). Chrome headless über `playwright-core` (Systemchrome, kein Browser-Download), 1440 × 900 und 390 × 844 CSS-Pixel. Testkonto mit Standardrolle „Übungsplanung“ (ohne Staff/Superuser), eine synthetische Abteilung, zwei Gruppen; keine Anwendungsechtdaten.

| Ablauf | Ergebnis |
| --- | --- |
| Monatsserie ab 31.10. im Planer „Serie“ prüfen | bestanden: vollständige Vorschau 30.11., 31.12., 31.01., 28.02. (Monatsanker), „4 neu“, nichts angelegt |
| Fehlende Termine anlegen | bestanden: 4 Entwürfe; erneute Vorschau „0 neu · 4 vorhanden“; Datenbank enthält genau 4 Vorkommen mit eigenem ursprünglichem Datum |
| Kalender | bestanden: nur gespeicherte Termine; ein Vorkommen öffnet seinen eigenen Plan (`/sessions/2/plan`), nicht den Ursprung |
| Vorkommen bearbeiten (Titel, 18:30–20:30), speichern, „Dieser und folgende“ | bestanden: 3 Folgetermine „Wird geändert“ mit konkreten Titel-/Zeitänderungen; Hauptaktion ohne Scrollen sichtbar |
| Übertragen | bestanden: danach „3 unverändert“, früherer Termin und Ursprung unverändert |
| Als Vorlage speichern / auf anderes Datum kopieren | bestanden: Erfolgsmeldung; Kopie öffnet als Entwurf Version 1 |
| Kalender „Vorlagen“ → Übung anlegen | bestanden: neuer Entwurf mit Vorlagennamen geöffnet |
| 390 Pixel | bestanden: Dokumentbreite 390; Seriendialog 366 Pixel breit, Felder und Hauptaktion bedienbar |
| Konsole | keine Trainingsfehler. 403 beim globalen Vorladen der Mitgliedsstatus für eine reine Trainingsrolle (Members-Store, nicht TRAIN) |

Befunde während der Abnahme und behoben: Die Erfolgsmeldung erschien vor dem Neuladen der Vorschau und stand kurz neben der veralteten Vorschau; Meldung jetzt erst nach aktualisierter Vorschau. Die Hauptaktion lag bei langer Vorschau unterhalb des sichtbaren Dialogbereichs; sie steht jetzt neben der Zusammenfassung über der scrollbaren Tabelle.

Grenzen: Abweichende/historische Termine und 409-Konflikte sind in Backend- und Komponententests abgedeckt, im Browser nicht gesondert erzeugt. Kein echter Touch-Hardwarelauf.

# TRAIN-02.4: Browserabnahme Stationen, Rotation und Ressourcen

Geprüft am 07.10.2026 mit frisch migrierter synthetischer SQLite-Datenbank (Migrationen bis 0010) im Sitzungs-Scratchpad, Django-Testserver 18081, Vite 15183, Chrome headless über `playwright-core`, 1440 × 900 und 390 × 844 CSS-Pixel. Testkonto mit Standardrolle „Übungsplanung“ ohne Staff, synthetische Abteilung mit zwei Gruppen, ein Ausbilderkonto, ein Artikel mit Bestand 3, drei öffentliche Bibliotheksbausteine; keine Anwendungsechtdaten.

| Ablauf | Ergebnis |
| --- | --- |
| Rotation mit zwei Gruppen und zwei Stationen | bestanden: Vorschau „2 Runden · 19:00–19:45“, Wechsel zwischen den Runden, jede Gruppe jede Station; Übernahme als ein Schritt, nach Speichern 7 Bausteine |
| Stationsformular | bestanden: Art, Ort, Lernziel, Ausbilder und Material (5 × Artikel) gespeichert und nach Neuladen vorhanden |
| Planungswarnungen | bestanden: „1 Planungswarnung“ eingeklappt, nach „Anzeigen“ Materialwarnung „gleichzeitig 5 benötigt, rechnerisch 3 verfügbar“ mit Sprung zum Baustein |
| Veröffentlichen trotz Warnung | bestanden: Begründungsdialog; Status veröffentlicht, Begründung und 1 Warntext gespeichert |
| Bibliotheksbaustein als Station (TRAIN-02.3b) | bestanden: Suche „Kno“, Titel und Inhalt übernommen, drei Bausteine mit gemeinsamer Verknüpfung |
| Verknüpfte Station bearbeiten | bestanden: Hinweis nennt die andere Gruppe; Umbenennung wirkt auf beide Gruppen |
| Verknüpfung für eine Gruppe lösen | bestanden: nur dieser Baustein geändert, nach Speichern und Neuladen 1 verknüpft, 1 gelöst |
| 390 Pixel | bestanden: Dokument- und Scrollbreite 390 |
| Konsole | keine Fehler |

Grenzen: Konflikte mit anderen Übungen und anonymisierte Übungen sind in Backendtests abgedeckt, im Browser nicht gesondert erzeugt. Kein echter Touch-Hardwarelauf.

# TRAIN-04.5: Browserabnahme Durchführung, Nachbereitung und Handout

Geprüft am 07.10.2026 mit frisch migrierter synthetischer SQLite-Datenbank (Migrationen bis 0011) im Sitzungs-Scratchpad, Django-Testserver 18081, Vite 15183, Chrome headless über `playwright-core`, 390 × 844, 1280 × 900 und 1440 × 900 CSS-Pixel, hell und dunkel. Konten: „Übungsplanung“ ohne Staff (Ausbilder der Station „Knotenkunde“) und ein synthetisches Leitungskonto mit Dienstbuchrecht und synthetischem Authenticator (MFA-Pflicht der Rolle). Eine veröffentlichte Übung, die zur Prüfzeit gerade lief, mit Rotation über zwei Gruppen, verknüpften Stationen, Ausbildern und Material; verknüpfter Dienst. Keine Anwendungsechtdaten.

| Ablauf | Ergebnis |
| --- | --- |
| Durchführung (390 px) | bestanden: „Jetzt · Runde 1 von 2“, Uhrzeit, Restzeit, Fortschritt, „Danach: Wechsel“; Stationskarten mit Gruppe jetzt/danach, Ausbilder, Ort |
| Meine Station | bestanden: eigene Station mit Lernziel, Ablauf, Material; Abhaken übersteht Neuladen, Hinweis „nur auf diesem Gerät“ |
| Ohne Verbindung | bestanden: Hinweis mit Stand der letzten Aktualisierung |
| Dienstbuch (1440/390 px) | bestanden: Heute-Karte „Durchführen“ und „Anwesenheit erfassen“; Klick in die Zeile öffnet `/servicebook/{id}/edit`; „Durchführen“ öffnet die Durchführung |
| Planer | bestanden: „Durchführen“ öffnet die Durchführung |
| Nachbereitung (390 px) | bestanden: Planzeit übernehmen, Ende ändern, Vergleich „110 Min. · tatsächlich 104 Min. (−6)“, Abschluss; danach Status „Abgeschlossen“, Planzeit unverändert |
| Handout und PDF | bestanden: Version, Stand, Stationskarten mit beiden Zeitfenstern, Materialliste; PDF-Text (`pdftotext`) mit Umlauten geprüft; 390 px ohne Überbreite |
| Dunkelmodus | bestanden nach Korrektur (siehe unten) |
| Konsole | keine Fehler |

Befunde während der Abnahme und behoben: Bei drei Aktionen war die Fußleiste der Durchführung bei 390 px abgeschnitten (Spalten und Schrift angepasst). Eine abgeschlossene Übung zählte im Kopf weiter herunter (gespeicherter Status hat Vorrang, kein Fortschrittsbalken). In TRAIN-04.4 gefunden: Das Handout war bei 390 px 654 px breit und Datum/Stand klebten zusammen.

Grenzen: Gerätezeit bestimmt den Abschnitt; eine falsch gestellte Geräteuhr verschiebt die Anzeige (Blättern bleibt möglich). Kein echter Touch-Hardwarelauf; Offline wurde über den Browser-Offlinemodus simuliert.
