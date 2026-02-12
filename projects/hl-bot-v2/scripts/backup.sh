#!/bin/bash
#
# Automated backup script for hl-bot-v2
# Add to crontab: 0 2 * * * /opt/hlbot/scripts/backup.sh
#

set -e

# Configuration
PROJECT_DIR="/opt/swarmops/projects/hl-bot-v2"
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

cd "$PROJECT_DIR" || error "Could not change to project directory"

log "Starting backup..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    error "Docker is not running"
fi

# Check if containers are running
if ! docker compose ps | grep -q "hlbot-postgres"; then
    warn "PostgreSQL container is not running. Skipping database backup."
else
    # Database backup
    log "Backing up PostgreSQL database..."
    docker compose exec -T postgres pg_dump -U hlbot -d hlbot -F c -f /tmp/backup.dump || error "Database backup failed"
    docker compose cp postgres:/tmp/backup.dump "$BACKUP_DIR/db-$DATE.dump" || error "Could not copy database backup"
    docker compose exec -T postgres rm /tmp/backup.dump
    log "Database backup created: db-$DATE.dump"
fi

# Application data backup
if [ -d "$PROJECT_DIR/data" ]; then
    log "Backing up application data..."
    tar -czf "$BACKUP_DIR/data-$DATE.tar.gz" -C "$PROJECT_DIR" data/ || warn "Data backup failed"
    log "Data backup created: data-$DATE.tar.gz"
fi

# Configuration backup
if [ -f "$PROJECT_DIR/.env" ]; then
    log "Backing up configuration..."
    cp "$PROJECT_DIR/.env" "$BACKUP_DIR/env-$DATE.bak" || warn "Config backup failed"
    chmod 600 "$BACKUP_DIR/env-$DATE.bak"  # Protect secrets
    log "Config backup created: env-$DATE.bak"
fi

# Cleanup old backups
log "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "db-*.dump" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "data-*.tar.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "env-*.bak" -mtime +$RETENTION_DAYS -delete

# Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Total backup size: $BACKUP_SIZE"

# List recent backups
log "Recent backups:"
ls -lht "$BACKUP_DIR" | head -10

log "Backup completed successfully!"

# Optional: Upload to S3 or remote storage
# Uncomment and configure if needed:
# if command -v aws &> /dev/null; then
#     log "Uploading to S3..."
#     aws s3 cp "$BACKUP_DIR/db-$DATE.dump" s3://your-bucket/backups/hlbot/
#     aws s3 cp "$BACKUP_DIR/data-$DATE.tar.gz" s3://your-bucket/backups/hlbot/
# fi

exit 0
