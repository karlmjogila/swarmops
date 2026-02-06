/**
 * Pipeline Runner Service
 * P2: Executes pipeline steps sequentially with auto-continue logic
 */

import { EventEmitter } from 'events';
import {
  Pipeline,
  PipelineStep,
  PipelineRunState,
  PipelineStepState,
  PipelineEvent,
  PipelineRunStatus,
  PipelineStepStatus,
  DEFAULT_CONVERGENCE,
} from '../types/pipeline';
import { WorkItem, WorkCreateInput } from '../types/work';
import { TrackedSession } from '../types/session';
import { 
  getPipelineStorage, 
  getPipelineRunStorage, 
  PipelineStorage, 
  PipelineRunStorage,
  getWorkStorage,
  WorkStorage,
} from '../storage';
import { getOrchestratorService, OrchestratorService } from './orchestrator';
import { ConvergenceEngine, getConvergenceEngine } from './convergence';
import { timestamp } from '../storage/base';

/**
 * Options for creating a PipelineRunner
 */
export interface PipelineRunnerOptions {
  /** Pipeline storage instance */
  pipelineStorage?: PipelineStorage;
  /** Run storage instance */
  runStorage?: PipelineRunStorage;
  /** Work storage instance */
  workStorage?: WorkStorage;
  /** Orchestrator service instance */
  orchestrator?: OrchestratorService;
  /** Convergence engine instance */
  convergenceEngine?: ConvergenceEngine;
}

/**
 * Context passed to step execution
 */
export interface StepExecutionContext {
  /** The pipeline being executed */
  pipeline: Pipeline;
  /** Current run state */
  runState: PipelineRunState;
  /** The step being executed */
  step: PipelineStep;
  /** Index of the step */
  stepIndex: number;
  /** Resolved input for the step */
  resolvedInput: Record<string, unknown>;
}

/**
 * Result of step execution
 */
export interface StepExecutionResult {
  /** Whether the step succeeded */
  success: boolean;
  /** Output from the step */
  output?: Record<string, unknown>;
  /** Error message if failed */
  error?: string;
  /** Number of convergence iterations */
  iterations: number;
}

/**
 * Pipeline Runner - Executes pipeline steps sequentially
 */
export class PipelineRunner extends EventEmitter {
  private pipelineStorage: PipelineStorage;
  private runStorage: PipelineRunStorage;
  private workStorage: WorkStorage;
  private orchestrator: OrchestratorService;
  private convergenceEngine: ConvergenceEngine;
  
  /** Currently running pipelines (runId -> active flag) */
  private activeRuns: Map<string, boolean> = new Map();

  constructor(options: PipelineRunnerOptions = {}) {
    super();
    this.pipelineStorage = options.pipelineStorage ?? getPipelineStorage();
    this.runStorage = options.runStorage ?? getPipelineRunStorage();
    this.workStorage = options.workStorage ?? getWorkStorage();
    this.orchestrator = options.orchestrator ?? getOrchestratorService();
    this.convergenceEngine = options.convergenceEngine ?? getConvergenceEngine();
  }

  /**
   * Emit a pipeline event
   */
  private emitEvent(event: PipelineEvent): void {
    this.emit('pipeline:event', event);
    this.emit(`pipeline:${event.type}`, event);
  }

  /**
   * Start a new pipeline run
   */
  async startRun(
    pipelineId: string, 
    input?: Record<string, unknown>,
    options?: { autoContinue?: boolean; startFromStep?: number }
  ): Promise<PipelineRunState> {
    // Get the pipeline
    const pipeline = await this.pipelineStorage.get(pipelineId);

    // Create the run
    let run = await this.runStorage.create(pipeline, input);

    // Apply options
    const autoContinue = options?.autoContinue ?? pipeline.autoContinue;
    const startFromStep = options?.startFromStep ?? 0;

    // Update run to started
    run = await this.runStorage.update(run.id, {
      status: 'running',
      currentStepIndex: startFromStep,
      startedAt: timestamp(),
    });

    this.activeRuns.set(run.id, true);
    this.emitEvent({ type: 'run_started', runId: run.id, pipelineId });

    // Execute steps if auto-continue is enabled
    if (autoContinue) {
      // Don't await - let it run in background
      this.executeSteps(run.id, pipeline).catch(err => {
        console.error(`Pipeline run ${run.id} failed:`, err);
      });
    }

    return run;
  }

  /**
   * Execute pipeline steps sequentially
   */
  private async executeSteps(runId: string, pipeline: Pipeline): Promise<void> {
    while (this.activeRuns.get(runId)) {
      const run = await this.runStorage.get(runId);

      // Check if run is complete or stopped
      if (run.status !== 'running') {
        this.activeRuns.delete(runId);
        return;
      }

      // Check if all steps are done
      if (run.currentStepIndex >= pipeline.steps.length) {
        await this.completeRun(runId);
        return;
      }

      // Get current step
      const step = pipeline.steps[run.currentStepIndex];
      const stepState = run.stepStates[run.currentStepIndex];

      // Skip if already complete
      if (stepState.status === 'complete' || stepState.status === 'skipped') {
        await this.advanceToNextStep(runId);
        continue;
      }

      // Check step condition
      if (step.condition) {
        const shouldExecute = this.evaluateCondition(step.condition, run);
        if (!shouldExecute) {
          await this.skipStep(runId, step.id, 'Condition not met');
          await this.advanceToNextStep(runId);
          continue;
        }
      }

      // Execute the step
      try {
        const result = await this.executeStep({
          pipeline,
          runState: run,
          step,
          stepIndex: run.currentStepIndex,
          resolvedInput: this.resolveStepInput(step, run),
        });

        if (result.success) {
          await this.completeStep(runId, step.id, result.output, result.iterations);
          await this.advanceToNextStep(runId);
        } else {
          await this.failStep(runId, step.id, result.error || 'Unknown error');
          
          // Stop on failure if configured
          if (pipeline.stopOnFailure && !step.optional) {
            await this.failRun(runId, `Step "${step.name}" failed: ${result.error}`);
            return;
          }
          
          await this.advanceToNextStep(runId);
        }
      } catch (err) {
        const error = err instanceof Error ? err.message : String(err);
        await this.failStep(runId, step.id, error);
        
        if (pipeline.stopOnFailure && !step.optional) {
          await this.failRun(runId, `Step "${step.name}" failed: ${error}`);
          return;
        }
        
        await this.advanceToNextStep(runId);
      }
    }
  }

  /**
   * Execute a single step
   */
  private async executeStep(context: StepExecutionContext): Promise<StepExecutionResult> {
    const { pipeline, runState, step, stepIndex, resolvedInput } = context;

    this.emitEvent({
      type: 'step_started',
      runId: runState.id,
      stepId: step.id,
      stepIndex,
    });

    // Update step state to running
    await this.runStorage.updateStepState(runState.id, step.id, {
      status: 'running',
      startedAt: timestamp(),
    });

    // Create work item for this step
    const workInput: WorkCreateInput = {
      type: 'task',
      roleId: step.roleId,
      title: `[Pipeline: ${pipeline.name}] ${step.name}`,
      description: step.action,
      input: resolvedInput,
      tags: ['pipeline', pipeline.id, runState.id],
    };

    const workItem = await this.workStorage.create(workInput);

    // Update step with work item ID
    await this.runStorage.updateStepState(runState.id, step.id, {
      workItemId: workItem.id,
    });

    // Spawn worker for this step
    const assignment = await this.orchestrator.assignSession({
      roleId: step.roleId,
      workItemId: workItem.id,
      label: `pipeline-${runState.id}-step-${stepIndex}`,
      task: step.action,
    });

    // Update step with session key
    await this.runStorage.updateStepState(runState.id, step.id, {
      sessionKey: assignment.session.sessionKey,
    });

    // Wait for work completion (poll-based for now)
    const result = await this.waitForWorkCompletion(workItem.id, step.timeoutMs);

    // Handle convergence if configured
    const convergence = step.convergence ?? pipeline.defaultConvergence;
    if (convergence && result.success) {
      const convergeResult = await this.convergenceEngine.converge({
        runId: runState.id,
        stepId: step.id,
        workItemId: workItem.id,
        output: result.output,
        criteria: convergence,
        onIteration: async (iteration, review) => {
          this.emitEvent({
            type: 'step_converging',
            runId: runState.id,
            stepId: step.id,
            iteration,
          });
          
          await this.runStorage.updateStepState(runState.id, step.id, {
            status: 'converging',
            iterations: iteration,
            reviews: [
              ...(runState.stepStates[stepIndex].reviews || []),
              review,
            ],
          });
        },
      });

      return {
        success: convergeResult.converged,
        output: convergeResult.finalOutput,
        error: convergeResult.converged ? undefined : 'Failed to converge',
        iterations: convergeResult.iterations,
      };
    }

    return {
      success: result.success,
      output: result.output,
      error: result.error,
      iterations: 1,
    };
  }

  /**
   * Wait for a work item to complete
   */
  private async waitForWorkCompletion(
    workItemId: string,
    timeoutMs?: number
  ): Promise<{ success: boolean; output?: Record<string, unknown>; error?: string }> {
    const timeout = timeoutMs || 300000; // 5 minutes default
    const startTime = Date.now();
    const pollInterval = 1000; // 1 second

    while (Date.now() - startTime < timeout) {
      const workItem = await this.workStorage.get(workItemId);

      switch (workItem.status) {
        case 'complete':
          return {
            success: true,
            output: workItem.output,
          };
        case 'failed':
          return {
            success: false,
            error: workItem.error || 'Work item failed',
          };
        case 'cancelled':
          return {
            success: false,
            error: 'Work item was cancelled',
          };
        default:
          // Still running, wait and poll again
          await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }

    return {
      success: false,
      error: `Timeout after ${timeout}ms`,
    };
  }

  /**
   * Resolve step input by substituting template variables
   */
  private resolveStepInput(step: PipelineStep, run: PipelineRunState): Record<string, unknown> {
    const input: Record<string, unknown> = step.input ? { ...step.input } : {};

    // Add global run input
    if (run.input) {
      Object.assign(input, { _runInput: run.input });
    }

    // Add outputs from previous steps
    const stepOutputs: Record<string, unknown> = {};
    for (const stepState of run.stepStates) {
      if (stepState.output) {
        stepOutputs[stepState.stepId] = stepState.output;
      }
    }
    Object.assign(input, { _stepOutputs: stepOutputs });

    // Template substitution (basic implementation)
    const resolved = JSON.stringify(input);
    const substituted = resolved.replace(
      /\{\{(\w+)\.output\.?(\w*)\}\}/g,
      (match, stepId, field) => {
        const stepOutput = stepOutputs[stepId] as Record<string, unknown> | undefined;
        if (!stepOutput) return match;
        if (field) {
          return JSON.stringify(stepOutput[field]) || match;
        }
        return JSON.stringify(stepOutput);
      }
    );

    return JSON.parse(substituted);
  }

  /**
   * Evaluate a condition expression
   */
  private evaluateCondition(condition: string, run: PipelineRunState): boolean {
    try {
      // Build context with step outputs
      const context: Record<string, unknown> = {};
      for (const stepState of run.stepStates) {
        if (stepState.output) {
          context[stepState.stepId] = { output: stepState.output };
        }
      }

      // Simple evaluation (in production, use a proper expression evaluator)
      const fn = new Function(...Object.keys(context), `return ${condition}`);
      return Boolean(fn(...Object.values(context)));
    } catch {
      console.warn(`Failed to evaluate condition: ${condition}`);
      return true; // Default to executing on evaluation failure
    }
  }

  /**
   * Advance to the next step
   */
  private async advanceToNextStep(runId: string): Promise<void> {
    const run = await this.runStorage.get(runId);
    await this.runStorage.update(runId, {
      currentStepIndex: run.currentStepIndex + 1,
    });
  }

  /**
   * Mark a step as complete
   */
  private async completeStep(
    runId: string,
    stepId: string,
    output?: Record<string, unknown>,
    iterations: number = 1
  ): Promise<void> {
    await this.runStorage.updateStepState(runId, stepId, {
      status: 'complete',
      output,
      iterations,
      completedAt: timestamp(),
    });

    this.emitEvent({
      type: 'step_completed',
      runId,
      stepId,
      output,
    });
  }

  /**
   * Mark a step as failed
   */
  private async failStep(runId: string, stepId: string, error: string): Promise<void> {
    await this.runStorage.updateStepState(runId, stepId, {
      status: 'failed',
      error,
      completedAt: timestamp(),
    });

    this.emitEvent({
      type: 'step_failed',
      runId,
      stepId,
      error,
    });
  }

  /**
   * Mark a step as skipped
   */
  private async skipStep(runId: string, stepId: string, reason: string): Promise<void> {
    await this.runStorage.updateStepState(runId, stepId, {
      status: 'skipped',
      completedAt: timestamp(),
    });

    this.emitEvent({
      type: 'step_skipped',
      runId,
      stepId,
      reason,
    });
  }

  /**
   * Complete a pipeline run
   */
  private async completeRun(runId: string): Promise<void> {
    const run = await this.runStorage.get(runId);

    // Aggregate outputs from all steps
    const output: Record<string, unknown> = {};
    for (const stepState of run.stepStates) {
      if (stepState.output) {
        output[stepState.stepId] = stepState.output;
      }
    }

    await this.runStorage.update(runId, {
      status: 'complete',
      output,
      completedAt: timestamp(),
    });

    this.activeRuns.delete(runId);
    this.emitEvent({
      type: 'run_completed',
      runId,
      output,
    });
  }

  /**
   * Fail a pipeline run
   */
  private async failRun(runId: string, error: string): Promise<void> {
    await this.runStorage.update(runId, {
      status: 'failed',
      error,
      completedAt: timestamp(),
    });

    this.activeRuns.delete(runId);
    this.emitEvent({
      type: 'run_failed',
      runId,
      error,
    });
  }

  /**
   * Pause a pipeline run
   */
  async pauseRun(runId: string, reason?: string): Promise<PipelineRunState> {
    this.activeRuns.set(runId, false);
    
    const run = await this.runStorage.update(runId, {
      status: 'paused',
    });

    this.emitEvent({
      type: 'run_paused',
      runId,
      reason,
    });

    return run;
  }

  /**
   * Resume a paused pipeline run
   */
  async resumeRun(runId: string): Promise<PipelineRunState> {
    const run = await this.runStorage.get(runId);

    if (run.status !== 'paused') {
      throw new Error(`Cannot resume run in status: ${run.status}`);
    }

    const pipeline = await this.pipelineStorage.get(run.pipelineId);

    const updated = await this.runStorage.update(runId, {
      status: 'running',
    });

    this.activeRuns.set(runId, true);

    // Continue execution
    this.executeSteps(runId, pipeline).catch(err => {
      console.error(`Pipeline run ${runId} failed:`, err);
    });

    return updated;
  }

  /**
   * Cancel a pipeline run
   */
  async cancelRun(runId: string, reason?: string): Promise<PipelineRunState> {
    this.activeRuns.set(runId, false);

    const run = await this.runStorage.update(runId, {
      status: 'cancelled',
      completedAt: timestamp(),
    });

    this.emitEvent({
      type: 'run_cancelled',
      runId,
      reason,
    });

    return run;
  }

  /**
   * Manually trigger the next step (for runs with autoContinue=false)
   */
  async triggerNextStep(runId: string): Promise<PipelineRunState> {
    const run = await this.runStorage.get(runId);

    if (run.status !== 'running' && run.status !== 'paused') {
      throw new Error(`Cannot trigger step for run in status: ${run.status}`);
    }

    const pipeline = await this.pipelineStorage.get(run.pipelineId);

    if (run.currentStepIndex >= pipeline.steps.length) {
      await this.completeRun(runId);
      return this.runStorage.get(runId);
    }

    // Execute single step
    const step = pipeline.steps[run.currentStepIndex];
    const stepState = run.stepStates[run.currentStepIndex];

    if (stepState.status === 'complete' || stepState.status === 'skipped') {
      await this.advanceToNextStep(runId);
      return this.runStorage.get(runId);
    }

    try {
      const result = await this.executeStep({
        pipeline,
        runState: run,
        step,
        stepIndex: run.currentStepIndex,
        resolvedInput: this.resolveStepInput(step, run),
      });

      if (result.success) {
        await this.completeStep(runId, step.id, result.output, result.iterations);
      } else {
        await this.failStep(runId, step.id, result.error || 'Unknown error');
        
        if (pipeline.stopOnFailure && !step.optional) {
          await this.failRun(runId, `Step "${step.name}" failed: ${result.error}`);
        }
      }

      await this.advanceToNextStep(runId);
    } catch (err) {
      const error = err instanceof Error ? err.message : String(err);
      await this.failStep(runId, step.id, error);
      
      if (pipeline.stopOnFailure && !step.optional) {
        await this.failRun(runId, `Step "${step.name}" failed: ${error}`);
      } else {
        await this.advanceToNextStep(runId);
      }
    }

    return this.runStorage.get(runId);
  }

  /**
   * Get the current status of a run
   */
  async getRunStatus(runId: string): Promise<PipelineRunState> {
    return this.runStorage.get(runId);
  }

  /**
   * Check if a run is currently active
   */
  isRunActive(runId: string): boolean {
    return this.activeRuns.get(runId) === true;
  }

  /**
   * Get all active run IDs
   */
  getActiveRunIds(): string[] {
    return Array.from(this.activeRuns.entries())
      .filter(([_, active]) => active)
      .map(([runId]) => runId);
  }
}

/** Singleton instance */
let defaultRunner: PipelineRunner | null = null;

/**
 * Get the default PipelineRunner instance
 */
export function getPipelineRunner(): PipelineRunner {
  if (!defaultRunner) {
    defaultRunner = new PipelineRunner();
  }
  return defaultRunner;
}
