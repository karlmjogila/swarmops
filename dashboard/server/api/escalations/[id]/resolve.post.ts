import { resolveEscalation, getEscalation } from '../../../utils/escalation-store'
import { requireAuth } from '../../../utils/security'

interface ResolveRequest {
  resolution: string
  resolvedBy?: string
}

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'Escalation ID required' })
  }

  const body = await readBody<ResolveRequest>(event)
  
  if (!body?.resolution) {
    throw createError({ statusCode: 400, statusMessage: 'Resolution description required' })
  }

  // Check if escalation exists
  const existing = await getEscalation(id)
  if (!existing) {
    throw createError({ statusCode: 404, statusMessage: 'Escalation not found' })
  }

  if (existing.status !== 'open') {
    throw createError({ 
      statusCode: 400, 
      statusMessage: `Escalation is already ${existing.status}` 
    })
  }

  const resolved = await resolveEscalation(id, body.resolution, body.resolvedBy)

  return {
    success: true,
    escalation: resolved
  }
})
