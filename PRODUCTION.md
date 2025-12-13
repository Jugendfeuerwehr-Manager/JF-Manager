# 🔐 Production Docker Setup - Quick Reference

## 🚀 Quick Start

```bash
# 1. Run automated setup
./setup.sh

# 2. Access your application
# Frontend: http://localhost
# Admin: http://localhost/admin
```

## 📋 What's Included

### Architecture
- **Frontend Container**: Nginx serving Vue.js SPA + reverse proxy
- **Backend Container**: Django REST API (uWSGI)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Backups**: Automated backup/restore system

### Security Features
- ✅ Multi-stage builds (minimal attack surface)
- ✅ Non-root containers
- ✅ Read-only root filesystems
- ✅ No new privileges
- ✅ Hardened Nginx configuration
- ✅ Security headers enabled

### File Structure
```
JF-Manager/
├── docker-compose.yml           # Production compose file
├── docker-compose.dev.yml       # Development override
├── .env.example                 # Environment template
├── Makefile                     # Management commands
├── setup.sh                     # Automated setup script
├── DEPLOYMENT.md                # Full deployment guide
├── backend/
│   ├── Dockerfile               # Multi-stage backend image
│   └── .dockerignore
├── frontend/
│   ├── Dockerfile               # Multi-stage frontend image
│   ├── nginx.conf               # Main Nginx config
│   ├── conf.d/
│   │   ├── default.conf         # Server blocks
│   │   └── locations/           # Modular location configs
│   │       ├── api.conf         # API proxy
│   │       ├── admin.conf       # Django admin proxy
│   │       ├── static.conf      # Static files
│   │       └── spa.conf         # Vue.js SPA
│   └── .dockerignore
├── scripts/
│   ├── backup.sh                # Backup script
│   └── restore.sh               # Restore script
├── nginx/ssl/                   # SSL certificates
└── backups/                     # Database backups
```

## 🎯 Common Operations

### Management Commands (Makefile)

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
make restore ARGS='./backups/backup_20251128.sql.gz'
make health            # Check service health
make ssl-cert          # Generate self-signed SSL cert
make shell-backend     # Access backend shell
make shell-frontend    # Access frontend shell
make shell-db          # Access database shell
make migrate           # Run Django migrations
make collectstatic     # Collect static files
make createsuperuser   # Create Django superuser
make update            # Update application
```

### Manual Docker Commands

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f [service_name]

# Stop services
docker-compose down

# Remove everything including volumes
docker-compose down -v
```

## 🔧 Configuration

### Environment Variables (.env)

**Required:**
```bash
POSTGRES_PASSWORD=your_strong_password
DJANGO_SECRET_KEY=your_random_50_char_key
DJANGO_ADMIN_PASSWORD=your_admin_password
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
```

**Optional:**
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

### SSL/TLS Setup

**Development (self-signed):**
```bash
make ssl-cert
```

**Production (Let's Encrypt):**
```bash
# 1. Install certbot
sudo apt-get install certbot

# 2. Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# 3. Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem

# 4. Enable HTTPS in frontend/conf.d/default.conf
# Uncomment the HTTPS server block

# 5. Restart
make restart
```

## 💾 Backup & Restore

### Automated Backups

Backups are organized in tiers:
- **Daily**: Last 7 days
- **Weekly**: Last 4 weeks (created on Sundays)
- **Monthly**: Last 6 months (created on 1st)

**Schedule with cron:**
```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/JF-Manager && make backup
```

### Manual Backup
```bash
make backup
```

### Restore from Backup
```bash
# List available backups
ls -lh backups/*.sql.gz

# Restore specific backup
make restore ARGS='./backups/backup_20251128_120000.sql.gz'
```

## 🏥 Health Checks

All services have health checks:
- **Frontend**: `wget http://localhost/health`
- **Backend**: `curl http://localhost/api/v1/`
- **Database**: `pg_isready`
- **Redis**: `redis-cli ping`

Check all health statuses:
```bash
make health
```

## 🔍 Monitoring

### View Resource Usage
```bash
# Container stats
docker stats

# Disk usage
docker system df
```

### Access Logs
```bash
# All services
make logs

# Specific service
make logs ARGS='backend'
make logs ARGS='frontend'
make logs ARGS='db'
```

## 🛡️ Security Checklist

- [ ] Strong passwords in `.env`
- [ ] `DEBUG=False` in production
- [ ] Correct `ALLOWED_HOSTS`
- [ ] SSL/TLS certificates configured
- [ ] Firewall configured (ports 80, 443)
- [ ] Automated backups scheduled
- [ ] Backup restoration tested
- [ ] `.env` file permissions: `chmod 600 .env`
- [ ] Regular security updates

## 🚨 Troubleshooting

### Services won't start
```bash
# Check logs
make logs

# Verify configuration
docker-compose config

# Check ports
sudo lsof -i :80
sudo lsof -i :443
```

### Database connection issues
```bash
# Check database health
docker-compose exec db pg_isready -U jf_manager

# Test connection
make shell-db
```

### Frontend can't reach backend
```bash
# Test network connectivity
docker-compose exec frontend ping backend

# Check backend is running
docker-compose exec frontend curl http://backend:8000/health/
```

### Static files not loading
```bash
make collectstatic
```

## 📚 Additional Documentation

- **Full Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **API Documentation**: [backend/API_DOCUMENTATION_ENHANCED.md](backend/API_DOCUMENTATION_ENHANCED.md)
- **Main README**: [README.md](README.md)

## 🔄 Development vs Production

### Production (default)
```bash
docker-compose up -d
```

### Development
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Or use the development script:
```bash
./start-dev.sh
```

## 📊 Performance Tuning

### PostgreSQL
Edit `docker-compose.yml`:
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
Add to `frontend/nginx.conf`:
```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;
```

## 🌐 Endpoints

After deployment, these endpoints are available:

- **Frontend SPA**: `http://localhost/`
- **Django Admin**: `http://localhost/admin/`
- **REST API**: `http://localhost/api/v1/`
- **Static Files**: `http://localhost/static/`
- **Uploads**: `http://localhost/uploads/`
- **Health Check**: `http://localhost/health`

## 💡 Tips

1. **Always test backups**: Regularly test restoration in a dev environment
2. **Monitor disk space**: Backups and uploads can grow quickly
3. **Update regularly**: Keep base images and dependencies updated
4. **Use strong passwords**: Generate with `openssl rand -base64 32`
5. **Enable HTTPS**: Always use SSL/TLS in production
6. **Set up monitoring**: Use tools like Prometheus or Grafana
7. **Review logs**: Regularly check for errors and warnings

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Jugendfeuerwehr-Manager/JF-Manager/issues)
- **Documentation**: Check repo docs

---

**Quick Setup**: `./setup.sh`  
**All Commands**: `make help`  
**Full Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
