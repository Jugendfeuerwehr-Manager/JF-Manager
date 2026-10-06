# JF-Manager Documentation

## Getting Started

- [Getting Started](getting-started.md) – Local development setup, environment variables, first steps

## Architecture

- [Architecture Overview](architecture/overview.md) – Docker architecture, network flow, security layers, build process
- [Backend Structure](architecture/backend-structure.md) – Django app/module layout, ViewSet conventions, API registration pattern
- [Frontend Structure](architecture/frontend-structure.md) – Vue 3 layers, Pinia pattern, atomic design implementation
- [Departments And Permissions](architecture/departments-and-permissions.md) – Department scoping, active department context, backend enforcement, shared data rules
- [Vue.js Integration](architecture/vue-integration.md) – Vue 3 + Pinia integration patterns, API service layer, stores
- [Training Module Architecture](architecture/training-module.md) – Training models, API viewsets, permission model, frontend integration

## API

- [API Reference](api/reference.md) – REST API endpoints, authentication, pagination, Swagger/ReDoc

## Betrieb (Produktion)

Unterstützt: Docker Compose und Debian 13 nativ (auch im Proxmox-LXC), beide über `jfctl`.

- [Überblick und Layout](operations/ops-overview.md) – Aufbau, Verzeichnisse, HTTPS und Proxy-Vertrauen, beide Betriebswege
- [Installation](operations/ops-install.md) – Assistent, Vorabprüfung, Antwortdatei, Proxmox-LXC
- [jfctl](operations/ops-jfctl.md) – Befehle, Rückgabecodes, Protokoll, Wartungsplan
- [Sicherung, Wiederherstellung und Updates](operations/ops-backup-restore-update.md)
- [Migration bestehender Installationen](operations/ops-migration.md) – Compose/Portainer/Synology, PostgreSQL 15 → 17, Wechsel Docker ↔ nativ
- [Releasepakete und Herkunftsnachweis](operations/ops-release.md)
- [Produktionsvorgaben](operations/production-security.md), [Cookie-Sitzungen](operations/session-auth.md), [Schlüsselrotation](operations/encryption-rotation.md)

Abgelöste Anleitungen (Docker-Einzelanleitung, Portainer, Synology, Produktions-Checkliste) verweisen auf diese Seiten.

## Domain Guides

- [Inventory System](domains/inventory.md) – Inventory models, transactions, permissions, discard tracking
- [Order Notifications](domains/orders-notifications.md) – Notification system architecture, workflow, templates
- [Qualifications](domains/qualifications.md) – Qualification and special task management
- [Members, Lists, Group Editor, Excel Export](domains/members-lists-groups-exports.md) – Member lists, group management, export column selection
- [Settings, LDAP, SSO](domains/settings-ldap-sso.md) – Runtime settings API, LDAP config, OIDC flow and mappings
- [Departments (Operational Guide)](domains/departments.md) – Department-level operation model and integrations
- [External Sync With Spond](domains/external-sync-spond.md) – Sync jobs, Spond modes, provider extension guide
- [Training Module](domains/training-module.md) – Calendar/planner workflow, library usage, handout and mobile mode

## Development

- [API Testing](development/testing.md) – Test structure, running tests, adding new tests
- [Build Pipeline](development/build-pipeline.md) – CI, GHCR image build/push, manual deployment workflow
