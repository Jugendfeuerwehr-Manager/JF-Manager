# Sicherung, Wiederherstellung und Updates

Gilt ab OPS-04. Ersetzt `scripts/backup.sh`, `scripts/restore.sh`, `deploy.sh` und `make backup/restore/update`. Docker- und native Installationen verwenden dasselbe logische Sicherungsformat; eine Sicherung lässt sich auf dem jeweils anderen Weg wiederherstellen.

## Sicherung

`jfctl backup create` (geplant über `jf-manager-backup.timer`, Standard täglich 02:30):

1. Kurzes Wartungsfenster: Oberfläche, Backend und Worker anhalten, damit Datenbank und Uploads zusammenpassen. Die Datenbank läuft weiter.
2. `pg_dump` im Custom-Format; ein fehlgeschlagener oder leerer Dump bricht ab.
3. `app.env` (enthält `DJANGO_SECRET_KEY`, `FIELD_ENCRYPTION_KEY` und frühere Schlüssel), `jfctl.conf` und ein Manifest (Version, Modus, PostgreSQL-Version, Prüfsumme und Größe des Dumps, Anzahl/Größe der Uploads).
4. Restic schreibt Dump, Konfiguration, Manifest und `/var/lib/jf-manager/uploads` verschlüsselt ins Repository. Nur wenn Restic einen Snapshot meldet, gilt die Sicherung als erfolgreich.
5. Wartungsfenster endet – auch bei Fehlern.
6. Aufbewahrung: reguläre Sicherungen 7 täglich, 4 wöchentlich, 6 monatlich (`JF_BACKUP_KEEP_*`; Restic behält je Zeitraum die jüngste) und zusätzlich die letzten drei. Sicherheitskopien `pre-update`/`pre-restore` bleiben unabhängig davon 30 Tage erhalten (mindestens die letzten zwei), damit eine spätere Sicherung am selben Tag sie nicht verdrängt.

Ergebnis und letzte erfolgreiche Sicherung stehen in `/var/lib/jf-manager/state/last-backup.json`, in `jfctl status` und `jfctl doctor` (Warnung ab 26 Stunden).

**Backup-Passwort:** `/etc/jf-manager/backup.pass`. Ohne dieses Passwort ist keine Sicherung lesbar. Es gehört zusätzlich an einen Ort außerhalb des Servers (Passwortmanager, Tresor). Das Repository sollte auf einem anderen Gerät liegen: lokaler Pfad auf zweitem Datenträger, `sftp:benutzer@host:/pfad` oder S3-kompatibler Speicher. Zugangsdaten für entfernte Repositorys gehören in `/etc/jf-manager/restic.env` (0600, z. B. `AWS_ACCESS_KEY_ID=…`).

`jfctl backup list` zeigt Sicherungen mit Version und Art (`scheduled`, `manual`, `pre-update`, `pre-restore`). `jfctl backup verify [ID]` prüft das Repository (`restic check`, 10 % der Daten gelesen), liest die Sicherung vollständig aus und kontrolliert Prüfsumme und Lesbarkeit des Dumps (`pg_restore --list`), die enthaltenen Schlüssel und die Zahl der Uploaddateien.

## Wiederherstellung

`jfctl restore <ID> [--confirm INSTANZNAME]`

1. **Vorabprüfung, nichts wird ersetzt:** Repository und Passwort, Sicherung vollständig lesbar, Prüfsumme und Lesbarkeit des Dumps, Schlüssel vorhanden, Uploads vollständig, Version der Sicherung nicht neuer als die installierte, genug freier Speicher.
2. **Ausdrückliche Bestätigung:** Instanzname eintippen (oder `--confirm` in Skripten). Es gibt keinen Countdown.
3. **Ist-Zustand sichern** (Sicherung der Art `pre-restore`).
4. **Vorbereiten:** Dump in die temporäre Datenbank `jf_manager_restore` einspielen und prüfen.
5. **Aktivieren:** Datenbanken umbenennen (bisherige bleibt als `jf_manager_before_restore`), Uploads tauschen (bisherige als `uploads.before-restore`), Anwendungsschlüssel aus der Sicherung übernehmen. Hostbezogene Werte (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `FRONTEND_URL`, `WEBAUTHN_RP_ID`, `WEBAUTHN_ORIGINS`, `TIME_ZONE`, `DEBUG`) bleiben die des Zielsystems. Bei geänderter Domain funktionieren registrierte Passkeys nicht mehr (siehe [session-auth.md](session-auth.md#passkeys-domain-und-https)).
6. Migrationen auf den installierten Stand, **alle Sitzungen verworfen**, Redis geleert.
7. **Worker bleiben angehalten**, damit wartende Versand-, Synchronisations- und Push-Aufträge aus der Sicherung nicht ungeprüft laufen. Nach Prüfung: `jfctl workers release`.

Scheitert Schritt 5 oder 6, stellt `jfctl` Datenbank, Uploads und `app.env` automatisch zurück (Rückgabecode 7).

**Neuer Host:** `jfctl install` mit Aktion `restore`, Repository und Backup-Passwort. Die Installation prüft das Passwort vorab und spielt die Sicherung anschließend über denselben Ablauf ein. Der Wechsel zwischen Docker und nativ funktioniert so ebenfalls.

**Wiederherstellungsprobe:** Mindestens vierteljährlich eine Sicherung auf einem leeren Testsystem einspielen (`jfctl install`, Aktion `restore`) und die Anmeldung prüfen. Dieser Ablauf ist der Abnahmenachweis aus der Roadmap.

## Update

`jfctl update --version X.Y.Z`

| Stufe | Inhalt | Bei Fehler |
| --- | --- | --- |
| 1 | Zielversion gültig und neuer; kein unvollständiges Update | nichts geändert |
| 2 | Release laden, Prüfsummen/Herkunft prüfen, PostgreSQL-Hauptversion und Speicher prüfen, Images ziehen bzw. Python-Umgebung bauen | nichts geändert |
| 3 | Wartungsmodus (Oberfläche gesperrt, Worker gestoppt), vollständige Sicherung `pre-update` | Anwendung wieder freigegeben, Update nicht begonnen |
| 4 | Release wechseln, Migrationen | vorherige Version; ab Migration zusätzlich Datenbank aus der `pre-update`-Sicherung |
| 5 | Backend, `check --deploy`, keine offenen Migrationen, Worker – Oberfläche noch gesperrt | wie Stufe 4 |
| 6 | Oberfläche freigeben | – |

Ein automatisches Zurückrollen erfolgt nur vor der Freigabe; Nutzer konnten bis dahin nichts schreiben. Ein späteres Zurück auf eine ältere Version geht nur über `jfctl restore` einer Sicherung dieser Version, weil ein Imagewechsel ein bereits migriertes Schema nicht zurücksetzt. Der Fortschritt steht in `/var/lib/jf-manager/state/update.state`; ein unvollständiges Update blockiert weitere Updates, bis der Zustand geklärt ist.

Releases liegen unter `/opt/jf-manager/releases/`; behalten werden die aktive, die vorherige und die zwei neuesten Versionen.
