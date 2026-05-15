# Settings, LDAP, And SSO (OIDC)

## Overview

Settings are exposed through a dedicated settings API and UI sections under `/settings`.

Categories:

- General
- Email
- Email templates
- Member
- Service
- Order
- LDAP
- OIDC (SSO)

## Settings API

Base endpoints:

- `GET /api/v1/settings/`
- `GET /api/v1/settings/permissions/`

Category endpoints:

- `GET/PATCH /api/v1/settings/general/`
- `GET/PATCH /api/v1/settings/email/`
- `GET/PATCH /api/v1/settings/member/`
- `GET/PATCH /api/v1/settings/service/`
- `GET/PATCH /api/v1/settings/order/`
- `GET/PATCH /api/v1/settings/ldap/`
- `GET/PATCH /api/v1/settings/oidc/`

Permission model:

- Superuser has full access.
- Staff has broad access except sensitive auth categories are still checked.
- Fine-grained permissions exist per category (`view_*_settings`, `change_*_settings`) plus global (`view_all_settings`, `change_all_settings`).

## LDAP Integration

LDAP is runtime-configurable through `LDAPConfig` and does not require code deployment for common config changes.

Key endpoints:

- `POST /api/v1/settings/ldap/test-connection/`
- `POST /api/v1/settings/ldap/browse/` (superuser-only)

LDAP to department-role mappings:

- `GET /api/v1/ldap-department-mappings/`
- `POST /api/v1/ldap-department-mappings/`
- `DELETE /api/v1/ldap-department-mappings/{id}/`

Behavior:

- LDAP login uses configurable bind/search parameters.
- Mappings can create/update department roles for users based on LDAP group DN membership.

## SSO (OIDC)

OIDC is implemented as Authorization Code flow on the backend with JWT handoff for the SPA.

Public/login flow endpoints:

- `GET /api/v1/auth/oidc/public-config/`
- `GET /api/v1/auth/oidc/login/`
- `GET /api/v1/auth/oidc/callback/`
- `POST /api/v1/auth/oidc/exchange/`

OIDC settings and validation:

- `GET/PATCH /api/v1/settings/oidc/`
- `POST /api/v1/settings/oidc/test-discovery/`

OIDC group mappings:

- `GET /api/v1/oidc-group-mappings/`
- `POST /api/v1/oidc-group-mappings/`
- `DELETE /api/v1/oidc-group-mappings/{id}/`

Behavior:

- OIDC users are created/updated on login.
- Optional mapping from OIDC group claim values to department roles and auth groups.
- Optional `hide_local_login` can reduce local-login visibility on the login page.

## Related References

- Department architecture: `docs/architecture/departments-and-permissions.md`
- API reference: `docs/api/reference.md`
