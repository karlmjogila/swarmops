#!/bin/bash

# HL Bot v2 - Quick Start Script
# Usage: ./docker-start.sh [dev|prod]

set -e

MODE="${1:-dev}"
COLOR_GREEN='\033[0;32m'
COLOR_BLUE='\033[0;34m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[0;31m'
COLOR_RESET='\033[0m'

echo -e "${COLOR_BLUE}"
echo "╔═══════════════════════════════════════╗"
echo "║     HL Bot v2 - Docker Launcher       ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${COLOR_RESET}"

# Check prerequisites
echo -e "${COLOR_YELLOW}Checking prerequisites...${COLOR_RESET}"

if ! command -v docker &> /dev/null; then
    echo -e "${COLOR_RED}❌ Docker is not installed${COLOR_RESET}"
    echo "Install: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${COLOR_RED}❌ Docker Compose is not installed${COLOR_RESET}"
    exit 1
fi

echo -e "${COLOR_GREEN}✅ Docker installed${COLOR_RESET}"

# Check environment file
if [ "$MODE" = "prod" ]; then
    ENV_FILE=".env.production"
else
    ENV_FILE=".env"
fi

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${COLOR_RED}❌ $ENV_FILE not found${COLOR_RESET}"
    
    if [ "$MODE" = "prod" ]; then
        echo "Creating from template..."
        cp .env.production.template .env.production 2>/dev/null || cp .env.example .env.production
    else
        echo "Creating from template..."
        cp .env.example .env
    fi
    
    echo -e "${COLOR_YELLOW}⚠️  Please edit $ENV_FILE with your API keys and settings${COLOR_RESET}"
    exit 1
fi

# Validate critical env vars
if [ "$MODE" = "prod" ]; then
    echo -e "${COLOR_YELLOW}Validating production configuration...${COLOR_RESET}"
    
    if grep -q "CHANGE_THIS" "$ENV_FILE"; then
        echo -e "${COLOR_RED}❌ Please update placeholder values in $ENV_FILE${COLOR_RESET}"
        exit 1
    fi
    
    if grep -q "your-production-key-here" "$ENV_FILE"; then
        echo -e "${COLOR_RED}❌ Please add your API keys in $ENV_FILE${COLOR_RESET}"
        exit 1
    fi
fi

echo -e "${COLOR_GREEN}✅ Environment configured${COLOR_RESET}"

# Start services
echo -e "${COLOR_BLUE}Starting services in $MODE mode...${COLOR_RESET}"

if [ "$MODE" = "prod" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

# Build and start
docker-compose -f "$COMPOSE_FILE" up -d --build

# Wait for services to be healthy
echo -e "${COLOR_YELLOW}Waiting for services to be ready...${COLOR_RESET}"
sleep 5

# Check health
BACKEND_HEALTHY=false
RETRIES=30

for i in $(seq 1 $RETRIES); do
    if curl -f http://localhost:8000/health &>/dev/null; then
        BACKEND_HEALTHY=true
        break
    fi
    echo -n "."
    sleep 2
done

echo ""

if [ "$BACKEND_HEALTHY" = true ]; then
    echo -e "${COLOR_GREEN}✅ Backend is healthy${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}⚠️  Backend health check timeout (this is normal on first start)${COLOR_RESET}"
fi

# Show status
echo ""
echo -e "${COLOR_BLUE}Container Status:${COLOR_RESET}"
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo -e "${COLOR_GREEN}╔═══════════════════════════════════════╗${COLOR_RESET}"
echo -e "${COLOR_GREEN}║         Services Started! 🚀          ║${COLOR_RESET}"
echo -e "${COLOR_GREEN}╚═══════════════════════════════════════╝${COLOR_RESET}"
echo ""

if [ "$MODE" = "prod" ]; then
    echo -e "${COLOR_BLUE}Access your application:${COLOR_RESET}"
    echo "  Nginx Proxy:  http://localhost"
    echo "  Backend API:  http://localhost:8000"
    echo "  API Docs:     http://localhost:8000/docs"
else
    echo -e "${COLOR_BLUE}Access your application:${COLOR_RESET}"
    echo "  Frontend:     http://localhost:3000"
    echo "  Backend API:  http://localhost:8000"
    echo "  API Docs:     http://localhost:8000/docs"
fi

echo ""
echo -e "${COLOR_BLUE}Useful commands:${COLOR_RESET}"
echo "  View logs:    docker-compose -f $COMPOSE_FILE logs -f"
echo "  Stop:         docker-compose -f $COMPOSE_FILE down"
echo "  Restart:      docker-compose -f $COMPOSE_FILE restart"
echo "  Shell:        docker-compose -f $COMPOSE_FILE exec backend /bin/bash"
echo ""
echo "  Or use:       make help"
echo ""
