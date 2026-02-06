/**
 * Pipeline Storage
 * P2: File-based storage for pipelines and pipeline runs
 */

import * as path from 'path';
import { BaseStorage, NotFoundError, ConflictError, generateId, timestamp } from './base';
import {
  Pipeline,
  PipelineStep,
  PipelineRunState,
  PipelineCreateInput,
  PipelineUpdateInput,
  PipelineStepInput,
  PipelineRunInput,
  PipelineQueryFilters,
  PipelineListResult,
  PipelineRunQueryFilters,
  PipelineRunListResult,
  PipelineStepState,
  DEFAULT_CONVERGENCE,
} from '../types/pipeline';

/** Default storage directory */
const DEFAULT_STORAGE_DIR = process.env.ORCHESTRATOR_STORAGE_DIR || 
  path.join(process.env.HOME || '/tmp', '.orchestrator');

/**
 * Storage class for Pipeline definitions
 */
export class PipelineStorage extends BaseStorage<Pipeline> {
  constructor(filePath?: string) {
    super(filePath || path.join(DEFAULT_STORAGE_DIR, 'pipelines.json'));
  }

  /**
   * Create a new pipeline
   */
  async create(input: PipelineCreateInput): Promise<Pipeline> {
    const data = await this.readData();

    // Check for name conflict
    const existing = data.find(p => p.name.toLowerCase() === input.name.toLowerCase());
    if (existing) {
      throw new ConflictError(`Pipeline with name "${input.name}" already exists`);
    }

    const now = timestamp();
    const id = generateId();

    // Process steps if provided
    const steps: PipelineStep[] = (input.steps || []).map((step, index) => ({
      ...step,
      id: generateId(),
      order: index,
    }));

    const pipeline: Pipeline = {
      id,
      name: input.name,
      description: input.description || '',
      steps,
      inputSchema: input.inputSchema,
      defaultConvergence: input.defaultConvergence,
      autoContinue: input.autoContinue ?? true,
      stopOnFailure: input.stopOnFailure ?? true,
      tags: input.tags,
      createdAt: now,
      updatedAt: now,
    };

    data.push(pipeline);
    await this.writeData(data);

    return pipeline;
  }

  /**
   * Get a pipeline by ID
   */
  async get(id: string): Promise<Pipeline> {
    const data = await this.readData();
    const pipeline = data.find(p => p.id === id);

    if (!pipeline) {
      throw new NotFoundError('Pipeline', id);
    }

    return pipeline;
  }

  /**
   * Get a pipeline by name
   */
  async getByName(name: string): Promise<Pipeline> {
    const data = await this.readData();
    const pipeline = data.find(p => p.name.toLowerCase() === name.toLowerCase());

    if (!pipeline) {
      throw new NotFoundError('Pipeline', name);
    }

    return pipeline;
  }

  /**
   * Update a pipeline
   */
  async update(id: string, input: PipelineUpdateInput): Promise<Pipeline> {
    const data = await this.readData();
    const index = data.findIndex(p => p.id === id);

    if (index === -1) {
      throw new NotFoundError('Pipeline', id);
    }

    // Check for name conflict if updating name
    if (input.name) {
      const existing = data.find(p => 
        p.id !== id && p.name.toLowerCase() === input.name!.toLowerCase()
      );
      if (existing) {
        throw new ConflictError(`Pipeline with name "${input.name}" already exists`);
      }
    }

    const pipeline = data[index];
    const now = timestamp();

    // Process steps if provided
    let steps = pipeline.steps;
    if (input.steps) {
      steps = input.steps.map((step, index) => ({
        ...step,
        id: generateId(),
        order: index,
      }));
    }

    const updated: Pipeline = {
      ...pipeline,
      name: input.name ?? pipeline.name,
      description: input.description ?? pipeline.description,
      steps,
      inputSchema: input.inputSchema ?? pipeline.inputSchema,
      defaultConvergence: input.defaultConvergence ?? pipeline.defaultConvergence,
      autoContinue: input.autoContinue ?? pipeline.autoContinue,
      stopOnFailure: input.stopOnFailure ?? pipeline.stopOnFailure,
      tags: input.tags ?? pipeline.tags,
      updatedAt: now,
    };

    data[index] = updated;
    await this.writeData(data);

    return updated;
  }

  /**
   * Delete a pipeline
   */
  async delete(id: string): Promise<void> {
    const data = await this.readData();
    const index = data.findIndex(p => p.id === id);

    if (index === -1) {
      throw new NotFoundError('Pipeline', id);
    }

    data.splice(index, 1);
    await this.writeData(data);
  }

  /**
   * List pipelines with optional filters
   */
  async list(filters?: PipelineQueryFilters): Promise<PipelineListResult> {
    let data = await this.readData();

    // Apply filters
    if (filters?.nameContains) {
      const search = filters.nameContains.toLowerCase();
      data = data.filter(p => p.name.toLowerCase().includes(search));
    }

    if (filters?.tag) {
      data = data.filter(p => p.tags?.includes(filters.tag!));
    }

    const total = data.length;

    // Sort by createdAt descending
    data.sort((a, b) => 
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );

    // Apply pagination
    const offset = filters?.offset || 0;
    const limit = filters?.limit || 50;
    const paged = data.slice(offset, offset + limit);

    return {
      pipelines: paged,
      total,
      hasMore: offset + paged.length < total,
    };
  }

  /**
   * Add a step to a pipeline
   */
  async addStep(pipelineId: string, input: PipelineStepInput): Promise<PipelineStep> {
    const data = await this.readData();
    const index = data.findIndex(p => p.id === pipelineId);

    if (index === -1) {
      throw new NotFoundError('Pipeline', pipelineId);
    }

    const pipeline = data[index];
    const position = input.position ?? pipeline.steps.length;

    const step: PipelineStep = {
      id: generateId(),
      name: input.name,
      roleId: input.roleId,
      action: input.action,
      input: input.input,
      outputSchema: input.outputSchema,
      convergence: input.convergence,
      optional: input.optional,
      condition: input.condition,
      timeoutMs: input.timeoutMs,
      retryCount: input.retryCount,
      order: position,
    };

    // Insert at position and update order for subsequent steps
    pipeline.steps.splice(position, 0, step);
    pipeline.steps.forEach((s, i) => s.order = i);
    pipeline.updatedAt = timestamp();

    data[index] = pipeline;
    await this.writeData(data);

    return step;
  }

  /**
   * Remove a step from a pipeline
   */
  async removeStep(pipelineId: string, stepId: string): Promise<void> {
    const data = await this.readData();
    const pipelineIndex = data.findIndex(p => p.id === pipelineId);

    if (pipelineIndex === -1) {
      throw new NotFoundError('Pipeline', pipelineId);
    }

    const pipeline = data[pipelineIndex];
    const stepIndex = pipeline.steps.findIndex(s => s.id === stepId);

    if (stepIndex === -1) {
      throw new NotFoundError('PipelineStep', stepId);
    }

    pipeline.steps.splice(stepIndex, 1);
    pipeline.steps.forEach((s, i) => s.order = i);
    pipeline.updatedAt = timestamp();

    data[pipelineIndex] = pipeline;
    await this.writeData(data);
  }

  /**
   * Update a step in a pipeline
   */
  async updateStep(
    pipelineId: string, 
    stepId: string, 
    input: Partial<Omit<PipelineStepInput, 'position'>>
  ): Promise<PipelineStep> {
    const data = await this.readData();
    const pipelineIndex = data.findIndex(p => p.id === pipelineId);

    if (pipelineIndex === -1) {
      throw new NotFoundError('Pipeline', pipelineId);
    }

    const pipeline = data[pipelineIndex];
    const stepIndex = pipeline.steps.findIndex(s => s.id === stepId);

    if (stepIndex === -1) {
      throw new NotFoundError('PipelineStep', stepId);
    }

    const step = pipeline.steps[stepIndex];
    const updated: PipelineStep = {
      ...step,
      name: input.name ?? step.name,
      roleId: input.roleId ?? step.roleId,
      action: input.action ?? step.action,
      input: input.input ?? step.input,
      outputSchema: input.outputSchema ?? step.outputSchema,
      convergence: input.convergence ?? step.convergence,
      optional: input.optional ?? step.optional,
      condition: input.condition ?? step.condition,
      timeoutMs: input.timeoutMs ?? step.timeoutMs,
      retryCount: input.retryCount ?? step.retryCount,
    };

    pipeline.steps[stepIndex] = updated;
    pipeline.updatedAt = timestamp();

    data[pipelineIndex] = pipeline;
    await this.writeData(data);

    return updated;
  }
}

/**
 * Storage class for Pipeline Runs
 */
export class PipelineRunStorage extends BaseStorage<PipelineRunState> {
  constructor(filePath?: string) {
    super(filePath || path.join(DEFAULT_STORAGE_DIR, 'pipeline-runs.json'));
  }

  /**
   * Create a new pipeline run
   */
  async create(pipeline: Pipeline, input?: Record<string, unknown>): Promise<PipelineRunState> {
    const data = await this.readData();
    const now = timestamp();

    // Initialize step states
    const stepStates: PipelineStepState[] = pipeline.steps.map(step => ({
      stepId: step.id,
      status: 'pending',
      iterations: 0,
    }));

    const run: PipelineRunState = {
      id: generateId(),
      pipelineId: pipeline.id,
      status: 'pending',
      currentStepIndex: 0,
      stepStates,
      input,
      createdAt: now,
      updatedAt: now,
    };

    data.push(run);
    await this.writeData(data);

    return run;
  }

  /**
   * Get a run by ID
   */
  async get(id: string): Promise<PipelineRunState> {
    const data = await this.readData();
    const run = data.find(r => r.id === id);

    if (!run) {
      throw new NotFoundError('PipelineRun', id);
    }

    return run;
  }

  /**
   * Update run state
   */
  async update(id: string, updates: Partial<Omit<PipelineRunState, 'id' | 'pipelineId' | 'createdAt'>>): Promise<PipelineRunState> {
    const data = await this.readData();
    const index = data.findIndex(r => r.id === id);

    if (index === -1) {
      throw new NotFoundError('PipelineRun', id);
    }

    const run = data[index];
    const updated: PipelineRunState = {
      ...run,
      ...updates,
      updatedAt: timestamp(),
    };

    data[index] = updated;
    await this.writeData(data);

    return updated;
  }

  /**
   * Update a specific step's state
   */
  async updateStepState(runId: string, stepId: string, updates: Partial<PipelineStepState>): Promise<PipelineRunState> {
    const data = await this.readData();
    const runIndex = data.findIndex(r => r.id === runId);

    if (runIndex === -1) {
      throw new NotFoundError('PipelineRun', runId);
    }

    const run = data[runIndex];
    const stepIndex = run.stepStates.findIndex(s => s.stepId === stepId);

    if (stepIndex === -1) {
      throw new NotFoundError('PipelineStepState', stepId);
    }

    run.stepStates[stepIndex] = {
      ...run.stepStates[stepIndex],
      ...updates,
    };
    run.updatedAt = timestamp();

    data[runIndex] = run;
    await this.writeData(data);

    return run;
  }

  /**
   * List runs with optional filters
   */
  async list(filters?: PipelineRunQueryFilters): Promise<PipelineRunListResult> {
    let data = await this.readData();

    // Apply filters
    if (filters?.pipelineId) {
      data = data.filter(r => r.pipelineId === filters.pipelineId);
    }

    if (filters?.status) {
      const statuses = Array.isArray(filters.status) ? filters.status : [filters.status];
      data = data.filter(r => statuses.includes(r.status));
    }

    if (filters?.fromDate) {
      data = data.filter(r => r.createdAt >= filters.fromDate!);
    }

    if (filters?.toDate) {
      data = data.filter(r => r.createdAt <= filters.toDate!);
    }

    const total = data.length;

    // Sort by createdAt descending
    data.sort((a, b) => 
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );

    // Apply pagination
    const offset = filters?.offset || 0;
    const limit = filters?.limit || 50;
    const paged = data.slice(offset, offset + limit);

    return {
      runs: paged,
      total,
      hasMore: offset + paged.length < total,
    };
  }

  /**
   * Delete a run
   */
  async delete(id: string): Promise<void> {
    const data = await this.readData();
    const index = data.findIndex(r => r.id === id);

    if (index === -1) {
      throw new NotFoundError('PipelineRun', id);
    }

    data.splice(index, 1);
    await this.writeData(data);
  }

  /**
   * Get active runs (running or paused)
   */
  async getActiveRuns(): Promise<PipelineRunState[]> {
    const data = await this.readData();
    return data.filter(r => r.status === 'running' || r.status === 'paused');
  }
}

/** Singleton instances */
let defaultPipelineStorage: PipelineStorage | null = null;
let defaultRunStorage: PipelineRunStorage | null = null;

/**
 * Get the default PipelineStorage instance
 */
export function getPipelineStorage(): PipelineStorage {
  if (!defaultPipelineStorage) {
    defaultPipelineStorage = new PipelineStorage();
  }
  return defaultPipelineStorage;
}

/**
 * Get the default PipelineRunStorage instance
 */
export function getPipelineRunStorage(): PipelineRunStorage {
  if (!defaultRunStorage) {
    defaultRunStorage = new PipelineRunStorage();
  }
  return defaultRunStorage;
}
