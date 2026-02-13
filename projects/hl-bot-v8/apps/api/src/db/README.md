# Database Management

This directory contains database utilities and repository patterns for the hl-bot-v8 project.

## Overview

- **Database**: PostgreSQL 16 with TimescaleDB extension
- **Migration Tool**: [Flyway](https://flywaydb.org/) (Docker-based)
- **Schema Tracking**: `flyway_schema_history` table
- **Connection Pooling**: pg Pool with optimal sizing

## Quick Start

```bash
# Start PostgreSQL container
cd infrastructure/docker
docker-compose up -d postgres

# Run all pending migrations
pnpm db:migrate

# Check migration status
pnpm db:info

# Validate migrations
pnpm db:validate
```

## Directory Structure

```
db/
├── README.md                    # This file
├── pool.ts                      # Connection pool configuration
├── repositories/                # Data access layer
├── seeds/                       # Optional seed data helpers
├── seed.ts                      # Seed runner
├── test/                        # Database tests
└── _archived/                   # Old migration runner (deprecated)

infrastructure/docker/
├── docker-compose.yml           # Service definitions (includes Flyway)
├── flyway.conf                  # Flyway configuration
└── migrations/                  # Flyway SQL migrations
    ├── V1__initial_schema.sql
    ├── U1__initial_schema.sql   # Undo migration
    ├── V2__timescale_hypertables.sql
    ├── U2__timescale_hypertables.sql
    ├── V3__seed_data.sql
    ├── U3__seed_data.sql
    ├── V4__performance_indexes.sql
    └── U4__performance_indexes.sql
```

## Flyway Commands

All commands are run from `apps/api/`:

```bash
# Run pending migrations
pnpm db:migrate

# Show migration info/status
pnpm db:info

# Validate migrations (checksums, naming)
pnpm db:validate

# Repair schema history (fix checksums, remove failed entries)
pnpm db:repair

# Create baseline for existing database
pnpm db:baseline

# Clean database (DANGEROUS - drops everything)
pnpm db:clean
```

## Environment Variables

```bash
# Required (set via .env or docker-compose)
POSTGRES_USER=hlbot
POSTGRES_PASSWORD=hlbot_dev_password
POSTGRES_DB=hlbot
POSTGRES_PORT=5432

# Flyway uses these via docker-compose environment
FLYWAY_PASSWORD=${POSTGRES_PASSWORD}
FLYWAY_ENVIRONMENT=development
```

## Migration Naming Convention

Flyway uses a strict naming convention:

### Versioned Migrations (applied once, in order)
```
V{version}__{description}.sql
```

Examples:
- ✅ `V1__initial_schema.sql`
- ✅ `V2__timescale_hypertables.sql`
- ✅ `V5__add_user_preferences.sql`
- ❌ `001_initial_schema.sql` (wrong format)
- ❌ `V1_initial.sql` (need double underscore)

### Undo Migrations (rollback, requires Flyway Teams for auto-undo)
```
U{version}__{description}.sql
```

Examples:
- ✅ `U1__initial_schema.sql`
- ✅ `U2__timescale_hypertables.sql`

### Repeatable Migrations (run on every checksum change)
```
R__{description}.sql
```

Used for views, stored procedures, etc.

## Creating a New Migration

1. **Create the migration file**:
   ```bash
   # In infrastructure/docker/migrations/
   touch V5__add_user_preferences.sql
   touch U5__add_user_preferences.sql
   ```

2. **Write the migration**:
   ```sql
   -- V5__add_user_preferences.sql
   ALTER TABLE users ADD COLUMN preferences JSONB DEFAULT '{}';
   CREATE INDEX idx_users_preferences ON users USING GIN (preferences);
   ```

3. **Write the undo migration**:
   ```sql
   -- U5__add_user_preferences.sql
   DROP INDEX IF EXISTS idx_users_preferences;
   ALTER TABLE users DROP COLUMN IF EXISTS preferences;
   ```

4. **Apply the migration**:
   ```bash
   pnpm db:migrate
   ```

5. **Verify**:
   ```bash
   pnpm db:info
   ```

## Safe Migration Patterns

```sql
-- ✅ Adding a column (safe)
ALTER TABLE projects ADD COLUMN priority INTEGER DEFAULT 0;

-- ✅ Adding an index concurrently (PostgreSQL-specific, safe)
CREATE INDEX CONCURRENTLY idx_tasks_status ON tasks(status);

-- ✅ Use IF NOT EXISTS / IF EXISTS for idempotency
CREATE INDEX IF NOT EXISTS idx_foo ON bar(baz);
DROP INDEX IF EXISTS idx_foo;

-- ⚠️ DANGEROUS: Renaming column (breaks existing queries)
ALTER TABLE projects RENAME COLUMN name TO display_name;

-- ⚠️ DANGEROUS: Changing column type (may truncate data)
ALTER TABLE projects ALTER COLUMN priority TYPE BIGINT;
```

## Common Operations

### Reset Database (Development Only)

```bash
# WARNING: Deletes all data
cd infrastructure/docker
docker-compose down -v
docker-compose up -d postgres
cd ../..
pnpm --filter @hl-bot/api run db:migrate
```

### Inspect Database

```bash
# Connect to PostgreSQL
docker exec -it hl-bot-postgres psql -U hlbot -d hlbot

# List tables
\dt

# Describe table
\d users

# View Flyway migration history
SELECT * FROM flyway_schema_history ORDER BY installed_rank;

# Exit
\q
```

### Backup and Restore

```bash
# Backup
docker exec hl-bot-postgres pg_dump -U hlbot hlbot > backup.sql

# Restore
docker exec -i hl-bot-postgres psql -U hlbot hlbot < backup.sql
```

## Connection Pooling

For application code, use the configured pool:

```typescript
import { pool } from './db/pool'

// Query directly
const result = await pool.query('SELECT * FROM users WHERE id = $1', [userId])

// Or use transaction pattern
const client = await pool.connect()
try {
  await client.query('BEGIN')
  // ... queries
  await client.query('COMMIT')
} catch (e) {
  await client.query('ROLLBACK')
  throw e
} finally {
  client.release()
}
```

Pool configuration in `pool.ts`:
```typescript
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,  // (core_count * 2) + 1 for SSD
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
})
```

## TimescaleDB Notes

TimescaleDB is enabled for time-series tables:

- **Candles**: OHLCV price data
- **Detected Patterns**: Historical pattern detection results
- **Market Structure**: Swing highs/lows, BOS, CHoCH
- **Ticks**: High-frequency tick data

See `V2__timescale_hypertables.sql` for hypertable configuration including:
- Compression policies
- Retention policies
- Continuous aggregates

## Troubleshooting

### Migration checksum mismatch

If you've modified an already-applied migration (don't do this!):
```bash
pnpm db:repair
```

### Can't connect to database

```bash
# Check if container is running
docker ps | grep postgres

# Check logs
docker logs hl-bot-postgres

# Restart container
docker-compose restart postgres
```

### Flyway container exits immediately

This is expected! Flyway runs, applies migrations, then exits. Check output for success/failure.

### TimescaleDB extension not available

```bash
# Verify TimescaleDB is installed
docker exec -it hl-bot-postgres psql -U hlbot -d hlbot -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';"

# If not installed, the image might be wrong
# Check docker-compose.yml uses: timescale/timescaledb:latest-pg16
```

## Migration from Old System

The project previously used a custom TypeScript migration runner (`migrate.ts`). This has been replaced with Flyway for:

- Industry-standard migration tooling
- Better versioning and checksums
- Team-wide consistency
- Production-ready rollback capabilities

The old migration runner is archived in `_archived/migrate.ts.bak`.

If you have an existing database with the old `schema_migrations` table, Flyway will baseline automatically on first run (`flyway.baselineOnMigrate=true`).

## Best Practices Checklist

- [ ] Migration has a descriptive name following `V{n}__{description}.sql` format
- [ ] Migration includes both versioned (V) and undo (U) files
- [ ] Migration is idempotent where possible (IF NOT EXISTS, IF EXISTS)
- [ ] Migration uses constraints (NOT NULL, CHECK, FK)
- [ ] Large schema changes are split into multiple migrations
- [ ] Indexes are created for foreign keys and frequent queries
- [ ] Migration has been tested locally before pushing

## References

- [Flyway Documentation](https://flywaydb.org/documentation/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
