# Abgelöst

Die früheren systemd-Units für `docker-compose` sind entfernt; `jfctl` richtet Dienste und Timer selbst ein. Unterstützt werden ab OPS-05 nur noch **Docker Compose** und **Debian 13 nativ** (auch im Proxmox-LXC), beide über `jfctl`.

- Neuinstallation: [Installation](../operations/ops-install.md)
- Bestehende Installation (Compose, Portainer, Synology) übernehmen: [Migration](../operations/ops-migration.md)
- Betrieb, Sicherung, Updates: [jfctl](../operations/ops-jfctl.md), [Sicherung, Wiederherstellung und Updates](../operations/ops-backup-restore-update.md)
- Produktionsprüfung: `jfctl doctor` und [Produktionsvorgaben](../operations/production-security.md)
