/**
 * API exports for the Agent Orchestration Platform
 */

export * from './router';
export * from './roles';
export * from './work';
export * from './pipelines';
export * from './webhooks';
export * from './config';
export * from './openclaw';

import { Router, json, notFound } from './router';
import { createRolesRouter } from './roles';
import { createWorkRouter } from './work';
import { createPipelinesRouter } from './pipelines';
import { createWebhooksRouter } from './webhooks';
import { createConfigRouter } from './config';
import { createOpenClawRouter } from './openclaw';

/**
 * Create the main API router with all endpoints mounted
 */
export function createApiRouter(): Router {
  const router = new Router('/api');

  // Health check endpoint
  router.get('/health', async ({ res }) => {
    json(res, { 
      status: 'ok', 
      service: 'orchestrator',
      timestamp: new Date().toISOString(),
    });
  });

  // Mount role endpoints
  router.use('/api/roles', createRolesRouter());

  // Mount work endpoints
  router.use('/api/work', createWorkRouter());

  // Mount pipeline endpoints
  router.use('/api/pipelines', createPipelinesRouter());

  // Mount webhook endpoints (P4-2)
  router.use('/api/webhooks', createWebhooksRouter());

  // Mount config export/import endpoints (P4-3)
  router.use('/api/config', createConfigRouter());

  // Mount OpenClaw sessions endpoints (P4-1)
  router.use('/api/openclaw', createOpenClawRouter());

  return router;
}

/**
 * Create a request handler for the API
 * Can be used with Node.js http server
 */
export function createApiHandler() {
  const router = createApiRouter();

  return async (req: import('http').IncomingMessage, res: import('http').ServerResponse) => {
    try {
      // Handle CORS preflight
      if (req.method === 'OPTIONS') {
        res.writeHead(204, {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        });
        res.end();
        return;
      }

      const handled = await router.handle(req, res);
      if (!handled) {
        notFound(res, `Route not found: ${req.method} ${req.url}`);
      }
    } catch (err) {
      console.error('API Error:', err);
      json(res, { error: 'Internal server error' }, 500);
    }
  };
}
