/**
 * Work API Endpoints
 * P1-08: REST API for work item management
 */

import { Router, json, notFound, badRequest, error } from './router';
import { getWorkStorage, NotFoundError, InvalidTransitionError } from '../storage';
import type { WorkCreateInput, WorkEventInput, WorkStatus, WorkType } from '../types';

/**
 * Validate work create input
 */
function validateWorkCreate(body: unknown): WorkCreateInput {
  if (!body || typeof body !== 'object') {
    throw new Error('Request body must be an object');
  }

  const input = body as Record<string, unknown>;

  if (!input.title || typeof input.title !== 'string') {
    throw new Error('title is required and must be a string');
  }

  if (!input.type || typeof input.type !== 'string') {
    throw new Error('type is required and must be a string');
  }

  const validTypes: WorkType[] = ['task', 'pipeline', 'batch', 'review', 'converge'];
  if (!validTypes.includes(input.type as WorkType)) {
    throw new Error(`type must be one of: ${validTypes.join(', ')}`);
  }

  return {
    type: input.type as WorkType,
    title: input.title,
    description: input.description as string | undefined,
    roleId: input.roleId as string | undefined,
    sessionKey: input.sessionKey as string | undefined,
    parentId: input.parentId as string | undefined,
    input: input.input as Record<string, unknown> | undefined,
    tags: input.tags as string[] | undefined,
    priority: input.priority as number | undefined,
  };
}

/**
 * Validate work event input
 */
function validateEventInput(body: unknown): WorkEventInput {
  if (!body || typeof body !== 'object') {
    throw new Error('Request body must be an object');
  }

  const input = body as Record<string, unknown>;

  if (!input.type || typeof input.type !== 'string') {
    throw new Error('type is required and must be a string');
  }

  if (!input.message || typeof input.message !== 'string') {
    throw new Error('message is required and must be a string');
  }

  return {
    type: input.type,
    message: input.message,
    data: input.data as Record<string, unknown> | undefined,
  };
}

/**
 * Parse query filters from URL search params
 */
function parseQueryFilters(query: URLSearchParams) {
  const filters: Record<string, unknown> = {};

  const date = query.get('date');
  if (date) filters.date = date;

  const fromDate = query.get('fromDate');
  if (fromDate) filters.fromDate = fromDate;

  const toDate = query.get('toDate');
  if (toDate) filters.toDate = toDate;

  const status = query.get('status');
  if (status) {
    // Support comma-separated values
    filters.status = status.includes(',') 
      ? status.split(',') as WorkStatus[]
      : status as WorkStatus;
  }

  const type = query.get('type');
  if (type) {
    filters.type = type.includes(',')
      ? type.split(',') as WorkType[]
      : type as WorkType;
  }

  const roleId = query.get('roleId');
  if (roleId) filters.roleId = roleId;

  const parentId = query.get('parentId');
  if (parentId) filters.parentId = parentId;

  const tag = query.get('tag');
  if (tag) filters.tag = tag;

  const limit = query.get('limit');
  if (limit) filters.limit = parseInt(limit, 10);

  const offset = query.get('offset');
  if (offset) filters.offset = parseInt(offset, 10);

  return filters;
}

/**
 * Create the work router with all endpoints
 */
export function createWorkRouter(): Router {
  const router = new Router();
  const storage = getWorkStorage();

  /**
   * GET /work - List work items with optional filters
   * 
   * Query params:
   * - date: YYYY-MM-DD (filter by specific date)
   * - fromDate: YYYY-MM-DD (filter from date)
   * - toDate: YYYY-MM-DD (filter to date)
   * - status: WorkStatus or comma-separated list
   * - type: WorkType or comma-separated list
   * - roleId: string
   * - parentId: string
   * - tag: string
   * - limit: number (default 100)
   * - offset: number (default 0)
   */
  router.get('', async ({ res, query }) => {
    try {
      const filters = parseQueryFilters(query);
      const result = await storage.list(filters);
      json(res, result);
    } catch (err) {
      error(res, (err as Error).message, 500);
    }
  });

  /**
   * GET /work/:id - Get a single work item by ID
   */
  router.get('/:id', async ({ res, params }) => {
    try {
      const item = await storage.get(params.id);
      json(res, item);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * POST /work - Create a new work item
   */
  router.post('', async ({ res, body }) => {
    try {
      const input = validateWorkCreate(body);
      const item = await storage.create(input);
      json(res, item, 201);
    } catch (err) {
      if ((err as Error).message.includes('required') || 
          (err as Error).message.includes('must be')) {
        badRequest(res, (err as Error).message);
      } else {
        throw err;
      }
    }
  });

  /**
   * POST /work/:id/event - Append an event to a work item
   */
  router.post('/:id/event', async ({ res, params, body }) => {
    try {
      const eventInput = validateEventInput(body);
      const item = await storage.appendEvent(params.id, eventInput);
      json(res, item);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else if ((err as Error).message.includes('required') ||
                 (err as Error).message.includes('must be')) {
        badRequest(res, (err as Error).message);
      } else {
        throw err;
      }
    }
  });

  /**
   * POST /work/:id/cancel - Cancel a work item
   */
  router.post('/:id/cancel', async ({ res, params, body }) => {
    try {
      const reason = (body as { reason?: string })?.reason;
      const item = await storage.cancel(params.id, reason);
      json(res, item);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else if (err instanceof InvalidTransitionError) {
        badRequest(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * GET /work/:id/children - Get child work items
   */
  router.get('/:id/children', async ({ res, params }) => {
    try {
      // First verify the parent exists
      await storage.get(params.id);
      const children = await storage.getChildren(params.id);
      json(res, { items: children, total: children.length });
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * POST /work/:id/status - Update work item status
   * Body: { status: WorkStatus, error?: string }
   */
  router.post('/:id/status', async ({ res, params, body }) => {
    try {
      const input = body as { status?: WorkStatus; error?: string };
      
      if (!input.status) {
        badRequest(res, 'status is required');
        return;
      }

      const validStatuses: WorkStatus[] = [
        'pending', 'queued', 'running', 'converging', 'complete', 'failed', 'cancelled'
      ];
      
      if (!validStatuses.includes(input.status)) {
        badRequest(res, `status must be one of: ${validStatuses.join(', ')}`);
        return;
      }

      const item = await storage.updateStatus(params.id, input.status, input.error);
      json(res, item);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else if (err instanceof InvalidTransitionError) {
        badRequest(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * POST /work/:id/output - Set work item output
   * Body: { output: Record<string, unknown> }
   */
  router.post('/:id/output', async ({ res, params, body }) => {
    try {
      const input = body as { output?: Record<string, unknown> };
      
      if (!input.output || typeof input.output !== 'object') {
        badRequest(res, 'output is required and must be an object');
        return;
      }

      const item = await storage.setOutput(params.id, input.output);
      json(res, item);
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
