# Docker Stack (Docker Compose)

This guide is the single reference for running JF-Manager with Docker Compose.

If you deploy in Portainer, use the same compose file and environment variables from this guide.

## 1. Prerequisites

- Docker Engine 20.10+
- Docker Compose v2
- At least 4 GB RAM and 20 GB free disk

## 2. Choose Your Compose Stack

Use exactly one base stack.

| Stack file | When to use |
|---|---|
| `docker-compose.yml` | Primary production compose for Docker hosts |
| `portainer/docker-compose.portainer.yml` | Portainer stack using GHCR prebuilt images |
| `portainer/docker-compose.portainer-synology.yml` | Portainer on Synology (bind mounts) |

Optional overrides:

- `docker-compose.dev.yml`: development override (open extra ports, run Django dev server)
- `docker-compose.prod.yml`: production restart/logging and PostgreSQL tuning

Recommended simplification for long-term maintenance:

- Keep one production base compose (`docker-compose.yml`).
- Keep one development override (`docker-compose.dev.yml`).
- Keep one Synology/Portainer bind-mount variant.
- Treat extra Portainer variants (`portainer-build`, `portainer-build-synology`, `portainer-local-images`) as optional legacy files unless still needed.

## 3. GHCR Images (Recommended)

You can run JF-Manager directly from GitHub Container Registry:

- `ghcr.io/jugendfeuerwehr-manager/jf-manager/backend:latest`
- `ghcr.io/jugendfeuerwehr-manager/jf-manager/frontend:latest`

This is recommended for Portainer and Synology because it avoids in-place builds.

For background jobs, include a dedicated `worker` service with the same backend image:

```yaml
worker:
	image: ghcr.io/jugendfeuerwehr-manager/jf-manager/backend:latest
	command: python manage.py rqworker default
	environment:
		DATABASE_URL: postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db/${POSTGRES_DB}
		REDIS_URL: redis://redis:6379
		DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY}
```

## 4. Create Environment File

Create a `.env` file in repository root.

Required values:

```env
POSTGRES_DB=jf_manager_backend
POSTGRES_USER=jf_manager
POSTGRES_PASSWORD=CHANGE_ME

DJANGO_SECRET_KEY=CHANGE_ME
DJANGO_ADMIN_PASSWORD=CHANGE_ME
DJANGO_ADMIN_EMAIL=admin@example.com

ALLOWED_HOSTS=example.com,localhost
CSRF_TRUSTED_ORIGINS=https://example.com,http://localhost
```

Common optional values:

```env
DJANGO_MANAGEPY_MIGRATE=on
DEBUG=False
DEFAULT_FROM_EMAIL=noreply@example.com

EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True

HTTP_PORT=80
VITE_API_BASE_URL=/api/v1
```

Generate secrets:

```bash
openssl rand -base64 32
openssl rand -base64 50
openssl rand -base64 16
```

## 5. Start The Stack With Docker Compose

### Standard deployment (recommended)

```bash
docker compose -f docker-compose.yml up -d --build
```

### Development override

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### Production override

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Portainer compose file from CLI (optional)

```bash
docker compose -f portainer/docker-compose.portainer.yml up -d
```

### Synology bind-mount stack from CLI (optional)

```bash
docker compose -f portainer/docker-compose.portainer-synology.yml up -d
```

## 6. Verify The Deployment

```bash
docker compose ps
docker compose logs -f backend
```

Expected services:

- frontend
- backend
- worker
- db
- redis

Application URLs:

- Frontend: `http://localhost/` (or `http://<server>:${HTTP_PORT}`)
- Admin: `http://localhost/admin/`
- Health: `http://localhost/health`

## 7. Operations

Start / stop:

```bash
docker compose up -d
docker compose down
```

Update after pulling new code:

```bash
git pull
docker compose build
docker compose up -d
```

Run migrations manually:

```bash
docker compose exec backend python manage.py migrate
```

Open backend shell:

```bash
docker compose exec backend sh
```

Run one-off backup container (base stack):

```bash
docker compose --profile backup run --rm backup
```

## 8. Portainer Mapping

In Portainer Stacks:

1. Choose Repository or Web editor.
2. Use one compose file from section 2 (Synology usually uses `portainer/docker-compose.portainer-synology.yml`).
3. Provide the same `.env` values from section 4.
4. Deploy stack.

Use GHCR image tags (`ghcr.io/jugendfeuerwehr-manager/jf-manager/backend:latest` and `ghcr.io/jugendfeuerwehr-manager/jf-manager/frontend:latest`) for a stable pull-and-redeploy workflow.

## 9. Troubleshooting Quick Checks

```bash
docker compose config
docker compose logs --tail=200 backend
docker compose logs --tail=200 db
docker compose ps
```

- If frontend is up but API fails, verify `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- If backend fails on startup, check database credentials in `.env`.
- If jobs are not processed, ensure Redis is healthy and worker is running.
