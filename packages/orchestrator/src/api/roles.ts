/**
 * Role API endpoints
 */

import { Router, json, notFound, badRequest, conflict } from './router';
import { getRoleStorage, NotFoundError, ConflictError } from '../storage';
import { validateRoleCreate, validateRoleUpdate, ValidationError } from '../validation';
import type { RoleCreateInput, RoleUpdateInput } from '../types';

/**
 * Create the roles router with all endpoints
 */
export function createRolesRouter(): Router {
  const router = new Router();
  const storage = getRoleStorage();

  /**
   * GET /roles - List all roles
   */
  router.get('', async ({ res }) => {
    const roles = await storage.list();
    json(res, roles);
  });

  /**
   * GET /roles/:id - Get a role by ID
   */
  router.get('/:id', async ({ res, params }) => {
    try {
      const role = await storage.get(params.id);
      json(res, role);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * POST /roles - Create a new role
   */
  router.post('', async ({ res, body }) => {
    try {
      // Validate input
      const input = validateRoleCreate(body as RoleCreateInput);
      
      // Check name availability
      const nameAvailable = await storage.isNameAvailable(input.name);
      if (!nameAvailable) {
        conflict(res, `Role with name "${input.name}" already exists`);
        return;
      }

      const role = await storage.create(input);
      json(res, role, 201);
    } catch (err) {
      if (err instanceof ValidationError) {
        badRequest(res, err.message);
      } else if (err instanceof ConflictError) {
        conflict(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * PUT /roles/:id - Update a role
   */
  router.put('/:id', async ({ res, params, body }) => {
    try {
      // Validate input
      const input = validateRoleUpdate(body as RoleUpdateInput);

      // Check name availability if changing name
      if (input.name) {
        const nameAvailable = await storage.isNameAvailable(input.name, params.id);
        if (!nameAvailable) {
          conflict(res, `Role with name "${input.name}" already exists`);
          return;
        }
      }

      const role = await storage.update(params.id, input);
      json(res, role);
    } catch (err) {
      if (err instanceof ValidationError) {
        badRequest(res, err.message);
      } else if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else if (err instanceof ConflictError) {
        conflict(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * PATCH /roles/:id - Partial update a role
   */
  router.patch('/:id', async ({ res, params, body }) => {
    try {
      // Validate input (same as PUT for partial updates)
      const input = validateRoleUpdate(body as RoleUpdateInput);

      // Check name availability if changing name
      if (input.name) {
        const nameAvailable = await storage.isNameAvailable(input.name, params.id);
        if (!nameAvailable) {
          conflict(res, `Role with name "${input.name}" already exists`);
          return;
        }
      }

      const role = await storage.update(params.id, input);
      json(res, role);
    } catch (err) {
      if (err instanceof ValidationError) {
        badRequest(res, err.message);
      } else if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else if (err instanceof ConflictError) {
        conflict(res, err.message);
      } else {
        throw err;
      }
    }
  });

  /**
   * DELETE /roles/:id - Delete a role
   */
  router.delete('/:id', async ({ res, params }) => {
    try {
      await storage.delete(params.id);
      json(res, { success: true }, 200);
    } catch (err) {
      if (err instanceof NotFoundError) {
        notFound(res, err.message);
      } else if (err instanceof ConflictError) {
        conflict(res, err.message);
      } else {
        throw err;
      }
    }
  });

  return router;
}
