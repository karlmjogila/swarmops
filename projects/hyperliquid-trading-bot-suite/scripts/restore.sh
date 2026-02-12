#!/bin/bash
# Database Restore Script for Trading Bot Suite
# Usage: ./scripts/restore.sh <backup_file.sql.gz>

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.prod.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh "${PROJECT_DIR}/backups/"*.sql.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo -e "${RED}ERROR: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Load environment
if [[ -f "${PROJECT_DIR}/.env.production" ]]; then
    source "${PROJECT_DIR}/.env.production"
fi

POSTGRES_USER="${POSTGRES_USER:-trading_bot}"
POSTGRES_DB="${POSTGRES_DB:-trading_bot}"

echo -e "${YELLOW}WARNING: This will restore the database from:${NC}"
echo "  $BACKUP_FILE"
echo ""
echo -e "${RED}ALL EXISTING DATA IN THE DATABASE WILL BE OVERWRITTEN!${NC}"
echo ""
read -p "Type 'RESTORE' to confirm: " confirm

if [[ "$confirm" != "RESTORE" ]]; then
    echo "Restore cancelled"
    exit 1
fi

echo ""
echo "$(date): Starting restore..."

# Stop backend to prevent writes
echo "$(date): Stopping backend service..."
docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" stop backend frontend || true

# Ensure postgres is running
docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" up -d postgres
sleep 5

# Drop and recreate database
echo "$(date): Recreating database..."
docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" exec -T postgres \
    psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" exec -T postgres \
    psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE ${POSTGRES_DB};"
docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" exec -T postgres \
    psql -U "$POSTGRES_USER" -d "${POSTGRES_DB}" -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Restore from backup
echo "$(date): Restoring from backup..."
gunzip -c "$BACKUP_FILE" | docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" exec -T postgres \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

# Start services
echo "$(date): Starting services..."
docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" up -d

# Health check
echo "$(date): Waiting for services to be ready..."
sleep 10

if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}$(date): Restore completed successfully!${NC}"
else
    echo -e "${YELLOW}$(date): Services starting, check logs if issues persist${NC}"
fi
