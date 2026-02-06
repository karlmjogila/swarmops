import { getEscalation } from '../../../utils/escalation-store'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  
  if (!id) {
    throw createError({ statusCode: 400, statusMessage: 'Escalation ID required' })
  }

  const escalation = await getEscalation(id)
  
  if (!escalation) {
    throw createError({ statusCode: 404, statusMessage: 'Escalation not found' })
  }

  return escalation
})
