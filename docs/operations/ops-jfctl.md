# Verwaltungsbefehl `jfctl`

Gilt ab OPS-03. `jfctl` ist der einzige Weg für Installation, Betrieb, Sicherung, Wiederherstellung und Updates – für Docker Compose und Debian 13 nativ gleichermaßen. Fachliche Einstellungen (Abteilungen, Rollen, E-Mail-Vorlagen, SSO …) erfolgen in der Weboberfläche.

Ohne Argument öffnet `sudo jfctl` ein Menü. Jeder Menüpunkt ruft denselben Unterbefehl auf, der sich auch in Skripten verwenden lässt.

## Befehle

| Befehl | Wirkung |
| --- | --- |
| `jfctl install [--answers DATEI] [--expert] [--ignore-memory-check]` | Assistent für Neuinstallation oder Wiederherstellung auf einem neuen Host ([ops-install.md](ops-install.md)) |
| `jfctl status` | Instanz, Modus, Version, Adresse, letzte Sicherung, Update- und Workerzustand, Dienststatus |
| `jfctl doctor` | Prüft Rechte und Inhalt der Konfiguration, Plattform, Speicher, Erreichbarkeit, `check --deploy`, offene Migrationen, Alter der letzten Sicherung und Timer |
| `jfctl start \| stop \| restart` | Anwendung starten/stoppen; `start` wartet auf Backend und Nginx |
| `jfctl logs [dienst] [-f] [-n N]` | Protokolle der Dienste (`backend`, `worker`, `push-worker`, `frontend`, nativ `web`, `worker`, `push`, `nginx`); `jfctl logs jfctl` zeigt das eigene Protokoll |
| `jfctl update --version X.Y.Z` | Geprüfter Releasewechsel ([ops-backup-restore-update.md](ops-backup-restore-update.md)) |
| `jfctl backup create \| list \| verify [ID]` | Verschlüsselte Sicherung mit Restic |
| `jfctl restore <ID>` | Wiederherstellung mit Vorabprüfung und ausdrücklicher Bestätigung |
| `jfctl config show` | Betriebsangaben und Anwendungswerte (Geheimnisse maskiert) |
| `jfctl config set KEY WERT` | Ändert eine Betriebsangabe (`JF_DOMAIN`, `JF_TLS`, `JF_BACKUP_*` …) oder einen Infrastrukturwert der Anwendung (`EMAIL_*`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` …); Schlüssel nur über `config edit` |
| `jfctl config edit` | Bearbeitet `app.env` im Editor; Syntaxprüfung vor dem Speichern |
| `jfctl admin bootstrap` | Legt das erste Administrationskonto an, sofern noch keines existiert |
| `jfctl admin recover --user NAME [--reset-mfa]` | Setzt Passwort zurück, entfernt bei Bedarf Authenticator-App, Passkeys und Wiederherstellungscodes und beendet alle Sitzungen des Kontos |
| `jfctl admin reset-mfa --user NAME` | Setzt nur die Zwei-Faktor-Anmeldung zurück (Authenticator-App, Passkeys, Wiederherstellungscodes) und beendet alle Sitzungen; einziger Weg für Superuser, Staff und Konten mit MFA-Pflicht ([session-auth.md](session-auth.md#zwei-faktor-anmeldung-zurücksetzen)) |
| `jfctl workers hold \| release \| status` | Hintergrundaufträge anhalten oder freigeben |
| `jfctl maintenance list \| run AUFGABE` | Wiederkehrende Wartung ([Wartungsplan](#wartungsplan)) |
| `jfctl migrate legacy-compose --from VERZ.` | Übernahme einer alten Compose-Installation ([ops-migration.md](ops-migration.md)) |

Optionen: `-y/--yes` beantwortet Ja/Nein-Fragen (nie die Bestätigung einer Datenersetzung), `--non-interactive` verbietet Rückfragen.

`jfctl` funktioniert auch bei gestoppter oder defekter Webanwendung: Verwaltungsbefehle starten dafür einen eigenen kurzlebigen Prozess (`docker compose run` bzw. `manage.py` als Dienstbenutzer).

## Rückgabecodes

| Code | Bedeutung |
| --- | --- |
| 0 | Erfolg |
| 1 | Unerwarteter Fehler |
| 2 | Falscher Aufruf oder ungültige Angabe |
| 3 | Vorabprüfung fehlgeschlagen – **nichts wurde geändert** |
| 4 | Ein anderer `jfctl`-Vorgang läuft (Sperre `/run/lock/jfctl.lock`) |
| 5 | Bestätigung verweigert |
| 6 | Prüfung nach einer Änderung fehlgeschlagen; Zustand steht im Protokoll und in `jfctl status` |
| 7 | Änderung fehlgeschlagen, vorheriger Zustand wiederhergestellt |
| 8 | Keine Installation gefunden |

## Sperre und Protokoll

Verändernde Befehle (Installation, Start/Stopp, Sicherung, Wiederherstellung, Update, Konfiguration) nehmen eine exklusive Sperre. Ein zweiter Aufruf bricht mit Code 4 ab und nennt den laufenden Vorgang.

Alle Aktionen landen in `/var/log/jf-manager/jfctl.log`. Registrierte Geheimnisse (Schlüssel, Datenbank-, Backup- und Administrationspasswörter), Zugangsdaten in URLs und `…KEY=`/`…PASSWORD=`-Zuweisungen werden vor dem Schreiben ersetzt. Dasselbe gilt für `jfctl logs`.

## Geheimnisse

- `jfctl` erzeugt Schlüssel und Passwörter selbst oder fragt sie verdeckt ab; sie erscheinen nie in Prozessargumenten. Werte gelangen über Dateien mit Rechten 0600, über die Standardeingabe oder über Umgebungsvariablen an die Zielprozesse.
- Konfigurationsdateien werden gelesen, nie als Shellskript ausgeführt. Werte mit Leerzeichen oder Sonderzeichen stehen in einfachen Hochkommas; ein Hochkomma im Wert ist nicht zulässig.

## Keine Root-Steuerung aus der Webanwendung

Die Webanwendung erhält weder Docker-Socket noch Root-Rechte. Nach Installation, Sicherung, Wiederherstellung, Update und Workerwechsel schreibt `jfctl` `/var/lib/jf-manager/state/ops-status.json` (Instanz, Modus, Version, Workerzustand, letzte Sicherung) und eine gleichlautende, für alle lesbare Kopie nach `/var/lib/jf-manager/ops-public/ops-status.json`. Die Kopie enthält keine Geheimnisse.

Die Weboberfläche zeigt sie unter **Einstellungen → System → Betriebsstatus** nur lesend an (Systemadministration). Compose bindet das Verzeichnis schreibgeschützt nach `/ops-public` ein, nativ zeigt `OPS_STATUS_FILE` in `native.env` darauf. Warnungen erscheinen, wenn die letzte Sicherung fehlschlug, seit 36 Stunden keine erfolgreiche Sicherung vorliegt, die Angaben älter als zwei Tage sind oder Hintergrundaufgaben angehalten sind.

## Wartungsplan

`jfctl install` richtet auf dem Host systemd-Timer ein; sie gelten für beide Betriebswege; Cronjobs sind nicht nötig. Jeder Timer ruft `jfctl maintenance run <aufgabe>` auf.

| Aufgabe | Zeitplan | Befehl | Standard |
| --- | --- | --- | --- |
| `sessions` | täglich 03:10 | `clearsessions` | an |
| `export-audits` | täglich 03:20 | `purge_export_audits` | an |
| `booking-requests` | täglich 03:30 | `purge_booking_requests` | an |
| `sync-due` | alle 5 Minuten | `run_due_sync_jobs` | an |
| `order-reminders` | montags 07:00 | `send_pending_reminders` | aus (verschickt E-Mails) |
| Sicherung | `JF_BACKUP_SCHEDULE`, Standard täglich 02:30 | `jfctl backup create --scheduled` | an |

- `jfctl maintenance list` zeigt Aufgaben und Zustand, `enable`/`disable` schaltet einzelne Aufgaben, `run` führt sie sofort aus.
- Läuft gerade ein Update, eine Wiederherstellung oder eine Sicherung, überspringt die Wartung ihren Lauf ohne Fehler; der nächste Lauf holt ihn nach. `sync-due` pausiert zusätzlich, solange Worker angehalten sind.
- Ergebnisse stehen im Journal: `journalctl -u 'jf-manager-maint@*' -u jf-manager-backup`.

## Daten zwischen Organisation und Abteilungen verschieben

`jfctl departments list` zeigt aktive/inaktive Abteilungen mit ihren eindeutigen Kürzeln.
`global` bezeichnet Datensätze ohne Abteilungszuordnung; bei Mitgliedern bedeutet das keine Abteilungsmitgliedschaft.
Quelle und Ziel werden als Kürzel angegeben. Eine neue Zielabteilung lässt sich mit `--create-target NAME` anlegen;
die Vorschau legt sie noch nicht an. Andere künftige Abteilungen werden nicht angelegt.

```bash
sudo jfctl departments move --from global --to jugendfeuerwehr \
  --create-target Jugendfeuerwehr \
  --areas members,groups,lists,events,services,training,templates,email
```

Ohne `--apply` ist der Aufruf eine reine Vorschau mit Mengen, Abhängigkeiten und Fingerprint.
Die Auswahl ist immer ausdrücklich anzugeben. Bereiche:

| Bereich | Inhalt |
| --- | --- |
| `members` | Mitgliedszuordnungen; Elternbezüge, Qualifikationen, Sonderaufgaben, Portalzugänge und Anhänge bleiben an denselben IDs erhalten |
| `groups` | Mitgliedergruppen |
| `lists` | Mitgliederlisten einschließlich Einträge/Abhakstatus; organisationsweite Listen werden Abteilungslisten |
| `events` | Mitgliedsereignistypen; Ereignisse bleiben am Mitglied |
| `services` | Alle vergangenen und zukünftigen Dienste einschließlich Anwesenheiten/Leitung |
| `training` | Alle Planungen, Serien, Bausteine, Medien, Teilnahme und Rückmeldungen |
| `templates` | Übungsvorlagen einschließlich Bausteine |
| `email` | E-Mail-Historie einschließlich Empfänger/Anhänge |
| `inventory` | Artikel/Lagerorte mit bestehenden Varianten, Beständen und Buchungen |
| `orders` | Bestellungen mit Positionen und unverändertem Statusverlauf |

Inventar und Bestellungen sind unabhängig auswählbar und im Beispiel ausgeschlossen: Die zentrale Kleiderkammer bleibt global.
Die Trainingsbibliothek, Qualifikationstypen, globale Konfiguration, Teilnahmevorgaben, Portalrichtlinien,
Benutzer, Favoriten und Rollen bleiben bestehen. Rechte müssen bei Bedarf separat in der Benutzerverwaltung vergeben werden.
Mitglieder mit mehreren Abteilungen verlieren nur die Quellzuordnung und behalten ihre übrigen Zuordnungen.
Verknüpfte Fachbereiche müssen zusammen gewählt werden; Konflikte und Altlisten-Zielzuordnungen verhindern den Umzug.

Nach Prüfung dieselben Argumente um `--apply --confirm INSTANZNAME` ergänzen (`jfctl status` zeigt den Namen).
Auch `--yes` ersetzt diese Bestätigung nicht. jfctl sperrt andere Betriebsvorgänge, hält Webzugriffe/Worker an,
erstellt eine vollständige verschlüsselte Vorabsicherung und liest sie zur Verifikation wieder aus.
Erst danach prüft der Umzug die Vorschau erneut unter Datenbanksperren und verändert alle ausgewählten Zuordnungen
in einer Transaktion. Auf PostgreSQL vergleicht der Befehl vor dem Commit zusätzlich Rohdatenprüfsummen aller Tabellen (einschließlich Altbestand); ausschließlich die vorgesehenen Zuordnungsfelder werden ausgenommen. Ein abweichender Datenvergleich rollt den Umzug zurück. Bei Änderung seit der Vorschau oder Fehler wird vollständig abgebrochen/zurückgerollt;
die Anwendung wird wieder gestartet. IDs und Uploaddateien werden nicht verändert. Zugehörige Eingangseinträge
folgen ihrem verschobenen Objekt, ohne neue Benachrichtigungen zu versenden.

Die ausgegebene Sicherungs-ID ist der Rückkehrpunkt (`jfctl restore ID --confirm INSTANZNAME`).
Nach Freigabe entstandene Änderungen würden bei einem Restore verloren gehen; deshalb den Umzug sofort prüfen.
Das interaktive Menü enthält denselben Ablauf unter „Daten in andere Abteilung verschieben“.
