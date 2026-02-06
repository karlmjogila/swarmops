/**
 * Pipeline API endpoints
 * P2: REST API for pipeline CRUD and run management
 */

import { Router, json, notFound, badRequest, conflict } from './router';
import { 
  getPipelineStorage, 
  getPipelineRunStorage, 
  NotFoundError, 
  ConflictError 
} from '../storage';
import type { 
  PipelineCreateInput, 
  PipelineUpdateInput, 
  PipelineStepInput,
  PipelineQueryFilters,
  PipelineRunQueryFilters,
} from '../types';

/**
 * Validate pipeline create input
 */
function validatePipelineCreate(input: unknown): PipelineCreateInput {
  if (!input || typeof input !== 'object') {
    throw new Error('Invalid input: expected object');
  }

  const data = input as Record<string, unknown>;

  if (!data.name || typeof data.name !== 'string') {
    throw new Error('Invalid input: name is required and must be a string');
  }

  if (data.name.length < 1 || data.name.length > 100) {
    throw new Error('Invalid input: name must be 1-100 characters');
  }

  return {
    name: data.name,
    description: typeof data.description === 'string' ? data.description : undefined,
    steps: Array.isArray(data.steps) ? data.steps : undefined,
    inputSchema: data.inputSchema as Record<string, unknown> | undefined,
    defaultConvergence: data.defaultConvergence as PipelineCreateInput['defaultConvergence'],
    autoContinue: typeof data.autoContinue === 'boolean' ? data.autoContinue : undefined,
    stopOnFailure: typeof data.stopOnFailure === 'boolean' ? data.stopOnFailure : undefined,
    tags: Array.isArray(data.tags) ? data.tags : undefined,
  };
}

/**
 * Validate pipeline update input
 */
function validatePipelineUpdate(input: unknown): PipelineUpdateInput {
  if (!input || typeof input !== 'object') {
    throw new Error('Invalid input: expected object');
  }

  const data = input as Record<string, unknown>;

  if (data.name !== undefined) {
    if (typeof data.name !== 'string' || data.name.length < 1 || data.name.length > 100) {
      throw new Error('Invalid input: name must be a string of 1-100 characters');
    }
  }

  return {
    name: typeof data.name === 'string' ? data.name : undefined,
    description: typeof data.description === 'string' ? data.description : undefined,
    steps: Array.isArray(data.steps) ? data.steps : undefined,
    inputSchema: data.inputSchema as Record<string, unknown> | undefined,
    defaultConvergence: data.defaultConvergence as PipelineUpdateInput['defaultConvergence'],
    autoContinue: typeof data.autoContinue === 'boolean' ? data.autoContinue : undefined,
    stopOnFailure: typeof data.stopOnFailure === 'boolean' ? data.stopOnFailure : undefined,
    tags: Array.isArray(data.tags) ? data.tags : undefined,
  };
}

/**
 * Validate step input
 */
function validateStepInput(input: unknown): PipelineStepInput {
  if (!input || typeof input !== 'object') {
    throw new Error('Invalid input: expected object');
  }

  const data = input as Record<string, unknown>;

  if (!data.name || typeof data.name !== 'string') {
    throw new Error('Invalid input: name is required');
  }

  if (!data.roleId || typeof data.roleId !== 'string') {
    throw new Error('Invalid input: roleId is required');
  }

  if (!data.action || typeof data.action !== 'string') {
    throw new Error('Invalid input: action is required');
  }

  return {
    name: data.name,
    roleId: data.roleId,
    action: data.action,
    input: data.input as Record<string, unknown> | undefined,
    outputSchema: typeof data.outputSchema === 'string' ? data.outputSchema : undefined,
    convergence: data.convergence as PipelineStepInput['convergence'],
    optional: typeof data.optional === 'boolean' ? data.optional : undefined,
    condition: typeof data.condition === 'string' ? data.condition : undefined,
    timeoutMs: typeof data.timeoutMs === 'number' ? data.timeoutMs : undefined,
    retryCount: typeof data.retryCount === 'number' ? data.retryCount : undefined,
    position: typeof data.position === 'number' ? data.position : undefined,
  };
}

/**
 * Parse query filters from URL search params
 */
function parseQueryFilters(url: string): PipelineQueryFilters {
  const searchParams = new URL(url, 'http://localhost').searchParams;
  const filters: PipelineQueryFilters = {};

  const nameContains = searchParams.get('name');
  if (nameContains) filters.nameContains = nameContains;

  const tag = searchParams.get('tag');
  if (tag) filters.tag = tag;

  const limit = searchParams.get('limit');
  if (limit) filters.limit = parseInt(limit, 10);

  const offset = searchParams.get('offset');
  if (offset) filters.offset = parseInt(offset, 10);

  return filters;
}

/**
 * Parse run query filters from URL search params
 */
function parseRunQueryFilters(url: string): PipelineRunQueryFilters {
  const searchParams = new URL(url, 'http://localhost').searchParams;
  const filters: PipelineRunQueryFilters = {};

  const pipelineId = searchParams.get('pipelineId');
  if (pipelineId) filters.pipelineId = pipelineId;

  const status = searchParams.get('status');
  if (status) filters.status = status as PipelineRunQueryFilters['status'];

  const fromDate = searchParams.get('fromDate');
  if (fromDate) filters.fromDate = fromDate;

  const toDate = searchParams.get('toDate');
  if (toDate) filters.toDate = toDate;

  const limit = searchParams.get('limit');
  if (limit) filters.limit = parseInt(limit, 10);

  const offset = searchParams.get('offset');
  if (offset) filters.offset = parseInt(offset, 10);

  return filters;
}

/**
 * Create the pipelines router with all endpoints
 */
export function createPipelinesRouter(): Router {
  const router = new Router();
  const storage = getPipelineStorage();
  const runStorage = getPipelineRunStorage();

  /**
   * GET /pipelines - List all pipelines
   */
  router.get('', async ({ req, res }) => {
    const filters = parseQueryFilters(req.url || '');
    const result = await storage.list(filters);
    json(res, result);
  });

  /**
   * GET /pipelines/:id - Get a pipeline by ID
   */
  router.get('/:id', async ({ res, params }) => {
    try {
      const pipeline = await storage.get(params.id);
      json(res, pipeline);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * POST /pipelines - Create a new pipeline
   */
  router.post('', async ({ res, body }) => {
    try {
      const input = validatePipelineCreate(body);
      const pipeline = await storage.create(input);
      json(res, pipeline, 201);
    } catch (err) {
      if (err instanceof ConflictError) {
        conflict(res, err.message);
      } else if (err instanceof Error && err.message.startsWith('Invalid input')) {
        badRequest(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * PUT /pipelines/:id - Update a pipeline
   */
  router.put('/:id', async ({ res, params, body }) => {
    try {
      const input = validatePipelineUpdate(body);
      const pipeline = await storage.update(params.id, input);
      json(res, pipeline);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else if (err instanceof ConflictError) {
        conflict(res, err.message);
      } else if (err instanceof Error && err.message.startsWith('Invalid input')) {
        badRequest(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * PATCH /pipelines/:id - Partial update a pipeline
   */
  router.patch('/:id', async ({ res, params, body }) => {
    try {
      const input = validatePipelineUpdate(body);
      const pipeline = await storage.update(params.id, input);
      json(res, pipeline);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else if (err instanceof ConflictError) {
        conflict(res, err.message);
      } else if (err instanceof Error && err.message.startsWith('Invalid input')) {
        badRequest(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * DELETE /pipelines/:id - Delete a pipeline
   */
  router.delete('/:id', async ({ res, params }) => {
    try {
      await storage.delete(params.id);
      json(res, { success: true }, 200);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * POST /pipelines/:id/steps - Add a step to a pipeline
   */
  router.post('/:id/steps', async ({ res, params, body }) => {
    try {
      const input = validateStepInput(body);
      const step = await storage.addStep(params.id, input);
      json(res, step, 201);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else if (err instanceof Error && err.message.startsWith('Invalid input')) {
        badRequest(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * PUT /pipelines/:id/steps/:stepId - Update a step
   */
  router.put('/:id/steps/:stepId', async ({ res, params, body }) => {
    try {
      const input = validateStepInput(body);
      const step = await storage.updateStep(params.id, params.stepId, input);
      json(res, step);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else if (err instanceof Error && err.message.startsWith('Invalid input')) {
        badRequest(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * DELETE /pipelines/:id/steps/:stepId - Remove a step
   */
  router.delete('/:id/steps/:stepId', async ({ res, params }) => {
    try {
      await storage.removeStep(params.id, params.stepId);
      json(res, { success: true }, 200);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * GET /pipelines/runs - List pipeline runs
   */
  router.get('/runs', async ({ req, res }) => {
    const filters = parseRunQueryFilters(req.url || '');
    const result = await runStorage.list(filters);
    json(res, result);
  });

  /**
   * GET /pipelines/runs/:runId - Get a specific run
   */
  router.get('/runs/:runId', async ({ res, params }) => {
    try {
      const run = await runStorage.get(params.runId);
      json(res, run);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * POST /pipelines/:id/runs - Start a new run
   */
  router.post('/:id/runs', async ({ res, params, body }) => {
    try {
      const pipeline = await storage.get(params.id);
      const input = body as Record<string, unknown> | undefined;
      const run = await runStorage.create(pipeline, input?.input as Record<string, unknown>);
      json(res, run, 201);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * DELETE /pipelines/runs/:runId - Delete a run
   */
  router.delete('/runs/:runId', async ({ res, params }) => {
    try {
      await runStorage.delete(params.runId);
      json(res, { success: true }, 200);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else {
        throw err;
      }
    }
  });

  return router;
}
