# Systemd Service Files for JF-Manager

These systemd service files provide an alternative to cron jobs for managing JF-Manager on production servers.

## Installation

### 1. Copy service files to systemd directory

```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/
```

### 2. Update WorkingDirectory in service files

Edit the service files and replace `/opt/jf-manager` with your actual installation path:

```bash
sudo sed -i 's|/opt/jf-manager|/path/to/your/jf-manager|g' /etc/systemd/system/jf-manager*.service
```

### 3. Reload systemd

```bash
sudo systemctl daemon-reload
```

## Usage

### Main Application Service

```bash
# Enable service to start on boot
sudo systemctl enable jf-manager.service

# Start the application
sudo systemctl start jf-manager.service

# Stop the application
sudo systemctl stop jf-manager.service

# Restart the application
sudo systemctl restart jf-manager.service

# Check status
sudo systemctl status jf-manager.service

# View logs
sudo journalctl -u jf-manager.service -f
```

### Backup Timer

```bash
# Enable backup timer
sudo systemctl enable jf-manager-backup.timer

# Start backup timer
sudo systemctl start jf-manager-backup.timer

# Check timer status
sudo systemctl status jf-manager-backup.timer

# List all timers
sudo systemctl list-timers

# Run backup manually
sudo systemctl start jf-manager-backup.service

# View backup logs
sudo journalctl -u jf-manager-backup.service -f
```

## Service Files

### jf-manager.service
Main application service that manages the Docker Compose stack.

**Features:**
- Starts on boot
- Automatic restart on failure
- Proper dependency on Docker service
- Network readiness check

### jf-manager-backup.service
Backup service for database backups.

**Features:**
- One-shot service
- Requires main application
- Logging to systemd journal

### jf-manager-backup.timer
Timer for automated backups.

**Features:**
- Runs daily at 2 AM
- Randomized delay (up to 15 minutes)
- Persistent across reboots

## Advantages Over Cron

1. **Better Logging**: All logs in systemd journal
2. **Dependency Management**: Services can depend on each other
3. **Restart Policies**: Automatic restart on failure
4. **Resource Control**: Can set CPU/memory limits
5. **Monitoring**: Easier to monitor with `systemctl status`
6. **Calendar Expressions**: More flexible scheduling

## Monitoring

### Check if services are running

```bash
sudo systemctl is-active jf-manager.service
sudo systemctl is-enabled jf-manager.service
```

### View service logs

```bash
# Last 100 lines
sudo journalctl -u jf-manager.service -n 100

# Follow logs
sudo journalctl -u jf-manager.service -f

# Logs since yesterday
sudo journalctl -u jf-manager.service --since yesterday

# Logs with specific priority (error, warning, etc.)
sudo journalctl -u jf-manager.service -p err
```

### Check timer next run

```bash
sudo systemctl list-timers jf-manager-backup.timer
```

## Customization

### Change backup time

Edit `/etc/systemd/system/jf-manager-backup.timer`:

```ini
[Timer]
# Run at 3 AM instead of 2 AM
OnCalendar=*-*-* 03:00:00
```

Then reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart jf-manager-backup.timer
```

### Add resource limits

Edit `/etc/systemd/system/jf-manager.service`:

```ini
[Service]
# Limit memory to 4GB
MemoryLimit=4G

# Limit CPU to 2 cores
CPUQuota=200%
```

### Add email notifications on failure

Create `/etc/systemd/system/jf-manager-notify@.service`:

```ini
[Unit]
Description=JF-Manager Failure Notification

[Service]
Type=oneshot
ExecStart=/usr/bin/mail -s "JF-Manager Service Failed: %i" admin@example.com
StandardInput=null
```

Then add to main service:

```ini
[Unit]
OnFailure=jf-manager-notify@%n.service
```

## Troubleshooting

### Service fails to start

```bash
# Check status
sudo systemctl status jf-manager.service

# View logs
sudo journalctl -u jf-manager.service -n 50

# Check if Docker is running
sudo systemctl status docker
```

### Timer not running

```bash
# Check timer status
sudo systemctl status jf-manager-backup.timer

# Check if timer is enabled
sudo systemctl is-enabled jf-manager-backup.timer

# List all timers
sudo systemctl list-timers --all
```

### Backup service fails

```bash
# Run manually to see errors
sudo systemctl start jf-manager-backup.service

# Check logs
sudo journalctl -u jf-manager-backup.service -n 50
```

## Uninstallation

```bash
# Stop and disable services
sudo systemctl stop jf-manager.service
sudo systemctl disable jf-manager.service
sudo systemctl stop jf-manager-backup.timer
sudo systemctl disable jf-manager-backup.timer

# Remove service files
sudo rm /etc/systemd/system/jf-manager*.service
sudo rm /etc/systemd/system/jf-manager*.timer

# Reload systemd
sudo systemctl daemon-reload
```

## See Also

- Main documentation: [DEPLOYMENT.md](../DEPLOYMENT.md)
- Cron alternative: [crontab.example](../crontab.example)
- Systemd documentation: `man systemd.service`, `man systemd.timer`
