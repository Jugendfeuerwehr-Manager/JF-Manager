# Getting Started

## Prerequisites

- Python 3.10+
- Node.js 22+
- pipenv
- Docker (optional, for production setup)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Jugendfeuerwehr-Manager/JF-Manager.git
cd JF-Manager
```

### 2. Backend Setup

```bash
cd backend
pipenv install
pipenv shell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The backend runs on http://localhost:8000. Django Admin is available at http://localhost:8000/admin/.

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on http://localhost:5173.

### 4. Quick Start (Both)

```bash
./start-dev.sh
```

## Environment Variables

### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | *required in production* |
| `DEBUG` | Debug mode | `False` |
| `DATABASE_URL` | Database connection string | `sqlite:///db.sqlite3` |
| `ALLOWED_HOSTS` | Comma-separated hostnames | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins | `http://localhost:5173` (dev) |
| `REDIS_URL` | Redis connection | `none` |

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API URL | `http://localhost:8000/api/v1` |

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Vue.js Frontend (via Nginx in production) |
| `/admin/` | Django Admin |
| `/api/v1/` | REST API |
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | ReDoc API docs |
| `/health/` | Health check |

## Docker Installation

For a quick Docker Compose based setup:

```bash
cp backend/example.env .env
# adjust required values in .env (especially DJANGO_SECRET_KEY and DB credentials)
docker compose -f docker-compose.yml up -d --build
```

Then create an admin user:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

For production and Portainer/Synology variants, see:

- [Docker Deployment](deployment/docker.md)
- [Portainer Deployment](deployment/portainer.md)
- [Synology NAS](deployment/synology.md)
