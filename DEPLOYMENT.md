# JF-Manager Production Deployment Guide

## Overview

This guide covers deploying JF-Manager in a production environment using Docker Compose with:
- Multi-stage Docker builds for minimal image sizes
- Nginx reverse proxy for the frontend
- Secure, non-root containers
- Automated backup/restore functionality
- SSL/TLS support

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Nginx (Frontend)                     │
│  - Serves Vue.js SPA                                     │
│  - Proxies /api/* to Backend                            │
│  - Proxies /admin/* to Backend                          │
│  - Serves /static/* and /uploads/*                      │
└─────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼────┐      ┌────▼────┐    ┌─────▼─────┐
    │  Backend │      │   DB    │    │   Redis   │
    │ (Django) │◄─────┤(Postgres)    │           │
    └──────────┘      └─────────┘    └───────────┘
```

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM
- 20GB disk space

## Quick Start

### 1. Initial Setup

```bash
# Clone the repository
git clone https://github.com/Jugendfeuerwehr-Manager/JF-Manager.git
cd JF-Manager

# Copy environment file and configure
cp .env.example .env
nano .env  # Edit configuration

# Generate strong passwords
openssl rand -base64 32  # For POSTGRES_PASSWORD
openssl rand -base64 50  # For DJANGO_SECRET_KEY
```

### 2. Configure Environment Variables

Edit `.env` and set at minimum:

```bash
POSTGRES_PASSWORD=your_strong_password_here
DJANGO_SECRET_KEY=your_random_secret_key_here
DJANGO_ADMIN_PASSWORD=your_admin_password_here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
```

### 3. Build and Start Services

```bash
# Build images
make build

# Start all services
make up

# Check status
make ps
make health
```

The application will be available at:
- Frontend: http://localhost
- Django Admin: http://localhost/admin
- API: http://localhost/api/v1/

## SSL/TLS Configuration

### Development (Self-Signed Certificate)

```bash
# Generate self-signed certificate
make ssl-cert

# Edit frontend/conf.d/default.conf
# Uncomment the HTTPS server block
```

### Production (Let's Encrypt)

```bash
# 1. Install certbot
sudo apt-get install certbot

# 2. Generate certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# 3. Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem

# 4. Enable HTTPS in frontend/conf.d/default.conf
# Uncomment the HTTPS server block and HTTP redirect

# 5. Restart services
make restart
```

### Auto-renewal with Cron

```bash
# Add to crontab
0 0 * * * certbot renew --quiet --post-hook "docker-compose restart frontend"
```

## Backup and Restore

### Automated Backups

The backup system runs automatically and keeps:
- Daily backups for 7 days
- Weekly backups for 4 weeks
- Monthly backups for 6 months

```bash
# Manual backup
make backup

# Backups are stored in ./backups/
```

### Restore from Backup

```bash
# List available backups
ls -lh backups/*.sql.gz

# Restore specific backup
make restore ARGS='./backups/backup_20251128_120000.sql.gz'

# Or restore interactively
docker-compose run --rm backup sh /restore.sh
```

### Schedule Automated Backups

Add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/JF-Manager && docker-compose run --rm backup
```

## Maintenance

### View Logs

```bash
# All services
make logs

# Specific service
make logs ARGS='backend'
make logs ARGS='frontend'
```

### Update Application

```bash
# Pull latest code and update
make update

# Or manually
git pull
make build
make restart
```

### Database Operations

```bash
# Run migrations
make migrate

# Access database shell
make shell-db

# Create superuser
make createsuperuser
```

### Container Shell Access

```bash
# Backend container
make shell-backend

# Frontend container
make shell-frontend
```

## Production Checklist

- [ ] Strong passwords in `.env`
- [ ] `DEBUG=False` in `.env`
- [ ] Correct `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
- [ ] SSL/TLS certificates configured
- [ ] Email configuration for notifications
- [ ] Automated backups scheduled
- [ ] Firewall configured (ports 80, 443 only)
- [ ] Regular security updates scheduled
- [ ] Monitoring configured
- [ ] Backup restoration tested

## Security Best Practices

### 1. Environment Security

```bash
# Secure .env file
chmod 600 .env

# Never commit .env to git
echo ".env" >> .gitignore
```

### 2. Container Security

All containers run as non-root users:
- Backend: `django` user (UID 1000)
- Frontend: `nginx` user (UID 101)
- Read-only root filesystems where possible
- No new privileges allowed

### 3. Network Security

```bash
# Use firewall to restrict access
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Consider using fail2ban
sudo apt-get install fail2ban
```

### 4. Regular Updates

```bash
# Update base images regularly
docker-compose pull
make build
make restart
```

## Monitoring

### Health Checks

```bash
# Check all services
make health

# Individual health endpoints
curl http://localhost/health        # Frontend
curl http://localhost/api/v1/       # Backend API
```

### Resource Usage

```bash
# Container resource usage
docker stats

# Disk usage
docker system df
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
make logs

# Verify environment variables
docker-compose config

# Check port conflicts
sudo lsof -i :80
sudo lsof -i :443
```

### Database Connection Issues

```bash
# Check database health
docker-compose exec db pg_isready -U jf_manager

# Verify credentials
docker-compose exec db psql -U jf_manager -d jf_manager_backend -c "SELECT version();"
```

### Static Files Not Loading

```bash
# Collect static files
make collectstatic

# Check permissions
docker-compose exec backend ls -la /static/
```

### Frontend Can't Reach Backend

```bash
# Check network connectivity
docker-compose exec frontend ping backend

# Verify backend is running
docker-compose exec frontend curl http://backend:8000/health/
```

## Performance Tuning

### Database Optimization

```bash
# Tune PostgreSQL settings in docker-compose.yml
services:
  db:
    environment:
      POSTGRES_INITDB_ARGS: "-E UTF8 --locale=en_US.UTF-8"
    command: 
      - postgres
      - -c
      - max_connections=200
      - -c
      - shared_buffers=256MB
```

### Nginx Caching

Edit `frontend/nginx.conf` to add caching:

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=100m;
```

## Scaling

### Horizontal Scaling

```bash
# Scale backend workers
docker-compose up -d --scale backend=3

# Update nginx upstream in frontend/conf.d/locations/api.conf
```

### Load Balancing

Consider using:
- Nginx as load balancer
- HAProxy
- Cloud provider load balancers

## Support

For issues and questions:
- GitHub Issues: https://github.com/Jugendfeuerwehr-Manager/JF-Manager/issues
- Documentation: Check README.md and other docs in the repository

## License

See LICENSE file in the repository.
