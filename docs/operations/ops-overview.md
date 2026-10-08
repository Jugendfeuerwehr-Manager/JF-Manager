# Betrieb: Überblick und Layout

Gilt ab OPS-01. Unterstützte Produktionswege sind **Docker Compose** und **Debian 13 nativ** (auch in einem Proxmox-LXC). Beide verwenden denselben Installationskern unter `ops/` und dasselbe Verwaltungswerkzeug `jfctl`. Entwicklungsanleitungen stehen in [getting-started.md](../getting-started.md); `dev/compose.yml` dient nur der Entwicklung und dem lokalen Imagebau.

## Aufbau

```text
Internet ──> Caddy (integriertes HTTPS, Port 80/443)   ──┐
        oder vorhandener Reverse Proxy (TLS)            ──┤
                                                          v
                         Nginx (Frontend, Port 8080, Sicherheitsheader/CSP)
                                │ /api, /admin           │ /static, Oberfläche
                                v
                         uWSGI/Django (Port 8000, nur intern)
                          │            │
                    PostgreSQL 17    Redis (Cache, Limits, RQ-Warteschlange)
                                       │
                         RQ-Worker (Synchronisation)  ·  Push-Worker
```

Nginx verwendet in beiden Wegen dieselbe Konfiguration aus `frontend/nginx.conf`, `frontend/conf.d/default.conf` und `frontend/snippets/`. Datenbank, Redis und uWSGI sind nie von außen erreichbar.

## Verzeichnisse und Dateien

| Pfad | Inhalt | Rechte |
| --- | --- | --- |
| `/etc/jf-manager/jfctl.conf` | Betriebsangaben (Modus, Version, Domain, HTTPS, Backupziel, Zeitplan) | root, 0600 |
| `/etc/jf-manager/app.env` | Anwendungsumgebung: `DJANGO_SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, E-Mail, Web-Push, `ALLOWED_HOSTS` usw. Identisch in beiden Wegen, wird gesichert. | root, 0600 |
| `/etc/jf-manager/secrets.env` | Datenbankpasswort (nur Infrastruktur, wird bei Restore neu gesetzt) | root, 0600 |
| `/etc/jf-manager/compose.env` | Von `jfctl` erzeugte Interpolationswerte für Compose | root, 0600 |
| `/etc/jf-manager/trusted-proxies.conf` | Adressen, deren `X-Forwarded-Proto` Nginx vertraut | root, 0644 |
| `/etc/jf-manager/backup.pass` | Restic-Passwort. **Zusätzlich getrennt vom Backup aufbewahren.** | root, 0600 |
| `/opt/jf-manager/releases/<version>/` | Entpacktes Releasepaket (`ops/`, nativ zusätzlich `backend/`, `frontend/`, `venv/`) | root |
| `/opt/jf-manager/current` | Verweis auf die aktive Version | root |
| `/var/lib/jf-manager/uploads/` | Private Medien und Anhänge | Anwendung |
| `/var/lib/jf-manager/static/` | Von `collectstatic` erzeugte statische Dateien (Admin, API-Dokumentation) | Anwendung, für Nginx lesbar |
| `/var/lib/jf-manager/postgres/`, `redis/`, `caddy/` | Datenbank-, Redis- und Zertifikatsdaten (Compose) | Container |
| `/var/lib/jf-manager/state/` | Status von Installation, letzter Sicherung, Update und Workerfreigabe | root |
| `/var/backups/jf-manager/restic/` | Standardziel des Restic-Repositorys (besser: zweites Gerät oder entfernter Speicher) | root |
| `/var/log/jf-manager/jfctl.log` | Bereinigtes Protokoll aller `jfctl`-Aktionen | root, 0640 |

Infrastrukturwerte (`DATABASE_URL`, `REDIS_URL`, `STATIC_ROOT`, `MEDIA_ROOT`) stehen nicht in `app.env`; Compose bzw. die systemd-Dienste setzen sie selbst. Dadurch lässt sich eine Sicherung zwischen Docker und nativer Installation wiederherstellen.

## Docker Compose

`ops/compose/compose.yml` (Compose V2) verwendet ausschließlich vorgebaute, versionsgebundene Images aus der GitHub Container Registry. `jfctl` erzeugt `compose.env` und ruft Compose immer als Projekt `jf-manager` auf. Dienste:

| Dienst | Aufgabe |
| --- | --- |
| `db` | PostgreSQL 17, Daten in `/var/lib/jf-manager/postgres` |
| `redis` | Redis 7 mit AOF; `volatile-lru` verdrängt nur Schlüssel mit Ablaufzeit (Cache, Limitzähler), nie die Warteschlange |
| `backend` | uWSGI/Django; migriert beim Start **nicht** (`DJANGO_MANAGEPY_MIGRATE=off`), Migrationen führt `jfctl` nach einer Sicherung aus |
| `worker` | `rqworker default` für Synchronisationsaufträge (fehlte in den bisherigen Compose-Dateien) |
| `push-worker` | Web-Push-Auslieferung |
| `frontend` | Nginx; bei integriertem HTTPS nur an `127.0.0.1:8080` gebunden |
| `caddy` | Profil `tls`: integriertes HTTPS mit automatischen Zertifikaten |

Datenbank und Redis liegen in einem internen Netz ohne Außenverbindung. Backend und Worker benötigen ausgehende Verbindungen (SMTP, OIDC, Spond, Web Push) und hängen deshalb zusätzlich am Netz `edge`.

## HTTPS und Proxy-Vertrauen

- **Integriert (`tls=caddy`):** Caddy beantwortet Port 80/443 für die konfigurierte Domain, holt Zertifikate selbst und überschreibt `X-Forwarded-Proto`. Nginx ist nur lokal erreichbar.
- **Vorhandener Reverse Proxy (`tls=proxy`):** Nginx wird an die konfigurierte Adresse gebunden (z. B. `192.168.1.5:8080`). `trusted-proxies.conf` enthält nur die angegebenen Proxyadressen; von allen anderen Absendern wird ein mitgeschicktes `X-Forwarded-Proto` ignoriert. Der Proxy muss den Header selbst setzen und Port 8080 darf nicht öffentlich erreichbar sein (siehe [production-security.md](production-security.md)).

Im Compose-Weg liegt das Netz `edge` auf einem festen Subnetz (`JF_EDGE_SUBNET`, Standard `172.30.83.0/24`, im Expertenmodus änderbar). Nginx vertraut diesem Subnetz bei integriertem HTTPS (Caddy) und dann, wenn der Reverse Proxy auf demselben Host läuft (`127.0.0.1`): Verbindungen auf einen veröffentlichten Port kommen dort über `docker-proxy` von der Gateway-Adresse des Netzes.

Das Frontend-Image vertraut ohne eingebundene Datei weiterhin jedem Absender (bisheriges Verhalten für eigene Setups).

## Gepinnte Laufzeitkomponenten

`backend/requirements-server.txt` legt uWSGI und den optionalen MySQL-Treiber mit Version und Prüfsumme fest; Image und natives Releasepaket installieren daraus. Anwendungsabhängigkeiten kommen unverändert aus `backend/Pipfile.lock`.

## Debian 13 nativ

Gleicher Aufbau ohne Container. Debian liefert PostgreSQL 17, Redis, Nginx und Caddy; die Anwendung läuft in einer Python-Umgebung je Release (`/opt/jf-manager/releases/<version>/venv`), installiert ausschließlich aus `backend/requirements.lock.txt` (aus `Pipfile.lock` erzeugt) und `requirements-server.txt`, jeweils mit `--require-hashes`.

| Unit | Aufgabe |
| --- | --- |
| `jf-manager.target` | Fasst die Anwendungsdienste zusammen |
| `jf-manager-web.service` | uWSGI an `127.0.0.1:8000`; prüft vorher `check --deploy` und sammelt statische Dateien |
| `jf-manager-worker.service` | `rqworker default` |
| `jf-manager-push.service` | Web-Push-Auslieferung |
| `jf-manager-nginx.service` | Eigene Nginx-Instanz (`/etc/jf-manager/nginx/`), erzeugt aus derselben Konfiguration wie das Frontend-Image; der Debian-Standarddienst `nginx.service` wird deaktiviert |
| `caddy.service` | Nur bei integriertem HTTPS; `/etc/caddy/Caddyfile` erzeugt `jfctl` |
| `postgresql.service`, `redis-server.service` | Debian-Pakete, nur lokal erreichbar |

Die Anwendungsdienste laufen als Systembenutzer `jfmanager` mit systemd-Härtung (`ProtectSystem=strict`, nur Uploads und statische Dateien beschreibbar). Infrastrukturwerte stehen in `/etc/jf-manager/native.env` (von `jfctl` erzeugt). Debian 13 bringt Python 3.13 mit, das Container-Image nutzt 3.12; beide Versionen werden von Django 5.2 unterstützt.

## Proxmox-LXC

`ops/proxmox/jf-lxc.sh` läuft auf dem Proxmox-Host, legt einen unprivilegierten Debian-13-Container an und führt darin denselben nativen Installationskern aus. Auf dem Host selbst werden keine Anwendungsdienste installiert (siehe [ops-install.md](ops-install.md)).
