/**
 * List active pipeline runs
 */

import { PipelineRunner } from '../../utils/pipeline-runner'

export default defineEventHandler(async () => {
  const runs = PipelineRunner.getActiveRuns()
  
  return runs.map(r => ({
    runId: r.runId,
    pipelineId: r.pipelineId,
    pipelineName: r.pipelineName,
    status: r.status,
    currentStep: r.currentStepIndex + 1,
    totalSteps: r.totalSteps,
    completedSteps: r.stepResults.length,
    activeSessionKey: r.activeSessionKey,
    startedAt: r.startedAt,
  }))
})
