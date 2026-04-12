# Docker Deployment

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Internet Traffic                          │
└────────────────────────┬────────────────────────────────────┘
                         │ Port 80/443
┌────────────────────────▼────────────────────────────────────┐
│                  Frontend Container (Nginx)                  │
│  • Serves Vue.js SPA from /usr/share/nginx/html             │
│  • Proxies /api/* → backend:8000                            │
│  • Proxies /admin/* → backend:8000                          │
│  • Serves /static/* and /uploads/* from volumes             │
│  • Security headers, gzip, SSL/TLS termination              │
└────────┬──────────────┬──────────────┬──────────────┬───────┘
         │              │              │              │
    ┌────▼──────┐  ┌───▼────┐  ┌─────▼─────┐  ┌────▼───┐
    │  Backend  │  │   DB   │  │   Redis   │  │ Backup │
    │  Django   │  │Postgres│  │  Cache    │  │ (cron) │
    │  uWSGI    │  │  15    │  │  7        │  │        │
    │ :8000     │  │ :5432  │  │ :6379     │  │        │
    └───────────┘  └────────┘  └───────────┘  └────────┘
```

All containers run as non-root users with read-only filesystems where possible.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM, 20GB disk space

## Quick Start

```bash
# Automated setup
./setup.sh

# Or manually:
cp .env.example .env
nano .env  # Configure required variables
make build
make up
make health
```

## Environment Variables

### Required

```bash
POSTGRES_PASSWORD=your_strong_password        # openssl rand -base64 32
DJANGO_SECRET_KEY=your_random_secret_key      # openssl rand -base64 50
DJANGO_ADMIN_PASSWORD=your_admin_password     # openssl rand -base64 16
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
```

### Optional

```bash
DEBUG=False
HTTP_PORT=80
HTTPS_PORT=443
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=user@example.com
EMAIL_HOST_PASSWORD=password
BACKUP_KEEP_DAYS=7
BACKUP_KEEP_WEEKS=4
BACKUP_KEEP_MONTHS=6
```

## Makefile Commands

```bash
make help              # Show all commands
make build             # Build Docker images
make up                # Start services
make down              # Stop services
make restart           # Restart services
make logs              # View logs
make logs ARGS='backend'  # View specific service logs
make ps                # Show running containers
make backup            # Create database backup
make restore ARGS='./backups/backup.sql.gz'
make health            # Check service health
make ssl-cert          # Generate self-signed SSL cert
make shell-backend     # Backend shell
make shell-frontend    # Frontend shell
make shell-db          # Database shell
make migrate           # Run Django migrations
make collectstatic     # Collect static files
make createsuperuser   # Create Django superuser
make update            # Pull & rebuild & restart
```

## SSL/TLS Configuration

### Development (Self-Signed)

```bash
make ssl-cert
# Uncomment HTTPS server block in frontend/conf.d/default.conf
```

### Production (Let's Encrypt)

```bash
sudo apt-get install certbot
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
# Uncomment HTTPS server block and HTTP redirect in frontend/conf.d/default.conf
make restart
```

Auto-renewal:

```bash
# Add to crontab
0 0 * * * certbot renew --quiet --post-hook "docker-compose restart frontend"
```

## Backup & Restore

Backups are organized in tiers:
- **Daily**: Last 7 days
- **Weekly**: Last 4 weeks (Sundays)
- **Monthly**: Last 6 months (1st of month)

```bash
# Manual backup
make backup

# Schedule daily at 2 AM
0 2 * * * cd /path/to/JF-Manager && make backup

# List backups
ls -lh backups/*.sql.gz

# Restore
make restore ARGS='./backups/backup_20251128_120000.sql.gz'
```

## Health Checks

All services have health checks:

| Service | Endpoint | Method |
|---------|----------|--------|
| Frontend | `/health` | wget |
| Backend | `/api/v1/` | curl |
| Database | – | `pg_isready` |
| Redis | – | `redis-cli ping` |

```bash
make health
```

## Docker Images

| Image | Base | Size | Build Time |
|-------|------|------|------------|
| Backend | `python:3.11-slim-bookworm` | ~350MB | ~3-5 min |
| Frontend | `nginx:1.27-alpine` | ~50MB | ~2-3 min |

Both use multi-stage builds for minimal attack surface.

## Resource Usage

| Service | RAM Limit | RAM (idle) | CPU (idle) |
|---------|-----------|------------|------------|
| Backend | 2GB | ~200MB | <5% |
| Frontend | 512MB | ~10MB | <1% |
| Database | 1GB | ~50MB | <2% |
| Redis | 256MB | ~5MB | <1% |
| **Total** | – | ~300MB | – |

## Deployment Options

```bash
# Automated setup
./setup.sh

# Production deployment
./deploy.sh

# Manual
make build && make up && make health

# Development mode (with hot-reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Troubleshooting

### Services won't start
```bash
make logs
docker-compose config  # Verify configuration
sudo lsof -i :80      # Check port conflicts
```

### Database connection issues
```bash
docker-compose exec db pg_isready -U jf_manager
make shell-db
```

### Frontend can't reach backend
```bash
docker-compose exec frontend ping backend
docker-compose exec frontend curl http://backend:8000/health/
```

### Static files not loading
```bash
make collectstatic
```
