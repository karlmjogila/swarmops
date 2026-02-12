# Scripts

Utility scripts for managing hl-bot-v2 deployment.

## Available Scripts

### `backup.sh`
Automated backup script for database, application data, and configuration.

**Usage:**
```bash
./scripts/backup.sh
```

**Cron setup** (daily at 2 AM):
```bash
0 2 * * * /opt/swarmops/projects/hl-bot-v2/scripts/backup.sh >> /var/log/hlbot-backup.log 2>&1
```

**Features:**
- Backs up PostgreSQL database
- Backs up application data directory
- Backs up .env configuration (with secure permissions)
- Automatic cleanup of old backups (30 days retention)
- Optional S3 upload support

**Output:** `backups/` directory
- `db-YYYYMMDD_HHMMSS.dump` - PostgreSQL dump
- `data-YYYYMMDD_HHMMSS.tar.gz` - Application data
- `env-YYYYMMDD_HHMMSS.bak` - Environment configuration

---

### `health-check.sh`
Comprehensive health check for all services.

**Usage:**
```bash
./scripts/health-check.sh
```

**Exit codes:**
- `0` - All services healthy
- `1` - One or more services unhealthy

**Checks:**
- Docker container status
- HTTP endpoints (backend, frontend)
- Backend health details (if jq is installed)

**Use in monitoring:**
```bash
# Add to cron for monitoring
*/5 * * * * /opt/swarmops/projects/hl-bot-v2/scripts/health-check.sh || echo "ALERT: Services unhealthy" | mail -s "HLBot Health Alert" admin@example.com
```

---

## Future Scripts (TODO)

- `restore.sh` - Interactive restore from backup
- `migrate.sh` - Database migration helper
- `deploy.sh` - One-command deployment
- `rollback.sh` - Rollback to previous version
- `monitor.sh` - Real-time monitoring dashboard

---

## Contributing

When adding new scripts:
1. Add execute permissions: `chmod +x scripts/your-script.sh`
2. Include a header comment explaining purpose and usage
3. Use proper error handling (`set -e`)
4. Add logging with timestamps
5. Document here in README
