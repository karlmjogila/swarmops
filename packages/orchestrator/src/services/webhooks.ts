/**
 * Webhook Hooks Service
 * P4-2: Notify external systems of pipeline events, completions, failures
 */

import { EventEmitter } from 'events';
import * as fs from 'fs/promises';
import * as path from 'path';
import { PipelineEvent, PipelineRunState, Pipeline } from '../types/pipeline';
import { WorkItem, WorkEvent } from '../types/work';
import { TrackedSession } from '../types/session';
import { timestamp, generateId } from '../storage/base';

/**
 * Ensure directory exists
 */
async function ensureDir(dir: string): Promise<void> {
  await fs.mkdir(dir, { recursive: true });
}

/**
 * Webhook event types
 */
export type WebhookEventType =
  | 'pipeline.started'
  | 'pipeline.completed'
  | 'pipeline.failed'
  | 'pipeline.step.started'
  | 'pipeline.step.completed'
  | 'pipeline.step.failed'
  | 'work.created'
  | 'work.started'
  | 'work.completed'
  | 'work.failed'
  | 'work.cancelled'
  | 'session.spawned'
  | 'session.active'
  | 'session.stopped'
  | 'session.error';

/**
 * Webhook configuration
 */
export interface WebhookConfig {
  /** Unique webhook ID */
  id: string;
  /** Human-readable name */
  name: string;
  /** Target URL to send webhooks to */
  url: string;
  /** HTTP method (default POST) */
  method?: 'POST' | 'PUT' | 'PATCH';
  /** Event types to subscribe to (empty = all) */
  events: WebhookEventType[];
  /** Additional headers to include */
  headers?: Record<string, string>;
  /** Secret for HMAC signature */
  secret?: string;
  /** Whether webhook is active */
  enabled: boolean;
  /** Retry configuration */
  retry?: {
    maxAttempts: number;
    delayMs: number;
    backoffMultiplier: number;
  };
  /** Filter by pipeline ID (optional) */
  pipelineIds?: string[];
  /** Filter by role ID (optional) */
  roleIds?: string[];
  /** Created timestamp */
  createdAt: string;
  /** Updated timestamp */
  updatedAt: string;
}

/**
 * Webhook delivery payload
 */
export interface WebhookPayload {
  /** Delivery ID */
  id: string;
  /** Event type */
  event: WebhookEventType;
  /** Timestamp */
  timestamp: string;
  /** Event data */
  data: Record<string, unknown>;
}

/**
 * Webhook delivery record
 */
export interface WebhookDelivery {
  /** Delivery ID */
  id: string;
  /** Webhook ID */
  webhookId: string;
  /** Event type */
  event: WebhookEventType;
  /** Request payload */
  payload: WebhookPayload;
  /** Response status code */
  statusCode?: number;
  /** Response body (truncated) */
  responseBody?: string;
  /** Error message if failed */
  error?: string;
  /** Number of attempts */
  attempts: number;
  /** Success status */
  success: boolean;
  /** Created timestamp */
  createdAt: string;
  /** Completed timestamp */
  completedAt?: string;
}

/**
 * Input for creating a webhook
 */
export interface WebhookCreateInput {
  name: string;
  url: string;
  method?: 'POST' | 'PUT' | 'PATCH';
  events: WebhookEventType[];
  headers?: Record<string, string>;
  secret?: string;
  enabled?: boolean;
  retry?: {
    maxAttempts: number;
    delayMs: number;
    backoffMultiplier: number;
  };
  pipelineIds?: string[];
  roleIds?: string[];
}

/**
 * Webhook update input
 */
export interface WebhookUpdateInput {
  name?: string;
  url?: string;
  method?: 'POST' | 'PUT' | 'PATCH';
  events?: WebhookEventType[];
  headers?: Record<string, string>;
  secret?: string;
  enabled?: boolean;
  retry?: {
    maxAttempts: number;
    delayMs: number;
    backoffMultiplier: number;
  };
  pipelineIds?: string[];
  roleIds?: string[];
}

/**
 * Default retry configuration
 */
const DEFAULT_RETRY = {
  maxAttempts: 3,
  delayMs: 1000,
  backoffMultiplier: 2,
};

/**
 * Webhook Hooks Service
 */
export class WebhookService extends EventEmitter {
  private dataDir: string;
  private webhooks: Map<string, WebhookConfig> = new Map();
  private deliveryLog: WebhookDelivery[] = [];
  private maxDeliveryLogSize: number = 1000;
  private initialized: boolean = false;

  constructor(dataDir?: string) {
    super();
    this.dataDir = dataDir ?? path.join(process.cwd(), '.orchestrator', 'webhooks');
  }

  /**
   * Initialize the service (load webhooks from disk)
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    await ensureDir(this.dataDir);
    
    const webhooksFile = path.join(this.dataDir, 'webhooks.json');
    try {
      const data = await fs.readFile(webhooksFile, 'utf-8');
      const webhooks = JSON.parse(data) as WebhookConfig[];
      for (const webhook of webhooks) {
        this.webhooks.set(webhook.id, webhook);
      }
    } catch (error) {
      // File doesn't exist yet, start fresh
    }

    // Load recent deliveries
    const deliveriesFile = path.join(this.dataDir, 'deliveries.json');
    try {
      const data = await fs.readFile(deliveriesFile, 'utf-8');
      this.deliveryLog = JSON.parse(data) as WebhookDelivery[];
    } catch {
      // File doesn't exist yet
    }

    this.initialized = true;
  }

  /**
   * Save webhooks to disk
   */
  private async saveWebhooks(): Promise<void> {
    const webhooksFile = path.join(this.dataDir, 'webhooks.json');
    const webhooks = Array.from(this.webhooks.values());
    await fs.writeFile(webhooksFile, JSON.stringify(webhooks, null, 2));
  }

  /**
   * Save deliveries to disk
   */
  private async saveDeliveries(): Promise<void> {
    const deliveriesFile = path.join(this.dataDir, 'deliveries.json');
    // Keep only recent deliveries
    const recentDeliveries = this.deliveryLog.slice(-this.maxDeliveryLogSize);
    await fs.writeFile(deliveriesFile, JSON.stringify(recentDeliveries, null, 2));
  }

  /**
   * Create a new webhook
   */
  async create(input: WebhookCreateInput): Promise<WebhookConfig> {
    await this.initialize();

    const now = timestamp();
    const webhook: WebhookConfig = {
      id: generateId(),
      name: input.name,
      url: input.url,
      method: input.method ?? 'POST',
      events: input.events,
      headers: input.headers,
      secret: input.secret,
      enabled: input.enabled ?? true,
      retry: input.retry ?? DEFAULT_RETRY,
      pipelineIds: input.pipelineIds,
      roleIds: input.roleIds,
      createdAt: now,
      updatedAt: now,
    };

    this.webhooks.set(webhook.id, webhook);
    await this.saveWebhooks();

    this.emit('webhook:created', webhook);
    return webhook;
  }

  /**
   * Get a webhook by ID
   */
  async get(id: string): Promise<WebhookConfig | null> {
    await this.initialize();
    return this.webhooks.get(id) ?? null;
  }

  /**
   * List all webhooks
   */
  async list(filters?: {
    enabled?: boolean;
    event?: WebhookEventType;
  }): Promise<WebhookConfig[]> {
    await this.initialize();

    let webhooks = Array.from(this.webhooks.values());

    if (filters?.enabled !== undefined) {
      webhooks = webhooks.filter(w => w.enabled === filters.enabled);
    }

    if (filters?.event) {
      webhooks = webhooks.filter(w => 
        w.events.length === 0 || w.events.includes(filters.event!)
      );
    }

    return webhooks;
  }

  /**
   * Update a webhook
   */
  async update(id: string, input: WebhookUpdateInput): Promise<WebhookConfig> {
    await this.initialize();

    const webhook = this.webhooks.get(id);
    if (!webhook) {
      throw new Error(`Webhook ${id} not found`);
    }

    const updated: WebhookConfig = {
      ...webhook,
      ...input,
      updatedAt: timestamp(),
    };

    this.webhooks.set(id, updated);
    await this.saveWebhooks();

    this.emit('webhook:updated', updated);
    return updated;
  }

  /**
   * Delete a webhook
   */
  async delete(id: string): Promise<boolean> {
    await this.initialize();

    const deleted = this.webhooks.delete(id);
    if (deleted) {
      await this.saveWebhooks();
      this.emit('webhook:deleted', { id });
    }
    return deleted;
  }

  /**
   * Enable/disable a webhook
   */
  async setEnabled(id: string, enabled: boolean): Promise<WebhookConfig> {
    return this.update(id, { enabled });
  }

  /**
   * Trigger webhook(s) for an event
   */
  async trigger(
    event: WebhookEventType,
    data: Record<string, unknown>,
    context?: {
      pipelineId?: string;
      roleId?: string;
    }
  ): Promise<WebhookDelivery[]> {
    await this.initialize();

    // Find matching webhooks
    const webhooks = Array.from(this.webhooks.values()).filter(w => {
      if (!w.enabled) return false;
      if (w.events.length > 0 && !w.events.includes(event)) return false;
      if (context?.pipelineId && w.pipelineIds?.length && 
          !w.pipelineIds.includes(context.pipelineId)) return false;
      if (context?.roleId && w.roleIds?.length && 
          !w.roleIds.includes(context.roleId)) return false;
      return true;
    });

    // Deliver to each webhook
    const deliveries: WebhookDelivery[] = [];
    for (const webhook of webhooks) {
      const delivery = await this.deliver(webhook, event, data);
      deliveries.push(delivery);
    }

    return deliveries;
  }

  /**
   * Deliver a webhook
   */
  private async deliver(
    webhook: WebhookConfig,
    event: WebhookEventType,
    data: Record<string, unknown>
  ): Promise<WebhookDelivery> {
    const deliveryId = generateId();
    const payload: WebhookPayload = {
      id: deliveryId,
      event,
      timestamp: timestamp(),
      data,
    };

    const delivery: WebhookDelivery = {
      id: deliveryId,
      webhookId: webhook.id,
      event,
      payload,
      attempts: 0,
      success: false,
      createdAt: timestamp(),
    };

    const retry = webhook.retry ?? DEFAULT_RETRY;
    let delay = retry.delayMs;

    for (let attempt = 1; attempt <= retry.maxAttempts; attempt++) {
      delivery.attempts = attempt;

      try {
        const result = await this.sendRequest(webhook, payload);
        delivery.statusCode = result.statusCode;
        delivery.responseBody = result.body?.substring(0, 1000); // Truncate
        delivery.success = result.statusCode >= 200 && result.statusCode < 300;
        delivery.completedAt = timestamp();

        if (delivery.success) {
          break;
        }
      } catch (error) {
        delivery.error = error instanceof Error ? error.message : String(error);
      }

      // Wait before retry (except on last attempt)
      if (attempt < retry.maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, delay));
        delay *= retry.backoffMultiplier;
      }
    }

    // Log delivery
    this.deliveryLog.push(delivery);
    await this.saveDeliveries();

    this.emit('webhook:delivered', delivery);
    return delivery;
  }

  /**
   * Send HTTP request
   */
  private async sendRequest(
    webhook: WebhookConfig,
    payload: WebhookPayload
  ): Promise<{ statusCode: number; body: string }> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'User-Agent': 'Orchestrator-Webhook/1.0',
      'X-Webhook-ID': webhook.id,
      'X-Delivery-ID': payload.id,
      'X-Event-Type': payload.event,
      ...webhook.headers,
    };

    // Add HMAC signature if secret is configured
    if (webhook.secret) {
      const { createHmac } = await import('crypto');
      const signature = createHmac('sha256', webhook.secret)
        .update(JSON.stringify(payload))
        .digest('hex');
      headers['X-Signature'] = `sha256=${signature}`;
    }

    const response = await fetch(webhook.url, {
      method: webhook.method ?? 'POST',
      headers,
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(30000),
    });

    const body = await response.text();
    return {
      statusCode: response.status,
      body,
    };
  }

  /**
   * Get delivery history
   */
  async getDeliveries(filters?: {
    webhookId?: string;
    event?: WebhookEventType;
    success?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<{ deliveries: WebhookDelivery[]; total: number }> {
    await this.initialize();

    let deliveries = [...this.deliveryLog].reverse(); // Newest first

    if (filters?.webhookId) {
      deliveries = deliveries.filter(d => d.webhookId === filters.webhookId);
    }
    if (filters?.event) {
      deliveries = deliveries.filter(d => d.event === filters.event);
    }
    if (filters?.success !== undefined) {
      deliveries = deliveries.filter(d => d.success === filters.success);
    }

    const total = deliveries.length;
    const offset = filters?.offset ?? 0;
    const limit = filters?.limit ?? 50;
    
    deliveries = deliveries.slice(offset, offset + limit);

    return { deliveries, total };
  }

  /**
   * Retry a failed delivery
   */
  async retryDelivery(deliveryId: string): Promise<WebhookDelivery | null> {
    await this.initialize();

    const original = this.deliveryLog.find(d => d.id === deliveryId);
    if (!original) return null;

    const webhook = this.webhooks.get(original.webhookId);
    if (!webhook) return null;

    return this.deliver(webhook, original.event, original.payload.data);
  }

  /**
   * Test a webhook by sending a test event
   */
  async test(id: string): Promise<WebhookDelivery> {
    await this.initialize();

    const webhook = this.webhooks.get(id);
    if (!webhook) {
      throw new Error(`Webhook ${id} not found`);
    }

    return this.deliver(webhook, 'pipeline.started', {
      test: true,
      message: 'This is a test webhook delivery',
      timestamp: timestamp(),
    });
  }

  // ==========================================
  // Event Integration Helpers
  // ==========================================

  /**
   * Trigger pipeline event webhooks
   */
  async triggerPipelineEvent(
    event: PipelineEvent,
    pipeline: Pipeline,
    run?: PipelineRunState
  ): Promise<void> {
    const eventTypeMap: Record<string, WebhookEventType> = {
      'run_started': 'pipeline.started',
      'run_completed': 'pipeline.completed',
      'run_failed': 'pipeline.failed',
      'step_started': 'pipeline.step.started',
      'step_completed': 'pipeline.step.completed',
      'step_failed': 'pipeline.step.failed',
    };

    const webhookEvent = eventTypeMap[event.type];
    if (!webhookEvent) return;

    await this.trigger(webhookEvent, {
      event,
      pipeline: {
        id: pipeline.id,
        name: pipeline.name,
        description: pipeline.description,
      },
      run: run ? {
        id: run.id,
        status: run.status,
        currentStepIndex: run.currentStepIndex,
        input: run.input,
        output: run.output,
        startedAt: run.startedAt,
        completedAt: run.completedAt,
      } : undefined,
    }, { pipelineId: pipeline.id });
  }

  /**
   * Trigger work item event webhooks
   */
  async triggerWorkEvent(
    workItem: WorkItem,
    event: WorkEvent
  ): Promise<void> {
    const eventTypeMap: Record<string, WebhookEventType> = {
      'created': 'work.created',
      'started': 'work.started',
      'session_completed': 'work.completed',
      'session_failed': 'work.failed',
      'cancelled': 'work.cancelled',
    };

    const webhookEvent = eventTypeMap[event.type];
    if (!webhookEvent) return;

    await this.trigger(webhookEvent, {
      workItem: {
        id: workItem.id,
        type: workItem.type,
        roleId: workItem.roleId,
        title: workItem.title,
        status: workItem.status,
        input: workItem.input,
        output: workItem.output,
      },
      event,
    }, { roleId: workItem.roleId });
  }

  /**
   * Trigger session event webhooks
   */
  async triggerSessionEvent(
    eventType: 'spawned' | 'active' | 'stopped' | 'error',
    session: TrackedSession,
    error?: string
  ): Promise<void> {
    const webhookEvent = `session.${eventType}` as WebhookEventType;

    await this.trigger(webhookEvent, {
      session: {
        sessionKey: session.sessionKey,
        sessionId: session.sessionId,
        roleId: session.roleId,
        label: session.label,
        status: session.status,
        task: session.task,
        tokenUsage: session.tokenUsage,
        error: error ?? session.error,
      },
    }, { roleId: session.roleId });
  }
}

/** Singleton instance */
let defaultService: WebhookService | null = null;

/**
 * Get the default WebhookService instance
 */
export function getWebhookService(dataDir?: string): WebhookService {
  if (!defaultService) {
    defaultService = new WebhookService(dataDir);
  }
  return defaultService;
}

/**
 * Reset the singleton (for testing)
 */
export function resetWebhookService(): void {
  defaultService = null;
}
