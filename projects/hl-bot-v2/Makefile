.PHONY: help dev prod build up down restart logs clean test migrate backup

# Default target
help:
	@echo "HL Bot v2 - Docker Management Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development environment"
	@echo "  make dev-build    - Build and start development environment"
	@echo "  make dev-logs     - View development logs"
	@echo "  make dev-down     - Stop development environment"
	@echo ""
	@echo "Production:"
	@echo "  make prod         - Start production environment"
	@echo "  make prod-build   - Build and start production environment"
	@echo "  make prod-logs    - View production logs"
	@echo "  make prod-down    - Stop production environment"
	@echo ""
	@echo "Database:"
	@echo "  make migrate      - Run database migrations"
	@echo "  make migrate-dev  - Run migrations (development)"
	@echo "  make backup       - Create database backup"
	@echo "  make restore      - Restore database (set BACKUP_FILE=path)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make restart      - Restart all services"
	@echo "  make logs         - View all logs"
	@echo "  make ps           - Show running containers"
	@echo "  make clean        - Remove containers and volumes"
	@echo "  make prune        - Clean up Docker system"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make check        - Run all checks"

# Development commands
dev:
	docker-compose up -d
	@echo "✅ Development environment started"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend:  http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

dev-build:
	docker-compose up -d --build
	@echo "✅ Development environment built and started"

dev-logs:
	docker-compose logs -f

dev-down:
	docker-compose down
	@echo "✅ Development environment stopped"

# Production commands
prod:
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Production environment started"

prod-build:
	docker-compose -f docker-compose.prod.yml build
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Production environment built and started"

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

prod-down:
	docker-compose -f docker-compose.prod.yml down
	@echo "✅ Production environment stopped"

# Database commands
migrate:
	docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
	@echo "✅ Migrations applied"

migrate-dev:
	docker-compose exec backend alembic upgrade head
	@echo "✅ Migrations applied (dev)"

migrate-new:
	@read -p "Migration name: " name; \
	docker-compose exec backend alembic revision --autogenerate -m "$$name"
	@echo "✅ Migration created"

backup:
	@mkdir -p backups
	docker-compose -f docker-compose.prod.yml exec -T postgres \
		pg_dump -U hlbot hlbot > backups/hlbot_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created in backups/"

restore:
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "❌ Error: Set BACKUP_FILE=path/to/backup.sql"; \
		exit 1; \
	fi
	@echo "⚠️  This will overwrite the current database!"
	@read -p "Continue? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ]; then \
		docker-compose -f docker-compose.prod.yml stop backend celery-worker; \
		cat $(BACKUP_FILE) | docker-compose -f docker-compose.prod.yml exec -T postgres psql -U hlbot hlbot; \
		docker-compose -f docker-compose.prod.yml start backend celery-worker; \
		echo "✅ Database restored"; \
	else \
		echo "Cancelled"; \
	fi

# Maintenance commands
restart:
	docker-compose restart
	@echo "✅ Services restarted"

restart-prod:
	docker-compose -f docker-compose.prod.yml restart
	@echo "✅ Production services restarted"

logs:
	docker-compose logs -f

ps:
	docker-compose ps

shell-backend:
	docker-compose exec backend /bin/bash

shell-db:
	docker-compose exec postgres psql -U hlbot -d hlbot

# Cleanup commands
clean:
	docker-compose down -v
	@echo "✅ Containers and volumes removed"

clean-prod:
	docker-compose -f docker-compose.prod.yml down -v
	@echo "✅ Production containers and volumes removed"

prune:
	docker system prune -a --volumes
	@echo "✅ Docker system cleaned"

# Testing commands
test:
	docker-compose exec backend pytest
	@echo "✅ Tests completed"

lint:
	docker-compose exec backend black --check app/
	docker-compose exec backend ruff app/
	@echo "✅ Linting completed"

check: lint test
	@echo "✅ All checks passed"

# Status commands
status:
	@echo "=== Container Status ==="
	@docker-compose ps
	@echo ""
	@echo "=== Resource Usage ==="
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
	@echo ""
	@echo "=== Disk Usage ==="
	@docker system df

health:
	@echo "Checking backend health..."
	@curl -f http://localhost:8000/health && echo "✅ Backend healthy" || echo "❌ Backend unhealthy"
	@echo "Checking frontend..."
	@curl -f http://localhost:3000 && echo "✅ Frontend healthy" || echo "❌ Frontend unhealthy"
