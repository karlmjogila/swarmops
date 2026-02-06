# SwarmOps

**Multi-agent orchestration platform for AI-powered software development.**

SwarmOps coordinates multiple AI agents to work on software projects in parallel — decomposing tasks, spawning workers, merging results, and handling code reviews automatically.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

### 🤖 Parallel Agent Orchestration
- Spawn multiple AI workers simultaneously
- Automatic task decomposition and assignment
- Smart merge conflict resolution with task-aware context
- Git worktree isolation for parallel development

### 📊 Real-time Dashboard
- Project monitoring with live status updates
- Visual pipeline editor with drag-and-drop
- Worker tracking and log viewing
- Activity timeline and ledger

### 🔄 Intelligent Workflows
- Customizable pipelines (interview → spec → build → review → fix)
- Role-based agents with tailored prompts
- Automatic phase advancement
- Review-fix loops with escalation

### 🛡️ Resilience
- Circuit breaker for spawn protection
- Retry handling with exponential backoff
- Progress watchdog for stuck workers
- Graceful error escalation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SwarmOps Dashboard                      │
│                      (Nuxt 4 + Vue 3)                        │
├─────────────────────────────────────────────────────────────┤
│  Projects │ Pipelines │ Roles │ Workers │ Ledger │ Docs    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Engine                       │
├─────────────────────────────────────────────────────────────┤
│  Phase Collector │ Task Queue │ Worker Tracker │ Merger    │
│  Review Handler  │ Retry Logic │ Spawn Guard   │ Ledger    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      OpenClaw Gateway                        │
│              (sessions_spawn / sessions_send)                │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- **Node.js** 20+ (22 recommended)
- **pnpm** (preferred) or npm
- **OpenClaw** with `sessions_spawn` capability
- **Git** for worktree management

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/siimvene/SwarmOps.git
cd SwarmOps

# Install dashboard dependencies
cd dashboard
pnpm install

# Install orchestrator package (optional, for programmatic use)
cd ../packages/orchestrator
pnpm install
```

### 2. Configure Environment

```bash
cd dashboard
cp .env.example .env
```

Edit `.env`:
```env
# Path to your projects directory
PROJECTS_DIR=/path/to/your/projects

# Data directory for orchestrator state
ORCHESTRATOR_DATA_DIR=/path/to/swarmops/data/orchestrator

# OpenClaw gateway URL
OPENCLAW_GATEWAY_URL=http://localhost:3284

# Server binding
HOST=0.0.0.0
PORT=3939
```

### 3. Initialize Data

```bash
cd ../data/orchestrator
cp roles.example.json roles.json
cp pipelines.example.json pipelines.json
```

### 4. Start the Dashboard

```bash
cd ../../dashboard
pnpm dev
```

Visit `http://localhost:3939` (or your Tailscale IP for remote access).

## Project Structure

```
SwarmOps/
├── dashboard/                  # Nuxt 4 web dashboard
│   ├── app/                   # Vue components, pages, composables
│   │   ├── components/        # UI components
│   │   │   ├── pipeline/      # Visual pipeline editor
│   │   │   └── ui/           # Base UI components
│   │   ├── composables/       # Vue composables
│   │   ├── pages/            # Route pages
│   │   └── types/            # TypeScript types
│   ├── server/               # Nitro server
│   │   ├── api/              # API endpoints
│   │   └── utils/            # Server utilities
│   │       ├── phase-collector.ts      # Task collection
│   │       ├── phase-merger.ts         # Result merging
│   │       ├── worker-tracker.ts       # Worker monitoring
│   │       ├── spawn-guard.ts          # Rate limiting
│   │       └── smart-conflict-resolver.ts
│   └── tests/                # Test suites
├── packages/
│   └── orchestrator/         # Core orchestrator library
│       ├── src/
│       │   ├── api/          # REST API routes
│       │   ├── services/     # Business logic
│       │   ├── storage/      # Data persistence
│       │   └── types/        # TypeScript types
│       └── tests/
└── data/                     # Runtime data (gitignored)
    └── orchestrator/
        ├── roles.json        # Agent role definitions
        ├── pipelines.json    # Pipeline graphs
        └── ledger.jsonl      # Event log
```

## How It Works

### 1. Project Creation
Create a project with requirements. SwarmOps initializes a `state.json` and `progress.md`.

### 2. Task Decomposition
The task-decomposer agent breaks requirements into parallelizable tasks with dependencies.

### 3. Parallel Execution
Workers spawn in isolated git worktrees, each implementing their assigned task.

### 4. Smart Merging
When workers complete, SwarmOps:
- Collects all changes
- Detects conflicts
- Uses task-aware AI to resolve conflicts intelligently
- Merges to main branch

### 5. Review Loop
A reviewer agent checks the merged code. Issues get assigned back to fix agents. This loops until quality gates pass.

## API Reference

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all projects |
| POST | `/api/projects` | Create new project |
| GET | `/api/projects/:name` | Get project details |
| POST | `/api/projects/:name/control` | Control project (pause/resume/kill) |
| POST | `/api/projects/:name/orchestrate` | Start orchestration |

### Pipelines
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orchestrator/pipelines` | List pipelines |
| POST | `/api/orchestrator/pipelines` | Create pipeline |
| PUT | `/api/orchestrator/pipelines/:id` | Update pipeline |
| DELETE | `/api/orchestrator/pipelines/:id` | Delete pipeline |
| POST | `/api/orchestrator/pipelines/:id/run` | Execute pipeline |

### Roles
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orchestrator/roles` | List roles |
| POST | `/api/orchestrator/roles` | Create role |
| PUT | `/api/orchestrator/roles/:id` | Update role |
| DELETE | `/api/orchestrator/roles/:id` | Delete role |

### Workers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orchestrator/workers` | List active workers |
| GET | `/api/orchestrator/workers/:id/logs` | Get worker logs |
| GET | `/api/orchestrator/worker-tracker` | Get tracker state |

### WebSocket
Connect to `/_ws` for real-time updates on project status, worker progress, and phase transitions.

## Configuration

### Roles
Define agent personas in `data/orchestrator/roles.json`:

```json
{
  "id": "builder",
  "name": "Builder",
  "model": "claude-sonnet-4",
  "thinking": "low",
  "prompt": "You are a skilled developer..."
}
```

**Models**: `claude-opus-4`, `claude-sonnet-4`, `claude-haiku-3`
**Thinking**: `off`, `low`, `medium`, `high`

### Pipelines
Create execution graphs with the visual editor or JSON:

- **Start Node**: Entry point
- **Role Nodes**: Agent execution steps
- **End Node**: Completion marker
- **Edges**: Define flow and parallelism

## Development

### Running Tests

```bash
# Dashboard tests
cd dashboard
pnpm test

# Orchestrator tests
cd packages/orchestrator
pnpm test
```

### Building for Production

```bash
cd dashboard
pnpm build
node .output/server/index.mjs
```

## Integration with OpenClaw

SwarmOps uses OpenClaw's native session management:

```typescript
// Spawn a worker
sessions_spawn({
  task: "Implement feature X",
  agentId: "swarmops-builder",
  label: "worker-feature-x",
  model: "claude-sonnet-4",
  thinking: "low"
});

// Check worker status
sessions_list({ kinds: ["isolated"] });

// Get worker output
sessions_history({ sessionKey: "..." });
```

## Troubleshooting

### Workers not spawning
- Check OpenClaw gateway is running (`openclaw status`)
- Verify `OPENCLAW_GATEWAY_URL` in `.env`
- Check spawn guard status: `GET /api/orchestrator/spawn-guard`

### Merge conflicts
- Smart resolver logs to `data/orchestrator/ledger.jsonl`
- Manual resolution available via dashboard

### Memory issues
- Server needs ~2GB RAM minimum
- Add swap for npm/pnpm heavy operations
- Monitor with `htop` during builds

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

---

Built with [OpenClaw](https://github.com/openclaw/openclaw) 🦞
