# 🐳 JF-Manager Deployment with Portainer

Complete guide for deploying JF-Manager using Portainer.

## 📋 Prerequisites

- Portainer CE or Business Edition installed
- Docker Engine 20.10+
- At least 4GB RAM available
- 20GB+ disk space

**📦 Migrating from old setup?** See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) to preserve your existing database and uploads.

## 🚀 Quick Deployment

### Option 1: Deploy via Portainer Web UI (Recommended)

#### Step 1: Access Portainer
1. Open Portainer in your browser (e.g., `http://your-server:9000`)
2. Login to your Portainer instance
3. Select your Docker environment

#### Step 2: Create New Stack
1. Navigate to **Stacks** in the left sidebar
2. Click **+ Add stack**
3. Enter stack name: `jf-manager`

#### Step 3: Configure Stack

**Method A: Use Repository**
1. Select **Repository** as build method
2. Enter repository URL: `https://github.com/Jugendfeuerwehr-Manager/JF-Manager`
3. Reference: `refs/heads/main` or `refs/heads/nextgeneration-frontend`
4. Compose path: `portainer/docker-compose.portainer.yml`

**Method B: Upload / Paste Compose File**
1. Select **Web editor**
2. Copy content from `portainer/docker-compose.portainer.yml`
3. Paste into editor

#### Step 4: Configure Environment Variables

Click on **+ Add an environment variable** or use **Advanced mode**

Copy these variables from `portainer/stack.env.example` and set values:

```env
# Required Variables
POSTGRES_DB=jf_manager_backend
POSTGRES_USER=jf_manager
POSTGRES_PASSWORD=your_strong_password_here
DJANGO_SECRET_KEY=your_random_50_char_secret_here
DJANGO_ADMIN_PASSWORD=your_admin_password_here
DJANGO_ADMIN_EMAIL=admin@yourdomain.com
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
```

**Generate Strong Passwords** (run locally):
```bash
# PostgreSQL password
openssl rand -base64 32

# Django secret key
openssl rand -base64 50

# Admin password
openssl rand -base64 16
```

#### Step 5: Deploy
1. Click **Deploy the stack**
2. Wait for all containers to start (2-3 minutes)
3. Check container logs if any issues occur

### Option 2: Deploy via Portainer API

```bash
# Set your Portainer details
PORTAINER_URL="http://your-portainer:9000"
PORTAINER_TOKEN="your_api_token"
ENDPOINT_ID="1"

# Deploy stack
curl -X POST "${PORTAINER_URL}/api/stacks?type=2&method=repository&endpointId=${ENDPOINT_ID}" \
  -H "X-API-Key: ${PORTAINER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "jf-manager",
    "repositoryURL": "https://github.com/Jugendfeuerwehr-Manager/JF-Manager",
    "repositoryReferenceName": "refs/heads/main",
    "composeFile": "portainer/docker-compose.portainer.yml",
    "env": [
      {"name": "POSTGRES_PASSWORD", "value": "your_password"},
      {"name": "DJANGO_SECRET_KEY", "value": "your_secret"},
      {"name": "DJANGO_ADMIN_PASSWORD", "value": "your_admin_password"},
      {"name": "DJANGO_ADMIN_EMAIL", "value": "admin@yourdomain.com"},
      {"name": "ALLOWED_HOSTS", "value": "yourdomain.com"},
      {"name": "CSRF_TRUSTED_ORIGINS", "value": "https://yourdomain.com"}
    ]
  }'
```

## 🔍 Verify Deployment

### Check Container Status
1. In Portainer, navigate to **Stacks** → **jf-manager**
2. All containers should show as "running" and "healthy"
3. Expected containers:
   - `jf_manager_frontend` (healthy)
   - `jf_manager_backend` (healthy)
   - `jf_manager_db` (healthy)
   - `jf_manager_redis` (healthy)

### Access Application
- **Frontend**: `http://your-server/`
- **Django Admin**: `http://your-server/admin/`
- **API**: `http://your-server/api/v1/`
- **Health Check**: `http://your-server/health`

### View Logs
1. Click on container name in Portainer
2. Select **Logs** tab
3. Check for errors

## 🔧 Post-Deployment Configuration

### Create First Admin User

If admin user wasn't created automatically:

1. In Portainer, go to **Containers**
2. Click on `jf_manager_backend`
3. Select **Console** tab
4. Connect with `/bin/sh`
5. Run:
   ```bash
   python manage.py createsuperuser
   ```

### Configure SSL/TLS

#### Option 1: Use Reverse Proxy (Recommended)
Deploy a reverse proxy like Traefik or Nginx Proxy Manager in front of JF-Manager.

#### Option 2: Mount SSL Certificates
1. Create volume for SSL certificates:
   - Go to **Volumes** → **Add volume**
   - Name: `jf_manager_ssl`
   
2. Upload certificates to volume:
   ```bash
   # On Docker host
   docker volume create jf_manager_ssl
   docker run --rm -v jf_manager_ssl:/ssl -v $(pwd):/certs alpine \
     sh -c "cp /certs/cert.pem /certs/key.pem /ssl/"
   ```

3. Update stack:
   - Uncomment SSL volume mount in `docker-compose.portainer.yml`
   - Edit `frontend` container environment or mount custom nginx config

### Setup Automated Backups

#### Option 1: Portainer Scheduled Tasks (Business Edition)

1. Go to **Stacks** → **jf-manager**
2. Add scheduled task:
   - **Name**: Daily Backup
   - **Schedule**: `0 2 * * *` (2 AM daily)
   - **Command**:
     ```bash
     docker exec jf_manager_db sh -c 'PGPASSWORD=$POSTGRES_PASSWORD pg_dump -U $POSTGRES_USER -d $POSTGRES_DB | gzip > /backups/backup_$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz'
     ```

#### Option 2: Host Cron Job

Add to host crontab:
```bash
# Daily backup at 2 AM
0 2 * * * docker exec jf_manager_db sh -c 'PGPASSWORD=$POSTGRES_PASSWORD pg_dump -U $POSTGRES_USER -d $POSTGRES_DB | gzip > /backups/backup_$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz'

# Cleanup old backups (keep 7 days)
0 3 * * * docker exec jf_manager_db find /backups -name "backup_*.sql.gz" -mtime +7 -delete
```

#### Option 3: Backup Container

Add to stack:
```yaml
  backup:
    image: postgres:15-alpine
    container_name: jf_manager_backup
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - jf_manager_backups:/backups
    networks:
      - jf_manager_backend
    entrypoint: |
      sh -c 'while true; do
        PGPASSWORD=$$POSTGRES_PASSWORD pg_dump -h db -U $$POSTGRES_USER -d $$POSTGRES_DB | gzip > /backups/backup_$$(date +%Y%m%d_%H%M%S).sql.gz
        echo "Backup completed at $$(date)"
        sleep 86400
      done'
    restart: unless-stopped
    depends_on:
      - db
```

## 🔄 Updating the Application

### Via Portainer UI

1. Go to **Stacks** → **jf-manager**
2. Click **Editor** tab
3. Click **Pull and redeploy** or **Update the stack**
4. Portainer will pull latest images and redeploy

### Via Portainer Webhooks

1. Go to **Stacks** → **jf-manager** → **Webhooks**
2. Create webhook for stack update
3. Use webhook URL in CI/CD pipeline:
   ```bash
   curl -X POST "https://your-portainer/api/webhooks/your-webhook-id"
   ```

### Manual Update

```bash
# Pull latest images
docker pull ghcr.io/jugendfeuerwehr-manager/jf-manager/backend:latest
docker pull ghcr.io/jugendfeuerwehr-manager/jf-manager/frontend:latest

# In Portainer: Stacks → jf-manager → Update the stack
```

## 💾 Backup and Restore

### Create Manual Backup

1. In Portainer, go to **Containers** → `jf_manager_db`
2. Select **Console**, connect with `/bin/sh`
3. Run:
   ```bash
   pg_dump -U jf_manager -d jf_manager_backend | gzip > /backups/manual_backup_$(date +%Y%m%d).sql.gz
   ```

### Restore from Backup

1. Stop backend container:
   - Go to **Containers** → `jf_manager_backend` → **Stop**

2. Restore database:
   - Console into `jf_manager_db`
   - Run:
     ```bash
     dropdb -U jf_manager jf_manager_backend
     createdb -U jf_manager jf_manager_backend
     gunzip < /backups/your_backup.sql.gz | psql -U jf_manager -d jf_manager_backend
     ```

3. Start backend container:
   - **Containers** → `jf_manager_backend` → **Start**

### Export Backups from Volume

```bash
# On Docker host
docker run --rm -v jf_manager_backups:/backups -v $(pwd):/export alpine \
  sh -c "cp /backups/*.gz /export/"
```

## 📊 Monitoring

### Container Stats in Portainer

1. Navigate to **Containers**
2. View resource usage graphs for each container
3. Set up alerts in Portainer Business Edition

### Health Checks

All containers include health checks visible in Portainer:
- **Frontend**: HTTP check on `/health`
- **Backend**: HTTP check on `/health/`
- **Database**: `pg_isready` check
- **Redis**: `redis-cli ping` check

### Logs

View container logs in Portainer:
1. **Containers** → Select container → **Logs** tab
2. Enable **Auto-refresh** for real-time logs
3. Use **Search** to filter logs

## 🔐 Security Best Practices

### In Portainer

1. **Restrict Registry Access**
   - Use private registry if possible
   - Configure registry credentials in Portainer

2. **Enable Access Control**
   - Create separate user for JF-Manager management
   - Assign minimal required permissions

3. **Use Secrets** (Portainer Business)
   - Store sensitive variables as secrets
   - Reference in stack instead of plain text

4. **Enable Audit Logs**
   - Track all stack modifications
   - Review regularly

### In Application

1. **Change Default Passwords**
   - Set strong `POSTGRES_PASSWORD`
   - Set strong `DJANGO_ADMIN_PASSWORD`
   - Generate random `DJANGO_SECRET_KEY`

2. **Configure Domain**
   - Set `ALLOWED_HOSTS` to your domain only
   - Set `CSRF_TRUSTED_ORIGINS` with HTTPS URLs

3. **Enable HTTPS**
   - Use reverse proxy with SSL termination
   - Or mount SSL certificates directly

4. **Regular Updates**
   - Pull latest images monthly
   - Check for security updates

## 🚨 Troubleshooting

### Containers Won't Start

**Check logs in Portainer:**
1. **Containers** → Click failing container → **Logs**

**Common issues:**
- Database not ready: Wait for health check to pass
- Port conflicts: Change `HTTP_PORT` or `HTTPS_PORT`
- Volume permissions: Check volume ownership

### Can't Access Application

1. **Check container ports:**
   - Verify `HTTP_PORT` is correct
   - Check firewall allows traffic

2. **Check container health:**
   - All should show "healthy" in Portainer
   - If unhealthy, check logs

3. **Check environment variables:**
   - Verify `ALLOWED_HOSTS` includes your domain
   - Check `CSRF_TRUSTED_ORIGINS` for HTTPS URLs

### Database Connection Errors

1. **Check environment variables:**
   - `POSTGRES_PASSWORD` must match in all services
   - `DATABASE_URL` format is correct

2. **Check network:**
   - All containers in same network
   - Database container is running and healthy

### Backend Migrations Fail

1. **Console into backend container**
2. **Run manually:**
   ```bash
   python manage.py migrate --noinput
   ```
3. **Check logs** for specific errors

## 📚 Additional Resources

### Official Documentation
- [Portainer Documentation](https://docs.portainer.io/)
- [JF-Manager GitHub](https://github.com/Jugendfeuerwehr-Manager/JF-Manager)

### Related Files
- `../DEPLOYMENT.md` - General deployment guide
- `../PRODUCTION.md` - Production operations reference
- `../docker-compose.yml` - Standard Docker Compose file
- `stack.env.example` - Environment variables template

## 🆘 Getting Help

### Portainer Issues
- [Portainer Community Forums](https://community.portainer.io/)
- [Portainer Documentation](https://docs.portainer.io/)

### JF-Manager Issues
- [GitHub Issues](https://github.com/Jugendfeuerwehr-Manager/JF-Manager/issues)
- Check `DEPLOYMENT.md` for general troubleshooting

## 📝 Tips for Portainer Users

1. **Use Stack Environment Variables Editor**
   - Edit variables without modifying compose file
   - Easy to update secrets

2. **Enable Auto-Update** (Portainer Business)
   - Automatically pull and redeploy on new images
   - Set maintenance windows

3. **Use Templates**
   - Save JF-Manager as custom template
   - Quick deployment for multiple instances

4. **Enable Notifications**
   - Get alerts on container failures
   - Configure webhook integrations

5. **Backup Stack Configuration**
   - Export stack definition regularly
   - Store environment variables securely

---

**Ready to deploy!** Follow Step 1-5 above to get started. 🚀
