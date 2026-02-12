#!/bin/bash
#
# Quick start script for hl-bot-v2
# Sets up the environment and starts the development stack
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[SETUP]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║   hl-bot-v2 Quick Start Setup        ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Check prerequisites
log "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker first."
fi

if ! command -v docker compose &> /dev/null; then
    error "Docker Compose is not installed. Please install Docker Compose first."
fi

if ! docker info &> /dev/null; then
    error "Docker is not running. Please start Docker first."
fi

log "✓ Docker and Docker Compose are installed"

# Check if .env exists
if [ ! -f .env ]; then
    log "Creating .env from .env.example..."
    cp .env.example .env
    warn "⚠️  IMPORTANT: Edit .env and add your API keys!"
    warn "   At minimum, you need to set: ANTHROPIC_API_KEY"
    echo ""
    read -p "Press Enter to open .env in your default editor, or Ctrl+C to exit... "
    ${EDITOR:-nano} .env
else
    info ".env file already exists"
fi

# Create necessary directories
log "Creating directories..."
mkdir -p data/cache/videos
mkdir -p data/cache/pdfs
mkdir -p logs
mkdir -p backups

log "✓ Directories created"

# Build and start services
log "Building and starting services (this may take a few minutes)..."
docker compose up -d --build

# Wait for services to be healthy
log "Waiting for services to be healthy..."
sleep 5

max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker compose ps | grep -q "hlbot-postgres.*healthy"; then
        break
    fi
    echo -n "."
    sleep 2
    attempt=$((attempt + 1))
done

echo ""

if [ $attempt -eq $max_attempts ]; then
    error "Services failed to start. Check logs with: docker compose logs"
fi

log "✓ Services are healthy"

# Run migrations
log "Running database migrations..."
docker compose exec -T backend alembic upgrade head || warn "Migration failed - you may need to run this manually"

# Show status
echo ""
log "✓ Setup complete!"
echo ""
echo "╔═══════════════════════════════════════╗"
echo "║   Services Running                    ║"
echo "╚═══════════════════════════════════════╝"
docker compose ps

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║   Access URLs                         ║"
echo "╚═══════════════════════════════════════╝"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""

echo "╔═══════════════════════════════════════╗"
echo "║   Useful Commands                     ║"
echo "╚═══════════════════════════════════════╝"
echo "  View logs:      docker compose logs -f"
echo "  Stop services:  docker compose down"
echo "  Restart:        docker compose restart"
echo "  Health check:   ./scripts/health-check.sh"
echo "  Makefile help:  make help"
echo ""

# Run health check
if [ -x ./scripts/health-check.sh ]; then
    log "Running health check..."
    ./scripts/health-check.sh || warn "Some services may not be fully healthy yet"
fi

echo ""
info "Happy trading! 📈"
echo ""
