---
name: database
description: >
  Design and implement database schemas, queries, migrations, caching layers, and data access
  patterns across PostgreSQL, MySQL, DynamoDB, and Redis with focus on correctness, performance,
  and production readiness. Covers schema design, indexing strategies, query optimization, ORMs
  (Drizzle, SQLAlchemy), connection pooling, cache-aside patterns, AWS managed databases
  (RDS/Aurora, DynamoDB, ElastiCache), high availability (read replicas, Multi-AZ failover,
  point-in-time recovery), and data integrity. Databases are backing services — treat them as
  attached resources swappable via connection string in environment variables, never hardcoded.
  Trigger this skill for any task involving databases, data models, schemas, migrations, queries,
  data access layers, caching, replication, or connection management.
triggers:
  - database
  - db
  - schema
  - migration
  - query
  - sql
  - prisma
  - drizzle
  - sqlite
  - postgres
  - postgresql
  - mysql
  - mongo
  - model
  - table
  - index
  - orm
  - redis
  - dynamodb
  - rds
  - aurora
  - connection pool
  - replication
  - cache
  - elasticache
---

# Database Excellence

A database is the foundation of your application — get it wrong and everything built on top wobbles. Design schemas that model your domain accurately, write queries that perform well at scale, and treat migrations as first-class code. Databases are backing services: your app connects via a `DATABASE_URL` from the environment, never a hardcoded string.

## Core Principles

1. **Model the domain, not the UI** — Schema should reflect business entities and relationships, not what a particular page needs to display.
2. **Data integrity is non-negotiable** — Use constraints, foreign keys, and transactions. The database is your last line of defense against bad data.
3. **Optimize for reads you actually make** — Don't index everything. Don't denormalize everything. Profile first, optimize second.
4. **Backing services are attached resources** — Connect to PostgreSQL, MySQL, Redis, and DynamoDB through environment variables (`DATABASE_URL`, `REDIS_URL`). Swapping from a local PostgreSQL to RDS should require only a connection string change.

## Schema Design

### Naming Conventions
```sql
-- Tables: plural, snake_case
CREATE TABLE projects ( ... );
CREATE TABLE task_assignments ( ... );

-- Columns: snake_case, descriptive
id           -- Primary key (UUID or auto-increment)
created_at   -- Timestamp columns end with _at
updated_at
deleted_at   -- Soft delete
project_id   -- Foreign keys: referenced_table_singular_id
status       -- Not 'stat' or 's'
is_active    -- Booleans prefixed with is_/has_/can_
```

### Primary Keys
```sql
-- UUIDs for distributed systems or public-facing IDs
id UUID PRIMARY KEY DEFAULT gen_random_uuid()

-- Auto-increment for internal, non-exposed tables
id SERIAL PRIMARY KEY

-- NEVER use business data as primary key (email, username, etc.)
-- Those change. Primary keys should not.
```

### Relationships
```sql
-- One-to-many: FK on the "many" side
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
);

-- Many-to-many: junction table
CREATE TABLE task_dependencies (
  task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  depends_on_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  PRIMARY KEY (task_id, depends_on_id),
  CHECK (task_id != depends_on_id)  -- No self-dependencies
);

-- One-to-one: FK with UNIQUE constraint
CREATE TABLE project_settings (
  project_id UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  theme TEXT DEFAULT 'dark',
  notifications_enabled BOOLEAN DEFAULT true
);
```

### Constraints — Use Them
```sql
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'archived', 'deleted')),
  phase TEXT NOT NULL DEFAULT 'interview'
    CHECK (phase IN ('interview', 'spec', 'build', 'review', 'complete')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT valid_name CHECK (length(name) BETWEEN 1 AND 200)
);

-- Partial unique index (unique only among non-deleted)
CREATE UNIQUE INDEX idx_projects_name_active
  ON projects (name)
  WHERE status != 'deleted';
```

## Migrations

### TDD for Migrations — Write the Test First

Before writing the migration, write a test that asserts the schema change works. This catches issues before they reach staging.

```typescript
// test/migrations/003_add_priority_column.test.ts
// Write this BEFORE writing the migration itself
import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { migrate, rollback, getPool } from '../helpers/db-test-utils'

describe('003_add_priority_column', () => {
  const pool = getPool(process.env.TEST_DATABASE_URL!)

  beforeAll(async () => {
    await migrate(pool, { to: '003_add_priority_column' })
  })

  afterAll(async () => {
    await rollback(pool, { to: '002_add_task_dependencies' })
    await pool.end()
  })

  it('should add priority column with default value 0', async () => {
    const result = await pool.query(`
      SELECT column_name, column_default, is_nullable, data_type
      FROM information_schema.columns
      WHERE table_name = 'projects' AND column_name = 'priority'
    `)
    expect(result.rows[0]).toEqual({
      column_name: 'priority',
      column_default: '0',
      is_nullable: 'YES',
      data_type: 'integer',
    })
  })

  it('should preserve existing rows after migration', async () => {
    const result = await pool.query('SELECT priority FROM projects LIMIT 1')
    expect(result.rows[0].priority).toBe(0)
  })
})
```

Now write the migration to make the test pass:

```sql
-- migrations/003_add_priority_column.sql
ALTER TABLE projects ADD COLUMN priority INTEGER DEFAULT 0;
```

### Migration Rules
```
- One migration per logical change
- Migrations are append-only — NEVER edit a migration that's been applied
- Every migration must be reversible (include down/rollback)
- Test migrations on a copy of production data before deploying
- Name migrations descriptively: 001_create_projects.sql, 002_add_task_dependencies.sql
```

### Safe Migration Patterns
```sql
-- Adding a column (safe — no lock on reads)
ALTER TABLE projects ADD COLUMN priority INTEGER DEFAULT 0;

-- Adding an index concurrently (safe — no table lock in PostgreSQL)
CREATE INDEX CONCURRENTLY idx_tasks_status ON tasks(status);

-- DANGEROUS: Renaming a column (breaks existing queries)
-- Instead: add new column, migrate data, update code, drop old column
ALTER TABLE projects ADD COLUMN display_name TEXT;
UPDATE projects SET display_name = name;
-- Deploy code that reads display_name
-- Later migration: ALTER TABLE projects DROP COLUMN name;

-- DANGEROUS: Changing column type
-- Instead: add new column with new type, migrate, swap
```

## Indexing

### When to Index
```sql
-- Index columns that appear in:
-- WHERE clauses
CREATE INDEX idx_tasks_status ON tasks(status);

-- JOIN conditions (foreign keys)
CREATE INDEX idx_tasks_project_id ON tasks(project_id);

-- ORDER BY (if queried frequently with that sort)
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);

-- Composite indexes for multi-column queries
-- Column order matters: most selective first, or match query order
CREATE INDEX idx_tasks_project_status ON tasks(project_id, status);
-- This index serves: WHERE project_id = ? AND status = ?
-- AND: WHERE project_id = ? (leftmost prefix)
-- NOT: WHERE status = ? (no leftmost prefix)
```

### When NOT to Index
```
- Small tables (< 1000 rows) — full scan is fast enough
- Columns with low cardinality (boolean flags with 50/50 distribution)
- Tables that are write-heavy and rarely queried
- Every possible column "just in case" — each index slows writes
```

## Query Patterns

### Efficient Queries
```sql
-- Use specific columns, not SELECT *
SELECT id, name, status FROM projects WHERE status = 'active';

-- GOOD: Use EXISTS for existence checks
SELECT EXISTS(SELECT 1 FROM tasks WHERE project_id = $1 AND status = 'running');
-- BAD: COUNT for existence checks
SELECT COUNT(*) FROM tasks WHERE project_id = $1 AND status = 'running';

-- GOOD: Keyset (cursor) pagination — fast regardless of position
SELECT * FROM tasks WHERE created_at < $1 ORDER BY created_at DESC LIMIT 20;
-- BAD: OFFSET pagination — slow on large offsets
SELECT * FROM tasks ORDER BY created_at DESC LIMIT 20 OFFSET 10000;

-- GOOD: Batch operations
UPDATE tasks SET status = 'done' WHERE id = ANY($1::uuid[]);
-- BAD: N+1 loop
-- for (const id of taskIds) { await db.query('UPDATE tasks SET status = $1 WHERE id = $2', ['done', id]) }
```

### N+1 Query Prevention
```typescript
// BAD — N+1: one query per project
const projects = await db.query('SELECT * FROM projects')
for (const project of projects) {
  project.tasks = await db.query('SELECT * FROM tasks WHERE project_id = $1', [project.id])
}

// GOOD — 2 queries total
const projects = await db.query('SELECT * FROM projects')
const projectIds = projects.map(p => p.id)
const tasks = await db.query('SELECT * FROM tasks WHERE project_id = ANY($1)', [projectIds])

const tasksByProject = new Map<string, Task[]>()
for (const task of tasks) {
  if (!tasksByProject.has(task.project_id)) tasksByProject.set(task.project_id, [])
  tasksByProject.get(task.project_id)!.push(task)
}
```

## Transactions

```typescript
// Use transactions for operations that must be atomic
await db.transaction(async (tx) => {
  const project = await tx.insert(projects).values({ name, slug }).returning()

  await tx.insert(projectStates).values({
    projectId: project.id,
    phase: 'interview',
    status: 'active',
  })

  await tx.insert(activityLog).values({
    projectId: project.id,
    type: 'created',
    message: 'Project created',
  })

  // If ANY of these fail, ALL are rolled back
})
```

## Data Access Layer

### Repository Pattern with Drizzle ORM
```typescript
// db/repositories/projects.ts
import { eq, and, sql } from 'drizzle-orm'
import { db } from '../client'
import { projects, projectStates } from '../schema'

export async function findProjectBySlug(slug: string): Promise<Project | null> {
  const [row] = await db
    .select()
    .from(projects)
    .where(eq(projects.slug, slug))
    .limit(1)

  return row ?? null
}

export async function createProject(data: NewProject): Promise<Project> {
  const [row] = await db
    .insert(projects)
    .values(data)
    .returning()

  return row
}

export async function listActiveProjects(cursor?: Date, limit = 20): Promise<Project[]> {
  return db
    .select()
    .from(projects)
    .where(
      and(
        eq(projects.status, 'active'),
        cursor ? sql`${projects.createdAt} < ${cursor}` : undefined,
      )
    )
    .orderBy(sql`${projects.createdAt} DESC`)
    .limit(limit)
}

// API handler uses the repository — no raw SQL in handlers
export default defineEventHandler(async (event) => {
  const slug = getRouterParam(event, 'slug')!
  const project = await findProjectBySlug(slug)
  if (!project) throw createError({ statusCode: 404 })
  return project
})
```

### SQLAlchemy Repository Pattern (Python)
```python
# repositories/projects.py
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from models import Project

class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_slug(self, slug: str) -> Project | None:
        stmt = select(Project).where(Project.slug == slug).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, name: str, slug: str) -> Project:
        project = Project(name=name, slug=slug, status="active")
        self.session.add(project)
        await self.session.flush()
        return project

    async def list_active(self, cursor: datetime | None = None, limit: int = 20) -> list[Project]:
        stmt = select(Project).where(Project.status == "active")
        if cursor:
            stmt = stmt.where(Project.created_at < cursor)
        stmt = stmt.order_by(Project.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

## PostgreSQL Deep Patterns

### JSONB Operators
```sql
-- Store semi-structured data alongside relational columns
ALTER TABLE projects ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}';

-- Containment: does metadata contain this sub-object?
SELECT * FROM projects WHERE metadata @> '{"tier": "enterprise"}';

-- Extract text value with ->>
SELECT metadata->>'tier' AS tier FROM projects;

-- Deep path extraction with #>>
SELECT metadata#>>'{billing,plan}' AS plan FROM projects;

-- Index for containment queries
CREATE INDEX idx_projects_metadata ON projects USING GIN (metadata);

-- Partial index on a JSONB field
CREATE INDEX idx_projects_enterprise
  ON projects ((metadata->>'tier'))
  WHERE metadata->>'tier' = 'enterprise';
```

### Array Types
```sql
-- PostgreSQL arrays for tags/labels
ALTER TABLE tasks ADD COLUMN tags TEXT[] NOT NULL DEFAULT '{}';

-- Query: find tasks with a specific tag
SELECT * FROM tasks WHERE 'urgent' = ANY(tags);

-- Query: find tasks with ALL of these tags
SELECT * FROM tasks WHERE tags @> ARRAY['urgent', 'backend'];

-- Index for array containment
CREATE INDEX idx_tasks_tags ON tasks USING GIN (tags);
```

### CTEs (WITH) and Window Functions
```sql
-- CTE for readability and reuse
WITH active_projects AS (
  SELECT id, name, created_at
  FROM projects
  WHERE status = 'active'
),
task_counts AS (
  SELECT project_id, COUNT(*) AS total_tasks,
         COUNT(*) FILTER (WHERE status = 'done') AS done_tasks
  FROM tasks
  GROUP BY project_id
)
SELECT ap.name, tc.total_tasks, tc.done_tasks,
       ROUND(tc.done_tasks::numeric / NULLIF(tc.total_tasks, 0) * 100, 1) AS pct_done
FROM active_projects ap
JOIN task_counts tc ON tc.project_id = ap.id
ORDER BY pct_done DESC;

-- Window functions: rank projects by task completion rate
SELECT name,
       done_tasks,
       total_tasks,
       ROW_NUMBER() OVER (ORDER BY done_tasks DESC) AS rank,
       RANK() OVER (PARTITION BY phase ORDER BY created_at) AS phase_rank
FROM project_summary;
```

### LISTEN / NOTIFY for Pub/Sub
```sql
-- Trigger-based notifications for real-time updates
CREATE OR REPLACE FUNCTION notify_task_change() RETURNS TRIGGER AS $$
BEGIN
  PERFORM pg_notify('task_changes', json_build_object(
    'op', TG_OP,
    'id', NEW.id,
    'project_id', NEW.project_id,
    'status', NEW.status
  )::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER task_change_trigger
  AFTER INSERT OR UPDATE ON tasks
  FOR EACH ROW EXECUTE FUNCTION notify_task_change();
```

```typescript
// Listen in Node.js
import pg from 'pg'
const listener = new pg.Client(process.env.DATABASE_URL)
await listener.connect()
await listener.query('LISTEN task_changes')
listener.on('notification', (msg) => {
  const payload = JSON.parse(msg.payload!)
  console.log('Task changed:', payload)
})
```

### Useful Extensions
```sql
-- Fuzzy text search with pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_projects_name_trgm ON projects USING GIN (name gin_trgm_ops);
-- Now supports: SELECT * FROM projects WHERE name % 'simlar' (typo-tolerant)
-- And: SELECT * FROM projects WHERE name ILIKE '%search%' (uses the GIN index)

-- Vector similarity search with pgvector
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE documents ADD COLUMN embedding vector(1536);
CREATE INDEX idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- Nearest neighbors: SELECT * FROM documents ORDER BY embedding <=> $1 LIMIT 10;

-- Query performance analysis
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
-- Top 10 slowest queries:
SELECT query, mean_exec_time, calls, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## MySQL Patterns

### InnoDB Essentials
```sql
-- InnoDB clusters data on primary key — PK choice affects ALL query performance
-- GOOD: auto-increment PK (sequential inserts, no page splits)
CREATE TABLE tasks (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  project_id BIGINT UNSIGNED NOT NULL,
  title VARCHAR(255) NOT NULL,
  status ENUM('pending', 'running', 'done', 'failed') NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_tasks_project_id (project_id),
  INDEX idx_tasks_status (status),
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
-- ALWAYS utf8mb4. Never utf8 (it's only 3 bytes, can't store emoji or many CJK characters)

-- BAD: UUID as PK in InnoDB (random inserts cause page splits, fragmentation)
-- If you must use UUID, use uuid_to_bin(uuid, 1) for swap-ordered binary storage
```

### EXPLAIN Output Interpretation
```sql
-- Always EXPLAIN queries that touch large tables
EXPLAIN SELECT * FROM tasks WHERE project_id = 1 AND status = 'pending';
-- Look for:
--   type: ref or range (GOOD), ALL (BAD — full table scan)
--   key: the index being used (NULL = no index)
--   rows: estimated rows examined (lower is better)
--   Extra: "Using index" (covering index), "Using filesort" (needs sorting in memory)

-- Covering index: query satisfied entirely from the index, no row lookup
CREATE INDEX idx_tasks_covering
  ON tasks (project_id, status, created_at, id);
-- This covers: SELECT id, status, created_at FROM tasks WHERE project_id = ? AND status = ?
```

### GROUP_CONCAT for Aggregation
```sql
-- Aggregate related values into a comma-separated list
SELECT p.name,
       GROUP_CONCAT(t.title ORDER BY t.created_at SEPARATOR ', ') AS task_titles,
       COUNT(t.id) AS task_count
FROM projects p
LEFT JOIN tasks t ON t.project_id = p.id
GROUP BY p.id, p.name;
```

## Connection Pooling

### Pool Sizing Formula
```
connections = (core_count * 2) + spindle_count
-- For SSD: spindle_count = 1
-- 4-core machine with SSD: (4 * 2) + 1 = 9 connections
-- More connections != better performance. Too many causes contention.
-- A pool of 10-20 connections handles thousands of requests/second.
```

### Node.js with pg Pool
```typescript
// db/client.ts
import pg from 'pg'

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,  // Backing service via env var
  max: 10,                                     // Max pool size
  idleTimeoutMillis: 30_000,                   // Close idle connections after 30s
  connectionTimeoutMillis: 5_000,              // Fail fast if can't connect in 5s
  allowExitOnIdle: true,                       // Let process exit if pool is idle
})

// Health check
pool.on('error', (err) => {
  console.error('Unexpected pool error:', err)
})

export { pool }
```

### Drizzle ORM with Pool
```typescript
// db/drizzle.ts
import { drizzle } from 'drizzle-orm/node-postgres'
import pg from 'pg'
import * as schema from './schema'

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
})

export const db = drizzle(pool, { schema })
```

### Python with SQLAlchemy Async Pool
```python
# db/engine.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    os.environ["DATABASE_URL"],  # e.g., postgresql+asyncpg://user:pass@host/db
    pool_size=10,
    max_overflow=5,              # Allow 5 extra connections under burst
    pool_timeout=5,              # Seconds to wait for a connection
    pool_recycle=1800,           # Recycle connections every 30 min (avoid stale)
    pool_pre_ping=True,          # Test connections before use
    echo=False,                  # Set True for SQL logging in dev
)

async_session = async_sessionmaker(engine, expire_on_commit=False)
```

### PgBouncer for PostgreSQL
```ini
; pgbouncer.ini — connection pooler sitting between app and PostgreSQL
[databases]
mydb = host=127.0.0.1 port=5432 dbname=mydb

[pgbouncer]
listen_port = 6432
listen_addr = 0.0.0.0
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction          ; Release connection after each transaction
default_pool_size = 20
max_client_conn = 200            ; Accept 200 app connections, funnel to 20 PG connections
server_idle_timeout = 600
```

## Redis / Caching Layer

### Cache-Aside Pattern (Read-Through)
```typescript
// The most common caching pattern: check cache first, fall back to DB
import Redis from 'ioredis'

const redis = new Redis(process.env.REDIS_URL)  // Backing service via env var

async function getProject(slug: string): Promise<Project> {
  const cacheKey = `project:${slug}`

  // 1. Check cache
  const cached = await redis.get(cacheKey)
  if (cached) return JSON.parse(cached)

  // 2. Miss — query database
  const project = await db.select().from(projects).where(eq(projects.slug, slug)).limit(1)
  if (!project[0]) throw new NotFoundError('Project not found')

  // 3. Populate cache with TTL
  await redis.set(cacheKey, JSON.stringify(project[0]), 'EX', 300)  // 5 min TTL

  return project[0]
}
```

### Cache Invalidation
```typescript
// Invalidate on write — the hardest problem in computer science
async function updateProject(slug: string, data: Partial<Project>): Promise<Project> {
  const [updated] = await db.update(projects)
    .set({ ...data, updatedAt: new Date() })
    .where(eq(projects.slug, slug))
    .returning()

  // Delete the cached entry — next read will repopulate
  await redis.del(`project:${slug}`)

  // For list caches, use key patterns or versioned keys
  await redis.del('projects:active:page:*')  // Not ideal at scale — use tags or versioning

  return updated
}

// GOOD: Versioned cache keys for list invalidation
async function listProjects(): Promise<Project[]> {
  const version = await redis.get('projects:version') ?? '0'
  const cacheKey = `projects:list:v${version}`
  const cached = await redis.get(cacheKey)
  if (cached) return JSON.parse(cached)

  const rows = await db.select().from(projects).where(eq(projects.status, 'active'))
  await redis.set(cacheKey, JSON.stringify(rows), 'EX', 600)
  return rows
}

// On any write: increment version to bust all list caches
await redis.incr('projects:version')
```

### Redis Data Structures
```typescript
// Sorted sets for leaderboards / ranking
await redis.zadd('leaderboard', score, `user:${userId}`)
const top10 = await redis.zrevrange('leaderboard', 0, 9, 'WITHSCORES')

// Pub/Sub for real-time events
const subscriber = new Redis(process.env.REDIS_URL)
await subscriber.subscribe('deployments')
subscriber.on('message', (channel, message) => {
  const event = JSON.parse(message)
  broadcast(event)  // Push to WebSocket clients
})

// Session storage with TTL
await redis.set(`session:${sessionId}`, JSON.stringify(sessionData), 'EX', 86400)  // 24h
```

### TTL Strategies
```
- User sessions: 24 hours
- API response cache: 1-5 minutes (high-traffic endpoints)
- Database query cache: 5-15 minutes
- Configuration cache: 1 hour
- Static reference data: 24 hours
- NEVER cache without a TTL — stale data is worse than no cache
```

## AWS Managed Databases

### RDS / Aurora (PostgreSQL & MySQL)

```yaml
# Terraform — RDS Aurora PostgreSQL cluster
resource "aws_rds_cluster" "main" {
  cluster_identifier     = "${var.project}-db"
  engine                 = "aurora-postgresql"
  engine_version         = "15.4"
  database_name          = var.db_name
  master_username        = var.db_username
  manage_master_user_password = true  # Let AWS manage the password in Secrets Manager
  storage_encrypted      = true
  deletion_protection    = true
  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"
  skip_final_snapshot    = false
  final_snapshot_identifier = "${var.project}-db-final"

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 16
  }
}

resource "aws_rds_cluster_instance" "writer" {
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.main.engine
}
```

### DynamoDB Single-Table Design

```typescript
// DynamoDB: one table, multiple entity types, access pattern-driven design
// Table: AppTable
// PK: partitionKey (string), SK: sortKey (string)
// GSI1: gsi1pk / gsi1sk for inverted access patterns

// Entity: Project
// PK=PROJECT#<id>  SK=METADATA
// GSI1PK=STATUS#active  GSI1SK=<created_at>

// Entity: Task
// PK=PROJECT#<id>  SK=TASK#<task_id>
// GSI1PK=STATUS#pending  GSI1SK=<created_at>

import { DynamoDBClient } from '@aws-sdk/client-dynamodb'
import { DynamoDBDocumentClient, PutCommand, QueryCommand } from '@aws-sdk/lib-dynamodb'

const client = DynamoDBDocumentClient.from(new DynamoDBClient({}))
const TABLE = process.env.DYNAMODB_TABLE!  // Backing service via env var

// Write a project
await client.send(new PutCommand({
  TableName: TABLE,
  Item: {
    pk: `PROJECT#${projectId}`,
    sk: 'METADATA',
    gsi1pk: `STATUS#active`,
    gsi1sk: new Date().toISOString(),
    name: 'My Project',
    slug: 'my-project',
    entityType: 'Project',
  },
}))

// Query all tasks for a project (PK = project, SK begins_with TASK#)
const result = await client.send(new QueryCommand({
  TableName: TABLE,
  KeyConditionExpression: 'pk = :pk AND begins_with(sk, :sk)',
  ExpressionAttributeValues: {
    ':pk': `PROJECT#${projectId}`,
    ':sk': 'TASK#',
  },
}))

// Query all pending tasks across projects (GSI1)
const pending = await client.send(new QueryCommand({
  TableName: TABLE,
  IndexName: 'gsi1',
  KeyConditionExpression: 'gsi1pk = :status',
  ExpressionAttributeValues: {
    ':status': 'STATUS#pending',
  },
  ScanIndexForward: false,  // Newest first
  Limit: 50,
}))
```

```yaml
# Terraform — DynamoDB table with GSI and TTL
resource "aws_dynamodb_table" "app" {
  name         = "${var.project}-table"
  billing_mode = "PAY_PER_REQUEST"  # On-demand: no capacity planning needed
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
  attribute {
    name = "gsi1pk"
    type = "S"
  }
  attribute {
    name = "gsi1sk"
    type = "S"
  }

  global_secondary_index {
    name            = "gsi1"
    hash_key        = "gsi1pk"
    range_key       = "gsi1sk"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}
```

### ElastiCache (Redis)
```yaml
# Terraform — ElastiCache Redis cluster
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.project}-redis"
  description          = "Redis for caching and sessions"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.t4g.micro"
  num_cache_clusters   = 2  # 1 primary + 1 replica
  port                 = 6379
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  automatic_failover_enabled = true
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  parameter_group_name = "default.redis7"
}
```

## High Availability

### Read Replicas
```typescript
// Route reads to replicas, writes to primary
import pg from 'pg'

const primary = new pg.Pool({
  connectionString: process.env.DATABASE_URL,        // Writer endpoint
  max: 10,
})

const replica = new pg.Pool({
  connectionString: process.env.DATABASE_REPLICA_URL, // Reader endpoint
  max: 10,
})

// Writes always go to primary
async function createTask(data: NewTask): Promise<Task> {
  const result = await primary.query(
    'INSERT INTO tasks (project_id, title, status) VALUES ($1, $2, $3) RETURNING *',
    [data.projectId, data.title, 'pending']
  )
  return result.rows[0]
}

// Reads that tolerate slight lag go to replica
async function listTasks(projectId: string): Promise<Task[]> {
  const result = await replica.query(
    'SELECT * FROM tasks WHERE project_id = $1 ORDER BY created_at DESC',
    [projectId]
  )
  return result.rows
}

// Reads that need consistency go to primary (e.g., right after a write)
async function getTaskAfterUpdate(taskId: string): Promise<Task> {
  const result = await primary.query('SELECT * FROM tasks WHERE id = $1', [taskId])
  return result.rows[0]
}
```

### Connection Failover
```typescript
// Handle failover gracefully — retry on connection errors
import pg from 'pg'

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
  connectionTimeoutMillis: 5_000,
})

async function queryWithRetry<T>(
  sql: string,
  params: unknown[],
  maxRetries = 3
): Promise<pg.QueryResult<T>> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await pool.query(sql, params)
    } catch (err: any) {
      const isTransient = [
        '57P01', // admin_shutdown
        '57P03', // cannot_connect_now
        '08006', // connection_failure
        '08001', // sqlclient_unable_to_establish_sqlconnection
      ].includes(err.code)

      if (isTransient && attempt < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 8000)
        console.warn(`DB connection error (${err.code}), retry ${attempt}/${maxRetries} in ${delay}ms`)
        await new Promise(r => setTimeout(r, delay))
        continue
      }
      throw err
    }
  }
  throw new Error('Unreachable')
}
```

### Backup and Point-in-Time Recovery
```
- RDS/Aurora: automated daily snapshots + continuous WAL archiving
  - Restore to any second within the retention window (up to 35 days)
  - Test restores quarterly — backups you've never tested are not backups
- DynamoDB: enable point-in-time recovery (PITR) on every table
  - Continuous backups with 35-day recovery window
  - On-demand backups for pre-migration snapshots
- Redis (ElastiCache): daily snapshots for disaster recovery
  - Redis is ephemeral by nature — never use it as the sole data store
```

## Quality Checklist

- [ ] Schema has appropriate constraints (NOT NULL, CHECK, UNIQUE, FK)
- [ ] Primary keys are stable (not business data)
- [ ] Foreign keys have ON DELETE behavior specified
- [ ] Indexes exist for frequent WHERE/JOIN/ORDER BY columns
- [ ] No N+1 query patterns
- [ ] Transactions used for multi-step mutations
- [ ] Migrations are reversible, tested, and TDD'd
- [ ] Queries use parameterized values (no string concatenation)
- [ ] Large result sets use keyset pagination
- [ ] Connection pool is sized correctly (not too large, not too small)
- [ ] Database URL comes from environment variables, never hardcoded
- [ ] Cache has TTL set on every key — no unbounded cache growth
- [ ] Read replicas used for read-heavy workloads
- [ ] Sensitive data is encrypted at rest (RDS encryption, DynamoDB SSE)

## Anti-Patterns

- **SELECT * in production** — Fetches columns you don't need, breaks when schema changes, prevents covering indexes.
- **SQL injection via string concatenation** — Always use parameterized queries. Always.
- **Missing indexes on foreign keys** — Every FK column needs an index, or JOINs and CASCADE deletes become full scans.
- **OFFSET pagination on large datasets** — O(n) cost. Use keyset/cursor pagination instead.
- **Hardcoded connection strings** — Database URLs belong in environment variables. Treat databases as attached backing services.
- **No constraints in the schema** — "We'll validate in the app" is wishful thinking. Apps have bugs, constraints don't.
- **Unbounded cache without TTL** — Every cached key must expire. Stale data is a production incident waiting to happen.
- **UUID primary keys in MySQL InnoDB** — Random UUIDs cause page splits and fragmentation. Use auto-increment or ordered UUIDs.
- **Over-indexing write-heavy tables** — Every index slows INSERT/UPDATE. Profile before adding indexes.
- **Using Redis as sole data store** — Redis is ephemeral. It complements your database, it doesn't replace it.
