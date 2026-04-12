# Synology NAS Docker Build

If Portainer cannot build from Git URLs (no Git installed), build images manually via SSH.

## Option 1: Build Directly on NAS

```bash
ssh your-username@your-nas-ip

mkdir -p /volume1/docker/builds
cd /volume1/docker/builds
git clone https://github.com/Jugendfeuerwehr-Manager/JF-Manager.git
cd JF-Manager

# Build images (~5-10 min each)
docker build -t jf_manager_backend:latest backend/
docker build -t jf_manager_frontend:latest frontend/

# Verify
docker images | grep jf_manager
# jf_manager_backend   latest   ...   ~350MB
# jf_manager_frontend  latest   ...   ~50MB
```

Then use `portainer/docker-compose.portainer-local-images.yml` in Portainer.

## Option 2: Build on PC and Transfer

```bash
# On your local machine
git clone https://github.com/Jugendfeuerwehr-Manager/JF-Manager.git
cd JF-Manager

docker build -t jf_manager_backend:latest backend/
docker build -t jf_manager_frontend:latest frontend/

# Save and compress
docker save jf_manager_backend:latest | gzip > jf_manager_backend.tar.gz
docker save jf_manager_frontend:latest | gzip > jf_manager_frontend.tar.gz

# Transfer to NAS
scp jf_manager_*.tar.gz your-username@your-nas-ip:/volume1/docker/images/
```

On the NAS:

```bash
cd /volume1/docker/images
docker load < jf_manager_backend.tar.gz
docker load < jf_manager_frontend.tar.gz
```

## Option 3: Use GitHub Actions Images

Once the CI/CD pipeline builds successfully, images are available at:

```
ghcr.io/jugendfeuerwehr-manager/jf-manager/backend:latest
ghcr.io/jugendfeuerwehr-manager/jf-manager/frontend:latest
```

Use the standard `docker-compose.portainer-synology.yml` with these image references.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Git not found | Install via Package Center → Developer Tools → Git Server |
| Out of disk space | `docker system prune -a` |
| Build fails (low RAM) | Build on PC instead (Option 2) |
| Permission denied | `sudo docker build ...` or add user to docker group |
