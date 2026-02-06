/**
 * Convergence Engine
 * P2: Quality loops with self-review until criteria met
 */

import { ConvergenceCriteria, DEFAULT_CONVERGENCE } from '../types/pipeline';
import { WorkCreateInput, WorkItem } from '../types/work';
import { getWorkStorage, WorkStorage, getRoleStorage, RoleStorage } from '../storage';
import { getOrchestratorService, OrchestratorService } from './orchestrator';
import { timestamp } from '../storage/base';

/**
 * Review result from convergence iteration
 */
export interface ConvergenceReview {
  /** Iteration number (1-based) */
  iteration: number;
  /** Quality score (0-1) */
  score: number;
  /** Reviewer feedback */
  feedback: string;
  /** Whether this iteration passed criteria */
  passed: boolean;
  /** Reviewer session key */
  sessionKey?: string;
  /** When review was completed */
  reviewedAt: string;
}

/**
 * Result of convergence process
 */
export interface ConvergenceResult {
  /** Whether convergence was achieved */
  converged: boolean;
  /** Total iterations performed */
  iterations: number;
  /** Final output after all iterations */
  finalOutput?: Record<string, unknown>;
  /** History of all reviews */
  reviews: ConvergenceReview[];
  /** Final score achieved */
  finalScore: number;
  /** Reason if not converged */
  reason?: string;
}

/**
 * Input for convergence process
 */
export interface ConvergenceInput {
  /** Run ID for tracking */
  runId: string;
  /** Step ID being converged */
  stepId: string;
  /** Work item ID being reviewed */
  workItemId: string;
  /** Output to review */
  output?: Record<string, unknown>;
  /** Convergence criteria */
  criteria: ConvergenceCriteria;
  /** Callback for each iteration */
  onIteration?: (iteration: number, review: ConvergenceReview) => Promise<void>;
}

/**
 * Options for ConvergenceEngine
 */
export interface ConvergenceEngineOptions {
  /** Work storage instance */
  workStorage?: WorkStorage;
  /** Role storage instance */
  roleStorage?: RoleStorage;
  /** Orchestrator service instance */
  orchestrator?: OrchestratorService;
  /** Default poll interval in ms */
  pollIntervalMs?: number;
  /** Default timeout per iteration in ms */
  iterationTimeoutMs?: number;
}

/**
 * Convergence Engine - Quality loops with self-review
 */
export class ConvergenceEngine {
  private workStorage: WorkStorage;
  private roleStorage: RoleStorage;
  private orchestrator: OrchestratorService;
  private pollIntervalMs: number;
  private iterationTimeoutMs: number;

  constructor(options: ConvergenceEngineOptions = {}) {
    this.workStorage = options.workStorage ?? getWorkStorage();
    this.roleStorage = options.roleStorage ?? getRoleStorage();
    this.orchestrator = options.orchestrator ?? getOrchestratorService();
    this.pollIntervalMs = options.pollIntervalMs ?? 1000;
    this.iterationTimeoutMs = options.iterationTimeoutMs ?? 180000; // 3 minutes
  }

  /**
   * Run convergence loop until criteria met or max iterations reached
   */
  async converge(input: ConvergenceInput): Promise<ConvergenceResult> {
    const { runId, stepId, workItemId, output, criteria, onIteration } = input;
    const reviews: ConvergenceReview[] = [];
    
    const maxIterations = criteria.maxIterations || DEFAULT_CONVERGENCE.maxIterations;
    const minScore = criteria.minScore ?? DEFAULT_CONVERGENCE.minScore!;
    const reviewerRoleId = criteria.reviewerRoleId || DEFAULT_CONVERGENCE.reviewerRoleId!;

    let currentOutput = output;
    let iteration = 0;
    let lastScore = 0;

    while (iteration < maxIterations) {
      iteration++;

      // Perform review
      const review = await this.performReview({
        runId,
        stepId,
        workItemId,
        iteration,
        output: currentOutput,
        reviewerRoleId,
        criteria,
      });

      reviews.push(review);
      lastScore = review.score;

      // Notify callback
      if (onIteration) {
        await onIteration(iteration, review);
      }

      // Check if converged
      if (review.passed) {
        return {
          converged: true,
          iterations: iteration,
          finalOutput: currentOutput,
          reviews,
          finalScore: review.score,
        };
      }

      // Check custom success criteria
      if (criteria.successCriteria) {
        const success = this.evaluateSuccessCriteria(criteria.successCriteria, review, currentOutput);
        if (success) {
          return {
            converged: true,
            iterations: iteration,
            finalOutput: currentOutput,
            reviews,
            finalScore: review.score,
          };
        }
      }

      // If not last iteration, attempt to improve
      if (iteration < maxIterations) {
        const improved = await this.attemptImprovement({
          runId,
          stepId,
          workItemId,
          iteration,
          output: currentOutput,
          feedback: review.feedback,
          originalWorkItemId: workItemId,
        });

        if (improved) {
          currentOutput = improved;
        }
      }
    }

    // Max iterations reached without convergence
    return {
      converged: false,
      iterations: iteration,
      finalOutput: currentOutput,
      reviews,
      finalScore: lastScore,
      reason: `Max iterations (${maxIterations}) reached. Best score: ${lastScore.toFixed(2)}, required: ${minScore}`,
    };
  }

  /**
   * Perform a review iteration
   */
  private async performReview(params: {
    runId: string;
    stepId: string;
    workItemId: string;
    iteration: number;
    output?: Record<string, unknown>;
    reviewerRoleId: string;
    criteria: ConvergenceCriteria;
  }): Promise<ConvergenceReview> {
    const { runId, stepId, workItemId, iteration, output, reviewerRoleId, criteria } = params;
    const minScore = criteria.minScore ?? DEFAULT_CONVERGENCE.minScore!;

    // Get the original work item for context
    const originalWork = await this.workStorage.get(workItemId);

    // Create review work item
    const reviewTaskDescription = this.buildReviewPrompt(originalWork, output, criteria);
    
    const reviewWorkInput: WorkCreateInput = {
      type: 'converge',
      roleId: reviewerRoleId,
      title: `[Convergence Review] Iteration ${iteration} for ${originalWork.title}`,
      description: reviewTaskDescription,
      input: {
        originalTask: originalWork.description,
        originalInput: originalWork.input,
        outputToReview: output,
        iteration,
        minScore,
        successCriteria: criteria.successCriteria,
      },
      tags: ['convergence', 'review', runId, stepId],
    };

    const reviewWork = await this.workStorage.create(reviewWorkInput);

    // Spawn reviewer session
    const assignment = await this.orchestrator.assignSession({
      roleId: reviewerRoleId,
      workItemId: reviewWork.id,
      label: `convergence-review-${runId}-${stepId}-iter${iteration}`,
      task: reviewTaskDescription,
    });

    // Wait for review completion
    const reviewResult = await this.waitForWorkCompletion(reviewWork.id);

    // Parse review result
    const reviewOutput = reviewResult.output || {};
    const score = this.parseScore(reviewOutput);
    const feedback = this.parseFeedback(reviewOutput);
    const passed = score >= minScore;

    return {
      iteration,
      score,
      feedback,
      passed,
      sessionKey: assignment.session.sessionKey,
      reviewedAt: timestamp(),
    };
  }

  /**
   * Attempt to improve output based on feedback
   */
  private async attemptImprovement(params: {
    runId: string;
    stepId: string;
    workItemId: string;
    iteration: number;
    output?: Record<string, unknown>;
    feedback: string;
    originalWorkItemId: string;
  }): Promise<Record<string, unknown> | undefined> {
    const { runId, stepId, workItemId, iteration, output, feedback, originalWorkItemId } = params;

    // Get original work item
    const originalWork = await this.workStorage.get(originalWorkItemId);

    // Create improvement work item
    const improvementTaskDescription = this.buildImprovementPrompt(originalWork, output, feedback);

    const improvementWorkInput: WorkCreateInput = {
      type: 'task',
      roleId: originalWork.roleId || 'builder',
      title: `[Improvement] Iteration ${iteration + 1} for ${originalWork.title}`,
      description: improvementTaskDescription,
      input: {
        originalTask: originalWork.description,
        previousOutput: output,
        feedback,
        iteration: iteration + 1,
      },
      tags: ['convergence', 'improvement', runId, stepId],
    };

    const improvementWork = await this.workStorage.create(improvementWorkInput);

    // Spawn worker session
    await this.orchestrator.assignSession({
      roleId: originalWork.roleId || 'builder',
      workItemId: improvementWork.id,
      label: `convergence-improve-${runId}-${stepId}-iter${iteration + 1}`,
      task: improvementTaskDescription,
    });

    // Wait for improvement completion
    const result = await this.waitForWorkCompletion(improvementWork.id);

    return result.success ? result.output : undefined;
  }

  /**
   * Build review prompt for reviewer
   */
  private buildReviewPrompt(
    originalWork: WorkItem,
    output: Record<string, unknown> | undefined,
    criteria: ConvergenceCriteria
  ): string {
    const minScore = criteria.minScore ?? DEFAULT_CONVERGENCE.minScore!;
    
    return `
## Review Task

You are reviewing the output of a task to determine if it meets quality standards.

### Original Task
${originalWork.description || originalWork.title}

### Task Input
${JSON.stringify(originalWork.input, null, 2)}

### Output to Review
${JSON.stringify(output, null, 2)}

### Review Instructions

1. Evaluate the output against the original task requirements
2. Assign a quality score from 0.0 to 1.0:
   - 1.0: Perfect, meets all requirements excellently
   - 0.8-0.9: Good, minor improvements possible
   - 0.6-0.7: Acceptable but needs work
   - 0.4-0.5: Below expectations, significant issues
   - 0.0-0.3: Poor, major rework needed

3. Provide specific, actionable feedback

${criteria.successCriteria ? `### Success Criteria\n${criteria.successCriteria}` : ''}

### Required Output Format
Respond with a JSON object:
{
  "score": <number 0-1>,
  "feedback": "<specific feedback for improvement>",
  "strengths": ["<what was done well>"],
  "issues": ["<specific issues found>"],
  "suggestions": ["<concrete improvement suggestions>"]
}

Minimum passing score: ${minScore}
`.trim();
  }

  /**
   * Build improvement prompt for worker
   */
  private buildImprovementPrompt(
    originalWork: WorkItem,
    output: Record<string, unknown> | undefined,
    feedback: string
  ): string {
    return `
## Improvement Task

Your previous output needs improvement based on reviewer feedback.

### Original Task
${originalWork.description || originalWork.title}

### Previous Output
${JSON.stringify(output, null, 2)}

### Reviewer Feedback
${feedback}

### Instructions
1. Carefully read the feedback
2. Address each issue mentioned
3. Implement the suggested improvements
4. Ensure the output fully meets the original task requirements

Provide the improved output.
`.trim();
  }

  /**
   * Parse score from review output
   */
  private parseScore(output: Record<string, unknown>): number {
    // Try to get score directly
    if (typeof output.score === 'number') {
      return Math.max(0, Math.min(1, output.score));
    }

    // Try to parse from string
    if (typeof output.score === 'string') {
      const parsed = parseFloat(output.score);
      if (!isNaN(parsed)) {
        return Math.max(0, Math.min(1, parsed));
      }
    }

    // Try to extract from response text
    const response = output.response || output.result || output.text;
    if (typeof response === 'string') {
      const match = response.match(/score[:\s]+(\d*\.?\d+)/i);
      if (match) {
        const parsed = parseFloat(match[1]);
        if (!isNaN(parsed)) {
          return Math.max(0, Math.min(1, parsed > 1 ? parsed / 100 : parsed));
        }
      }
    }

    // Default to medium score if unparseable
    return 0.5;
  }

  /**
   * Parse feedback from review output
   */
  private parseFeedback(output: Record<string, unknown>): string {
    // Try to get feedback directly
    if (typeof output.feedback === 'string') {
      return output.feedback;
    }

    // Build feedback from components
    const parts: string[] = [];

    if (Array.isArray(output.issues)) {
      parts.push(`Issues: ${output.issues.join('; ')}`);
    }

    if (Array.isArray(output.suggestions)) {
      parts.push(`Suggestions: ${output.suggestions.join('; ')}`);
    }

    if (parts.length > 0) {
      return parts.join('\n');
    }

    // Try to get from response
    const response = output.response || output.result || output.text;
    if (typeof response === 'string') {
      return response;
    }

    return 'No specific feedback provided';
  }

  /**
   * Evaluate custom success criteria
   */
  private evaluateSuccessCriteria(
    criteria: string,
    review: ConvergenceReview,
    output?: Record<string, unknown>
  ): boolean {
    try {
      const context = {
        score: review.score,
        feedback: review.feedback,
        passed: review.passed,
        output,
      };

      // Simple evaluation (in production, use proper expression evaluator)
      const fn = new Function('ctx', `with(ctx) { return ${criteria} }`);
      return Boolean(fn(context));
    } catch {
      console.warn(`Failed to evaluate success criteria: ${criteria}`);
      return false;
    }
  }

  /**
   * Wait for work item completion
   */
  private async waitForWorkCompletion(
    workItemId: string
  ): Promise<{ success: boolean; output?: Record<string, unknown>; error?: string }> {
    const startTime = Date.now();

    while (Date.now() - startTime < this.iterationTimeoutMs) {
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
            error: workItem.error || 'Review failed',
          };
        case 'cancelled':
          return {
            success: false,
            error: 'Review was cancelled',
          };
        default:
          await new Promise(resolve => setTimeout(resolve, this.pollIntervalMs));
      }
    }

    return {
      success: false,
      error: `Review timeout after ${this.iterationTimeoutMs}ms`,
    };
  }

  /**
   * Perform a single review without the full convergence loop
   */
  async reviewOnce(params: {
    workItemId: string;
    reviewerRoleId?: string;
    minScore?: number;
  }): Promise<ConvergenceReview> {
    const workItem = await this.workStorage.get(params.workItemId);
    
    return this.performReview({
      runId: 'single-review',
      stepId: workItem.id,
      workItemId: workItem.id,
      iteration: 1,
      output: workItem.output,
      reviewerRoleId: params.reviewerRoleId || 'reviewer',
      criteria: {
        maxIterations: 1,
        minScore: params.minScore ?? 0.8,
      },
    });
  }
}

/** Singleton instance */
let defaultEngine: ConvergenceEngine | null = null;

/**
 * Get the default ConvergenceEngine instance
 */
export function getConvergenceEngine(): ConvergenceEngine {
  if (!defaultEngine) {
    defaultEngine = new ConvergenceEngine();
  }
  return defaultEngine;
}
