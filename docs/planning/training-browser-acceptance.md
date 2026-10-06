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
