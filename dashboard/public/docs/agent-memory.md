# Agent Memory: swarmops-dashboard

Lessons learned and patterns to remember across iterations.

---

## Entries

### Problem: Retry state shared across all tasks in a phase

**Wrong:**
```typescript
// All tasks share one retry counter
const stepOrder = phaseNumber
const retryState = await getRetryState(runId, stepOrder)
```

**Correct:**
```typescript
// Each task has its own retry counter
const stepOrder = phaseNumber * 100000 + hashTaskId(taskId)
const retryState = await getRetryState(runId, stepOrder)
```

**Why:** When 6 tasks fail once each, the shared counter hits 6 attempts and exhausts, even though each task only failed once.

---

### Problem: Activity icons wrong for quick operations

**Wrong:**
```typescript
// Interview agent wake logged as 'spawn' → shows "ongoing" forever
type: 'spawn',
message: 'Interview agent woken to continue conversation'
```

**Correct:**
```typescript
// Use 'event' for quick one-shot operations
type: 'event',
message: 'Waiting for agent response...'

// Log completion when agent responds
type: 'complete',
message: 'Agent responded in interview'
```

**Why:** `spawn` type maps to "working" (ongoing) icon. Quick operations should use `event` (info icon).

---

### Problem: Phase change logged even when phase unchanged

**Wrong:**
```typescript
await logActivity(projectPath, projectName, 'phase-change', 
  `Auto-advanced: ${oldPhase} → ${newPhase}`)
// Logs "spec → spec" when called twice
```

**Correct:**
```typescript
if (oldPhase !== newPhase) {
  await logActivity(projectPath, projectName, 'phase-change', 
    `Auto-advanced: ${oldPhase} → ${newPhase}`)
}
```

---

### Problem: Spawns fail after gateway issues

**Wrong:**
```typescript
// Just retry immediately
await wakeAgent(prompt, label)
```

**Correct:**
```typescript
// Check spawn guard before spawning
const guard = await getSpawnGuard()
if (guard.circuitOpen) {
  console.log('Circuit open, waiting...')
  return { willRetry: true, delayMs: guard.circuitOpensIn }
}

// And implement exponential backoff
const delay = baseDelay * Math.pow(2, attemptNumber)
```

---

### Problem: Simultaneous spawns overwhelm gateway

**Wrong:**
```typescript
await Promise.all(tasks.map(t => wakeAgent(buildPrompt(t))))
```

**Correct:**
```typescript
const SPAWN_DELAY_MS = 3000
for (let i = 0; i < tasks.length; i++) {
  if (i > 0) await sleep(SPAWN_DELAY_MS)
  await wakeAgent(buildPrompt(tasks[i]))
}
```

---

### Problem: Session labels collide on retry

**Wrong:**
```typescript
const label = `swarm:${projectName}:${taskId}`
// Same label on retry → collision
```

**Correct:**
```typescript
// Add unique suffix
const label = `swarm:${projectName}:${taskId}`.slice(0, 50) + `-${Date.now().toString(36)}`
// Or use spawn guard's unique label generation
```

---

### Problem: Gateway restart doesn't clear spawn guard

**Issue:** After restarting gateway to fix token mismatch, spawn guard in SwarmOps dashboard still shows circuit open.

**Fix:**
```bash
# After gateway restart, also reset spawn guard
curl -X POST http://localhost:3939/api/orchestrator/spawn-guard \
  -d '{"action": "reset"}'
```

---

### Problem: Nuxt telemetry prompt blocks startup

**Issue:** When running `pnpm dev`, Nuxt asks about telemetry and blocks.

**Fix:** Answer "No" via screen/terminal, or set env:
```bash
NUXT_TELEMETRY_DISABLED=1 pnpm dev
```

---

### Problem: Context lost on session compaction

**Issue:** When OpenClaw compacts context, work in progress is lost.

**Fix:** On compaction warning, ALWAYS write to memory files:
```typescript
// Even if summary is empty, write what you're working on
await writeFile('memory/YYYY-MM-DD.md', `
## Current Work
- Working on: ${description}
- Files changed: ${files}
- Pending: ${todos}
`)
```

**Why:** Empty summary means context was truncated, not that nothing happened.

---

### Problem: npm OOM on this machine

**Issue:** `npm install` runs out of memory on 3.8GB RAM server.

**Fix:** Use pnpm instead:
```bash
pnpm install  # Works better with limited RAM
```

---

### Problem: Route conflicts in Nuxt

**Issue:** Both `page.vue` and `page/index.vue` exist, causing conflicts.

**Fix:** Only use one pattern. Remove the conflicting file.


---

### Problem: OpenClaw model slug format mismatch

**Wrong:**
```
anthropic/claude-opus-4.5   (dots - OpenRouter format)
```

**Correct:**
```
anthropic/claude-opus-4-5   (dashes - OpenClaw format)
```

**Why:** OpenClaw uses dash-separated model slugs internally and resolves them to the correct OpenRouter format. Using dot format causes "Unknown model" errors. Check available models with:
```bash
grep -o "anthropic/claude[^\"]*" ~/.npm-global/lib/node_modules/openclaw/dist/config-*.js | sort -u
```

---

### Problem: New model not available in OpenClaw

**Issue:** New Anthropic model released (e.g., Opus 4.6) but OpenClaw rejects it as "Unknown model".

**Cause:** OpenClaw validates models against a built-in registry. New models require an OpenClaw update.

**Fix:**
```bash
npm install -g openclaw@latest
# Then restart gateway
pkill -f openclaw-gateway && openclaw gateway start &
```

**Check:** After update, verify model is in registry:
```bash
grep "claude" ~/.npm-global/lib/node_modules/openclaw/dist/config-*.js | sort -u
```

---

### Problem: Duplicate Nitro auto-import warnings

**Issue:** Nitro warns `Duplicated imports "X"` when two files export the same name.

**Fix for Task:** Renamed to `GraphTask` in `orchestrator.ts` to avoid collision with `Task` in `task-queue.ts`.

**Fix for ReviewDecision:** Changed `phase-reviewer.ts` from re-exporting the type to importing it:
```typescript
// Wrong: export type ReviewDecision = 'approve' | 'fix' | 'escalate'
// Right: import { type ReviewDecision } from './review-state'
```

**Why:** Nitro auto-imports all exports. Two files exporting the same name causes ambiguity warnings.

---

### Problem: SSH authentication with sshpass is fragile

**Issue:** `sshpass` connections fail intermittently and are slow.

**Fix:** Set up SSH key auth:
```bash
ssh-copy-id siim@100.82.136.103
# Then use: ssh siim@100.82.136.103 'command'
```

**Why:** Key auth is faster, more reliable, and doesn't expose passwords in command history.
