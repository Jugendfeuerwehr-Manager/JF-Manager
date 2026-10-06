# Entwicklung und Prüfung. Produktion (Installation, Updates, Sicherungen)
# läuft ausschließlich über jfctl: docs/operations/ops-jfctl.md
.PHONY: help dev-up dev-down dev-logs ops-check release-local

help: ## Diese Hilfe
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev-up: ## Lokale Container aus dem Quellcode bauen und starten (nur Entwicklung)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

dev-down: ## Lokale Entwicklungscontainer stoppen
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

dev-logs: ## Protokolle der Entwicklungscontainer
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f $(ARGS)

ops-check: ## ShellCheck und bats-Tests des Betriebswerkzeugs
	shellcheck -x ops/jfctl ops/lib/*.sh ops/release/build-release.sh ops/proxmox/jf-lxc.sh
	bats ops/tests

release-local: ## Releasepaket aus dem Arbeitsstand bauen (nur Tests): make release-local VERSION=0.0.1
	ops/release/build-release.sh --version $(VERSION) --out dist/release --ref WORKTREE
