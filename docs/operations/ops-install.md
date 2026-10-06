# Installation

Gilt ab OPS-02. Unterstützt werden **Docker Compose** (Compose V2) und **Debian 13 nativ** auf amd64, Letzteres auch in einem unprivilegierten **Proxmox-LXC** (Proxmox VE 9.x). Weitere Plattformen werden erst nach eigener Installations- und Restoreprüfung zugesichert.

## Voraussetzungen

- Debian 13 (für Compose auch andere Linux-Systeme mit systemd, Docker Engine und Compose V2), amd64, mindestens 2 GB RAM und 5 GB freier Speicher im Datenverzeichnis.
- Domainname mit DNS-Eintrag auf den Server (integriertes HTTPS) oder ein vorhandener Reverse Proxy.
- Bei integriertem HTTPS freie Ports 80 und 443.

## Ablauf

```sh
VERSION=1.4.0
BASE=https://github.com/Jugendfeuerwehr-Manager/JF-Manager/releases/download/v$VERSION
curl -fsSLO "$BASE/jf-manager-$VERSION.tar.gz" -O "$BASE/SHA256SUMS" -O "$BASE/release-manifest.json"
sha256sum -c SHA256SUMS
tar -xzf "jf-manager-$VERSION.tar.gz"
sudo "./jf-manager-$VERSION/ops/jfctl" install --version "$VERSION" --release-dir .
```

Danach steht `jfctl` als `/usr/local/sbin/jfctl` bereit.

Der Assistent fragt zuerst alle Angaben ab und ändert noch nichts:

| Angabe | Standard | Hinweis |
| --- | --- | --- |
| Aktion | `install` | `restore`: Wiederherstellung einer Sicherung auf diesem neuen Host; `import`: Export einer Altinstallation übernehmen ([ops-migration.md](ops-migration.md)) |
| Betriebsmodus | `compose`, wenn Docker vorhanden, sonst `native` | |
| Version | `latest` | wird zu einer festen Version aufgelöst; Branches sind nicht installierbar |
| Domain, Zeitzone | –, `Europe/Berlin` | |
| HTTPS | `caddy` | `proxy`: Adresse:Port für Nginx und IP-Adresse(n) des Proxys |
| Backup-Ziel, Backup-Passwort | `/var/backups/jf-manager/restic`, wird erzeugt | Passwort verdeckt; mindestens 12 Zeichen |
| Erstes Administrationskonto | `admin`, Passwort wird erzeugt | nur bei `install` |

Mit `--expert` zusätzlich: Instanzname, Datenverzeichnis, Backup-Zeitplan und -Aufbewahrung, Prüfung des Herkunftsnachweises.

**Vorabprüfung** vor jeder Änderung: Angaben, Betriebssystem und Architektur (nativ: Debian 13), systemd, Docker Compose V2 (Compose), freier Speicher, Arbeitsspeicher, belegte Ports, DNS (Warnung), Passwortlängen, bei `restore` Lesbarkeit des Repositorys mit dem Passwort, Release laden und Prüfsummen prüfen. Erst danach folgen Zusammenfassung und Rückfrage.

**Schritte** (`/etc/jf-manager/install.state`): Pakete, Konfiguration (Geheimnisse werden erzeugt), Release, Laufzeit (Images bzw. Python-Umgebung, Web-Push-Schlüssel), Datenbank, Migration und Rollenvorlagen (bzw. Wiederherstellung), Start, Backup-Repository, Wartungs-Timer, Administrationskonto, erste Sicherung, Abschlussprüfung. Ein abgebrochener Lauf setzt beim nächsten `jfctl install` am ersten offenen Schritt fort; erzeugte Geheimnisse bleiben erhalten.

Die fachliche Einrichtung (Organisation, Abteilungen, Rollen, E-Mail-Vorlagen, SSO) folgt in der Weboberfläche. Administratoren richten bei der ersten Anmeldung MFA ein.

## Automatisierung mit Antwortdatei

```sh
sudo install -m 600 /dev/null /root/jf-answers.env
sudo editor /root/jf-answers.env
sudo jfctl install --answers /root/jf-answers.env --yes
```

```dotenv
JF_ACTION=install
JF_MODE=native
JF_VERSION=1.4.0
JF_DOMAIN=jf.example.org
JF_TLS=caddy
JF_ACME_EMAIL=it@example.org
JF_ADMIN_USER=admin
JF_ADMIN_EMAIL=it@example.org
JF_BACKUP_REPO=sftp:backup@nas.example.org:/srv/restic/jf
# Optional; ohne Angabe erzeugt
JF_BACKUP_PASSWORD='…'
EMAIL_HOST=smtp.example.org
EMAIL_HOST_USER=jf@example.org
EMAIL_HOST_PASSWORD='…'
```

Die Datei muss root gehören und darf nur für den Besitzer lesbar sein; sonst bricht `jfctl` ab. Geheimnisse gelangen nie in Prozessargumente. Unbekannte Schlüssel sind ein Fehler.

## Proxmox-LXC

Auf dem Proxmox-Host (nicht im Container):

```sh
sudo ./jf-manager-$VERSION/ops/proxmox/jf-lxc.sh --release-dir .
```

Das Skript fragt CT-ID, Hostname, Storage, CPU, RAM, Plattengröße, Bridge, IP (DHCP oder statisch mit Gateway), DNS und anschließend die Angaben des Assistenten ab, prüft Proxmox-Version, freie CT-ID, Storage und Template, legt einen **unprivilegierten** Debian-13-Container an (`nesting=1` für systemd) und führt darin `jfctl install --mode native` mit einer geschützten Antwortdatei aus. Auf dem Host werden keine Anwendungsdienste installiert. Betrieb danach im Container: `pct enter <CT-ID>` und `jfctl …`.
