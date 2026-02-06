import { dismissEscalation, getEscalation } from '../../../utils/escalation-store'
import { requireAuth } from '../../../utils/security'

interface DismissRequest {
  reason?: string
  dismissedBy?: string
}

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'Escalation ID required' })
  }

  const body = await readBody<DismissRequest>(event)

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

  const dismissed = await dismissEscalation(id, body?.reason, body?.dismissedBy)

  return {
    success: true,
    escalation: dismissed
  }
})
