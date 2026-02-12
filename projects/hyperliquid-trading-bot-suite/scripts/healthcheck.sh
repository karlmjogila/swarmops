#!/bin/bash
# Health Check Script for Trading Bot Suite
# Usage: ./scripts/healthcheck.sh [--verbose] [--json]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.prod.yml"

VERBOSE=false
JSON_OUTPUT=false
EXIT_CODE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --json|-j)
            JSON_OUTPUT=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Colors (disabled for JSON output)
if [[ "$JSON_OUTPUT" == false ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

declare -A RESULTS

check_service() {
    local name=$1
    local check_cmd=$2
    
    if eval "$check_cmd" > /dev/null 2>&1; then
        RESULTS[$name]="healthy"
        [[ "$VERBOSE" == true ]] && echo -e "${GREEN}✓${NC} $name: healthy"
        return 0
    else
        RESULTS[$name]="unhealthy"
        [[ "$VERBOSE" == true ]] && echo -e "${RED}✗${NC} $name: unhealthy"
        EXIT_CODE=1
        return 1
    fi
}

# Run checks
[[ "$VERBOSE" == true ]] && echo "Running health checks..."
[[ "$VERBOSE" == true ]] && echo ""

# Backend API
check_service "backend" "curl -sf http://localhost:8000/api/health"

# Frontend
check_service "frontend" "curl -sf http://localhost:3000"

# PostgreSQL
check_service "postgres" "docker compose -f ${PROJECT_DIR}/${COMPOSE_FILE} exec -T postgres pg_isready -U trading_bot"

# Redis
check_service "redis" "docker compose -f ${PROJECT_DIR}/${COMPOSE_FILE} exec -T redis redis-cli ping"

# Nginx (if running)
if docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" ps nginx 2>/dev/null | grep -q "running"; then
    check_service "nginx" "curl -sf http://localhost"
fi

# Output results
if [[ "$JSON_OUTPUT" == true ]]; then
    echo "{"
    echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"status\": \"$([ $EXIT_CODE -eq 0 ] && echo 'healthy' || echo 'unhealthy')\","
    echo "  \"services\": {"
    first=true
    for service in "${!RESULTS[@]}"; do
        [[ "$first" == false ]] && echo ","
        echo -n "    \"$service\": \"${RESULTS[$service]}\""
        first=false
    done
    echo ""
    echo "  }"
    echo "}"
else
    [[ "$VERBOSE" == true ]] && echo ""
    
    if [[ $EXIT_CODE -eq 0 ]]; then
        echo -e "${GREEN}All services healthy${NC}"
    else
        echo -e "${RED}Some services unhealthy${NC}"
        echo ""
        echo "Unhealthy services:"
        for service in "${!RESULTS[@]}"; do
            if [[ "${RESULTS[$service]}" == "unhealthy" ]]; then
                echo "  - $service"
            fi
        done
        echo ""
        echo "Check logs: docker compose -f $COMPOSE_FILE logs <service>"
    fi
fi

exit $EXIT_CODE
