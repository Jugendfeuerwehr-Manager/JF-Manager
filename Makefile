.PHONY: help build up down restart logs ps backup restore clean ssl-cert

# Color output
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
NC     := \033[0m # No Color

help: ## Show this help message
	@echo '$(GREEN)JF-Manager Production Management$(NC)'
	@echo ''
	@echo 'Usage:'
	@echo '  make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all Docker images
	@echo "$(YELLOW)Building Docker images...$(NC)"
	docker-compose build --no-cache

up: ## Start all services
	@echo "$(YELLOW)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "Frontend: http://localhost"
	@echo "Backend Admin: http://localhost/admin"

down: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart: down up ## Restart all services

logs: ## Show logs (use ARGS='service_name' for specific service)
	docker-compose logs -f $(ARGS)

ps: ## Show running containers
	docker-compose ps

backup: ## Create database backup
	@echo "$(YELLOW)Creating backup...$(NC)"
	docker-compose run --rm backup
	@echo "$(GREEN)✓ Backup completed$(NC)"

restore: ## Restore database from backup (use ARGS='path/to/backup.sql.gz')
	@if [ -z "$(ARGS)" ]; then \
		echo "$(RED)Error: Please specify backup file with ARGS='path/to/backup.sql.gz'$(NC)"; \
		echo "Available backups:"; \
		docker-compose run --rm backup sh -c "ls -lh /backups/*.sql.gz | tail -10"; \
		exit 1; \
	fi
	@echo "$(RED)WARNING: This will replace the current database!$(NC)"
	@echo "Backup file: $(ARGS)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose run --rm -v $(ARGS):/backup.sql.gz:ro backup sh /restore.sh /backup.sql.gz; \
		echo "$(GREEN)✓ Restore completed$(NC)"; \
	else \
		echo "$(YELLOW)Restore cancelled$(NC)"; \
	fi

clean: ## Remove all containers, volumes, and images
	@echo "$(RED)WARNING: This will remove all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --rmi all; \
		echo "$(GREEN)✓ Cleanup completed$(NC)"; \
	else \
		echo "$(YELLOW)Cleanup cancelled$(NC)"; \
	fi

ssl-cert: ## Generate self-signed SSL certificate for development
	@echo "$(YELLOW)Generating self-signed SSL certificate...$(NC)"
	@mkdir -p nginx/ssl
	@openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout nginx/ssl/key.pem \
		-out nginx/ssl/cert.pem \
		-subj "/C=DE/ST=State/L=City/O=Organization/CN=localhost"
	@echo "$(GREEN)✓ SSL certificate generated$(NC)"
	@echo "Files created:"
	@echo "  - nginx/ssl/cert.pem"
	@echo "  - nginx/ssl/key.pem"

shell-backend: ## Open shell in backend container
	docker-compose exec backend sh

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend sh

shell-db: ## Open PostgreSQL shell
	docker-compose exec db psql -U jf_manager -d jf_manager_backend

migrate: ## Run Django migrations
	docker-compose exec backend python manage.py migrate

collectstatic: ## Collect static files
	docker-compose exec backend python manage.py collectstatic --noinput

createsuperuser: ## Create Django superuser
	docker-compose exec backend python manage.py createsuperuser

update: ## Pull latest images and restart
	@echo "$(YELLOW)Updating application...$(NC)"
	git pull
	docker-compose pull
	docker-compose build
	docker-compose up -d
	@echo "$(GREEN)✓ Update completed$(NC)"

health: ## Check health of all services
	@echo "$(YELLOW)Checking service health...$(NC)"
	@docker-compose ps
	@echo ""
	@echo "Frontend health:"
	@curl -s http://localhost/health || echo "$(RED)✗ Frontend unhealthy$(NC)"
	@echo ""
	@echo "Backend health:"
	@curl -s http://localhost/api/v1/ || echo "$(RED)✗ Backend unhealthy$(NC)"
