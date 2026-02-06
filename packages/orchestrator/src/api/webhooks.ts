/**
 * Webhook API Endpoints
 * P4-2: CRUD operations for webhook management
 */

import { Router, json, notFound, badRequest, error } from './router';
import {
  getWebhookService,
  WebhookCreateInput,
  WebhookUpdateInput,
  WebhookEventType,
} from '../services/webhooks';

/**
 * Create the webhooks API router
 */
export function createWebhooksRouter(): Router {
  const router = new Router();
  const service = getWebhookService();

  // List webhooks
  router.get('/', async ({ res, query }) => {
    const enabled = query.get('enabled');
    const event = query.get('event') as WebhookEventType | null;

    const webhooks = await service.list({
      enabled: enabled !== null ? enabled === 'true' : undefined,
      event: event ?? undefined,
    });

    json(res, { webhooks, total: webhooks.length });
  });

  // Get a single webhook
  router.get('/:id', async ({ res, params }) => {
    const webhook = await service.get(params.id);
    if (!webhook) {
      notFound(res, `Webhook ${params.id} not found`);
      return;
    }
    json(res, webhook);
  });

  // Create a webhook
  router.post('/', async ({ res, body }) => {
    if (!body || typeof body !== 'object') {
      badRequest(res, 'Request body required');
      return;
    }

    const input = body as WebhookCreateInput;
    
    if (!input.name || !input.url || !input.events) {
      badRequest(res, 'name, url, and events are required');
      return;
    }

    try {
      new URL(input.url);
    } catch {
      badRequest(res, 'Invalid URL');
      return;
    }

    const webhook = await service.create(input);
    json(res, webhook, 201);
  });

  // Update a webhook
  router.patch('/:id', async ({ res, params, body }) => {
    if (!body || typeof body !== 'object') {
      badRequest(res, 'Request body required');
      return;
    }

    const existing = await service.get(params.id);
    if (!existing) {
      notFound(res, `Webhook ${params.id} not found`);
      return;
    }

    const input = body as WebhookUpdateInput;
    
    if (input.url) {
      try {
        new URL(input.url);
      } catch {
        badRequest(res, 'Invalid URL');
        return;
      }
    }

    const webhook = await service.update(params.id, input);
    json(res, webhook);
  });

  // Delete a webhook
  router.delete('/:id', async ({ res, params }) => {
    const deleted = await service.delete(params.id);
    if (!deleted) {
      notFound(res, `Webhook ${params.id} not found`);
      return;
    }
    json(res, { deleted: true });
  });

  // Enable a webhook
  router.post('/:id/enable', async ({ res, params }) => {
    const existing = await service.get(params.id);
    if (!existing) {
      notFound(res, `Webhook ${params.id} not found`);
      return;
    }

    const webhook = await service.setEnabled(params.id, true);
    json(res, webhook);
  });

  // Disable a webhook
  router.post('/:id/disable', async ({ res, params }) => {
    const existing = await service.get(params.id);
    if (!existing) {
      notFound(res, `Webhook ${params.id} not found`);
      return;
    }

    const webhook = await service.setEnabled(params.id, false);
    json(res, webhook);
  });

  // Test a webhook
  router.post('/:id/test', async ({ res, params }) => {
    try {
      const delivery = await service.test(params.id);
      json(res, delivery);
    } catch (err) {
      if (err instanceof Error && err.message.includes('not found')) {
        notFound(res, err.message);
      } else {
        error(res, err instanceof Error ? err.message : String(err));
      }
    }
  });

  // Get delivery history
  router.get('/:id/deliveries', async ({ res, params, query }) => {
    const existing = await service.get(params.id);
    if (!existing) {
      notFound(res, `Webhook ${params.id} not found`);
      return;
    }

    const limit = query.get('limit') ? parseInt(query.get('limit')!, 10) : 50;
    const offset = query.get('offset') ? parseInt(query.get('offset')!, 10) : 0;
    const success = query.get('success');

    const { deliveries, total } = await service.getDeliveries({
      webhookId: params.id,
      success: success !== null ? success === 'true' : undefined,
      limit,
      offset,
    });

    json(res, { deliveries, total, hasMore: offset + deliveries.length < total });
  });

  // Retry a delivery
  router.post('/deliveries/:deliveryId/retry', async ({ res, params }) => {
    const delivery = await service.retryDelivery(params.deliveryId);
    if (!delivery) {
      notFound(res, `Delivery ${params.deliveryId} not found`);
      return;
    }
    json(res, delivery);
  });

  // List all deliveries
  router.get('/deliveries', async ({ res, query }) => {
    const limit = query.get('limit') ? parseInt(query.get('limit')!, 10) : 50;
    const offset = query.get('offset') ? parseInt(query.get('offset')!, 10) : 0;
    const event = query.get('event') as WebhookEventType | null;
    const success = query.get('success');

    const { deliveries, total } = await service.getDeliveries({
      event: event ?? undefined,
      success: success !== null ? success === 'true' : undefined,
      limit,
      offset,
    });

    json(res, { deliveries, total, hasMore: offset + deliveries.length < total });
  });

  // Manually trigger a webhook event
  router.post('/trigger', async ({ res, body }) => {
    if (!body || typeof body !== 'object') {
      badRequest(res, 'Request body required');
      return;
    }

    const { event, data, pipelineId, roleId } = body as {
      event: WebhookEventType;
      data: Record<string, unknown>;
      pipelineId?: string;
      roleId?: string;
    };

    if (!event || !data) {
      badRequest(res, 'event and data are required');
      return;
    }

    const deliveries = await service.trigger(event, data, { pipelineId, roleId });
    json(res, { deliveries, count: deliveries.length });
  });

  return router;
}
