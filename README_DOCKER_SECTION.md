# 🐳 Docker Production Deployment

Add this section to your main README.md to document the Docker setup.

---

## Production Deployment with Docker

JF-Manager includes a complete production-ready Docker setup with multi-stage builds, Nginx reverse proxy, automated backups, and comprehensive security hardening.

### Quick Start

**Option 1: Portainer (Recommended)**
```bash
# 1. Open Portainer Web UI
# 2. Stacks → Add stack → Use Git Repository
# 3. Repository: https://github.com/Jugendfeuerwehr-Manager/JF-Manager
# 4. Compose path: portainer/docker-compose.portainer.yml
# 5. Set environment variables → Deploy
# See portainer/QUICK_START.md for detailed steps
```

**Option 2: Command Line**
```bash
# Validate setup
./validate.sh

# Automated deployment
./setup.sh

# Or manual deployment
cp .env.example .env
# Edit .env with your configuration
make build
make up
```

### Architecture

```
Internet → Nginx (Frontend) → Django (Backend) → PostgreSQL
           ↓                   ↓
        Vue.js SPA         Redis Cache
```

**Components:**
- **Frontend**: Nginx serving Vue.js SPA + reverse proxy to backend
- **Backend**: Django REST API with uWSGI
- **Database**: PostgreSQL 15 with automated backups
- **Cache**: Redis 7

### Key Features

✅ **Multi-stage Docker builds** - Minimal production images (~350MB backend, ~50MB frontend)  
✅ **Security hardened** - Non-root containers, read-only filesystems, security headers  
✅ **Automated backups** - Daily/weekly/monthly with configurable retention  
✅ **Health monitoring** - Health checks for all services  
✅ **SSL/TLS ready** - Let's Encrypt support built-in  
✅ **CI/CD ready** - GitHub Actions workflows included  

### Management Commands

```bash
make help              # Show all commands
make build             # Build Docker images
make up                # Start all services
make logs              # View logs
make backup            # Create database backup
make health            # Check service health
```

### Access Points

After deployment:
- **Frontend**: http://localhost/
- **Django Admin**: http://localhost/admin/
- **API**: http://localhost/api/v1/

### Documentation

| Document | Description |
|----------|-------------|
| [DOCKER_PRODUCTION_READY.md](DOCKER_PRODUCTION_READY.md) | Quick start guide |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Complete deployment guide |
| [PRODUCTION.md](PRODUCTION.md) | Operations reference |

### Requirements

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 20GB+ disk space

---
