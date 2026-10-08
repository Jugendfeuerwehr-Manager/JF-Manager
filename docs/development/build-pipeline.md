# Build Pipeline

## Overview

Three GitHub Actions workflows in `.github/workflows/` take a change from a pull request to a running installation. Production servers never build or `git pull`; they install published, verified releases with `jfctl` (OPS-03.3).

```text
push/PR ──> ci.yml ──(main, success)──> build-push.yml: images (branch tags)
tag vX.Y.Z ──> build-push.yml: ci.yml (tests) ─> images ─> Trivy ─> release package + attestation ─> GitHub release
manual ──> deploy.yml ──ssh──> jfctl update --version X.Y.Z (verify, backup, migrate, check, rollback)
```

## 1. Continuous Integration (`ci.yml`)

Runs on pushes to `main`, pull requests against `main`, and as a reusable workflow before every release tag.

| Job | Checks |
| --- | --- |
| Backend Tests | Full suite on PostgreSQL 17 (same major version as both production paths), migration check, coverage |
| Backend Lint | Ruff |
| Dependency Audit | `pip-audit --strict` on the lock file, `npm audit` (runtime clean, tooling below critical) |
| Frontend Tests & Lint | Type check, ESLint, Vitest with coverage |
| Operations Tooling | ShellCheck of `ops/` and the container entrypoint, bats tests of `jfctl` (`ops/tests`), production compose file, `nginx -t` with the shipped configuration, `caddy validate`, release package build and checksum verification |
| Frontend Build Check | Production bundle |

## 2. Images and Release (`build-push.yml`)

- **Branches** (`main`, after successful CI): backend and frontend images on GHCR, tagged with branch name and commit; `latest` for the default branch. For development and testing only – `jfctl` installs releases, not branch images.
- **Version tags `vX.Y.Z`:**
  1. The complete CI runs first (tag pushes do not trigger `ci.yml` on their own).
  2. Images are built with SBOM and provenance and tagged `X.Y.Z` and `X.Y`.
  3. Trivy scans both images; critical/high findings with a fix stop the release.
  4. The release job builds the frontend, then `ops/release/build-release.sh` creates `jf-manager-X.Y.Z.tar.gz`, `release-manifest.json` (image references **by digest**, checked to contain `@sha256:`) and `SHA256SUMS`.
  5. `actions/attest-build-provenance` attests the package; `jfctl` verifies this attestation with `gh attestation verify` when the `gh` CLI is available ([ops-release.md](../operations/ops-release.md)).
  6. A GitHub release with all three files is published.

## 3. Deployment (`deploy.yml`)

Manual dispatch with environment and version. The workflow validates the version format and runs on the server via SSH:

```sh
sudo /usr/local/sbin/jfctl --non-interactive --yes update --version X.Y.Z
```

`jfctl` loads and verifies the release, takes a full backup in maintenance mode, migrates, verifies backend/workers before reopening and rolls back application **and** database schema on failure (exit code 7). Exit code 3 means a precheck failed and nothing changed; 4 means another `jfctl` operation is running. Deployments per environment are serialised.

## Required Secrets

| Secret | Used by | Purpose |
| --- | --- | --- |
| `GITHUB_TOKEN` (automatic) | build-push | GHCR push, SARIF upload, GitHub release |
| `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` | deploy | SSH access; the user needs `sudo` for `/usr/local/sbin/jfctl` only |

`DEPLOY_PATH` is no longer needed: there is no checkout on the server.

## Local Commands That Mirror CI

```sh
make ops-check                                  # ShellCheck + bats for jfctl
make release-local VERSION=0.0.1                # release package from the working tree (tests only)
cd backend && pipenv run python manage.py test  # backend suite
cd frontend && npm run type-check && npm run lint -- --no-fix && npm run test:unit
```

## Related Docs

- [Releasepakete und Herkunftsnachweis](../operations/ops-release.md)
- [jfctl](../operations/ops-jfctl.md)
- [Sicherung, Wiederherstellung und Updates](../operations/ops-backup-restore-update.md)
