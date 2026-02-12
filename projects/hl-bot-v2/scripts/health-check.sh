#!/bin/bash
#
# Health check script for hl-bot-v2
# Returns 0 if all services are healthy, 1 otherwise
#

set -e

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
TIMEOUT=5

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

exit_code=0

check_service() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    echo -n "Checking $name... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_code" ]; then
        echo -e "${GREEN}✓${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗${NC} (HTTP $response)"
        exit_code=1
        return 1
    fi
}

check_docker_service() {
    local service=$1
    echo -n "Checking Docker service $service... "
    
    if docker compose ps | grep -q "$service.*running"; then
        echo -e "${GREEN}✓${NC} Running"
        return 0
    else
        echo -e "${RED}✗${NC} Not running"
        exit_code=1
        return 1
    fi
}

echo "=== hl-bot-v2 Health Check ==="
echo ""

# Check Docker services
echo "Docker Services:"
check_docker_service "hlbot-postgres"
check_docker_service "hlbot-redis"
check_docker_service "hlbot-backend"
check_docker_service "hlbot-celery"
check_docker_service "hlbot-frontend"

echo ""

# Check HTTP endpoints
echo "HTTP Endpoints:"
check_service "Backend Health" "$BACKEND_URL/health"
check_service "Backend API Docs" "$BACKEND_URL/docs"
check_service "Frontend" "$FRONTEND_URL"

echo ""

# Check backend health details
if command -v jq &> /dev/null; then
    echo "Backend Health Details:"
    health_data=$(curl -s --max-time $TIMEOUT "$BACKEND_URL/health" 2>/dev/null || echo "{}")
    
    if [ -n "$health_data" ] && [ "$health_data" != "{}" ]; then
        echo "$health_data" | jq '.'
    else
        echo -e "${YELLOW}Could not retrieve health data${NC}"
    fi
    echo ""
fi

# Overall status
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✓ All services healthy${NC}"
else
    echo -e "${RED}✗ Some services unhealthy${NC}"
fi

exit $exit_code
