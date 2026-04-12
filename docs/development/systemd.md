# Systemd Services

Systemd service files in `systemd/` provide an alternative to cron jobs for managing JF-Manager on production servers.

## Installation

```bash
# Copy service files
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/

# Update paths
sudo sed -i 's|/opt/jf-manager|/path/to/your/jf-manager|g' /etc/systemd/system/jf-manager*.service

# Reload
sudo systemctl daemon-reload
```

## Main Application Service

```bash
sudo systemctl enable jf-manager.service   # Start on boot
sudo systemctl start jf-manager.service
sudo systemctl stop jf-manager.service
sudo systemctl restart jf-manager.service
sudo systemctl status jf-manager.service
sudo journalctl -u jf-manager.service -f   # View logs
```

Features: starts on boot, automatic restart on failure, depends on Docker service, network readiness check.

## Backup Timer

```bash
sudo systemctl enable jf-manager-backup.timer
sudo systemctl start jf-manager-backup.timer
sudo systemctl status jf-manager-backup.timer
sudo systemctl list-timers                     # List all timers
sudo systemctl start jf-manager-backup.service # Manual backup
sudo journalctl -u jf-manager-backup.service -f
```

Features: runs daily at 2 AM, randomized delay (up to 15 min), persistent across reboots.

## Service Files

| File | Type | Purpose |
|------|------|---------|
| `jf-manager.service` | Service | Manages Docker Compose stack |
| `jf-manager-backup.service` | One-shot | Database backup (requires main service) |
| `jf-manager-backup.timer` | Timer | Schedules daily backup |
