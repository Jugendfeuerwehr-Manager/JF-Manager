# Releasepakete und Herkunftsnachweis

Gilt ab OPS-01.2. Produktionssysteme beziehen ausschließlich veröffentlichte Releases; es gibt kein `git pull` und keinen Build beliebiger Branches auf dem Server.

## Bestandteile eines Releases

| Datei | Inhalt |
| --- | --- |
| `jf-manager-<version>.tar.gz` | `ops/` (jfctl, Compose-Datei, systemd-Units), `backend/` (nur committete Dateien, zusätzlich `requirements.lock.txt`), `frontend/dist/` (gebaute Oberfläche) und die Nginx-Konfiguration, `MANIFEST.json` |
| `release-manifest.json` | Version, Commit, Erstellzeit, Python-Version, PostgreSQL-Hauptversion, Image-Referenzen **mit Digest** und SHA-256 des Pakets |
| `SHA256SUMS` | Prüfsummen von Paket und Manifest |

Docker-Installationen verwenden aus dem Paket nur `ops/`; Images werden über die im Manifest festgehaltenen Digests geladen und lokal mit der Version markiert. Native Installationen bauen aus dem Paket die Python-Umgebung.

## Prüfung durch jfctl

1. `SHA256SUMS`, Manifest und Paket über HTTPS laden; Prüfsummen müssen stimmen, Manifest-Version und Paket-Hash zusammenpassen.
2. Herkunftsnachweis: Ist die `gh`-CLI vorhanden, prüft `jfctl` die GitHub-Attestierung des Pakets (`gh attestation verify`). `JF_VERIFY_ATTESTATION=required` erzwingt diese Prüfung, `off` schaltet sie ab (z. B. Offline-Installation aus einem lokalen Verzeichnis). Ohne Attestierung schützen Prüfsummen nur vor Übertragungsfehlern, nicht vor einem manipulierten Release.
3. Paketpfade werden vor dem Entpacken geprüft (keine absoluten Pfade, kein `..`).
4. Erst nach erfolgreicher Prüfung wird das Release unter `/opt/jf-manager/releases/<version>` abgelegt; der Wechsel von `/opt/jf-manager/current` erfolgt atomar.

## Lokal bauen

```sh
ops/release/build-release.sh --version 1.4.0 --out dist/release \
  --backend-image ghcr.io/jugendfeuerwehr-manager/jf-manager/backend@sha256:… \
  --frontend-image ghcr.io/jugendfeuerwehr-manager/jf-manager/frontend@sha256:…
```

`--ref WORKTREE` packt den Arbeitsstand für lokale Tests und ist für Veröffentlichungen nicht zulässig. Das Paket ist reproduzierbar (sortierte Einträge, feste Zeitstempel aus dem Commit, keine Benutzerkennungen).

## Gepinnte Server

`backend/requirements-server.txt` enthält uWSGI und den optionalen MySQL-Treiber mit Prüfsumme. Beim Aktualisieren Version und Hash von PyPI übernehmen (`https://pypi.org/pypi/<paket>/<version>/json`) und Image sowie nativen Weg erneut prüfen.
