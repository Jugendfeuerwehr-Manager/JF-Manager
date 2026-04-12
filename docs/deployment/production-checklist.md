# Production Checklist

## Security Checklist

- [ ] Strong passwords in `.env` (generated with `openssl rand -base64 32`)
- [ ] `DEBUG=False`
- [ ] Correct `ALLOWED_HOSTS` set
- [ ] `CSRF_TRUSTED_ORIGINS` configured
- [ ] SSL/TLS certificates installed
- [ ] Firewall configured (ports 80, 443 only)
- [ ] `.env` file permissions: `chmod 600 .env`
- [ ] Automated backups scheduled
- [ ] Backup restoration tested
- [ ] Email configuration for notifications
- [ ] Regular security updates scheduled
- [ ] Monitoring configured

## Container Security

- **Non-root users**: Backend runs as `django` (UID 1000), Frontend as `nginx` (UID 101)
- **Read-only filesystems**: Backend container has read-only root
- **No new privileges**: Security option enabled on all containers
- **Minimal base images**: Alpine Linux where possible
- **Multi-stage builds**: Reduced attack surface
- **Internal network**: Only frontend exposes ports 80/443

## Security Headers (Nginx)

- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Quick Operations

```bash
make build          # Build all images
make up             # Start all services
make down           # Stop all services
make restart        # Restart services
make update         # Pull & rebuild & restart
make health         # Check service health
make backup         # Create database backup
make migrate        # Run Django migrations
make collectstatic  # Collect static files
make createsuperuser # Create admin user
make logs           # All logs
make logs ARGS='backend'  # Specific service
make shell-backend  # Backend shell
make shell-db       # Database shell
```

## Monitoring

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Health check
make health
./healthcheck.sh
```

## Performance Tuning

### PostgreSQL

```yaml
db:
  command:
    - postgres
    - -c
    - max_connections=200
    - -c
    - shared_buffers=256MB
```

### Nginx Caching

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=100m;
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Vue.js Frontend |
| `/admin/` | Django Admin |
| `/api/v1/` | REST API |
| `/static/` | Django Static Files |
| `/uploads/` | User Uploads |
| `/health` | Health Check |
