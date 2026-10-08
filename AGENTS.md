# Arbeitsregeln für die Roadmap

Vor Änderungen an Sicherheit, Rollen, Übungsplanung, Bedienung oder Betrieb zuerst `docs/planning/security-ux-design-roadmap.md` lesen. Den Wiederaufnahmestand, Paketstatus und die letzten Journaleinträge mit Git-Diff und tatsächlichem Code abgleichen.

- Roadmap-Änderungen auf `feat/security-roles-training-operations` integrieren.
- Vor Paketbeginn den Detailblock in Abschnitt 6 mit Abnahme, Abhängigkeiten und stabilen Teilschritt-IDs ausfüllen.
- Jeden abgeschlossenen Teilschritt separat committen. Nur eigene zugehörige Dateien oder Hunks stagen und den Staged-Diff prüfen.
- Im selben Commit Wiederaufnahmeübersicht, Paketstatus und Journal aktualisieren. Prüfergebnisse als bestanden, fehlgeschlagen oder nicht ausgeführt kennzeichnen.
- Bei Unterbrechung einen wiederaufnehmbaren Checkpoint mit offenen Änderungen, Risiken und nächstem Schritt festhalten.
- Vorhandene oder fremde Änderungen nicht zurücksetzen oder als eigene Roadmap-Ergebnisse ausgeben. Keine Geheimnisse oder personenbezogenen Echtdaten ins Journal aufnehmen.

Die vollständigen fachlichen Anforderungen und Prüfregeln stehen in der Roadmap. Diese Datei ist nur der Einstiegspunkt.
