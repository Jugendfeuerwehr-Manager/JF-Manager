# Portainer Deployment

## Prerequisites

- Portainer CE or Business Edition installed
- Docker Engine 20.10+
- At least 4GB RAM, 20GB+ disk space

> **Migrating from an old setup?** See [Portainer Migration](portainer-migration.md) to preserve your existing database and uploads.

## Quick Start (5 Minutes)

### Step 1: Create Stack

1. Open Portainer → Select your Docker environment
2. **Stacks** → **+ Add stack**
3. Name: `jf-manager`

### Step 2: Add Compose File

**Option A: Git Repository (Recommended)**
1. Select **Repository**
2. Repository URL: `https://github.com/Jugendfeuerwehr-Manager/JF-Manager`
3. Reference: `refs/heads/main`
4. Compose path: `portainer/docker-compose.portainer.yml`

**Option B: Web Editor**
1. Select **Web editor**
2. Copy content from `portainer/docker-compose.portainer.yml`

### Step 3: Set Environment Variables

Click **+ Add environment variable** for each:

**Required (must change):**

```
POSTGRES_PASSWORD     = [openssl rand -base64 32]
DJANGO_SECRET_KEY     = [openssl rand -base64 50]
DJANGO_ADMIN_PASSWORD = [openssl rand -base64 16]
DJANGO_ADMIN_EMAIL    = admin@yourdomain.com
ALLOWED_HOSTS         = yourdomain.com,localhost
CSRF_TRUSTED_ORIGINS  = https://yourdomain.com,http://localhost
```

**Pre-filled defaults:**

```
POSTGRES_DB              = jf_manager_backend
POSTGRES_USER            = jf_manager
DJANGO_MANAGEPY_MIGRATE  = on
DEBUG                    = False
DEFAULT_FROM_EMAIL       = noreply@yourdomain.com
```

**Optional:**

```
EMAIL_HOST          = smtp.gmail.com
EMAIL_PORT          = 587
EMAIL_HOST_USER     = your-email@gmail.com
EMAIL_HOST_PASSWORD = your-app-password
EMAIL_USE_TLS       = True
HTTP_PORT           = 80
HTTPS_PORT          = 443
```

### Step 4: Deploy

1. Click **Deploy the stack**
2. Wait 2-3 minutes for containers to start
3. Verify all containers show "healthy" (green dot)

### Step 5: Access

- **Frontend**: `http://your-server/`
- **Admin Panel**: `http://your-server/admin/`
- **Health Check**: `http://your-server/health`

Login with username `admin` and your `DJANGO_ADMIN_PASSWORD`.

## Deploy via Portainer API

```bash
PORTAINER_URL="http://your-portainer:9000"
PORTAINER_TOKEN="your_api_token"
ENDPOINT_ID="1"

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

## Quick Operations

| Action | How |
|--------|-----|
| View Logs | Portainer → Containers → Click container → Logs |
| Update | Portainer → Stacks → jf-manager → Pull and redeploy |
| Backup DB | Portainer → Containers → db → Console → `pg_dump` |
| Shell Access | Portainer → Containers → backend → Console |

## Compose File Variants

| File | Use Case |
|------|----------|
| `docker-compose.portainer.yml` | Standard Portainer deployment |
| `docker-compose.portainer-synology.yml` | Synology NAS with bind mounts |
| `docker-compose.portainer-build.yml` | Build from source |
| `docker-compose.portainer-build-synology.yml` | Synology + build from source |
| `docker-compose.portainer-local-images.yml` | Pre-built local images |
