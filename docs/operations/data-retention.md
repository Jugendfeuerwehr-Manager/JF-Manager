# Aufbewahrung und Löschung personenbezogener Daten

Die Anwendung löscht personenbezogene Daten nach festen oder einstellbaren Fristen (Art. 5 Abs. 1 e DSGVO). Alle Aufträge laufen nachts als Wartungs-Timer (`jfctl maintenance`, [maintenance.sh](../../ops/lib/maintenance.sh)).

## Einstellbare Fristen

Unter **Einstellungen → Datenschutz → Aufbewahrungsfristen**, Recht `settings_manager.change_privacy_settings`. Ausgeführt durch `purge_personal_data` täglich um 04:20 Uhr. Probelauf: `python manage.py purge_personal_data --dry-run`.

| Daten | Standard | Minimum | Was passiert |
| --- | --- | --- | --- |
| E-Mail-Verlauf | 365 Tage | 30 | Nachricht mit Empfängern, persönlichem Text und Anhängen wird gelöscht (laufende Sendungen ausgenommen) |
| Bestell-Benachrichtigungsprotokoll | 180 Tage | 7 | Protokollzeile mit Empfängeradresse wird gelöscht |
| Hängende Benachrichtigungs-E-Mails | 90 Tage | 7 | Nicht zustellbarer Ausgangseintrag samt Inhalt wird gelöscht |
| Hängende Push-Mitteilungen | 30 Tage | 7 | Nicht zustellbarer Ausgangseintrag wird gelöscht |
| Synchronisationsläufe | 90 Tage | 7 | Abgeschlossene Läufe mit Zusammenfassung und Fehlermeldung werden gelöscht |
| Änderungsprotokoll der Stammdaten | 730 Tage | 90 | Alte und neue Werte aus Portal- und Eigenänderungen werden gelöscht |
| Abmeldegrund „Krankheit“ | 90 Tage nach dem Dienst | 7 | Kategorie wird geleert; die Abmeldung selbst bleibt |

## Feste Fristen

| Daten | Frist | Auftrag |
| --- | --- | --- |
| Abgelaufene Sitzungen und Geräteeinträge | bei Ablauf | `clearsessions` |
| Export-Auditeinträge | `AUDIT_RETENTION_DAYS`, Standard 180 Tage | `purge_export_audits` |
| Gespeicherte Buchungsantworten (Inventar) | 30 Tage | `purge_booking_requests` |
| Erledigte Aufgaben und gelesene Hinweise im Eingang | 180 Tage | `purge_inbox` |
| Abmelde-Kurztexte | 90 Tage nach dem Dienst | `purge_registration_notes` |
| Elternzugang | endet, wenn alle Kinder volljährig sind | `portal_access_lifecycle` |
| Zugriffsprotokolle (Webserver) | 14 Tage | logrotate bzw. Docker-Größenlimit ([production-security.md](production-security.md)) |

## Sicherungen

Gelöschte Daten bleiben in Sicherungen bis zu deren eigenem Ablauf erhalten: 7 tägliche, 4 wöchentliche und 6 monatliche Stände ([ops-backup-restore-update.md](ops-backup-restore-update.md)), also bis zu etwa sechs Monate. Nach einer Wiederherstellung führt der nächste nächtliche Lauf die Fristen erneut aus.

## Noch offen

Austritt und Anonymisierung von Mitgliedern sowie das Löschen inaktiver Konten folgen als eigene Schritte.
