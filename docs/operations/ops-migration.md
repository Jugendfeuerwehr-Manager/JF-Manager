# Migration bestehender Installationen

Gilt ab OPS-05. Bisherige Varianten – `docker-compose.yml` aus dem Projektwurzelverzeichnis mit `setup.sh`/`deploy.sh`/`make`, Portainer-Stacks, Synology-Builds, Compose V1 – werden nicht mehr gepflegt. Alle verwenden die Container `jf_manager_db`, `jf_manager_backend` und `jf_manager_frontend` und lassen sich auf denselben Weg übernehmen.

## Portainer → jfctl: Schritt für Schritt

Der neue Compose-Weg verwendet weiterhin Docker. Installation, Updates und Sicherungen werden auf dem Linux-Host per SSH mit `jfctl` verwaltet. Du musst Portainer für andere Anwendungen nicht entfernen. Den alten JF-Manager-Stack nach dem Wechsel nicht mehr über Portainer starten oder aktualisieren.

Die Übernahme kopiert Datenbank, Uploads und Anwendungskonfiguration in eine neue Installation. Alte Container und Volumes bleiben zunächst erhalten. PostgreSQL wird über einen logischen Export von der alten auf die neue Version übernommen; das alte Datenbankvolume wird nicht in die neue Installation eingebunden.

### 1. Ziel und Wartungsfenster festlegen

| Ziel | Vorgehen |
| --- | --- |
| Bisheriger Docker-Host mit Linux, systemd, amd64 und Compose V2 | Export und anschließend `jfctl install` im Modus `compose` auf diesem Host. |
| Neuer Docker-Host | Export auf dem bisherigen Docker-Host; Export auf das Ziel kopieren; dort Modus `compose`. |
| Neuer Debian-13-Server oder Debian-13-LXC auf Proxmox VE 9 | Export auf dem bisherigen Docker-Host; Export ins Debian-Ziel kopieren; dort Modus `native`. |
| Synology/NAS ohne passende Hostvoraussetzungen | Export auf dem Docker-Host; neue Installation auf einem unterstützten Linux-Ziel. Voraussetzungen des Exportwerkzeugs unten beachten. |

Plane eine Unterbrechung vom finalen Export bis zur Freigabe der neuen Installation ein. Ihre Dauer hängt von Datenmenge, Download, Imagebezug und Migrationen ab. Bereite Zielhost, Release und Proxyangaben vorher vor. Ein separater Zielhost erleichtert die Rückkehr.

Auf dem Ziel gelten die [Installationsvoraussetzungen](ops-install.md#voraussetzungen), insbesondere mindestens 2 GB RAM und 5 GB freier Speicher **zusätzlich zum Platz für Export, Uploads und Wiederherstellung**. Nativ einen eigenen Debian-13-Host verwenden: der Installer verwaltet PostgreSQL, Redis und Nginx.

Für Proxmox: einen leeren, unprivilegierten Debian-13-amd64-LXC mit `nesting=1`, mindestens 2 GB RAM und ausreichend Platte vorbereiten. Die folgenden Installationsbefehle laufen **im Container**, erreichbar über `pct enter <CT-ID>`. Das automatische `jf-lxc.sh` überträgt derzeit kein `JF_IMPORT_DIR` und keinen Altinstallations-Export; für diese direkte Übernahme deshalb den Installationskern im vorbereiteten Container verwenden.

### 2. Bestand aufnehmen und Stack-Variablen sichern

**Ort: Portainer und SSH-Terminal des bisherigen Docker-Hosts.** Bei Portainer mit mehreren Environments ist der Host des ausgewählten Environments gemeint, nicht zwingend der Portainer-Server.

1. In Portainer den bisherigen JF-Manager-Stack öffnen. Stackdefinition, Imageversionen, veröffentlichte Ports und Volumezuordnungen sichern. Variablen aus dem Stack und gegebenenfalls separat gesetzte Containerwerte abgleichen.
2. Domain und Reverse-Proxy-Ziel notieren (z. B. Nginx Proxy Manager, Traefik oder eigener Nginx). Bei Docker-internem Proxyziel wird sich der bisherige Containername ändern.
3. Auf dem Docker-Host prüfen:

   ```sh
   sudo docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
   sudo docker inspect jf_manager_backend --format '{{range .Mounts}}{{println .Destination "<-" .Source}}{{end}}'
   ```

   Erwartete Namen: `jf_manager_db`, `jf_manager_backend`, `jf_manager_frontend`, meist `jf_manager_redis`. Die Uploads müssen beim Backend unter `/uploads` eingebunden sein. Bei abweichendem Uploadpfad vor dem Export klären: das Werkzeug würde sonst nur warnen und keine Dateien übernehmen. Für abweichende Datenbank-/Backendnamen gibt es `--db-container NAME` und `--backend-container NAME`; Frontend, Redis und sämtliche eigenen Worker in diesem Fall ausdrücklich selbst anhalten.
4. Eine geschützte Variablendatei anlegen:

   ```sh
   sudo install -m 600 /dev/null /root/jf-legacy.env
   sudo editor /root/jf-legacy.env
   ```

   Format (Beispielwerte ersetzen):

   ```dotenv
   POSTGRES_USER=jf_manager
   POSTGRES_DB=jf_manager_backend
   POSTGRES_PASSWORD='BISHERIGER_DATENBANKWERT'
   DJANGO_SECRET_KEY='BISHERIGER_DJANGO_SCHLUESSEL'
   FIELD_ENCRYPTION_KEY='BISHERIGER_VERSCHLUESSELUNGSSCHLUESSEL'
   # Dazu alle bisherigen Anwendungswerte, z. B. EMAIL_*, LDAP/OIDC,
   # WEBPUSH_* und gegebenenfalls FIELD_ENCRYPTION_PREVIOUS_KEYS.
   ```

   `POSTGRES_USER` und `POSTGRES_DB` müssen den tatsächlichen Werten entsprechen. Schlüssel **unverändert übernehmen**, nicht neu erzeugen. Die Datei wird gelesen, nicht als Shellskript ausgeführt: `NAME=WERT`, bei Leerzeichen/Sonderzeichen einfache Hochkommas; keine `${…}`-Verweise oder Shellbefehle. Werte mit einem Hochkomma unterstützt das neue Konfigurationsformat nicht; solche Werte vorab kontrolliert beim Anbieter ändern und im Altbestand prüfen.

   **Falls bisher kein `FIELD_ENCRYPTION_KEY` gesetzt war:** nicht mit einem beliebigen neuen Schlüssel fortfahren. Alte Versionen nutzten teilweise einen festen Ersatzschlüssel. Den tatsächlich verwendeten Schlüssel aus dem alten Installationscode sichern und die [Umverschlüsselung und Rotation](encryption-rotation.md#update-bestehender-installationen) planen. Der Export verlangt einen ausdrücklich angegebenen Schlüssel; er kann seine fachliche Richtigkeit nicht allein aus der Variablendatei bestätigen.

### 3. Release und Werkzeuge vorbereiten

**Ort: bisheriger Docker-Host und später auch Zielhost.** Verwende ein veröffentlichtes Release, das `ops/jfctl`, Manifest und Prüfsummen enthält. Ein alter Tag oder eine ZIP des Quellcodes genügt nicht. Vor dem Wartungsfenster prüfen, ob die passenden [Release-Artefakte](https://github.com/Jugendfeuerwehr-Manager/JF-Manager/releases) und für Compose die zugehörigen Images tatsächlich verfügbar sind. Die Roadmap-Abnahme ist kein Nachweis einer Veröffentlichung.

Die folgende Versionsnummer ist ein Platzhalter und muss durch die gewünschte veröffentlichte Version ersetzt werden:

```sh
VERSION=X.Y.Z
mkdir -p "$HOME/jf-migration-release"
cd "$HOME/jf-migration-release"
BASE="https://github.com/Jugendfeuerwehr-Manager/JF-Manager/releases/download/v$VERSION"
curl -fSL -o "jf-manager-$VERSION.tar.gz" "$BASE/jf-manager-$VERSION.tar.gz"
curl -fSL -o SHA256SUMS "$BASE/SHA256SUMS"
curl -fSL -o release-manifest.json "$BASE/release-manifest.json"
sha256sum -c SHA256SUMS
tar -xzf "jf-manager-$VERSION.tar.gz"
```

Nur nach erfolgreicher Prüfung fortfahren. Dieses Terminal und Verzeichnis für die nächsten Befehle beibehalten. `--release-dir .` bezeichnet das Verzeichnis mit **Archiv, SHA256SUMS und release-manifest.json**, nicht den entpackten Unterordner.

Das Exportwerkzeug braucht auf dem alten Linux-Host Bash, Docker-Zugriff sowie u. a. `jq`, `flock` und GNU-Werkzeuge (`stat`, `du`, `readlink`, `sha256sum`, `numfmt`). Der Portainer-Webeditor führt diese Hostbefehle nicht aus. Auf Debian/Ubuntu fehlende Pakete beispielsweise mit `sudo apt-get install jq curl openssl ca-certificates coreutils util-linux` bereitstellen. Auf NAS-Systemen zuerst die Verfügbarkeit prüfen; keine Linux-Befehle ungeprüft durch plattformspezifische Varianten ersetzen.

### 4. Schreibzugriffe stoppen und zusätzliche Sicherung erstellen

**Ort: bisheriger Docker-Host. Ab hier beginnt die Unterbrechung.** Nutzer informieren, automatische Stackupdates/Webhooks, alte Cronjobs und Sync-Aufrufe pausieren. Oberfläche, Backend und **alle** alten Worker stoppen; Datenbank für den Export laufen lassen. Ein gestoppter Container darf nicht automatisch von Portainer, einem Watchdog oder einer anderen Automatisierung gestartet werden.

Bei den Standardnamen:

```sh
sudo docker stop jf_manager_frontend jf_manager_backend
# Falls vorhanden: auch jf_manager_worker und eigene Push-/Sync-Worker stoppen.
sudo install -d -m 700 /root/jf-before-migration
```

Zusätzlich zum jfctl-Export eine separate Sicherung erstellen. Im folgenden Beispiel Benutzer und Datenbank an den Bestand anpassen; der Uploadpfad ist die Ausgabe aus Schritt 2:

```sh
sudo bash -c 'set -euo pipefail; umask 077; docker exec jf_manager_db pg_dump -U jf_manager -d jf_manager_backend -Fc --no-owner --no-acl > /root/jf-before-migration/db.dump'
sudo tar -C /TATSAECHLICHER/UPLOADPFAD -czf /root/jf-before-migration/uploads.tar.gz .
sudo cp /root/jf-legacy.env /root/jf-before-migration/legacy.env
```

Dumps, Uploads und Schlüssel zusammen geschützt aufbewahren, möglichst zusätzlich auf einem anderen Gerät. Ohne die Uploads fehlen später Bilder und Anhänge; ohne die Schlüssel können verschlüsselte Zugangsdaten unlesbar sein. Redis-Warteschlangen werden nicht übertragen.

### 5. Finalen Export ausführen

**Ort: bisheriger Docker-Host, im Releaseverzeichnis aus Schritt 3.** Die Datenbank muss noch laufen. Ein echtes altes Projektverzeichnis ist bei Portainer nicht nötig; `--from /root` wird hier mit der expliziten Variablendatei kombiniert.

```sh
sudo "./jf-manager-$VERSION/ops/jfctl" migrate legacy-compose \
  --from /root \
  --env-file /root/jf-legacy.env \
  --out /root/jf-legacy-export
```

Ein neues, noch nicht belegtes Exportverzeichnis verwenden. Die Rückfrage bestätigen. Das Werkzeug prüft Datenbankzugriff, Schlüsselangaben und Speicher, hält die Standardcontainer an, exportiert Datenbank und Uploads und stoppt danach Datenbank und Redis. Bei anderen Namen deren Zustand selbst kontrollieren. Nicht `--keep-running` für die endgültige Übernahme verwenden: nachträgliche Änderungen würden im neuen Bestand fehlen.

Erwartetes Ergebnis:

```text
/root/jf-legacy-export/
├── backup-staging/
│   ├── db.dump
│   ├── manifest.json
│   └── config/app.env
└── uploads/
```

```sh
sudo test -s /root/jf-legacy-export/backup-staging/db.dump
sudo jq '{postgres_major, db_dump, uploads}' /root/jf-legacy-export/backup-staging/manifest.json
sudo docker ps --format 'table {{.Names}}\t{{.Status}}'
```

Uploadzahl im Manifest mit dem erwarteten Bestand abgleichen. Bei „Kein Uploadverzeichnis …“ trotz vorhandener Dateien hier abbrechen und die Zuordnung klären. Das Exportverzeichnis ist **unverschlüsselt** und enthält personenbezogene Daten und Schlüssel; nur geschützt übertragen und lagern.

### 6. Export auf das Ziel übertragen

Auf demselben Host entfällt die Übertragung. Auf einem neuen Host das vollständige Verzeichnis einschließlich `backup-staging/config/app.env` und `uploads` übertragen, z. B. über eine bereits eingerichtete SSH-Verbindung mit Root-Zugriff:

```sh
sudo rsync -a -e ssh /root/jf-legacy-export/ root@ZIELHOST:/root/jf-legacy-export/
```

Root-SSH dafür nicht eigens freischalten; alternativ mit einem berechtigten Administrationskonto geschützt übertragen und auf dem Ziel mit `sudo` nach `/root` verschieben. Danach auf dem Ziel:

```sh
sudo chown -R root:root /root/jf-legacy-export
sudo chmod 700 /root/jf-legacy-export
sudo chmod 600 /root/jf-legacy-export/backup-staging/config/app.env
```

Für einen LXC ohne SSH kann das Verzeichnis geschützt als Archiv zum Proxmox-Host übertragen, mit `pct push <CT-ID> ARCHIV /root/jf-legacy-export.tar.gz --perms 0600` in den Container kopiert und dort unter `/root` entpackt werden. Die Übernahme liest anschließend den Pfad **im Container**.

### 7. Neue Installation mit Aktion import

**Ort: Zielhost, bei Proxmox im Debian-Container.** Dort Release wie in Schritt 3 bereitstellen. Auf demselben Host das bestehende Releaseverzeichnis verwenden:

```sh
sudo "./jf-manager-$VERSION/ops/jfctl" install --expert --version "$VERSION" --release-dir .
```

Im Assistenten:

| Frage | Antwort für die Übernahme |
| --- | --- |
| Aktion | **`import`**, damit bestehende Daten übernommen werden |
| Exportverzeichnis | `/root/jf-legacy-export` |
| Betriebsmodus | `compose` auf dem Docker-Ziel, `native` auf Debian 13/LXC |
| Version | Gewählte feste Releaseversion |
| Compose-Projektname (Expertenmodus) | Auf demselben Host anderer Name als der Altstack, z. B. `jf-manager-v3`, damit alte Container für Rückkehr erhalten bleiben |
| Domain | Bisherige Domain, ohne `https://` und ohne Pfad |
| Zeitzone | `Europe/Berlin` oder bisherige Zeitzone |
| HTTPS | `proxy`, wenn der vorhandene Reverse Proxy bleiben soll; sonst `caddy` |
| Adresse:Port bei proxy | Beispielsweise `192.168.1.50:8080` (eigene Ziel-IP); bei Proxy auf demselben Host gegebenenfalls `127.0.0.1:8080` |
| Proxyadressen | Tatsächliche Quell-IP(s) des Proxys, keine pauschale Freigabe |
| Backupziel | Neues Restic-Repository, möglichst auf einem anderen Gerät |
| Backuppasswort | Sicheres Passwort mit mindestens 12 Zeichen; außerhalb des Servers verwahren |

Ein Proxy in einem Dockercontainer erreicht `127.0.0.1` seines eigenen Containers, nicht automatisch den Host. Eine für ihn erreichbare Host-/LAN-Adresse wählen und das [Proxy-Vertrauen](ops-overview.md#https-und-proxy-vertrauen) berücksichtigen. Nginx muss den öffentlichen Hostnamen erhalten; der Proxy muss `X-Forwarded-Proto: https` selbst setzen. Den HTTP-Zielport nur für den Proxy erreichbar machen.

Bei `caddy` müssen 80, 443 und 8080 frei sein; ein bestehender Proxy auf 80/443 würde den Installationscheck blockieren. Auf dem bisherigen Docker-Host deshalb meist `proxy` beibehalten. Einen anderen freien Zielport wählen, wenn 8080 bereits verwendet wird.

Zusammenfassung prüfen und bestätigen. Der Installer erstellt die neue Laufzeit, spielt den Export über eine temporäre Datenbank ein, führt Migrationen aus und erstellt die erste verschlüsselte Sicherung. **Die bisherigen Konten werden übernommen**; bei `import` wird kein neues Erstkonto angelegt. Alle bisherigen Sitzungen werden verworfen. Hintergrundaufträge bleiben angehalten.

Bei Abbruch die Ursache anhand der Ausgabe und `/var/log/jf-manager/jfctl.log` beheben und denselben Installationsaufruf wiederholen; `/etc/jf-manager/install.state` nicht löschen. Bereits abgeschlossene Schritte und erzeugte Schlüssel werden beibehalten.

### 8. Proxy umstellen, prüfen und freigeben

**Ort: Zielhost und vorhandener Reverse Proxy.** Den alten Bestand gestoppt lassen. Beim bestehenden Proxy nur das Ziel auf die neue Adresse und den gewählten HTTP-Port ändern; Zertifikat und öffentliche Domain können bleiben. Ein Ziel wie `jf_manager_frontend:80` zeigt weiter auf den alten Container und muss ersetzt werden. Bei neuem integriertem Caddy gegebenenfalls DNS und Routerweiterleitung umstellen.

```sh
sudo jfctl status
sudo jfctl doctor
sudo jfctl workers status
sudo jfctl backup verify latest
sudo jfctl maintenance list
```

Über die öffentliche **HTTPS-Domain** prüfen:

- Anmeldung mit einem bestehenden Administrationskonto; gegebenenfalls MFA einrichten. Bei verlorenem Zugang: `sudo jfctl admin recover --user BENUTZERNAME` (bei Bedarf mit `--reset-mfa`).
- Mitglieder, Abteilungen, Dienstbuch und Inventar mit dem bisherigen Bestand vergleichen.
- Mehrere vorhandene Bilder und Anhänge öffnen; insbesondere geschützte Dateien prüfen.
- Mit einem eingeschränkten Konto die erwarteten Abteilungsrechte prüfen. Neue Rollen und Listenmigrationen können eine fachliche Nachprüfung verlangen.
- E-Mail-/LDAP-/OIDC-/Sync-Einstellungen und entschlüsselbare Zugangsdaten kontrollieren. Bei Schlüsselproblemen die Übernahme nicht freigeben; [Rotation](encryption-rotation.md) beachten.
- Wartende Sync-/Push-Aufträge prüfen und geplante Benachrichtigungen bewerten, bevor Hintergrundarbeit startet.

Wenn diese Prüfungen erfolgreich sind:

```sh
sudo jfctl workers release
sudo jfctl workers status
sudo jfctl backup create
sudo jfctl backup verify latest
```

Dann Nutzer informieren und den Betrieb freigeben. Backup-Passwort aus `/etc/jf-manager/backup.pass` getrennt sichern. Eine Sicherung auf derselben Platte schützt nicht vor Ausfall des Hosts.

### 9. Bei Problemen zum Altbestand zurückkehren

Die alten Container und Volumes bis zur Abnahme behalten. Bei Rückkehr zuerst auf dem Ziel `sudo jfctl stop` ausführen, neue Wartungs-/Backup-Timer aus `systemctl list-timers --all 'jf-manager*'` stoppen und den Proxy wieder auf das alte Ziel richten. Beide Bestände dürfen keine gleichzeitigen Schreibzugriffe oder Benachrichtigungen ausführen.

Auf dem bisherigen Docker-Host die **vorher vorhandenen** Container wieder starten, zuerst Datenbank und Redis, danach Backend, Worker und Oberfläche. Bei Standardnamen beispielsweise:

```sh
sudo docker start jf_manager_db jf_manager_redis
# Warten, bis Datenbank und Redis bereit sind.
sudo docker start jf_manager_backend jf_manager_frontend
# Nur zuvor vorhandene Worker wieder starten; alte Wartung gezielt reaktivieren.
```

Der Altbestand enthält den Stand **zum Exportzeitpunkt**. Nach Freigabe neu erfasste Daten auf dem Ziel fehlen dort; dafür ist vor einer Rückkehr ein gesonderter Datenabgleich nötig. Die migrierte PostgreSQL-Datenbank nicht einfach in die alte Anwendung einspielen.

### 10. Altbestand erst nach Abnahme aufräumen

Nach erfolgreicher Funktionsprüfung, erster verifizierter Sicherung und möglichst einem Restore-Test auf einem separaten Ziel:

1. Alte JF-Manager-Cronjobs, Updater und eigene systemd-Units dauerhaft deaktivieren.
2. Alten JF-Manager-Stack in Portainer entfernen. Nur eindeutig zugehörige Container/Volumes löschen; Datenbank- und Uploadvolumes erst nach Ende der gewählten Rückkehrfrist entfernen. Kein globales `docker system prune --volumes` verwenden.
3. Klartextexport und temporäre Variablendateien gemäß Aufbewahrungsplan löschen; die zusätzliche Altsicherung bis zum Ende der Rückkehrfrist geschützt behalten. Auch Kopien auf Übertragungs- und Proxmox-Hosts berücksichtigen.
4. Ab dann über `sudo jfctl` verwalten, Updates mit `sudo jfctl update --version X.Y.Z` durchführen. Details: [Befehle](ops-jfctl.md), [Sicherung und Wiederherstellung](ops-backup-restore-update.md).

## Andere Altinstallationen

Für einen alten Compose-Checkout mit `.env` gilt derselbe Ablauf; beim Export statt der Portainer-Datei `--from /pfad/zur/alten/installation` verwenden. Ohne `--env-file` liest das Werkzeug dort `.env`. Anschließend mit Aktion `import` übernehmen.

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
| `docker-compose.yml`, `docker-compose.dev.yml`, `.env.example`, `backups/` im Projektwurzelverzeichnis | Produktion: `jfctl install`; Entwicklung: `dev/compose.yml`, `dev/.env.example` |
