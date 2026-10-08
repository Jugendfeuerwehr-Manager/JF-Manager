# Server & Operations

Der Produktionsbetrieb verwendet **`jfctl`** für beide unterstützten Wege: Docker Compose mit Releaseimages oder Debian 13 nativ, auch in einem Proxmox-LXC. Fachliche Einstellungen liegen in der Weboberfläche. Entwicklungscontainer unter `dev/` sind keine Produktionsinstallation.

## Vor der Installation entscheiden

| Frage | Entscheidung |
| --- | --- |
| Betriebsweg | Docker Compose oder Debian 13 nativ; LXC nutzt den nativen Kern |
| Öffentliche Adresse | Feste Domain; HTTPS selbst mit Caddy oder über vorhandenen Reverse Proxy |
| Sicherungsziel | Separates Gerät/Repository und außerhalb des Hosts gesichertes Backup-Passwort |
| Verantwortlichkeiten | Hostzugang, Updates, Sicherungsprüfung, Alarmierung und Wiederherstellungsprobe |
| Bestehende Installation | Geprüfter Export/Import statt Überschreiben; Portainer-Migrationsanleitung verwenden |

Die öffentliche Oberfläche und API laufen unter derselben Herkunft. Eine Änderung der Domain betrifft Passkeys. Datenbank, Uploads, Schlüsselring und passende Anwendungsversion gehören zusammen; eine reine Datenbankkopie reicht nicht als vollständige Wiederherstellung.

## Schrittweise Betriebsanleitungen

1. [Produktionsvorgaben](../../operations/production-security.md) und [Aufbau/Verzeichnisse](../../operations/ops-overview.md) lesen.
2. [Installationsassistent](../../operations/ops-install.md) durchführen: Angaben, Vorabprüfung, Zusammenfassung, Bestätigung, Installation.
3. Mit `sudo jfctl status` und `sudo jfctl doctor` Ergebnis prüfen, HTTPS und Anmeldung im Browser kontrollieren.
4. Organisation durch die [Administration](../administrators/index.md) einrichten lassen.
5. `sudo jfctl backup create` und `sudo jfctl backup verify latest` ausführen; Sicherungsziel und Wiederherstellung auf einem getrennten Testhost nachweisen.
6. [Regelbetrieb](routine.md) und [Notfallhilfe](emergency.md) als Übergabe verwenden.

| Nachschlagen | Anleitung |
| --- | --- |
| CLI, Rückgabecodes, Protokolle, Timer | [jfctl-Referenz](../../operations/ops-jfctl.md) |
| Update, Backup, Restore und automatischer Rückfall | [Sicherung, Wiederherstellung und Updates](../../operations/ops-backup-restore-update.md) |
| Portainer, alte Compose-/Synology-Installation | [Migration mit konkreter Portainer-Anleitung](../../operations/ops-migration.md) |
| Paket, Prüfsummen und Herkunft | [Releasepakete](../../operations/ops-release.md) |
| Sitzungen, Passkeys, MFA, SSO | [Anmeldesicherheit](../../operations/session-auth.md) |
| Alte Geheimnisse neu verschlüsseln | [Schlüsselrotation](../../operations/encryption-rotation.md) |

Die vorhandenen Betriebsanleitungen sind die verbindliche Befehlsreferenz. Die Installation verlangt verfügbare Releaseartefakte; Versionsbeispiele ersetzen keine Prüfung des gewünschten Releases.
