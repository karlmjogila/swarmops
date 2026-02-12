# Hyperliquid Trading Bot Suite - Development Makefile

.PHONY: help setup dev test clean build deploy lint format docs

# Default target
help:
	@echo "🚀 Hyperliquid Trading Bot Suite - Development Commands"
	@echo ""
	@echo "📦 Setup Commands:"
	@echo "  make setup          Setup complete development environment"
	@echo "  make install        Install all dependencies"
	@echo "  make env            Copy environment template"
	@echo ""
	@echo "🏃 Development Commands:"
	@echo "  make dev            Start development servers (backend + frontend)"
	@echo "  make backend        Start backend development server"
	@echo "  make frontend       Start frontend development server"
	@echo "  make db             Start database and redis services"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  make test           Run all tests"
	@echo "  make test-backend   Run backend tests"
	@echo "  make test-frontend  Run frontend tests"
	@echo "  make coverage       Generate test coverage report"
	@echo ""
	@echo "🔧 Database Commands:"
	@echo "  make migrate        Run database migrations"
	@echo "  make migration      Create new migration"
	@echo "  make db-reset       Reset database (⚠️  destroys data)"
	@echo ""
	@echo "📝 Code Quality:"
	@echo "  make lint           Run all linters"
	@echo "  make format         Format all code"
	@echo "  make type-check     Run type checking"
	@echo ""
	@echo "🐳 Docker Commands:"
	@echo "  make docker         Start all services with Docker"
	@echo "  make docker-build   Build Docker images"
	@echo "  make docker-clean   Clean Docker containers and images"
	@echo ""
	@echo "🚢 Deployment:"
	@echo "  make build          Build production assets"
	@echo "  make deploy         Deploy to production"

# Setup targets
setup: env install migrate
	@echo "✅ Setup complete! Run 'make dev' to start development servers."

env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "📝 Created .env from template. Please update with your configuration."; \
	else \
		echo "📝 .env already exists."; \
	fi

install: install-backend install-frontend
	@echo "✅ All dependencies installed"

install-backend:
	@echo "📦 Installing backend dependencies..."
	cd backend && python -m pip install -e .

install-frontend:
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm install

# Development targets
dev: db
	@echo "🚀 Starting development servers..."
	@make -j 2 backend frontend

backend:
	@echo "🐍 Starting backend server..."
	cd backend && uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	@echo "🎨 Starting frontend server..."
	cd frontend && npm run dev

db:
	@echo "🗄️ Starting database services..."
	docker-compose up -d postgres redis
	@echo "⏳ Waiting for services to be ready..."
	@sleep 5

# Database targets
migrate:
	@echo "📊 Running database migrations..."
	cd backend && alembic upgrade head

migration:
	@read -p "Migration description: " desc; \
	cd backend && alembic revision --autogenerate -m "$$desc"

db-reset:
	@echo "⚠️  This will destroy all data in the database!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose down -v; \
		docker-compose up -d postgres redis; \
		sleep 10; \
		cd backend && alembic upgrade head; \
		echo "🗄️ Database reset complete"; \
	else \
		echo "❌ Cancelled"; \
	fi

# Testing targets
test: test-backend test-frontend
	@echo "✅ All tests completed"

test-backend:
	@echo "🧪 Running backend tests..."
	cd backend && pytest

test-frontend:
	@echo "🧪 Running frontend tests..."
	cd frontend && npm run test

coverage:
	@echo "📊 Generating test coverage..."
	cd backend && pytest --cov=src --cov-report=html
	@echo "📊 Coverage report generated in backend/htmlcov/index.html"

# Code quality targets
lint: lint-backend lint-frontend
	@echo "✅ All linting completed"

lint-backend:
	@echo "🔍 Linting backend..."
	cd backend && ruff check .
	cd backend && mypy .

lint-frontend:
	@echo "🔍 Linting frontend..."
	cd frontend && npm run lint

format: format-backend format-frontend
	@echo "✅ All code formatted"

format-backend:
	@echo "🎨 Formatting backend code..."
	cd backend && black .
	cd backend && ruff check . --fix

format-frontend:
	@echo "🎨 Formatting frontend code..."
	cd frontend && npm run lint:fix

type-check:
	@echo "🔍 Running type checks..."
	cd backend && mypy .
	cd frontend && npm run type-check

# Docker targets
docker:
	@echo "🐳 Starting all services with Docker..."
	docker-compose up --build

docker-build:
	@echo "🏗️ Building Docker images..."
	docker-compose build

docker-clean:
	@echo "🧹 Cleaning Docker containers and images..."
	docker-compose down -v --remove-orphans
	docker system prune -f

# Build and deployment
build: build-backend build-frontend
	@echo "✅ Production build completed"

build-backend:
	@echo "🏗️ Building backend..."
	cd backend && python -m build

build-frontend:
	@echo "🏗️ Building frontend..."
	cd frontend && npm run build

deploy:
	@echo "🚢 Deploying to production..."
	@echo "⚠️  Deployment configuration needed - check docker-compose.prod.yml"
	# docker-compose -f docker-compose.prod.yml up -d

# Utility targets
clean:
	@echo "🧹 Cleaning build artifacts..."
	cd backend && rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/
	cd frontend && rm -rf .nuxt/ dist/ .output/ node_modules/.cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:
	@echo "📚 Generating documentation..."
	@echo "📖 API docs available at: http://localhost:8000/docs"
	@echo "📖 Frontend docs available at: http://localhost:3000"

# Status check
status:
	@echo "🔍 System Status Check"
	@echo ""
	@echo "📦 Dependencies:"
	@command -v python3 >/dev/null 2>&1 && echo "  ✅ Python $(python3 --version)" || echo "  ❌ Python not found"
	@command -v node >/dev/null 2>&1 && echo "  ✅ Node $(node --version)" || echo "  ❌ Node.js not found"  
	@command -v docker >/dev/null 2>&1 && echo "  ✅ Docker $(docker --version)" || echo "  ❌ Docker not found"
	@echo ""
	@echo "🐳 Services:"
	@docker-compose ps 2>/dev/null || echo "  ❌ Docker Compose not running"
	@echo ""
	@echo "📁 Files:"
	@[ -f .env ] && echo "  ✅ .env file exists" || echo "  ⚠️  .env file missing (run 'make env')"
	@[ -f backend/requirements.txt ] && echo "  ✅ Backend dependencies defined" || echo "  ❌ Backend requirements missing"
	@[ -f frontend/package.json ] && echo "  ✅ Frontend dependencies defined" || echo "  ❌ Frontend package.json missing"