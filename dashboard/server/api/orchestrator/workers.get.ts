import { getTrackerState } from '../../utils/worker-tracker'
import { requireAuth } from '../../utils/security'

const GATEWAY_URL = process.env.OPENCLAW_GATEWAY_URL || 'http://127.0.0.1:18789'
const GATEWAY_TOKEN = process.env.OPENCLAW_GATEWAY_TOKEN || ''

interface Worker {
  id: string
  sessionKey: string
  label: string
  roleId: string
  roleName: string
  projectName?: string
  taskId?: string
  taskName?: string
  status: 'running' | 'completed' | 'error' | 'idle'
  startedAt: string
  duration?: number
}

interface GatewaySession {
  key: string
  label?: string
  updatedAt: number
  totalTokens: number
}

function parseLabel(label: string): { roleId: string; roleName: string; projectName?: string; taskName?: string } {
  // Parse labels like "swarm:junkyard-website:css-form:123" or "interview-project-123"
  // Format is typically: swarm:{project}:{task}:{timestamp}-{suffix}
  const lower = label.toLowerCase()
  
  let roleId = 'worker'
  let roleName = 'Worker'
  
  if (lower.includes('interview')) {
    roleId = 'interviewer'
    roleName = 'Interviewer'
  } else if (lower.includes('spec') || lower.includes('plan')) {
    roleId = 'architect'
    roleName = 'Architect'
  } else if (lower.includes('build')) {
    roleId = 'builder'
    roleName = 'Builder'
  } else if (lower.includes('review')) {
    roleId = 'reviewer'
    roleName = 'Reviewer'
  } else if (lower.includes('fix')) {
    roleId = 'fixer'
    roleName = 'Fixer'
  } else if (lower.includes('chat')) {
    roleId = 'chat'
    roleName = 'Chat Agent'
  }
  
  // Parse structured label: swarm:{project}:{task}:{timestamp}
  // or: {role}:{project}:{task}:{timestamp}
  // Examples:
  //   swarm:junkyard-website:css-form:1770367548897-79fo
  //   reviewer:phase-1:phase-1:1770367383949-8p78
  const colonParts = label.split(':')
  let projectName: string | undefined
  let taskName: string | undefined
  
  if (colonParts.length >= 3) {
    // Skip first part if it's a known prefix
    const skipFirst = ['swarm', 'interview', 'reviewer', 'builder', 'fixer', 'chat'].includes(colonParts[0]!.toLowerCase())
    const startIdx = skipFirst ? 1 : 0
    
    // Project is typically second element (after prefix)
    if (colonParts[startIdx]) {
      projectName = colonParts[startIdx]
    }
    
    // Task is typically third element
    if (colonParts[startIdx + 1]) {
      const taskPart = colonParts[startIdx + 1]!
      // Skip if it looks like a timestamp: starts with many digits or is digits-suffix format
      // Timestamp patterns: "1770367548897-79fo" or "1770367548897"
      const isTimestamp = /^\d{10,}/.test(taskPart)
      if (!isTimestamp) {
        taskName = taskPart
      }
    }
  }
  
  // Fallback: try dash-separated parsing if no task found
  if (!taskName && !projectName) {
    const parts = label.split(/[:-]/)
    for (const part of parts) {
      if (['swarm', 'interview', 'spec', 'build', 'review', 'fix', 'chat', 'phase', 'agent'].includes(part.toLowerCase())) {
        continue
      }
      if (/^\d+$/.test(part)) continue
      if (part.length <= 4 && /^[a-z0-9]+$/i.test(part)) continue
      
      if (!projectName) {
        projectName = part
      } else if (!taskName) {
        taskName = part
        break
      }
    }
  }
  
  return { roleId, roleName, projectName, taskName }
}

export default defineEventHandler(async (event): Promise<Worker[]> => {
  requireAuth(event)
  
  const workers: Worker[] = []
  const seen = new Set<string>()
  
  // Get tracker state for start times (more accurate than gateway)
  const state = getTrackerState()
  const trackerWorkers = new Map(state.workers.map(tw => [tw.sessionKey, tw]))
  
  // Query gateway for all subagent sessions (source of truth for status)
  try {
    const response = await fetch(`${GATEWAY_URL}/tools/invoke`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${GATEWAY_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tool: 'sessions_list',
        parameters: { limit: 100, messageLimit: 1 }  // Get last message to check stopReason
      })
    })
    
    if (response.ok) {
      const data = await response.json()
      // Gateway wraps result in result.content[0].text (JSON string) or result.details
      let sessions: GatewaySession[] = []
      if (data.result?.details?.sessions) {
        sessions = data.result.details.sessions
      } else if (data.result?.content?.[0]?.text) {
        const parsed = JSON.parse(data.result.content[0].text)
        sessions = parsed.sessions || []
      } else if (data.sessions) {
        sessions = data.sessions
      }
      
      // Filter to RECENTLY ACTIVE swarm/worker sessions
      const now = Date.now()
      const ACTIVE_THRESHOLD_MS = 15 * 60 * 1000 // 15 minutes - sessions older than this are hidden
      
      for (const session of sessions) {
        if (seen.has(session.key)) continue
        if (!session.label) continue
        
        // Only include swarm workers (have labels like swarm:project:task)
        const label = session.label.toLowerCase()
        if (!label.startsWith('swarm:') && !label.includes('builder') && !label.includes('reviewer')) {
          continue
        }
        
        // Skip sessions that haven't been updated recently
        const lastUpdate = session.updatedAt || 0
        if (now - lastUpdate > ACTIVE_THRESHOLD_MS) {
          continue
        }
        
        // Check stopReason to determine actual status
        // stopReason: "stop" = agent finished normally
        // stopReason: "toolUse" = agent waiting for tool result (still working)
        // no messages or no stopReason = just started
        let status: 'running' | 'completed' | 'error' | 'idle' = 'running'
        const lastMessage = (session as any).messages?.[0]
        if (lastMessage?.stopReason === 'stop') {
          status = 'completed'
        } else if (lastMessage?.stopReason === 'error') {
          status = 'error'
        } else if (session.totalTokens === 0) {
          // Session spawned but never started (stuck/queued)
          status = 'idle'
        }
        
        const { roleId, roleName, projectName, taskName } = parseLabel(session.label)
        
        // Use tracker start time if available (more accurate), otherwise estimate
        const trackerEntry = trackerWorkers.get(session.key)
        const startTime = trackerEntry?.startTime || (session.updatedAt - (session.totalTokens > 0 ? 60000 : 0))
        
        workers.push({
          id: session.key,
          sessionKey: session.key,
          label: session.label,
          roleId,
          roleName,
          projectName: projectName || trackerEntry?.projectName,
          taskId: taskName,
          taskName: taskName,
          status,
          startedAt: new Date(startTime).toISOString(),
          duration: Date.now() - startTime
        })
        seen.add(session.key)
      }
    }
  } catch (err) {
    console.error('[workers] Failed to fetch from gateway:', err)
  }
  
  // Fallback: Add any tracked workers that weren't in gateway response (edge case)
  for (const tw of state.workers) {
    if (seen.has(tw.sessionKey)) continue
    
    const { roleId, roleName, projectName, taskName } = parseLabel(tw.label)
    workers.push({
      id: tw.sessionKey,
      sessionKey: tw.sessionKey,
      label: tw.label,
      roleId,
      roleName,
      projectName: projectName || tw.projectName,
      taskId: taskName,
      taskName: taskName,
      status: 'running', // Assume running if not in gateway (just spawned)
      startedAt: new Date(tw.startTime).toISOString(),
      duration: Date.now() - tw.startTime
    })
  }
  
  // Sort by most recent first
  workers.sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
  
  return workers
})
