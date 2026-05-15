# Build Pipeline

## Overview

JF-Manager uses GitHub Actions for CI, image build/push, and deployment.
Workflows live in `.github/workflows/`.

## Pipeline Stages

```mermaid
flowchart LR
  A[CI: ci.yml] --> B[Build/Push: build-push.yml]
  B --> C[Deploy: deploy.yml (manual)]
```

## 1. Continuous Integration (`ci.yml`)

Triggers:

- push to `main` and `nextgeneration-frontend`
- pull requests to `main`

Jobs:

- Backend tests
  - PostgreSQL service container
  - `coverage run manage.py test api_tests`
- Backend lint
  - `ruff check .`
- Frontend quality gates
  - `npm run type-check`
  - `npm run lint -- --no-fix`
  - `npm run test:unit -- --coverage`
  - `npm run build-only`

Artifacts:

- backend coverage XML
- frontend coverage output

## 2. Container Build And Push (`build-push.yml`)

Triggers:

- after CI success (`workflow_run`)
- semantic tags (`v*`)

Outputs:

- GHCR backend image: `ghcr.io/<owner>/<repo>/backend`
- GHCR frontend image: `ghcr.io/<owner>/<repo>/frontend`

Tag strategy includes:

- branch refs
- semver tags
- short SHA tags
- `latest` on default branch

Security and supply-chain features:

- Docker Buildx cache
- SBOM + provenance enabled
- Trivy image scan (high/critical)
- SARIF upload to GitHub Security tab

## 3. Deployment (`deploy.yml`)

Trigger:

- manual (`workflow_dispatch`)

Inputs:

- environment (`production` or `staging`)
- image_tag (default: `latest`)

Remote deploy steps (SSH action):

1. pull repository changes
2. pull selected image tag
3. run backup container
4. `docker-compose up -d --remove-orphans`
5. backend health check
6. migrations
7. collectstatic
8. frontend health check
9. image prune

## Required Secrets

Deployment workflow expects:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_PATH`

## Local Commands That Mirror CI

Backend:

```bash
cd backend
pipenv run python manage.py test api_tests --verbosity=2
pipenv run ruff check .
pipenv run ruff format --check .
```

Frontend:

```bash
cd frontend
npm run type-check
npm run lint -- --no-fix
npm run test:unit -- --coverage
npm run build-only
```

## Related Docs

- `docs/architecture/overview.md`
- `docs/deployment/docker.md`
- `docs/deployment/portainer.md`
