#!/bin/bash
# Production Deployment Script for Trading Bot Suite
# Usage: ./scripts/deploy.sh [--no-backup] [--skip-migrations]

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
BACKUP_DIR="${PROJECT_DIR}/backups"

# Flags
SKIP_BACKUP=false
SKIP_MIGRATIONS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --skip-migrations)
            SKIP_MIGRATIONS=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Pre-flight checks
preflight_checks() {
    log_info "Running pre-flight checks..."
    
    # Check docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check docker compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose v2 is not installed"
        exit 1
    fi
    
    # Check env file
    if [[ ! -f "${PROJECT_DIR}/${ENV_FILE}" ]]; then
        log_error "Environment file ${ENV_FILE} not found"
        log_info "Copy .env.production.example to .env.production and configure"
        exit 1
    fi
    
    # Validate required env vars
    source "${PROJECT_DIR}/${ENV_FILE}"
    
    REQUIRED_VARS=(
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
        "ANTHROPIC_API_KEY"
        "HYPERLIQUID_PRIVATE_KEY"
        "HYPERLIQUID_WALLET_ADDRESS"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    log_success "Pre-flight checks passed"
}

# Backup database
backup_database() {
    if [[ "$SKIP_BACKUP" == true ]]; then
        log_warn "Skipping database backup (--no-backup flag)"
        return
    fi
    
    log_info "Creating database backup..."
    
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="${BACKUP_DIR}/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz"
    
    # Check if postgres is running
    if docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" ps postgres 2>/dev/null | grep -q "running"; then
        docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" exec -T postgres \
            pg_dump -U "${POSTGRES_USER:-trading_bot}" "${POSTGRES_DB:-trading_bot}" | gzip > "$BACKUP_FILE"
        log_success "Database backed up to: $BACKUP_FILE"
    else
        log_warn "PostgreSQL not running, skipping backup"
    fi
}

# Build images
build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_DIR"
    docker compose -f "$COMPOSE_FILE" build --no-cache
    
    log_success "Images built successfully"
}

# Pull latest images (for pre-built images)
pull_images() {
    log_info "Pulling latest images..."
    
    cd "$PROJECT_DIR"
    docker compose -f "$COMPOSE_FILE" pull
    
    log_success "Images pulled successfully"
}

# Run database migrations
run_migrations() {
    if [[ "$SKIP_MIGRATIONS" == true ]]; then
        log_warn "Skipping migrations (--skip-migrations flag)"
        return
    fi
    
    log_info "Running database migrations..."
    
    cd "$PROJECT_DIR"
    
    # Ensure postgres is up
    docker compose -f "$COMPOSE_FILE" up -d postgres
    
    # Wait for postgres
    log_info "Waiting for PostgreSQL to be ready..."
    sleep 10
    
    # Run migrations
    docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head
    
    log_success "Migrations completed"
}

# Deploy services
deploy_services() {
    log_info "Deploying services..."
    
    cd "$PROJECT_DIR"
    
    # Pull/build and start services
    docker compose -f "$COMPOSE_FILE" up -d
    
    log_success "Services deployed"
}

# Health check
health_check() {
    log_info "Running health checks..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
            log_success "Backend health check passed"
            break
        fi
        
        log_info "Waiting for backend to be ready (attempt $attempt/$max_attempts)..."
        sleep 5
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        log_error "Backend health check failed after $max_attempts attempts"
        log_info "Check logs with: docker compose -f $COMPOSE_FILE logs backend"
        exit 1
    fi
    
    # Check frontend
    attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf http://localhost:3000 > /dev/null 2>&1; then
            log_success "Frontend health check passed"
            break
        fi
        
        log_info "Waiting for frontend to be ready (attempt $attempt/$max_attempts)..."
        sleep 5
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        log_error "Frontend health check failed after $max_attempts attempts"
        log_info "Check logs with: docker compose -f $COMPOSE_FILE logs frontend"
        exit 1
    fi
}

# Show status
show_status() {
    log_info "Deployment Status:"
    echo ""
    docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" ps
    echo ""
    log_success "Deployment complete!"
    echo ""
    echo "Services available at:"
    echo "  - Frontend: http://localhost (or your configured domain)"
    echo "  - Backend API: http://localhost/api"
    echo "  - API Docs: http://localhost/api/docs"
    echo "  - Health Check: http://localhost/api/health"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: docker compose -f $COMPOSE_FILE logs -f"
    echo "  - Stop: docker compose -f $COMPOSE_FILE down"
    echo "  - Restart: docker compose -f $COMPOSE_FILE restart"
}

# Main
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     Hyperliquid Trading Bot Suite - Production Deploy       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    preflight_checks
    backup_database
    build_images
    run_migrations
    deploy_services
    health_check
    show_status
}

main "$@"
