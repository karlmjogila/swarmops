import { readEscalations, getOpenEscalations, getEscalationsByPipeline, getEscalationsByRun } from '../../utils/escalation-store'
import type { Escalation, EscalationStatus, EscalationSeverity } from '../../utils/escalation-store'

interface EscalationListResponse {
  escalations: Escalation[]
  total: number
  filters: {
    status?: EscalationStatus
    severity?: EscalationSeverity
    pipelineId?: string
    runId?: string
  }
}

export default defineEventHandler(async (event): Promise<EscalationListResponse> => {
  const query = getQuery(event)
  
  const status = query.status as EscalationStatus | undefined
  const severity = query.severity as EscalationSeverity | undefined
  const pipelineId = query.pipelineId as string | undefined
  const runId = query.runId as string | undefined
  const limit = query.limit ? parseInt(query.limit as string, 10) : undefined

  let escalations: Escalation[]

  // Use specific filters if provided
  if (runId) {
    escalations = await getEscalationsByRun(runId)
  } else if (pipelineId) {
    escalations = await getEscalationsByPipeline(pipelineId)
  } else if (status === 'open') {
    escalations = await getOpenEscalations()
  } else {
    escalations = await readEscalations()
  }

  // Apply additional filters
  if (status && status !== 'open') {
    escalations = escalations.filter(e => e.status === status)
  }
  
  if (severity) {
    escalations = escalations.filter(e => e.severity === severity)
  }

  // Sort by createdAt descending (newest first)
  escalations.sort((a, b) => 
    new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  )

  // Apply limit if specified
  if (limit && limit > 0) {
    escalations = escalations.slice(0, limit)
  }

  return {
    escalations,
    total: escalations.length,
    filters: { status, severity, pipelineId, runId }
  }
})
