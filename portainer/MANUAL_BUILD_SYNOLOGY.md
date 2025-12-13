# Manual Docker Build on Synology NAS

If Portainer cannot build from Git URLs (no Git installed), you need to build the images manually via SSH.

## Prerequisites

- SSH access to your Synology NAS
- Docker installed on Synology
- Sufficient disk space (~2GB for builds)

## Option 1: Build Directly on NAS

### Step 1: SSH into Your NAS

```bash
ssh your-username@your-nas-ip
```

### Step 2: Clone Repository

```bash
# Create workspace directory
mkdir -p /volume1/docker/builds
cd /volume1/docker/builds

# Clone repository (install git if needed: sudo apt-get install git)
git clone https://github.com/Jugendfeuerwehr-Manager/JF-Manager.git
cd JF-Manager
git checkout nextgeneration-frontend
```

### Step 3: Build Backend Image

```bash
cd backend
docker build -t jf_manager_backend:latest .
cd ..
```

This takes ~5-10 minutes.

### Step 4: Build Frontend Image

```bash
cd frontend
docker build -t jf_manager_frontend:latest .
cd ..
```

This takes ~5-10 minutes.

### Step 5: Verify Images

```bash
docker images | grep jf_manager
```

You should see:
```
jf_manager_backend   latest   ...   ~350MB
jf_manager_frontend  latest   ...   ~50MB
```

### Step 6: Update Portainer Stack

In Portainer, use this compose file with local images:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    # ... (same as before)

  redis:
    image: redis:7-alpine
    # ... (same as before)

  backend:
    image: jf_manager_backend:latest  # ← Uses local image
    container_name: jf_manager_backend
    # ... (rest of config)

  frontend:
    image: jf_manager_frontend:latest  # ← Uses local image
    container_name: jf_manager_frontend
    # ... (rest of config)
```

## Option 2: Build on Your PC and Transfer

If your NAS doesn't have enough resources or Git:

### Step 1: Build on Your Local Machine

```bash
# Clone repository
git clone https://github.com/Jugendfeuerwehr-Manager/JF-Manager.git
cd JF-Manager
git checkout nextgeneration-frontend

# Build images
docker build -t jf_manager_backend:latest backend/
docker build -t jf_manager_frontend:latest frontend/

# Save images to tar files
docker save jf_manager_backend:latest | gzip > jf_manager_backend.tar.gz
docker save jf_manager_frontend:latest | gzip > jf_manager_frontend.tar.gz
```

### Step 2: Transfer to NAS

```bash
# Using SCP
scp jf_manager_backend.tar.gz your-username@your-nas-ip:/volume1/docker/images/
scp jf_manager_frontend.tar.gz your-username@your-nas-ip:/volume1/docker/images/
```

### Step 3: Load Images on NAS

```bash
# SSH into NAS
ssh your-username@your-nas-ip

# Load images
cd /volume1/docker/images
docker load < jf_manager_backend.tar.gz
docker load < jf_manager_frontend.tar.gz

# Verify
docker images | grep jf_manager
```

## Option 3: Wait for GitHub Actions (Recommended)

The GitHub Actions workflow is building the images automatically. Check status:

https://github.com/Jugendfeuerwehr-Manager/JF-Manager/actions

Once successful, images will be available at:
- `ghcr.io/jugendfeuerwehr-manager/jf-manager/backend:nextgeneration-frontend`
- `ghcr.io/jugendfeuerwehr-manager/jf-manager/frontend:nextgeneration-frontend`

Then use the original `docker-compose.portainer-synology.yml` with these images:

```yaml
backend:
  image: ghcr.io/jugendfeuerwehr-manager/jf-manager/backend:nextgeneration-frontend
  # ...

frontend:
  image: ghcr.io/jugendfeuerwehr-manager/jf-manager/frontend:nextgeneration-frontend
  # ...
```

## Troubleshooting

### Git Not Found on Synology

Install Git via Package Center or manually:

```bash
# For DSM 7.x
sudo apt-get update
sudo apt-get install git
```

Or use Synology Package Center → Developer Tools → Git Server

### Out of Disk Space During Build

Check available space:
```bash
df -h /volume1
```

Clean up Docker:
```bash
docker system prune -a
```

### Build Fails on Synology (Low Memory)

If your NAS has limited RAM, build on your PC (Option 2) instead.

### Permission Denied Errors

Run docker commands with sudo:
```bash
sudo docker build -t jf_manager_backend:latest backend/
```

Or add your user to docker group:
```bash
sudo synogroup --add docker your-username
```

## After Successful Build

1. Go to Portainer → Stacks → Your JF-Manager stack
2. Update the compose file to use local images (`jf_manager_backend:latest`, `jf_manager_frontend:latest`)
3. Configure environment variables
4. Deploy stack

The local images will be used, and your data in `/volume1/docker/JFManager/` will be preserved!

---

**Tip**: Once GitHub Actions completes, you can switch to using GHCR images and delete the local build artifacts to free up space.
