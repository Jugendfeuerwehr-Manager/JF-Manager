# 🚀 JF-Manager Portainer - 5 Minute Quick Start

Deploy JF-Manager in Portainer in just 5 minutes!

## Step 1: Open Portainer (30 seconds)

1. Go to your Portainer URL (e.g., `http://your-server:9000`)
2. Login
3. Select your Docker environment
4. Click **Stacks** in left sidebar
5. Click **+ Add stack**
6. Name it: `jf-manager`

## Step 2: Add Compose File (1 minute)

Choose one method:

### Method A: Git Repository (Recommended)
1. Select **Repository**
2. Repository URL: `https://github.com/Jugendfeuerwehr-Manager/JF-Manager`
3. Reference: `refs/heads/main`
4. Compose path: `portainer/docker-compose.portainer.yml`

### Method B: Web Editor
1. Select **Web editor**
2. Copy content from `docker-compose.portainer.yml` file
3. Paste into editor

## Step 3: Set Environment Variables (2 minutes)

Click **+ Add environment variable** for each:

### Required (Must Change!)
```
POSTGRES_PASSWORD = [Generate: openssl rand -base64 32]
DJANGO_SECRET_KEY = [Generate: openssl rand -base64 50]
DJANGO_ADMIN_PASSWORD = [Generate: openssl rand -base64 16]
DJANGO_ADMIN_EMAIL = admin@yourdomain.com
ALLOWED_HOSTS = yourdomain.com,localhost
CSRF_TRUSTED_ORIGINS = https://yourdomain.com,http://localhost
```

### Pre-filled (Can keep defaults)
```
POSTGRES_DB = jf_manager_backend
POSTGRES_USER = jf_manager
DJANGO_MANAGEPY_MIGRATE = on
DEBUG = False
DEFAULT_FROM_EMAIL = noreply@yourdomain.com
```

### Optional (Add if needed)
```
EMAIL_HOST = smtp.gmail.com
EMAIL_PORT = 587
EMAIL_HOST_USER = your-email@gmail.com
EMAIL_HOST_PASSWORD = your-app-password
EMAIL_USE_TLS = True
HTTP_PORT = 80
HTTPS_PORT = 443
```

**Quick Password Generation** (run on your computer):
```bash
openssl rand -base64 32  # For POSTGRES_PASSWORD
openssl rand -base64 50  # For DJANGO_SECRET_KEY
openssl rand -base64 16  # For DJANGO_ADMIN_PASSWORD
```

## Step 4: Deploy! (30 seconds)

1. Click **Deploy the stack**
2. Wait 2-3 minutes for containers to start
3. Check all containers are "healthy" (green dot)

## Step 5: Access Your App (30 seconds)

Open in browser:
- **Frontend**: `http://your-server/`
- **Admin Panel**: `http://your-server/admin/`
- **Health Check**: `http://your-server/health`

Login to admin with:
- **Username**: admin
- **Password**: [Your DJANGO_ADMIN_PASSWORD]

## ✅ That's It!

Your JF-Manager is now running!

## 🔄 Quick Operations

### View Logs
Portainer → Containers → Click container → Logs tab

### Update Application
Portainer → Stacks → jf-manager → Pull and redeploy

### Backup Database
Portainer → Containers → jf_manager_db → Console:
```bash
pg_dump -U jf_manager -d jf_manager_backend | gzip > /backups/backup_$(date +%Y%m%d).sql.gz
```

### Check Health
All containers should show "healthy" status in Portainer

## 🆘 Troubleshooting

**Containers not starting?**
- Check logs in Portainer
- Verify environment variables are set
- Wait for database health check (30 seconds)

**Can't access application?**
- Check firewall allows port 80/443
- Verify `ALLOWED_HOSTS` includes your domain or server IP
- Add your IP to `ALLOWED_HOSTS` if needed

**502 Bad Gateway?**
- Wait for backend to become healthy (check in Portainer)
- Usually takes 30-60 seconds after start

## 📖 Full Documentation

For advanced configuration, see:
- `portainer/README.md` - Complete Portainer guide
- `../DEPLOYMENT.md` - General deployment docs
- `../PRODUCTION.md` - Operations reference

---

**Need help?** Check the full `README.md` in the portainer folder!
