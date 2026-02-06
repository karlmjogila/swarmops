/**
 * OpenClaw Sessions API Endpoints
 * P4-1: Integration with OpenClaw's sessions for actually running agents
 */

import { Router, json, notFound, badRequest, error } from './router';
import {
  getOpenClawService,
  OpenClawSpawnOptions,
  OpenClawSendOptions,
  OpenClawConfig,
} from '../services/openclaw';

/**
 * Create the OpenClaw sessions API router
 */
export function createOpenClawRouter(): Router {
  const router = new Router();
  const service = getOpenClawService();

  // Get service configuration
  router.get('/config', async ({ res }) => {
    const config = service.getConfig();
    // Don't expose the token
    json(res, { ...config, gatewayToken: config.gatewayToken ? '***' : undefined });
  });

  // Update service configuration
  router.patch('/config', async ({ res, body }) => {
    if (!body || typeof body !== 'object') {
      badRequest(res, 'Request body required');
      return;
    }

    const updates = body as Partial<OpenClawConfig>;
    service.updateConfig(updates);
    
    const config = service.getConfig();
    json(res, { ...config, gatewayToken: config.gatewayToken ? '***' : undefined });
  });

  // List OpenClaw sessions
  router.get('/sessions', async ({ res, query }) => {
    const status = query.get('status') as 'running' | 'stopped' | 'all' | null;
    const label = query.get('label');
    const limit = query.get('limit') ? parseInt(query.get('limit')!, 10) : undefined;

    try {
      const sessions = await service.listSessions({
        status: status ?? undefined,
        label: label ?? undefined,
        limit,
      });
      json(res, { sessions, total: sessions.length });
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Spawn a new OpenClaw session
  router.post('/sessions/spawn', async ({ res, body }) => {
    if (!body || typeof body !== 'object') {
      badRequest(res, 'Request body required');
      return;
    }

    const { roleId, task, label, model, thinking, workdir, env, timeoutMs, background, pty } = body as {
      roleId: string;
      task: string;
      label?: string;
      model?: string;
      thinking?: 'off' | 'low' | 'medium' | 'high';
      workdir?: string;
      env?: Record<string, string>;
      timeoutMs?: number;
      background?: boolean;
      pty?: boolean;
    };

    if (!roleId || !task) {
      badRequest(res, 'roleId and task are required');
      return;
    }

    const options: OpenClawSpawnOptions = {
      task,
      label,
      model,
      thinking,
      workdir,
      env,
      timeoutMs,
      background,
      pty,
    };

    try {
      const session = await service.spawnSession(roleId, options);
      json(res, session, 201);
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Send message to a session
  router.post('/sessions/:sessionKey/send', async ({ res, params, body }) => {
    if (!body || typeof body !== 'object') {
      badRequest(res, 'Request body required');
      return;
    }

    const { message, waitForResponse, timeoutMs } = body as {
      message: string;
      waitForResponse?: boolean;
      timeoutMs?: number;
    };

    if (!message) {
      badRequest(res, 'message is required');
      return;
    }

    const options: OpenClawSendOptions = {
      message,
      waitForResponse,
      timeoutMs,
    };

    try {
      const response = await service.sendMessage(params.sessionKey, options);
      json(res, response);
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Stop a session
  router.post('/sessions/:sessionKey/stop', async ({ res, params, body }) => {
    const { reason, force } = (body as { reason?: string; force?: boolean }) ?? {};

    try {
      await service.stopSession(params.sessionKey, { reason, force });
      json(res, { stopped: true, sessionKey: params.sessionKey });
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  // Get OpenClaw session ID for an orchestrator session
  router.get('/sessions/:sessionKey/openclaw-id', async ({ res, params }) => {
    const openclawId = service.getOpenClawSessionId(params.sessionKey);
    if (!openclawId) {
      notFound(res, `No OpenClaw session ID found for ${params.sessionKey}`);
      return;
    }
    json(res, { sessionKey: params.sessionKey, openclawSessionId: openclawId });
  });

  // Sync orchestrator sessions with OpenClaw
  router.post('/sync', async ({ res }) => {
    try {
      const result = await service.syncSessions();
      json(res, result);
    } catch (err) {
      error(res, err instanceof Error ? err.message : String(err));
    }
  });

  return router;
}
