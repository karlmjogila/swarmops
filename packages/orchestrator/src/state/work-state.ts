/**
 * Work Item State Machine
 * P1-09: Manages valid state transitions for work items
 */

import { WorkStatus } from '../types/work';

/**
 * Terminal states that cannot transition to other states (except cancelled)
 */
export const TERMINAL_STATES: readonly WorkStatus[] = ['complete', 'failed', 'cancelled'] as const;

/**
 * Valid state transitions map
 * Key: current state, Value: array of valid target states
 */
const STATE_TRANSITIONS: Record<WorkStatus, WorkStatus[]> = {
  pending: ['queued', 'cancelled'],
  queued: ['running', 'cancelled'],
  running: ['converging', 'complete', 'failed', 'cancelled'],
  converging: ['complete', 'failed', 'cancelled'],
  complete: [],  // Terminal - no transitions (cancellation not allowed after complete)
  failed: ['cancelled'],  // Can cancel a failed item to mark as "acknowledged"
  cancelled: [],  // Terminal - no transitions
};

/**
 * Error thrown when an invalid state transition is attempted
 */
export class InvalidTransitionError extends Error {
  readonly from: WorkStatus;
  readonly to: WorkStatus;
  readonly validTargets: WorkStatus[];

  constructor(from: WorkStatus, to: WorkStatus, validTargets: WorkStatus[]) {
    const validStr = validTargets.length > 0 ? validTargets.join(', ') : 'none';
    super(`Invalid state transition: ${from} → ${to}. Valid transitions from ${from}: ${validStr}`);
    this.name = 'InvalidTransitionError';
    this.from = from;
    this.to = to;
    this.validTargets = validTargets;
  }
}

/**
 * State machine for work item status transitions
 */
export class WorkStateMachine {
  /**
   * Check if a transition from one state to another is valid
   */
  canTransition(from: WorkStatus, to: WorkStatus): boolean {
    const validTargets = STATE_TRANSITIONS[from];
    return validTargets.includes(to);
  }

  /**
   * Get all valid transitions from a given state
   */
  getValidTransitions(from: WorkStatus): WorkStatus[] {
    return [...STATE_TRANSITIONS[from]];
  }

  /**
   * Attempt to transition from one state to another
   * Throws InvalidTransitionError if the transition is not valid
   * Returns the new state on success
   */
  transition(from: WorkStatus, to: WorkStatus): WorkStatus {
    if (!this.canTransition(from, to)) {
      throw new InvalidTransitionError(from, to, this.getValidTransitions(from));
    }
    return to;
  }

  /**
   * Check if a state is terminal (no further non-cancel transitions possible)
   */
  isTerminal(status: WorkStatus): boolean {
    return TERMINAL_STATES.includes(status);
  }

  /**
   * Check if a work item can be cancelled from its current state
   */
  canCancel(status: WorkStatus): boolean {
    return this.canTransition(status, 'cancelled');
  }

  /**
   * Get the next logical state for normal progression
   * Returns null if the item is in a terminal state
   */
  getNextProgressState(current: WorkStatus): WorkStatus | null {
    switch (current) {
      case 'pending':
        return 'queued';
      case 'queued':
        return 'running';
      case 'running':
        return 'converging';
      case 'converging':
        return 'complete';
      default:
        return null; // Terminal or unknown
    }
  }

  /**
   * Get all possible states
   */
  getAllStates(): WorkStatus[] {
    return Object.keys(STATE_TRANSITIONS) as WorkStatus[];
  }
}

/** Singleton instance */
let instance: WorkStateMachine | null = null;

/**
 * Get the WorkStateMachine singleton
 */
export function getWorkStateMachine(): WorkStateMachine {
  if (!instance) {
    instance = new WorkStateMachine();
  }
  return instance;
}

// Export default instance methods for convenience
export const workStateMachine = {
  canTransition: (from: WorkStatus, to: WorkStatus) => getWorkStateMachine().canTransition(from, to),
  transition: (from: WorkStatus, to: WorkStatus) => getWorkStateMachine().transition(from, to),
  getValidTransitions: (from: WorkStatus) => getWorkStateMachine().getValidTransitions(from),
  isTerminal: (status: WorkStatus) => getWorkStateMachine().isTerminal(status),
  canCancel: (status: WorkStatus) => getWorkStateMachine().canCancel(status),
  getNextProgressState: (current: WorkStatus) => getWorkStateMachine().getNextProgressState(current),
  getAllStates: () => getWorkStateMachine().getAllStates(),
};
