# Technische und organisatorische Maßnahmen (Art. 32)

Links die Maßnahme, rechts, wo sie umgesetzt ist. Der Abschnitt „Ergänzen im Betrieb“ listet, was der Betreiber selbst sicherstellen muss.

## In der Anwendung umgesetzt

| Ziel | Maßnahme |
| --- | --- |
| Zugangskontrolle | Sitzungen mit Secure/HttpOnly/SameSite-Cookies, CSRF, Drosselung von Anmeldeversuchen; MFA Pflicht für Admins, Leitung und alle Konten mit Zugriff auf Mitgliederdaten; Passwörter ab 10 Zeichen; erneute Bestätigung für Exporte, Datenauskunft und Gesundheitsangaben ([session-auth.md](../operations/session-auth.md)) |
| Zugriffskontrolle | Rechte serverseitig je Abteilung; Feldrechte für Kontakt-, vertrauliche und Gesundheitsdaten; Portal nur für eigene Kinder ([Rollen](../domains/roles-and-permissions.md)) |
| Trennung | Strikte Abteilungstrennung; Kontenliste nur für gemeinsame Abteilungen |
| Verschlüsselung | HTTPS mit HSTS; Gesundheitsangaben, TOTP-Geheimnisse und Zugangsdaten verschlüsselt in der Datenbank; Sicherungen mit restic verschlüsselt |
| Eingabe- und Weitergabekontrolle | Export-Audit für Excel, CSV, Datenauskunft und jeden Abruf von Gesundheitsangaben; Änderungsprotokoll für Portaländerungen; Uploads nur über geprüfte, nicht zwischenspeicherbare Links |
| Datenminimierung | Keine Drittanbieter im Browser (Schriften, CDN, Analyse); nur technisch notwendige Cookies, daher kein Cookie-Banner; E-Mails nennen keine Abmeldegründe; Logs ohne Tokens und Abfrageparameter, E-Mail-Adressen maskiert |
| Speicherbegrenzung | Einstellbare Fristen mit nächtlicher Bereinigung, Anonymisierung ehemaliger Mitglieder ([data-retention.md](../operations/data-retention.md)) |
| Sicherheitsheader | CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy ([production-security.md](../operations/production-security.md)) |

## Ergänzen im Betrieb

- Server-Updates, Firewall, nur notwendige Ports offen.
- **Datenträgerverschlüsselung** des Servers (die Datenbank selbst ist außer den genannten Feldern unverschlüsselt). Entscheidung hier dokumentieren: ☐ umgesetzt ☐ nicht umgesetzt, Begründung: ________
- Backup-Repository auf einem anderen Gerät; Backup-Passwort und `FIELD_ENCRYPTION_KEY` getrennt und offline sichern ([ops-backup-restore-update.md](../operations/ops-backup-restore-update.md)).
- Vorgelagerter Proxy: keine Abfrageparameter protokollieren, Protokolle höchstens 14 Tage.
- Rollen regelmäßig prüfen, ausgeschiedene Betreuende deaktivieren.
- Betreuende auf Vertraulichkeit verpflichten und das am Konto als Einwilligungsart „Verpflichtung auf Vertraulichkeit“ erfassen.
- Meldeweg für Datenschutzverletzungen (72 Stunden, Art. 33) festlegen.
