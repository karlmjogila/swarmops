# SwarmOps Data Directory

This directory contains runtime data for SwarmOps orchestration.

## Structure

```
data/orchestrator/
├── roles.json              # Role definitions (agents with prompts)
├── pipelines.json          # Pipeline definitions (execution graphs)
├── ledger.jsonl            # Event log (append-only)
├── task-registry.json      # Active task tracking
├── phases/                 # Phase state files
├── project-runs/           # Per-project run state
├── prompts/                # Shared prompt templates
├── runs/                   # Pipeline run history
├── sessions/               # Session tracking
└── work/                   # Work queue state
```

## Getting Started

1. Copy example files to create your initial configuration:
   ```bash
   cp roles.example.json roles.json
   cp pipelines.example.json pipelines.json
   ```

2. Customize roles with your own prompts and model preferences.

3. Create pipelines using the dashboard's visual editor.

## Files

### roles.json
Array of role definitions. Each role has:
- `id` — Unique identifier
- `name` — Display name
- `model` — Claude model (claude-opus-4, claude-sonnet-4, etc.)
- `thinking` — Thinking level (off, low, medium, high)
- `prompt` — System prompt for the agent

### pipelines.json
Array of pipeline definitions with Vue Flow graph structure:
- `nodes` — Array of start, end, and role nodes
- `edges` — Connections between nodes

### ledger.jsonl
Append-only event log tracking all orchestration events:
- Worker spawns and completions
- Phase transitions
- Reviews and escalations
- Errors and retries

## Example Files

- `roles.example.json` — Starter roles (architect, builder, reviewer, task-decomposer)
- `pipelines.example.json` — Simple build-review pipeline template
