# Verwaltungsbefehl `jfctl`

Gilt ab OPS-03. `jfctl` ist der einzige Weg für Installation, Betrieb, Sicherung, Wiederherstellung und Updates – für Docker Compose und Debian 13 nativ gleichermaßen. Fachliche Einstellungen (Abteilungen, Rollen, E-Mail-Vorlagen, SSO …) erfolgen in der Weboberfläche.

Ohne Argument öffnet `sudo jfctl` ein Menü. Jeder Menüpunkt ruft denselben Unterbefehl auf, der sich auch in Skripten verwenden lässt.

## Befehle

| Befehl | Wirkung |
| --- | --- |
| `jfctl install [--answers DATEI] [--expert]` | Assistent für Neuinstallation oder Wiederherstellung auf einem neuen Host ([ops-install.md](ops-install.md)) |
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
| `jfctl admin recover --user NAME [--reset-mfa]` | Setzt Passwort zurück, entfernt bei Bedarf MFA-Gerät und Wiederherstellungscodes und beendet alle Sitzungen des Kontos |
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

Die Webanwendung erhält weder Docker-Socket noch Root-Rechte. Für eine spätere lesende Statusanzeige schreibt `jfctl` `/var/lib/jf-manager/state/ops-status.json` (Instanz, Modus, Version, Workerzustand, letzte Sicherung).
