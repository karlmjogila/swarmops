import { getTrackerState } from '../../utils/worker-tracker'

export default defineEventHandler(() => {
  return getTrackerState()
})
