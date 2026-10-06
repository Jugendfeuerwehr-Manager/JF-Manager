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
