---
name: database
description: >
  Design and implement database schemas, queries, and data access patterns with focus on
  correctness, performance, and maintainability. Covers schema design, migrations, indexing,
  query optimization, ORMs, and data integrity. Trigger this skill for any task involving
  databases, data models, schemas, migrations, queries, or data access layers.
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
  - mysql
  - mongo
  - model
  - table
  - index
  - orm
---

# Database Excellence

A database is the foundation of your application — get it wrong and everything built on top wobbles. Design schemas that model your domain accurately, write queries that perform well at scale, and treat migrations as first-class code.

## Core Principles

1. **Model the domain, not the UI** — Schema should reflect business entities and relationships, not what a particular page needs to display.
2. **Data integrity is non-negotiable** — Use constraints, foreign keys, and transactions. The database is your last line of defense against bad data.
3. **Optimize for reads you actually make** — Don't index everything. Don't denormalize everything. Profile first, optimize second.

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

  -- Composite constraints
  CONSTRAINT valid_name CHECK (length(name) BETWEEN 1 AND 200)
);

-- Partial unique index (unique only among non-deleted)
CREATE UNIQUE INDEX idx_projects_name_active
  ON projects (name)
  WHERE status != 'deleted';
```

## Migrations

### Rules
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

-- Adding an index concurrently (safe — no table lock in Postgres)
CREATE INDEX CONCURRENTLY idx_tasks_status ON tasks(status);

-- DANGEROUS: Renaming a column (breaks existing queries)
-- Instead: add new column, migrate data, update code, drop old column
ALTER TABLE projects ADD COLUMN display_name TEXT;
UPDATE projects SET display_name = name;
-- Deploy code that reads display_name
-- Later: ALTER TABLE projects DROP COLUMN name;

-- DANGEROUS: Changing column type
-- Instead: add new column with new type, migrate, swap
```

## Indexing

### When to Index
```sql
-- Index columns that appear in:
-- WHERE clauses
CREATE INDEX idx_tasks_status ON tasks(status);

-- JOIN conditions
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

-- Use EXISTS instead of COUNT for existence checks
-- BAD
SELECT COUNT(*) FROM tasks WHERE project_id = ? AND status = 'running';
-- GOOD
SELECT EXISTS(SELECT 1 FROM tasks WHERE project_id = ? AND status = 'running');

-- Pagination: use keyset (cursor) pagination for large datasets
-- BAD (slow on large offsets)
SELECT * FROM tasks ORDER BY created_at DESC LIMIT 20 OFFSET 10000;
-- GOOD (fast regardless of position)
SELECT * FROM tasks WHERE created_at < ? ORDER BY created_at DESC LIMIT 20;

-- Batch operations instead of loops
-- BAD: N+1 queries
for (const id of taskIds) {
  await db.query('UPDATE tasks SET status = ? WHERE id = ?', ['done', id])
}
-- GOOD: single query
await db.query('UPDATE tasks SET status = ? WHERE id = ANY(?)', ['done', taskIds])
```

### N+1 Query Prevention
```typescript
// BAD — N+1: one query per project
const projects = await db.query('SELECT * FROM projects')
for (const project of projects) {
  project.tasks = await db.query('SELECT * FROM tasks WHERE project_id = ?', [project.id])
}

// GOOD — 2 queries total
const projects = await db.query('SELECT * FROM projects')
const projectIds = projects.map(p => p.id)
const tasks = await db.query('SELECT * FROM tasks WHERE project_id = ANY(?)', [projectIds])

// Group tasks by project
const tasksByProject = new Map()
for (const task of tasks) {
  if (!tasksByProject.has(task.project_id)) tasksByProject.set(task.project_id, [])
  tasksByProject.get(task.project_id).push(task)
}
```

## Transactions

```typescript
// Use transactions for operations that must be atomic
await db.transaction(async (tx) => {
  // Create project
  const project = await tx.insert(projects).values({ name, slug }).returning()

  // Create initial state
  await tx.insert(projectStates).values({
    projectId: project.id,
    phase: 'interview',
    status: 'active',
  })

  // Create activity log entry
  await tx.insert(activityLog).values({
    projectId: project.id,
    type: 'created',
    message: 'Project created',
  })

  // If ANY of these fail, ALL are rolled back
})
```

## Data Access Layer

### Repository Pattern
```typescript
// Keep database logic in dedicated modules
// db/projects.ts
export async function findProjectByName(name: string): Promise<Project | null> {
  const [row] = await db
    .select()
    .from(projects)
    .where(eq(projects.name, name))
    .limit(1)

  return row || null
}

export async function createProject(data: NewProject): Promise<Project> {
  const [row] = await db
    .insert(projects)
    .values(data)
    .returning()

  return row
}

// API handler uses the repository — no raw SQL in handlers
export default defineEventHandler(async (event) => {
  const project = await findProjectByName(name)
  if (!project) throw createError({ statusCode: 404 })
  return project
})
```

## File-Based Data (JSONL/JSON)

When using file-based storage (like SwarmOps does for activity logs):

```typescript
// JSONL for append-only logs (activity.jsonl)
// Advantages: append is atomic, no read-modify-write, easy to stream
await appendFile(activityPath, JSON.stringify(event) + '\n')

// JSON for state (state.json)
// Always write atomically (write to temp, rename)
const tempPath = statePath + '.tmp'
await writeFile(tempPath, JSON.stringify(state, null, 2))
await rename(tempPath, statePath)  // Atomic on same filesystem

// Handle concurrent reads during writes
try {
  const data = await readFile(path, 'utf-8')
  return JSON.parse(data)
} catch (err) {
  if (err.code === 'ENOENT') return defaultValue
  throw err  // Re-throw unexpected errors
}
```

## Quality Checklist

- [ ] Schema has appropriate constraints (NOT NULL, CHECK, UNIQUE, FK)
- [ ] Primary keys are stable (not business data)
- [ ] Foreign keys have ON DELETE behavior specified
- [ ] Indexes exist for frequent WHERE/JOIN/ORDER BY columns
- [ ] No N+1 query patterns
- [ ] Transactions used for multi-step mutations
- [ ] Migrations are reversible and tested
- [ ] Queries use parameterized values (no string concatenation)
- [ ] Large result sets are paginated
- [ ] Sensitive data is encrypted at rest where required

## Anti-Patterns

- Using SELECT * in production code
- String-concatenating user input into queries (SQL injection)
- Missing indexes on foreign key columns
- Using OFFSET pagination for large datasets
- Storing JSON blobs when structured columns would be better
- No constraints ("we'll validate in the app") — apps have bugs, databases don't forget
- Running schema changes without migrations
- Mixing business logic into raw SQL queries
- Not handling concurrent access (read-modify-write without transactions)
- Over-indexing tables that are write-heavy
