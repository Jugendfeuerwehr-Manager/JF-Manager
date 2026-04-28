# Contributing to JF-Manager

## Prerequisites

- Python 3.11+ with `pipenv`
- Node.js 20+ with `npm`
- Git

## Local Setup

```bash
git clone <repo>
cd JF-Manager
./setup.sh          # installs backend + frontend dependencies

./start-dev.sh      # starts both servers
# Backend:  http://localhost:8000
# Frontend: http://localhost:5173
```

Or start manually:

```bash
# Backend
cd backend
pipenv install
pipenv run python manage.py migrate
pipenv run python manage.py runserver

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Project Structure

- `backend/` — Django 5 + DRF, see [backend architecture](docs/architecture/backend-structure.md)
- `frontend/` — Vue 3 + TypeScript + Pinia, see [frontend architecture](docs/architecture/frontend-structure.md)
- `docs/` — Project documentation

## Adding a New API Endpoint

1. Add a ViewSet in `backend/{app}/api/viewsets/`
2. Re-export from `backend/{app}/api/viewsets/__init__.py`
3. Register with the router in `backend/jf_manager_backend/rest_urls.py`
4. Add a serializer in `backend/{app}/api/serializers/`
5. Run `python manage.py check` — must report 0 issues

See [backend-structure.md](docs/architecture/backend-structure.md) for the full pattern with code examples.

## Adding a New Frontend Feature

1. Define TypeScript interfaces in `frontend/src/types/{domain}.ts`
2. Add API functions in `frontend/src/api/{domain}.ts`
3. Create a Pinia store in `frontend/src/stores/{domain}.ts`
4. Build Vue components following atomic design (`atoms/` → `molecules/` → `organisms/`)

See [frontend-structure.md](docs/architecture/frontend-structure.md) for the full pattern with code examples.

## Code Style

### Backend

- Lint with `ruff` (config in `backend/ruff.toml`)
- All ViewSets subclass `BasePermissionedViewSet` from `jf_manager_backend/mixins.py`
- Use `get_serializer_class()` when actions need different serializer shapes
- Use `@action` decorators for custom endpoints, not standalone function-based views

### Frontend

- TypeScript strict mode — no `any` except at integration boundaries
- Pinia Composition API (`defineStore(() => {})`) — not Options API
- Components are presentation-only; business logic belongs in stores
- Always extract `.results` from paginated API responses

## Running Tests

```bash
# Backend
cd backend
pipenv run python run_api_tests.py

# Frontend unit tests
cd frontend
npm run test:unit

# Frontend type check
npm run type-check
```

## Migrations

After changing a model, always create and commit the migration:

```bash
cd backend
pipenv run python manage.py makemigrations {app}
pipenv run python manage.py migrate
```

Never hand-edit migration files unless absolutely necessary.

## Reference Implementation

The `orders` app is the gold standard for both backend and frontend patterns. When unsure how to structure something, look there first:

- Backend: `backend/orders/api/`
- Frontend: `frontend/src/components/orders/`, `frontend/src/stores/orders.ts`
