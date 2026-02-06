# SwarmOps Dashboard

A real-time web dashboard for monitoring and controlling SwarmOps AI orchestration projects.

## Features

### Project Management
- **Project Overview**: View all projects with status badges (running, paused, completed, error)
- **Real-time Updates**: WebSocket-based live updates when project state changes
- **Project Details**: See progress, implementation plans, specs, and iteration history
- **Control Panel**: Kill, pause, resume, trigger, and change phases for any project
- **Iteration Logs**: View detailed logs for each build iteration

### Pipeline Editor
- **Visual Editor**: Drag-and-drop pipeline builder with Vue Flow
- **Node Types**: Start, End, and Role nodes for defining execution flow
- **Real-time Validation**: Cycle detection, orphan node warnings, structural validation
- **Auto Layout**: Dagre-based automatic graph arrangement
- **Execution Monitoring**: Live status updates during pipeline runs
- **Log Viewer**: Real-time agent logs with search and filtering
- **Undo/Redo**: Full history support with keyboard shortcuts

See [Pipeline Editor Documentation](app/components/pipeline/README.md) for details.

## Tech Stack

- **Nuxt 4** (Vue 3 + Nitro)
- **TypeScript**
- **Nuxt UI** (Tailwind CSS)
- **WebSocket** (real-time updates)

## Setup

### Prerequisites

- Node.js 20+
- pnpm

### Installation

```bash
# Install dependencies
pnpm install

# Copy environment config
cp .env.example .env

# Edit .env with your projects directory
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECTS_DIR` | Path to projects directory | `/home/siim/swarmops/projects` |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `3939` |

## Development

Start the development server:

```bash
pnpm dev
```

The dashboard will be available at `http://localhost:3939` (or your Tailscale IP on port 3939).

## Production

Build for production:

```bash
pnpm build
```

Preview the production build:

```bash
pnpm preview
```

Run the production server:

```bash
# Using Node
node .output/server/index.mjs

# With custom host/port
HOST=0.0.0.0 PORT=3939 node .output/server/index.mjs
```

## Project Structure

```
src/
├── app/
│   ├── components/
│   │   ├── pipeline/         # Pipeline editor components
│   │   │   ├── README.md     # Pipeline editor documentation
│   │   │   ├── PipelineCanvas.vue
│   │   │   ├── PipelineSidebar.vue
│   │   │   ├── PipelineToolbar.vue
│   │   │   ├── PipelinePropertiesPanel.vue
│   │   │   ├── KeyboardShortcutsHelp.vue
│   │   │   ├── LogViewerModal.vue
│   │   │   ├── RoleNode.vue
│   │   │   └── nodes/
│   │   │       ├── StartNode.vue
│   │   │       └── EndNode.vue
│   │   ├── ControlBar.vue
│   │   ├── ProjectDetail.vue
│   │   └── ...
│   ├── composables/
│   │   ├── usePipeline.ts              # Pipeline CRUD
│   │   ├── usePipelineValidation.ts    # Graph validation
│   │   ├── usePipelineExecution.ts     # Execution monitoring
│   │   ├── usePipelineExecutionContext.ts
│   │   ├── useAutoLayout.ts            # Dagre layout
│   │   ├── useUndoRedo.ts              # History management
│   │   ├── useAutoSave.ts              # Debounced saving
│   │   ├── useProjects.ts
│   │   └── useWebSocket.ts
│   ├── types/
│   │   └── pipeline.ts     # Pipeline type definitions
│   ├── layouts/
│   │   └── default.vue
│   └── pages/
│       ├── index.vue
│       ├── pipelines.vue
│       ├── pipelines/
│       │   ├── index.vue
│       │   └── [id].vue    # Pipeline editor page
│       └── project/[name].vue
├── server/
│   ├── api/
│   │   ├── projects/
│   │   └── orchestrator/
│   │       ├── pipelines.get.ts
│   │       ├── pipelines.post.ts
│   │       ├── pipelines/[id].get.ts
│   │       ├── pipelines/[id].put.ts
│   │       ├── pipelines/[id].delete.ts
│   │       ├── pipelines/[id]/run.post.ts
│   │       ├── pipelines/[id]/runs.get.ts
│   │       ├── roles.get.ts
│   │       ├── roles.post.ts
│   │       ├── workers.get.ts
│   │       └── workers/[sessionId]/logs.get.ts
│   ├── plugins/
│   │   └── websocket.ts
│   └── routes/
│       └── _ws.ts
├── types/
│   └── project.ts
└── nuxt.config.ts
```

## API Endpoints

### Projects
- `GET /api/projects` - List all projects
- `GET /api/projects/:name` - Get project details
- `POST /api/projects/:name/control` - Control project (kill, pause, resume, trigger, phase-change)

### Pipelines
- `GET /api/orchestrator/pipelines` - List all pipelines
- `POST /api/orchestrator/pipelines` - Create pipeline
- `GET /api/orchestrator/pipelines/:id` - Get pipeline by ID
- `PUT /api/orchestrator/pipelines/:id` - Update pipeline
- `DELETE /api/orchestrator/pipelines/:id` - Delete pipeline
- `POST /api/orchestrator/pipelines/:id/run` - Run pipeline
- `GET /api/orchestrator/pipelines/:id/runs` - Get pipeline run history

### Roles
- `GET /api/orchestrator/roles` - List all roles
- `POST /api/orchestrator/roles` - Create role
- `PUT /api/orchestrator/roles/:id` - Update role
- `DELETE /api/orchestrator/roles/:id` - Delete role

### Execution
- `GET /api/orchestrator/runs` - Get active pipeline runs
- `GET /api/orchestrator/workers` - Get active workers
- `GET /api/orchestrator/workers/:sessionId/logs` - Get worker logs

### WebSocket
- `/_ws` - Real-time project and execution updates

## Tailscale Access

The dashboard binds to `0.0.0.0` by default, making it accessible on your Tailscale network. Access it via your machine's Tailscale IP:

```
http://<tailscale-ip>:3939
```

## License

MIT
