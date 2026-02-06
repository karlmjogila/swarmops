/**
 * Config Export/Import API Endpoints
 * P4-3: Export/import roles, pipelines as JSON
 */

import { Router, json, badRequest, error } from './router';
import {
  getConfigExportService,
  ExportOptions,
  ImportOptions,
  ExportBundle,
} from '../services/config-export';

/**
 * Create the config API router
 */
export function createConfigRouter(): Router {
  const router = new Router();
  const service = getConfigExportService();

  // Get export statistics
  router.get('/stats', async ({ res }) => {
    const stats = await service.getExportStats();
    json(res, stats);
  });

  // Export configurations
  router.post('/export', async ({ res, body }) => {
    const options = (body as ExportOptions) ?? {};

    try {
      const bundle = await service.export(options);
      json(res, bundle);
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Export as downloadable JSON file
  router.get('/export/download', async ({ res, query }) => {
    const options: ExportOptions = {
      includeRoles: query.get('roles') !== 'false',
      includePipelines: query.get('pipelines') !== 'false',
      includeWebhooks: query.get('webhooks') === 'true',
      includeRoleDependencies: query.get('dependencies') === 'true',
      description: query.get('description') ?? undefined,
    };

    // Parse specific IDs if provided
    const roleIds = query.get('roleIds');
    if (roleIds) {
      options.roleIds = roleIds.split(',');
    }
    const pipelineIds = query.get('pipelineIds');
    if (pipelineIds) {
      options.pipelineIds = pipelineIds.split(',');
    }

    try {
      const jsonStr = await service.exportToJson(options);
      const filename = `orchestrator-config-${new Date().toISOString().split('T')[0]}.json`;
      
      res.writeHead(200, {
        'Content-Type': 'application/json',
        'Content-Disposition': `attachment; filename="${filename}"`,
        'Access-Control-Allow-Origin': '*',
      });
      res.end(jsonStr);
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Validate an export bundle
  router.post('/validate', async ({ res, body }) => {
    if (!body || typeof body !== 'object') {
      badRequest(res, 'Request body required');
      return;
    }

    const bundle = body as ExportBundle;
    
    if (!bundle.manifest) {
      badRequest(res, 'Invalid bundle: missing manifest');
      return;
    }

    try {
      const result = await service.validate(bundle);
      json(res, result);
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Import configurations
  router.post('/import', async ({ res, body }) => {
    if (!body || typeof body !== 'object') {
      badRequest(res, 'Request body required');
      return;
    }

    const { bundle, options } = body as {
      bundle: ExportBundle;
      options?: ImportOptions;
    };

    if (!bundle || !bundle.manifest) {
      badRequest(res, 'Invalid bundle: missing manifest');
      return;
    }

    try {
      const result = await service.import(bundle, options ?? {});
      json(res, result, result.success ? 200 : 400);
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Dry-run import (validate without changes)
  router.post('/import/dry-run', async ({ res, body }) => {
    if (!body || typeof body !== 'object') {
      badRequest(res, 'Request body required');
      return;
    }

    const { bundle, options } = body as {
      bundle: ExportBundle;
      options?: ImportOptions;
    };

    if (!bundle || !bundle.manifest) {
      badRequest(res, 'Invalid bundle: missing manifest');
      return;
    }

    try {
      const result = await service.import(bundle, { ...options, dryRun: true });
      json(res, result);
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Export specific role(s)
  router.get('/export/roles', async ({ res, query }) => {
    const ids = query.get('ids')?.split(',');
    
    try {
      const bundle = await service.export({
        includeRoles: true,
        includePipelines: false,
        includeWebhooks: false,
        roleIds: ids,
      });
      json(res, { roles: bundle.roles });
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Export specific pipeline(s)
  router.get('/export/pipelines', async ({ res, query }) => {
    const ids = query.get('ids')?.split(',');
    const includeDeps = query.get('dependencies') === 'true';
    
    try {
      const bundle = await service.export({
        includeRoles: includeDeps,
        includePipelines: true,
        includeWebhooks: false,
        pipelineIds: ids,
        includeRoleDependencies: includeDeps,
      });
      json(res, { 
        pipelines: bundle.pipelines,
        roles: includeDeps ? bundle.roles : undefined,
      });
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Import roles only
  router.post('/import/roles', async ({ res, body }) => {
    if (!body || typeof body !== 'object') {
      badRequest(res, 'Request body required');
      return;
    }

    const { roles, mergeStrategy } = body as {
      roles: ExportBundle['roles'];
      mergeStrategy?: 'skip' | 'replace' | 'merge';
    };

    if (!roles || !Array.isArray(roles)) {
      badRequest(res, 'roles array required');
      return;
    }

    const bundle: ExportBundle = {
      manifest: {
        version: '1.0',
        exportedAt: new Date().toISOString(),
        description: 'Roles import',
      },
      roles,
    };

    try {
      const result = await service.import(bundle, {
        importRoles: true,
        importPipelines: false,
        importWebhooks: false,
        mergeStrategy,
      });
      json(res, result, result.success ? 200 : 400);
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Import pipelines only
  router.post('/import/pipelines', async ({ res, body }) => {
    if (!body || typeof body !== 'object') {
      badRequest(res, 'Request body required');
      return;
    }

    const { pipelines, roles, mergeStrategy } = body as {
      pipelines: ExportBundle['pipelines'];
      roles?: ExportBundle['roles'];
      mergeStrategy?: 'skip' | 'replace' | 'merge';
    };

    if (!pipelines || !Array.isArray(pipelines)) {
      badRequest(res, 'pipelines array required');
      return;
    }

    const bundle: ExportBundle = {
      manifest: {
        version: '1.0',
        exportedAt: new Date().toISOString(),
        description: 'Pipelines import',
      },
      pipelines,
      roles,
    };

    try {
      const result = await service.import(bundle, {
        importRoles: !!roles,
        importPipelines: true,
        importWebhooks: false,
        mergeStrategy,
      });
      json(res, result, result.success ? 200 : 400);
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  return router;
}
