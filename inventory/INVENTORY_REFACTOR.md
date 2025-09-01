# Inventory Module Refactor Roadmap

This document tracks migration from legacy mixed views + ad-hoc JSON endpoints to a clean DRF powered API and modular view architecture.

## Current State (Phase 1)
- New DRF viewsets under `inventory/api/viewsets.py` for: Items, Variants, Categories, Locations, Stock (RO), Transactions.
- Rich serializers with computed fields in `inventory/api/serializers.py`.
- Legacy AJAX endpoints in `inventory/api_views.py` now emit `X-Deprecated: true` response header.
- Frontend `static/js/smart-transaction-form.js` migrated to new DRF endpoints (search & stock info).

## Phase 2 (Next)
1. Split giant `inventory/views.py` into submodules:
   - `views/items.py`, `views/variants.py`, `views/transactions.py`, `views/locations.py`, `views/categories.py`, `views/dashboard.py`, `views/ajax_legacy.py`.
2. Update `inventory/urls.py` to import from new modules.
3. Add deprecation banner in templates that still call legacy AJAX endpoints.
4. Migrate remaining JavaScript / templates to DRF endpoints (search, category items, etc.).
5. Introduce a lightweight front-end adapter util for API calls (central error handling).

## Phase 3
1. Remove unused legacy endpoints from `api_views.py` (after confirming no calls in logs for 30 days or explicit sign-off).
2. Delete deprecation helper and file; adjust `urls.py` accordingly.
3. Add OpenAPI schema generation (consider `drf-spectacular`).
4. Add more granular permissions on viewsets (map to Django model perms or custom object-level rules).

## Testing
- Initial API tests in `inventory/tests/test_api.py` (expand with: variant create, transaction flow, stock adjustments).
- Add snapshot-style tests for serializers once stable.

## Notes
- Keep legacy field names in serializers until forms & imports are updated.
- Validate front-end after each migration step (console for `X-Deprecated`).

## Quick Reference of New Endpoints
Base prefix: `/api/v1/inventory/`
- `items/` (list/create) + `?search=<term>`
- `items/{id}/` (retrieve/update/delete)
- `items/{id}/variants/` (list variants of item)
- `items/{id}/stock/` (aggregated stock)
- `items/search/?q=<term>` (lightweight search action)
- `variants/` CRUD
- `variants/{id}/stock/`
- `categories/` CRUD
- `categories/{id}/items/`
- `locations/` CRUD + search
- `locations/{id}/stock/`
- `stocks/` (read-only)
- `transactions/` CRUD

## Deprecation Policy
All legacy `/inventory/api/...` JSON endpoints now return `X-Deprecated: true` and a `Link` header pointing to DRF routes. They will be removed in Phase 3.

---
Last updated: Phase 1 implementation.
