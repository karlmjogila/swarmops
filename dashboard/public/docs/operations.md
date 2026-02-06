# SwarmOps Operations Guide

Quick reference for running, debugging, and maintaining SwarmOps.

## Starting the Dashboard

```bash
cd /home/siim/swarmops/projects/swarmops-dashboard/src
NUXT_TELEMETRY_DISABLED=1 nohup npx nuxi dev --port 3939 --host 0.0.0.0 > /tmp/nuxt-dev.log 2>&1 &
```

Monitor: `tail -f /tmp/nuxt-dev.log`

## OpenClaw Gateway

```bash
# Check status
ps aux | grep openclaw-gateway

# Restart
pkill -f openclaw-gateway && openclaw gateway start &

# Check version
cat ~/.npm-global/lib/node_modules/openclaw/package.json | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])"

# Update
npm install -g openclaw@latest
```

**After gateway restart, always reset spawn guard:**
```bash
curl -X POST http://localhost:3939/api/orchestrator/spawn-guard \
  -H "Content-Type: application/json" -d '{"action": "reset"}'
```

---

## Role Management

Roles control which model and thinking level each agent type uses.

```bash
# View roles
curl http://localhost:3939/api/orchestrator/roles

# Update a role's model
curl -X PUT http://localhost:3939/api/orchestrator/roles/builder \
  -H "Content-Type: application/json" \
  -d '{"model": "anthropic/claude-sonnet-4-5", "thinking": "medium"}'

# Check supported models in OpenClaw
grep -o "anthropic/claude[^\"]*" ~/.npm-global/lib/node_modules/openclaw/dist/config-*.js | sort -u
```

Role cache: 30s TTL, auto-invalidated on API CRUD operations.

---

## Common Issues & Fixes

### Unknown Model Error
```bash
# Check if model is in OpenClaw's registry
grep "claude" ~/.npm-global/lib/node_modules/openclaw/dist/config-*.js | sort -u
# If not found: npm install -g openclaw@latest
```

### Circuit Breaker Stuck Open
```bash
curl http://localhost:3939/api/orchestrator/spawn-guard    # Check
curl -X POST http://localhost:3939/api/orchestrator/spawn-guard -d '{"action":"reset"}'  # Reset
```

### Task Shows "Running" But Nothing Happening
```bash
cat /home/siim/swarmops/data/orchestrator/task-registry.json | python3 -m json.tool
curl -X POST http://localhost:3939/api/orchestrator/cleanup-stale
```

### Review Chain Stuck
```bash
cat /home/siim/swarmops/data/orchestrator/reviews/{runId}-phase-{N}.json | python3 -m json.tool
# Re-trigger review:
curl -X POST http://localhost:3939/api/orchestrator/merge-phase \
  -d '{"runId":"run-...","phaseNumber":1}'
```

---

## State Files Reference

| File | Purpose | Safe to Delete? |
|------|---------|-----------------|
| `roles.json` | Role configurations | **No** |
| `retry-state.json` | Per-task retry tracking | Yes |
| `task-registry.json` | Task running/completed | Yes |
| `escalations.json` | Human escalation queue | Yes |
| `ledger.jsonl` | System event log | Yes |
| `phases/*.json` | Phase tracking | Yes |
| `reviews/*.json` | Review chain state | Yes |
| `project-runs/*.json` | Run metadata | Yes |

**Full reset:**
```bash
rm -f /home/siim/swarmops/data/orchestrator/{retry-state,task-registry,escalations,work-queue}.json
rm -rf /home/siim/swarmops/data/orchestrator/{project-runs,phases,reviews}/*
rm -rf /tmp/swarmops-worktrees/*
```

---

## Monitoring

```bash
# Dashboard logs
tail -f /tmp/nuxt-dev.log

# Project activity
tail -f /home/siim/swarmops/projects/{name}/activity.jsonl

# System ledger (last 20 events)
tail -20 /home/siim/swarmops/data/orchestrator/ledger.jsonl

# Active workers
curl http://localhost:3939/api/orchestrator/workers

# Health check
curl -s http://localhost:3939/api/projects > /dev/null && echo "Dashboard: OK"
curl -s http://127.0.0.1:18789/ > /dev/null && echo "Gateway: OK"
```

---

## Worktree Cleanup

```bash
rm -rf /tmp/swarmops-worktrees/*   # All (safe when no builds running)
rm -rf /tmp/swarmops-worktrees/run-{runId}*  # Specific run
```
