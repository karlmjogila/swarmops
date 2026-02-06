import { getEscalationStats } from '../../utils/escalation-store'

export default defineEventHandler(async () => {
  return await getEscalationStats()
})
