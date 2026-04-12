# JF-Manager Documentation

## Getting Started

- [Getting Started](getting-started.md) – Local development setup, environment variables, first steps

## Architecture

- [Architecture Overview](architecture/overview.md) – Docker architecture, network flow, security layers, build process
- [Vue.js Integration](architecture/vue-integration.md) – Vue 3 + Pinia integration patterns, API service layer, stores

## API

- [API Reference](api/reference.md) – REST API endpoints, authentication, pagination, Swagger/ReDoc

## Deployment

- [Docker Deployment](deployment/docker.md) – Docker Compose setup, SSL, backup/restore, CI/CD
- [Production Checklist](deployment/production-checklist.md) – Quick reference, environment config, security checklist
- [Portainer Deployment](deployment/portainer.md) – Deploy via Portainer UI or API
- [Portainer Migration](deployment/portainer-migration.md) – Migrate existing setup to new Docker architecture
- [Synology NAS](deployment/synology.md) – Manual Docker build on Synology NAS

## Domain Guides

- [Inventory System](domains/inventory.md) – Inventory models, transactions, permissions, discard tracking
- [Order Notifications](domains/orders-notifications.md) – Notification system architecture, workflow, templates
- [Qualifications](domains/qualifications.md) – Qualification and special task management

## Development

- [API Testing](development/testing.md) – Test structure, running tests, adding new tests
- [Systemd Services](development/systemd.md) – Systemd service files for production servers
