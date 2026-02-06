import type { InjectionKey, Ref } from 'vue'
import type { ExecutionStatus } from '../types/pipeline'

export interface PipelineExecutionContext {
  nodeStatuses: Ref<Map<string, ExecutionStatus>>
  isRunning: Ref<boolean>
  getNodeStatus: (nodeId: string) => ExecutionStatus
}

export const PIPELINE_EXECUTION_KEY: InjectionKey<PipelineExecutionContext> = Symbol('pipeline-execution')

export function providePipelineExecution(context: PipelineExecutionContext) {
  provide(PIPELINE_EXECUTION_KEY, context)
}

export function usePipelineExecutionContext() {
  return inject(PIPELINE_EXECUTION_KEY, null)
}
