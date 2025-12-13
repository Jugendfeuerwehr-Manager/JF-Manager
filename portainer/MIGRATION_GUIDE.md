# Migration Guide: Existing Portainer Setup to New Docker Architecture

This guide helps you migrate from your old Portainer deployment to the new redesigned Docker setup while **preserving all your data** (database and uploads).

## Prerequisites

- ✅ Your existing data in `/volume1/docker/JFManager/database` (PostgreSQL data)
- ✅ Your existing data in `/volume1/docker/JFManager/uploads` (uploaded files)
- ✅ Access to Portainer web interface
- ✅ SSH access to your NAS (optional, for verification)

## Migration Strategy

The new setup uses bind mounts to the **same directories** as your old setup, so your data will be preserved automatically.

## Step 1: Backup Your Data (Recommended)

Even though we're using the same directories, always backup before migration:

```bash
# SSH into your NAS
cd /volume1/docker/JFManager

# Backup database
sudo docker exec jf_manager_db pg_dump -U postgres jf_manager > backup_$(date +%Y%m%d).sql

# Backup uploads
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/
```

## Step 2: Stop and Remove Old Stack

In Portainer:

1. Go to **Stacks**
2. Find your old JF-Manager stack
3. Click **Stop** (this stops all containers)
4. Click **Remove** (this removes containers, but **NOT** your data directories)

**Important**: This does NOT delete your data in `/volume1/docker/JFManager/` - only the containers are removed.

## Step 3: Prepare Directories

Ensure all required directories exist on your NAS:

```bash
# SSH into your NAS
cd /volume1/docker/JFManager

# Create missing directories if needed
mkdir -p database static uploads backups

# Set correct permissions (adjust UID/GID if needed)
# PostgreSQL runs as UID 999, Django/Nginx as UID 1000
sudo chown -R 999:999 database
sudo chown -R 1000:1000 static uploads backups
```

## Step 4: Deploy New Stack in Portainer

### Method A: Web Editor (Recommended)

1. Go to **Stacks** → **Add stack**
2. Name: `jf-manager` (or your preferred name)
3. Choose **Web editor**
4. Copy the contents of `portainer/docker-compose.portainer-synology.yml` into the editor
5. **Important**: Verify the `device:` paths match your actual paths:
   ```yaml
   volumes:
     jf_manager_database:
       driver: local
       driver_opts:
         type: none
         o: bind
         device: /volume1/docker/JFManager/database  # ← Verify this path
   ```

### Method B: Repository (Alternative)

1. Go to **Stacks** → **Add stack**
2. Name: `jf-manager`
3. Choose **Repository**
4. Repository URL: `https://github.com/Jugendfeuerwehr-Manager/JF-Manager`
5. Repository reference: `nextgeneration-frontend`
6. Compose path: `portainer/docker-compose.portainer-synology.yml`

## Step 5: Configure Environment Variables

In the **Environment variables** section, set:

### Required Variables

```env
# Database Configuration
POSTGRES_DB=jf_manager
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_existing_password  # ⚠️ USE YOUR OLD PASSWORD!

# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_ADMIN_EMAIL=admin@example.com
DJANGO_ADMIN_PASSWORD=secure-admin-password
ALLOWED_HOSTS=your-domain.com,192.168.1.100
CSRF_TRUSTED_ORIGINS=https://your-domain.com,http://192.168.1.100

# Email Configuration
DEFAULT_FROM_EMAIL=noreply@your-domain.com
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_TLS=True

# Optional Settings
DEBUG=False
DJANGO_MANAGEPY_MIGRATE=on
HTTP_PORT=80
HTTPS_PORT=443
```

**⚠️ CRITICAL**: Use the **same PostgreSQL password** as your old setup! Otherwise, the database won't be accessible.

## Step 6: Deploy

1. Click **Deploy the stack**
2. Wait for all containers to start (check **Containers** view)
3. Monitor logs for any errors

## Step 7: Verify Migration

### Check Database Connection

In Portainer → Containers → `jf_manager_backend` → **Console** → `/bin/sh`:

```bash
# Check if database is accessible
python manage.py showmigrations

# Check if your data is present
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.count()  # Should show your existing users
>>> exit()
```

### Check Uploads

In Portainer → Containers → `jf_manager_frontend` → **Console** → `/bin/sh`:

```bash
# List uploads directory
ls -la /uploads

# Check if your files are there
du -sh /uploads
```

### Access Application

1. Open browser: `http://your-nas-ip`
2. Login with your existing credentials
3. Verify:
   - ✅ All members are present
   - ✅ All orders are visible
   - ✅ Uploaded files are accessible
   - ✅ All data looks correct

## Step 8: Run Migrations (if needed)

The new version might have schema updates:

In Portainer → Containers → `jf_manager_backend` → **Console** → `/bin/sh`:

```bash
# Apply any new migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput
```

## Troubleshooting

### Database Connection Failed

**Symptom**: Backend shows `could not connect to database`

**Solution**:
1. Check PostgreSQL password matches your old setup
2. Verify database directory permissions: `ls -la /volume1/docker/JFManager/database`
3. Check database logs: Portainer → Containers → `jf_manager_db` → **Logs**

### Uploads Not Visible

**Symptom**: Previously uploaded files return 404

**Solution**:
1. Verify uploads directory permissions: `sudo chown -R 1000:1000 /volume1/docker/JFManager/uploads`
2. Check uploads are mounted: `docker exec jf_manager_backend ls -la /uploads`
3. Check nginx logs: `docker logs jf_manager_frontend`

### Permission Denied Errors

**Symptom**: Backend or database can't write to directories

**Solution**:
```bash
# Fix database permissions (PostgreSQL UID 999)
sudo chown -R 999:999 /volume1/docker/JFManager/database

# Fix uploads/static permissions (Django UID 1000)
sudo chown -R 1000:1000 /volume1/docker/JFManager/static
sudo chown -R 1000:1000 /volume1/docker/JFManager/uploads
sudo chown -R 1000:1000 /volume1/docker/JFManager/backups
```

### Containers Restart Loop

**Symptom**: Containers keep restarting

**Solution**:
1. Check logs for specific error: Portainer → Containers → select container → **Logs**
2. Verify all environment variables are set correctly
3. Check healthcheck status: `docker inspect jf_manager_backend | grep Health -A 20`

## Rollback Plan

If migration fails, restore your old setup:

### Option 1: Quick Rollback

1. Stop new stack in Portainer
2. Redeploy old stack configuration
3. Your data is unchanged in `/volume1/docker/JFManager/`

### Option 2: Restore from Backup

```bash
# Stop all containers
docker stop jf_manager_db jf_manager_backend jf_manager_frontend jf_manager_redis

# Restore database backup
docker exec -i jf_manager_db psql -U postgres jf_manager < backup_20250113.sql

# Restore uploads
tar -xzf uploads_backup_20250113.tar.gz -C /volume1/docker/JFManager/
```

## Post-Migration Checklist

- [ ] All users can login
- [ ] All members data is visible
- [ ] All orders are accessible
- [ ] Uploaded files display correctly
- [ ] Inventory system works
- [ ] Service books are intact
- [ ] Email notifications work
- [ ] Backups are configured (see `portainer/README.md` Backup section)
- [ ] SSL certificates configured (if using HTTPS)
- [ ] Old stack removed from Portainer
- [ ] Backup files secured offsite

## Path Customization

If your data is **NOT** in `/volume1/docker/JFManager/`, update the volume paths in `docker-compose.portainer-synology.yml`:

```yaml
volumes:
  jf_manager_database:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /your/actual/path/database  # ← Change this

  jf_manager_uploads:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /your/actual/path/uploads  # ← Change this
```

## New Features in Redesigned Setup

After migration, you'll have access to:

- ✨ **Health checks**: Automatic container health monitoring
- ✨ **Automated backups**: PostgreSQL backup system (see README.md)
- ✨ **Resource limits**: Memory limits prevent container bloat
- ✨ **Log rotation**: Automatic log management (10MB max per file)
- ✨ **Security hardening**: No-new-privileges, read-only volumes where possible
- ✨ **Optimized images**: Multi-stage builds reduce image size
- ✨ **Better caching**: Static files cached for 30 days, uploads for 7 days

## Need Help?

- **Documentation**: See `portainer/README.md` for detailed Portainer usage
- **Quick Start**: See `portainer/QUICK_START.md` for basic deployment
- **General Setup**: See `DEPLOYMENT.md` for architecture overview
- **GitHub Issues**: https://github.com/Jugendfeuerwehr-Manager/JF-Manager/issues

---

**Last Updated**: December 2025  
**Version**: Docker Redesign v2.0
