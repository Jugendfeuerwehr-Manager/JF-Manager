# External Sync (Spond) And Provider Extension

## Overview

External member synchronization is managed through sync jobs.
Current providers in the codebase:

- `spond` (implemented)
- `hi_org` (placeholder, not implemented)

UI entry point:

- Settings card "Mitglieder Synchronisation" in the settings area.

## Sync Job Model

Sync jobs are represented by `SyncJob` with:

- provider (`spond`, `hi_org`)
- scope (`organization`, `department`)
- run mode (`manual`, `interval`)
- deletion mode (`review`, `auto_delete`)
- config and credentials payload

Important Spond config:

- `operation_mode`:
  - `groups_to_groups`
  - `groups_to_departments`
  - `members_only`
- optional `group_id` for top-level group filtering

## API Endpoints

Jobs:

- `GET /api/v1/sync-jobs/`
- `POST /api/v1/sync-jobs/`
- `DELETE /api/v1/sync-jobs/{id}/`

Actions:

- `POST /api/v1/sync-jobs/{id}/test_connection/`
- `POST /api/v1/sync-jobs/{id}/run_now/`
- `GET /api/v1/sync-jobs/{id}/garbage-collection-preview/`
- `POST /api/v1/sync-jobs/{id}/garbage-collect/`

Spond helper:

- `POST /api/v1/sync-jobs/spond-top-level-groups/`

Run history:

- `GET /api/v1/sync-runs/`

## Operational Notes

- Test connection before first run.
- Use review mode first for deletions, then switch to auto-delete only when validated.
- Use garbage-collection preview regularly to avoid unintended removals.

## How To Add A New Provider

### 1. Backend model choices

Add provider key to `SyncJob.Provider` in `backend/external_sync/models.py`.

### 2. Provider implementation

Create a new provider class in `backend/external_sync/services.py` based on `BaseExternalSyncProvider` and implement:

- `test_connection(job)`
- `run(job, triggered_by)`

### 3. Register provider

Add provider instance to `PROVIDERS` in `backend/external_sync/services.py` and ensure `get_provider()` resolves it.

### 4. API validation and provider-specific helpers

If your provider needs custom helper endpoints (similar to Spond top-level group lookup), add custom actions in `backend/external_sync/api/viewsets.py`.

### 5. Frontend integration

Update:

- `frontend/src/types/externalSync.ts` (provider union type)
- `frontend/src/components/settings/molecules/MemberSyncJobsCard.vue` (provider options/form)
- `frontend/src/api/externalSync.ts` (provider-specific helper calls)

### 6. Tests

Add API tests under `backend/api_tests/test_external_sync_api.py` for:

- job create/update validation
- connection test behavior
- run behavior
- provider error handling
- helper endpoints

## Related References

- Departments and permission scoping: `docs/architecture/departments-and-permissions.md`
- API reference: `docs/api/reference.md`
