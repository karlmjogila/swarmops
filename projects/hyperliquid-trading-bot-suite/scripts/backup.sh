#!/bin/bash
# Database Backup Script for Trading Bot Suite
# Usage: ./scripts/backup.sh [--s3 bucket-name] [--retention days]

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="${PROJECT_DIR}/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Parse arguments
S3_BUCKET=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --s3)
            S3_BUCKET="$2"
            shift 2
            ;;
        --retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Load environment
if [[ -f "${PROJECT_DIR}/.env.production" ]]; then
    source "${PROJECT_DIR}/.env.production"
fi

POSTGRES_USER="${POSTGRES_USER:-trading_bot}"
POSTGRES_DB="${POSTGRES_DB:-trading_bot}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "$(date): Starting backup..."

# Database backup
BACKUP_FILE="${BACKUP_DIR}/trading_bot_${DATE}.sql.gz"

if docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" ps postgres 2>/dev/null | grep -q "running"; then
    docker compose -f "${PROJECT_DIR}/${COMPOSE_FILE}" exec -T postgres \
        pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_FILE"
    
    echo "$(date): Database backup created: $BACKUP_FILE"
    echo "$(date): Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
else
    echo "$(date): ERROR - PostgreSQL is not running"
    exit 1
fi

# Configuration backup
CONFIG_BACKUP="${BACKUP_DIR}/config_${DATE}.tar.gz"
tar -czf "$CONFIG_BACKUP" \
    -C "$PROJECT_DIR" \
    .env.production \
    docker-compose.prod.yml \
    config/ \
    2>/dev/null || true

echo "$(date): Configuration backup created: $CONFIG_BACKUP"

# Upload to S3 if specified
if [[ -n "$S3_BUCKET" ]]; then
    if command -v aws &> /dev/null; then
        aws s3 cp "$BACKUP_FILE" "s3://${S3_BUCKET}/database/"
        aws s3 cp "$CONFIG_BACKUP" "s3://${S3_BUCKET}/config/"
        echo "$(date): Backups uploaded to S3: s3://${S3_BUCKET}/"
    else
        echo "$(date): WARNING - AWS CLI not found, skipping S3 upload"
    fi
fi

# Cleanup old backups
echo "$(date): Cleaning up backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete

# List current backups
echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"

echo ""
echo "$(date): Backup completed successfully"
