# Agent Context and Spawning

SwarmOps spawns AI agents via OpenClaw Gateway (`sessions_spawn`). Each agent receives a role-specific prompt with the context it needs.

## Role-Based Spawning

All agent spawns go through `spawnSession()` in `gateway-client.ts`. The model and thinking level come from the agent's role configuration:

```typescript
const role = await getRoleConfig(task.role || 'builder')
await spawnSession({
  task: prompt,
  label: uniqueLabel(`swarm:${projectName}:${taskId}`),
  model: role.model,      // From roles.json
  thinking: role.thinking, // From roles.json
})
```

### Available Roles

| Role | Purpose | Default Model | Thinking |
|------|---------|--------------|----------|
| architect | System design, implementation planning | Claude Opus 4 | high |
| task-decomposer | Break specs into parallelizable tasks | Claude Opus 4 | high |
| builder | Implement code from task descriptions | Claude Sonnet 4 | low |
| reviewer | General code quality review | Claude Opus 4 | high |
| security-reviewer | Security-focused code review | Claude Opus 4 | high |
| designer | Frontend/UI review | Claude Sonnet 4 | medium |
| workflow-coordinator | Multi-step workflow management | Claude Sonnet 4 | medium |
| researcher | Deep investigation and analysis | Claude Opus 4 | high |

Roles are configured in `/home/siim/swarmops/data/orchestrator/roles.json` and loaded via `getRoleConfig()` with 30s caching.

---

## Agent Types by Phase

### Interview Agent
- **Role**: None (uses default model)
- **Prompt**: Asks clarifying questions about project goals
- **Completion**: Sets `interview.json` `complete: true`
- **Callback**: `POST /api/projects/{name}/interview`

### Spec Agent (Architect + Task Decomposer)
- **Roles**: `architect` + `task-decomposer` (combined prompt)
- **Model**: Uses architect's model (Claude Opus 4) and thinking (high)
- **Prompt includes**: Both role instructions, interview messages, available `@role()` values
- **Output**: Creates `IMPLEMENTATION_PLAN.md` and populates `progress.md`
- **Callback**: `POST /api/projects/{name}/spec-complete`

### Builder Agent
- **Role**: Per-task from `@role()` annotation (default: `builder`)
- **Model**: From task's role config
- **Prompt includes**: Task description, worktree path, worker branch, completion endpoint
- **Callback**: `POST /api/projects/{name}/task-complete`

### Review Chain Agents
- **Roles**: `reviewer` -> `security-reviewer` -> `designer` (sequential)
- **Model**: Per role config
- **Prompt includes**: Role-specific review instructions, phase branch diff, decision endpoint
- **Callback**: `POST /api/orchestrator/review-result`

### Fixer Agent
- **Role**: Uses `builder` role config
- **Prompt includes**: Fix instructions from reviewer, phase branch path
- **Callback**: `POST /api/orchestrator/fix-complete`

### Conflict Resolver Agent
- **Role**: Uses `builder` role config
- **Prompt includes**: Conflicted files, task context, merge state

---

## Worker Prompts

Workers receive detailed prompts with everything needed:

```
[SWARMOPS WORKER] Task: {task.title}

**Your Task:** {task.description}
**Working Directory:** {worktreePath}
**Branch:** {workerBranch}
**Files to modify:** {task.files}

**When done:**
curl -X POST http://localhost:3939/api/projects/{name}/task-complete \
  -d '{"taskId":"{id}","runId":"{runId}","phaseNumber":{N},"success":true,"message":"..."}'

**On error:**
curl -X POST http://localhost:3939/api/projects/{name}/task-complete \
  -d '{"taskId":"{id}","runId":"{runId}","phaseNumber":{N},"success":false,"message":"..."}'
```

---

## Context Isolation

### Git Worktrees
Each builder gets an isolated git worktree:
```
/tmp/swarmops-worktrees/{runId}/{workerId}/
```
- Separate directory and branch per worker
- Branch naming: `swarmops/{runId}/worker-{workerId}`
- Workers commit independently; phase merger collects branches after completion

### Session Labels
Labels identify sessions in OpenClaw. Auto-uniquified with timestamp suffix (max 64 chars).

| Agent Type | Label Pattern |
|------------|--------------|
| Interview | `swarm:interview:{project}` |
| Spec | `swarm:{project}:spec-gen` |
| Builder | `swarm:{project}:{taskId}` |
| Reviewer | `swarm:{project}:reviewer` |
| Security Reviewer | `swarm:{project}:sec-review` |
| Designer | `swarm:{project}:designer` |
| Fixer | `swarm:{project}:fixer` |

---

## Agent Communication

Agents communicate back via HTTP callbacks:
```
Gateway -> Spawn Agent -> Agent Works -> HTTP Callback -> SwarmOps Dashboard
                                              |
                          task-complete / review-result / fix-complete
```

**Key endpoints agents call:**
- `POST /api/projects/{name}/task-complete` -- builder finished
- `POST /api/projects/{name}/interview` -- interview response
- `POST /api/projects/{name}/spec-complete` -- spec phase done
- `POST /api/orchestrator/review-result` -- reviewer decision
- `POST /api/orchestrator/fix-complete` -- fixer finished

---

## Cleanup

- **After phase**: Worktrees cleaned via `cleanupRunWorktrees(runId)`
- **After project**: Task states and retry states cleared
- **Stale sessions**: `cleanup: 'delete'` auto-deletes sessions; registry clears tasks >1hr old
