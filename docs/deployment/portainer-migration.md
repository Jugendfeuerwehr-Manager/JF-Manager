# Portainer Migration Guide

Migrate from your old Portainer deployment to the new Docker architecture while **preserving all your data**.

## Prerequisites

- Existing data in `/volume1/docker/JFManager/database` (PostgreSQL) and `/volume1/docker/JFManager/uploads`
- Access to Portainer web interface
- SSH access to your NAS (optional, for verification)

## Step 1: Backup Your Data

```bash
ssh your-username@your-nas-ip
cd /volume1/docker/JFManager

# Backup database
sudo docker exec jf_manager_db pg_dump -U postgres jf_manager > backup_$(date +%Y%m%d).sql

# Backup uploads
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/
```

## Step 2: Stop and Remove Old Stack

In Portainer:
1. **Stacks** → Find your old JF-Manager stack
2. Click **Stop** → Click **Remove**

This removes containers only — your data directories are untouched.

## Step 3: Prepare Directories

```bash
cd /volume1/docker/JFManager
mkdir -p database static uploads backups

# Set permissions
sudo chown -R 999:999 database          # PostgreSQL UID
sudo chown -R 1000:1000 static uploads backups  # Django UID
```

## Step 4: Deploy New Stack

### Method A: Web Editor (Recommended)

1. **Stacks** → **Add stack** → Name: `jf-manager`
2. Choose **Web editor**
3. Paste contents of `portainer/docker-compose.portainer-synology.yml`
4. Verify volume `device:` paths match your actual paths

### Method B: Repository

1. **Stacks** → **Add stack** → Name: `jf-manager`
2. Choose **Repository**
3. URL: `https://github.com/Jugendfeuerwehr-Manager/JF-Manager`
4. Reference: `nextgeneration-frontend`
5. Compose path: `portainer/docker-compose.portainer-synology.yml`

## Step 5: Configure Environment Variables

```env
# ⚠️ Use your OLD PostgreSQL password!
POSTGRES_DB=jf_manager
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_existing_password

DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_ADMIN_EMAIL=admin@example.com
DJANGO_ADMIN_PASSWORD=secure-admin-password
ALLOWED_HOSTS=your-domain.com,192.168.1.100
CSRF_TRUSTED_ORIGINS=https://your-domain.com,http://192.168.1.100

DEFAULT_FROM_EMAIL=noreply@your-domain.com
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_TLS=True

DEBUG=False
DJANGO_MANAGEPY_MIGRATE=on
```

## Step 6: Deploy and Verify

1. Click **Deploy the stack**
2. Wait for all containers to start

### Verify Database

Portainer → Containers → `jf_manager_backend` → Console → `/bin/sh`:

```bash
python manage.py showmigrations
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.count()  # Should show your existing users
```

### Verify Uploads

```bash
docker exec jf_manager_backend ls -la /uploads
```

### Verify Application

1. Open `http://your-nas-ip`
2. Login with existing credentials
3. Check: members, orders, uploads, inventory, service books

## Step 7: Run Migrations (if needed)

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

## Troubleshooting

### Database Connection Failed

- Check PostgreSQL password matches your old setup
- Verify permissions: `ls -la /volume1/docker/JFManager/database`
- Check DB logs in Portainer

### Uploads Not Visible

```bash
sudo chown -R 1000:1000 /volume1/docker/JFManager/uploads
```

### Permission Denied Errors

```bash
sudo chown -R 999:999 /volume1/docker/JFManager/database
sudo chown -R 1000:1000 /volume1/docker/JFManager/static
sudo chown -R 1000:1000 /volume1/docker/JFManager/uploads
sudo chown -R 1000:1000 /volume1/docker/JFManager/backups
```

### Containers Restart Loop

1. Check logs in Portainer → Containers → select container → Logs
2. Verify all environment variables
3. `docker inspect jf_manager_backend | grep Health -A 20`

## Rollback

If migration fails:

1. Stop new stack in Portainer
2. Redeploy old stack configuration
3. Data is unchanged in `/volume1/docker/JFManager/`

Or restore from backup:

```bash
docker exec -i jf_manager_db psql -U postgres jf_manager < backup_YYYYMMDD.sql
tar -xzf uploads_backup_YYYYMMDD.tar.gz -C /volume1/docker/JFManager/
```

## Post-Migration Checklist

- [ ] All users can login
- [ ] All members data visible
- [ ] Orders accessible
- [ ] Uploaded files display correctly
- [ ] Inventory system works
- [ ] Service books intact
- [ ] Email notifications work
- [ ] Backups configured
- [ ] SSL certificates configured
- [ ] Old stack removed from Portainer

## Path Customization

If your data is not in `/volume1/docker/JFManager/`, update the volume paths in `docker-compose.portainer-synology.yml`:

```yaml
volumes:
  jf_manager_database:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /your/actual/path/database
```
