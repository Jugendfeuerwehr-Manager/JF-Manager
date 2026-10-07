# Migration bestehender Installationen

Gilt ab OPS-05. Bisherige Varianten – `docker-compose.yml` aus dem Projektwurzelverzeichnis mit `setup.sh`/`deploy.sh`/`make`, Portainer-Stacks, Synology-Builds, Compose V1 – werden nicht mehr gepflegt. Alle verwenden die Container `jf_manager_db`, `jf_manager_backend` und `jf_manager_frontend` und lassen sich auf denselben Weg übernehmen.

## Ablauf

1. **Sichern wie bisher** (zusätzliche Absicherung): `docker exec jf_manager_db pg_dump -U <user> <db> | gzip > alt.sql.gz` und das Uploadvolume kopieren.
2. **Export** auf dem alten Host (alte Installation läuft):

   ```sh
   sudo ./jf-manager-$VERSION/ops/jfctl migrate legacy-compose --from /pfad/zur/alten/installation
   # Portainer: Stack-Variablen als Datei speichern und angeben
   sudo ./jf-manager-$VERSION/ops/jfctl migrate legacy-compose --from /tmp --env-file /root/stack.env
   ```

   Geprüft wird vorher: Umgebungsdatei mit `DJANGO_SECRET_KEY` und `FIELD_ENCRYPTION_KEY` (ohne den bisherigen Schlüssel wären verschlüsselte Zugangsdaten verloren), laufender Datenbankcontainer und Anmeldung, Uploadverzeichnis des Backends, freier Speicher. Nach Rückfrage stoppt `jfctl` Oberfläche und Backend der alten Installation, exportiert die Datenbank logisch (`pg_dump -Fc`), kopiert die Uploads, übernimmt die Anwendungswerte aus der `.env` (ohne Datenbank-, Port- und Build-Variablen) und stoppt danach auch Datenbank und Redis. Ergebnis: `/var/lib/jf-manager/import/legacy-<zeit>/` im Sicherungsformat (Rechte 0700).
3. **Neue Installation mit Übernahme** (gleicher oder neuer Host; bei neuem Host das Exportverzeichnis sicher kopieren):

   ```sh
   sudo ./jf-manager-$VERSION/ops/jfctl install --release-dir .   # Aktion: import
   ```

   Der Export wird über den regulären Wiederherstellungsablauf eingespielt: temporäre Datenbank, Prüfung, Umschalten, Migrationen auf den aktuellen Stand, Sitzungen verworfen, Worker angehalten. Anschließend wartende Aufträge prüfen und `jfctl workers release`.
4. **Prüfen:** Anmeldung, Mitglieder, Anhänge/Bilder, Synchronisationen; `jfctl doctor`. Danach Exportverzeichnis löschen und die alte Installation (Container, Volumes, Cronjobs, eigene systemd-Units) entfernen.

## PostgreSQL-Versionswechsel

Alte Installationen nutzen PostgreSQL 15, beide neuen Wege PostgreSQL 17. Der Wechsel erfolgt über den logischen Export (Schritt 2) und Import (Schritt 3); ein Kopieren des Datenverzeichnisses ist nicht möglich. Spätere Hauptversionswechsel laufen genauso: `jfctl backup create`, neue Installation mit Aktion `restore`. `jfctl update` lehnt Releases mit anderer PostgreSQL-Hauptversion ab.

## Wechsel zwischen Docker und nativ

Beide Wege verwenden dasselbe Sicherungsformat: Sicherung erstellen, auf dem Zielsystem `jfctl install` mit Aktion `restore`, demselben Repository und Passwort.

## Abgelöste Dateien

Die folgenden Dateien und Anleitungen sind aus dem Repository entfernt (OPS-05.3). Wer noch eine ältere Arbeitskopie nutzt, findet hier den Nachfolger.

| Bisher | Nachfolger |
| --- | --- |
| `setup.sh`, `validate.sh` | `jfctl install` (mit Vorabprüfung) |
| `deploy.sh`, `make update`, Workflow „Deploy“ mit `git pull` | `jfctl update --version` |
| `scripts/backup.sh`, `make backup`, `systemd/jf-manager-backup.*` | `jfctl backup create`, `jf-manager-backup.timer` |
| `scripts/restore.sh`, `make restore` (10-Sekunden-Countdown) | `jfctl restore` mit Vorabprüfung und Bestätigung |
| `healthcheck.sh`, `make health` | `jfctl status`, `jfctl doctor` |
| `crontab.example` | systemd-Timer (`jfctl maintenance list`) |
| `portainer/`, `docs/deployment/*.md` (Docker, Portainer, Synology, Produktions-Checkliste), `docs/development/systemd.md` | [Installation](ops-install.md), dieses Dokument |
| `docs/security-upgrade.md` (Update-Hinweise aus der JWT-Zeit) | [Produktionsvorgaben](production-security.md), [Cookie-Sitzungen](session-auth.md) |
| `backend/docker-compose.yml` (Compose V1) | `ops/compose/compose.yml` über `jfctl` |
