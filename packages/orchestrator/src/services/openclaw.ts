/**
 * OpenClaw Sessions API Integration
 * P4-1: Connects the orchestrator to OpenClaw's sessions_spawn, sessions_list, sessions_send APIs
 */

import { EventEmitter } from 'events';
import {
  TrackedSession,
  SessionSpawnInput,
  SessionStatus,
  SessionTokenUsage,
} from '../types/session';
import { Role } from '../types/role';
import { getSessionStorage, SessionStorage } from '../storage/sessions';
import { getRoleStorage, RoleStorage } from '../storage/roles';
import { timestamp, generateId } from '../storage/base';
import { resolveInstructions } from '../utils/prompt-resolver';

/**
 * OpenClaw session spawn options
 */
export interface OpenClawSpawnOptions {
  /** Model to use (overrides role default) */
  model?: string;
  /** Thinking level (overrides role default) */
  thinking?: 'off' | 'low' | 'medium' | 'high';
  /** Session label */
  label?: string;
  /** Initial task/prompt to send */
  task: string;
  /** Working directory */
  workdir?: string;
  /** Environment variables */
  env?: Record<string, string>;
  /** Timeout in milliseconds */
  timeoutMs?: number;
  /** Whether to run in background */
  background?: boolean;
  /** Whether to use PTY */
  pty?: boolean;
}

/**
 * OpenClaw session info from list API
 */
export interface OpenClawSessionInfo {
  sessionId: string;
  sessionKey: string;
  status: 'running' | 'stopped' | 'error';
  label?: string;
  model?: string;
  startedAt: string;
  lastActivityAt?: string;
  tokenUsage?: {
    input: number;
    output: number;
  };
}

/**
 * OpenClaw send message options
 */
export interface OpenClawSendOptions {
  /** Message to send */
  message: string;
  /** Wait for response */
  waitForResponse?: boolean;
  /** Timeout for response */
  timeoutMs?: number;
}

/**
 * OpenClaw session response
 */
export interface OpenClawResponse {
  sessionId: string;
  response?: string;
  status: 'success' | 'error' | 'timeout';
  error?: string;
  tokenUsage?: {
    input: number;
    output: number;
  };
}

/**
 * OpenClaw connection configuration
 */
export interface OpenClawConfig {
  /** Path to openclaw CLI binary */
  cliBinary?: string;
  /** Gateway URL (if using HTTP API) */
  gatewayUrl?: string;
  /** Gateway token (if using HTTP API) */
  gatewayToken?: string;
  /** Default timeout for operations */
  defaultTimeoutMs?: number;
  /** Use CLI or HTTP API */
  mode?: 'cli' | 'http';
}

/**
 * Event types emitted by OpenClawService
 */
export interface OpenClawServiceEvents {
  'session:spawned': { sessionKey: string; roleId: string; label?: string };
  'session:message_sent': { sessionKey: string; message: string };
  'session:response': { sessionKey: string; response: string };
  'session:stopped': { sessionKey: string; exitCode?: number; error?: string };
  'session:error': { sessionKey: string; error: string };
}

/**
 * OpenClaw Sessions API Integration Service
 * Connects orchestrator sessions to actual OpenClaw agent execution
 */
export class OpenClawService extends EventEmitter {
  private config: Required<OpenClawConfig>;
  private sessionStorage: SessionStorage;
  private roleStorage: RoleStorage;
  
  /** Map of orchestrator session keys to OpenClaw session IDs */
  private sessionMapping: Map<string, string> = new Map();
  
  /** Active session processes (for CLI mode) */
  private activeProcesses: Map<string, { pid?: number; killed: boolean }> = new Map();

  constructor(
    config?: OpenClawConfig,
    sessionStorage?: SessionStorage,
    roleStorage?: RoleStorage
  ) {
    super();
    this.config = {
      cliBinary: config?.cliBinary ?? 'openclaw',
      gatewayUrl: config?.gatewayUrl ?? 'http://localhost:3939',
      gatewayToken: config?.gatewayToken ?? '',
      defaultTimeoutMs: config?.defaultTimeoutMs ?? 300000, // 5 minutes
      mode: config?.mode ?? 'http',
    };
    this.sessionStorage = sessionStorage ?? getSessionStorage();
    this.roleStorage = roleStorage ?? getRoleStorage();
  }

  /**
   * Spawn a new OpenClaw session for the given role
   */
  async spawnSession(
    roleId: string,
    options: OpenClawSpawnOptions,
    orchestratorSessionKey?: string
  ): Promise<TrackedSession> {
    // Get role for configuration
    const role = await this.roleStorage.get(roleId);

    // Resolve instructions from promptFile or inline
    const resolvedInstructions = await resolveInstructions(role);

    // Generate session identifiers
    const sessionId = generateId();
    const sessionKey = orchestratorSessionKey ?? `agent:worker:${roleId}:${sessionId}`;
    const label = options.label ?? `openclaw-${role.name}-${sessionId.substring(0, 8)}`;

    // Build the spawn command/request
    const spawnConfig = this.buildSpawnConfig(role, options, resolvedInstructions);

    // Track session in orchestrator
    const trackedSession = await this.sessionStorage.track({
      roleId,
      label,
      task: options.task,
    }, sessionKey);

    try {
      // Execute based on mode
      if (this.config.mode === 'cli') {
        await this.spawnViaCli(sessionKey, spawnConfig, options);
      } else {
        await this.spawnViaHttp(sessionKey, spawnConfig, options);
      }

      // Mark session as active
      await this.sessionStorage.markActive(sessionKey);

      this.emit('session:spawned', { sessionKey, roleId, label });

      return trackedSession;
    } catch (error) {
      // Mark session as failed
      const errorMsg = error instanceof Error ? error.message : String(error);
      await this.sessionStorage.markStopped(sessionKey, 1, errorMsg);
      
      this.emit('session:error', { sessionKey, error: errorMsg });
      throw error;
    }
  }

  /**
   * Build spawn configuration from role and options
   */
  private buildSpawnConfig(
    role: Role, 
    options: OpenClawSpawnOptions,
    resolvedInstructions: string
  ): Record<string, unknown> {
    return {
      model: options.model ?? role.model,
      thinking: options.thinking ?? role.thinking,
      systemPrompt: resolvedInstructions,
      label: options.label,
      task: options.task,
      workdir: options.workdir,
      env: options.env,
      timeout: options.timeoutMs ?? this.config.defaultTimeoutMs,
      pty: options.pty ?? false,
    };
  }

  /**
   * Spawn session using CLI
   */
  private async spawnViaCli(
    sessionKey: string,
    config: Record<string, unknown>,
    options: OpenClawSpawnOptions
  ): Promise<void> {
    const { spawn } = await import('child_process');
    
    const args: string[] = [
      'session', 'spawn',
      '--model', String(config.model ?? 'claude-sonnet-4-20250514'),
      '--label', String(config.label ?? 'worker'),
    ];

    if (config.thinking && config.thinking !== 'off') {
      args.push('--thinking', String(config.thinking));
    }

    if (config.systemPrompt) {
      args.push('--system', String(config.systemPrompt));
    }

    if (options.background) {
      args.push('--background');
    }

    // Add the task as the final argument
    args.push(String(config.task));

    return new Promise((resolve, reject) => {
      const proc = spawn(this.config.cliBinary, args, {
        cwd: options.workdir,
        env: { ...process.env, ...options.env },
        stdio: options.background ? 'ignore' : 'pipe',
        detached: options.background,
      });

      this.activeProcesses.set(sessionKey, { pid: proc.pid, killed: false });

      if (options.background) {
        proc.unref();
        resolve();
        return;
      }

      let output = '';
      let errorOutput = '';

      proc.stdout?.on('data', (data) => {
        output += data.toString();
      });

      proc.stderr?.on('data', (data) => {
        errorOutput += data.toString();
      });

      proc.on('error', (err) => {
        this.activeProcesses.delete(sessionKey);
        reject(err);
      });

      proc.on('close', (code) => {
        this.activeProcesses.delete(sessionKey);
        if (code !== 0) {
          reject(new Error(`OpenClaw CLI exited with code ${code}: ${errorOutput}`));
        } else {
          resolve();
        }
      });

      // Timeout handling
      if (options.timeoutMs) {
        setTimeout(() => {
          if (!proc.killed) {
            proc.kill('SIGTERM');
            reject(new Error('OpenClaw session spawn timed out'));
          }
        }, options.timeoutMs);
      }
    });
  }

  /**
   * Spawn session using HTTP API
   */
  private async spawnViaHttp(
    sessionKey: string,
    config: Record<string, unknown>,
    options: OpenClawSpawnOptions
  ): Promise<void> {
    const url = `${this.config.gatewayUrl}/api/sessions/spawn`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    if (this.config.gatewayToken) {
      headers['Authorization'] = `Bearer ${this.config.gatewayToken}`;
    }

    const body = {
      model: config.model,
      thinking: config.thinking,
      systemPrompt: config.systemPrompt,
      label: config.label,
      task: config.task,
      workdir: options.workdir,
      env: options.env,
      background: options.background ?? true,
      pty: options.pty,
      orchestratorSessionKey: sessionKey,
    };

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(options.timeoutMs ?? this.config.defaultTimeoutMs),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OpenClaw API error (${response.status}): ${errorText}`);
    }

    const result = await response.json() as { sessionId: string };
    this.sessionMapping.set(sessionKey, result.sessionId);
  }

  /**
   * List all OpenClaw sessions
   */
  async listSessions(filters?: {
    status?: 'running' | 'stopped' | 'all';
    label?: string;
    limit?: number;
  }): Promise<OpenClawSessionInfo[]> {
    if (this.config.mode === 'cli') {
      return this.listViaCli(filters);
    } else {
      return this.listViaHttp(filters);
    }
  }

  /**
   * List sessions via CLI
   */
  private async listViaCli(filters?: {
    status?: 'running' | 'stopped' | 'all';
    label?: string;
    limit?: number;
  }): Promise<OpenClawSessionInfo[]> {
    const { execSync } = await import('child_process');
    
    const args: string[] = ['session', 'list', '--json'];
    
    if (filters?.status && filters.status !== 'all') {
      args.push('--status', filters.status);
    }

    try {
      const output = execSync(`${this.config.cliBinary} ${args.join(' ')}`, {
        encoding: 'utf-8',
        timeout: 30000,
      });

      const sessions = JSON.parse(output) as OpenClawSessionInfo[];
      
      let filtered = sessions;
      if (filters?.label) {
        filtered = filtered.filter(s => s.label?.includes(filters.label!));
      }
      if (filters?.limit) {
        filtered = filtered.slice(0, filters.limit);
      }

      return filtered;
    } catch (error) {
      // CLI might not support session list yet, return empty
      console.warn('OpenClaw session list not available:', error);
      return [];
    }
  }

  /**
   * List sessions via HTTP API
   */
  private async listViaHttp(filters?: {
    status?: 'running' | 'stopped' | 'all';
    label?: string;
    limit?: number;
  }): Promise<OpenClawSessionInfo[]> {
    const params = new URLSearchParams();
    if (filters?.status) params.set('status', filters.status);
    if (filters?.label) params.set('label', filters.label);
    if (filters?.limit) params.set('limit', String(filters.limit));

    const url = `${this.config.gatewayUrl}/api/sessions?${params}`;
    
    const headers: Record<string, string> = {};
    if (this.config.gatewayToken) {
      headers['Authorization'] = `Bearer ${this.config.gatewayToken}`;
    }

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers,
        signal: AbortSignal.timeout(30000),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return await response.json() as OpenClawSessionInfo[];
    } catch (error) {
      console.warn('OpenClaw session list API not available:', error);
      return [];
    }
  }

  /**
   * Send a message to an OpenClaw session
   */
  async sendMessage(
    sessionKey: string,
    options: OpenClawSendOptions
  ): Promise<OpenClawResponse> {
    // Get the OpenClaw session ID
    const openclawSessionId = this.sessionMapping.get(sessionKey);

    // Update last activity
    await this.sessionStorage.update(sessionKey, {
      lastActivityAt: timestamp(),
    });

    this.emit('session:message_sent', { sessionKey, message: options.message });

    try {
      let result: OpenClawResponse;
      
      if (this.config.mode === 'cli') {
        result = await this.sendViaCli(sessionKey, openclawSessionId, options);
      } else {
        result = await this.sendViaHttp(sessionKey, openclawSessionId, options);
      }

      if (result.response) {
        this.emit('session:response', { sessionKey, response: result.response });
      }

      // Update token usage if available
      if (result.tokenUsage) {
        await this.sessionStorage.addTokenUsage(sessionKey, {
          input: result.tokenUsage.input,
          output: result.tokenUsage.output,
        });
      }

      return result;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      this.emit('session:error', { sessionKey, error: errorMsg });
      
      return {
        sessionId: openclawSessionId ?? sessionKey,
        status: 'error',
        error: errorMsg,
      };
    }
  }

  /**
   * Send message via CLI
   */
  private async sendViaCli(
    sessionKey: string,
    openclawSessionId: string | undefined,
    options: OpenClawSendOptions
  ): Promise<OpenClawResponse> {
    const { execSync } = await import('child_process');
    
    const targetId = openclawSessionId ?? sessionKey;
    const args: string[] = [
      'session', 'send',
      '--session', targetId,
      '--message', options.message,
    ];

    if (options.waitForResponse) {
      args.push('--wait');
    }

    try {
      const output = execSync(`${this.config.cliBinary} ${args.join(' ')}`, {
        encoding: 'utf-8',
        timeout: options.timeoutMs ?? this.config.defaultTimeoutMs,
      });

      return {
        sessionId: targetId,
        response: output.trim(),
        status: 'success',
      };
    } catch (error) {
      return {
        sessionId: targetId,
        status: 'error',
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * Send message via HTTP API
   */
  private async sendViaHttp(
    sessionKey: string,
    openclawSessionId: string | undefined,
    options: OpenClawSendOptions
  ): Promise<OpenClawResponse> {
    const targetId = openclawSessionId ?? sessionKey;
    const url = `${this.config.gatewayUrl}/api/sessions/${encodeURIComponent(targetId)}/send`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    if (this.config.gatewayToken) {
      headers['Authorization'] = `Bearer ${this.config.gatewayToken}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message: options.message,
        waitForResponse: options.waitForResponse,
      }),
      signal: AbortSignal.timeout(options.timeoutMs ?? this.config.defaultTimeoutMs),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return {
        sessionId: targetId,
        status: 'error',
        error: `HTTP ${response.status}: ${errorText}`,
      };
    }

    const result = await response.json() as {
      response?: string;
      tokenUsage?: { input: number; output: number };
    };

    return {
      sessionId: targetId,
      response: result.response,
      status: 'success',
      tokenUsage: result.tokenUsage,
    };
  }

  /**
   * Stop an OpenClaw session
   */
  async stopSession(
    sessionKey: string,
    options?: { reason?: string; force?: boolean }
  ): Promise<void> {
    const openclawSessionId = this.sessionMapping.get(sessionKey);
    const reason = options?.reason ?? 'Session stopped';

    try {
      if (this.config.mode === 'cli') {
        await this.stopViaCli(sessionKey, openclawSessionId, options?.force);
      } else {
        await this.stopViaHttp(sessionKey, openclawSessionId, options?.force);
      }

      // Update tracked session
      await this.sessionStorage.markStopped(sessionKey, 0, reason);
      
      this.emit('session:stopped', { sessionKey, exitCode: 0 });
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      await this.sessionStorage.markStopped(sessionKey, 1, errorMsg);
      
      this.emit('session:stopped', { sessionKey, exitCode: 1, error: errorMsg });
      throw error;
    } finally {
      this.sessionMapping.delete(sessionKey);
      this.activeProcesses.delete(sessionKey);
    }
  }

  /**
   * Stop session via CLI
   */
  private async stopViaCli(
    sessionKey: string,
    openclawSessionId: string | undefined,
    force?: boolean
  ): Promise<void> {
    // First try to kill the process directly if we have it
    const proc = this.activeProcesses.get(sessionKey);
    if (proc?.pid && !proc.killed) {
      try {
        process.kill(proc.pid, force ? 'SIGKILL' : 'SIGTERM');
        proc.killed = true;
        return;
      } catch {
        // Process may have already exited
      }
    }

    // Otherwise try CLI command
    const { execSync } = await import('child_process');
    const targetId = openclawSessionId ?? sessionKey;
    const args = ['session', 'stop', '--session', targetId];
    if (force) args.push('--force');

    try {
      execSync(`${this.config.cliBinary} ${args.join(' ')}`, {
        encoding: 'utf-8',
        timeout: 30000,
      });
    } catch {
      // May fail if session doesn't exist or already stopped
    }
  }

  /**
   * Stop session via HTTP API
   */
  private async stopViaHttp(
    sessionKey: string,
    openclawSessionId: string | undefined,
    force?: boolean
  ): Promise<void> {
    const targetId = openclawSessionId ?? sessionKey;
    const url = `${this.config.gatewayUrl}/api/sessions/${encodeURIComponent(targetId)}/stop`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    if (this.config.gatewayToken) {
      headers['Authorization'] = `Bearer ${this.config.gatewayToken}`;
    }

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({ force }),
        signal: AbortSignal.timeout(30000),
      });

      if (!response.ok && response.status !== 404) {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch {
      // May fail if session doesn't exist
    }
  }

  /**
   * Sync orchestrator sessions with actual OpenClaw sessions
   * Useful for recovering state after restart
   */
  async syncSessions(): Promise<{
    synced: number;
    orphaned: string[];
    missing: string[];
  }> {
    // Get all active sessions from orchestrator
    const trackedSessions = (await this.sessionStorage.list({
      status: ['starting', 'active', 'idle'],
    })).sessions;

    // Get all running sessions from OpenClaw
    const openclawSessions = await this.listSessions({ status: 'running' });

    const synced: string[] = [];
    const orphaned: string[] = [];
    const missing: string[] = [];

    // Build lookup map for OpenClaw sessions
    const openclawMap = new Map<string, OpenClawSessionInfo>();
    for (const s of openclawSessions) {
      openclawMap.set(s.sessionKey, s);
      if (s.label) {
        openclawMap.set(s.label, s);
      }
    }

    // Check each tracked session
    for (const tracked of trackedSessions) {
      const openclawSession = openclawMap.get(tracked.sessionKey) 
        ?? openclawMap.get(tracked.label);

      if (openclawSession) {
        // Session exists - update mapping
        this.sessionMapping.set(tracked.sessionKey, openclawSession.sessionId);
        synced.push(tracked.sessionKey);
      } else {
        // Session missing in OpenClaw - mark as stopped
        await this.sessionStorage.markStopped(
          tracked.sessionKey, 
          1, 
          'Session not found in OpenClaw (sync)'
        );
        missing.push(tracked.sessionKey);
      }
    }

    // Find orphaned OpenClaw sessions (not tracked)
    const trackedKeys = new Set(trackedSessions.map(s => s.sessionKey));
    const trackedLabels = new Set(trackedSessions.map(s => s.label));
    
    for (const openclawSession of openclawSessions) {
      if (!trackedKeys.has(openclawSession.sessionKey) && 
          (!openclawSession.label || !trackedLabels.has(openclawSession.label))) {
        orphaned.push(openclawSession.sessionKey);
      }
    }

    return {
      synced: synced.length,
      orphaned,
      missing,
    };
  }

  /**
   * Get the OpenClaw session ID for an orchestrator session key
   */
  getOpenClawSessionId(sessionKey: string): string | undefined {
    return this.sessionMapping.get(sessionKey);
  }

  /**
   * Get current configuration
   */
  getConfig(): OpenClawConfig {
    return { ...this.config };
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<OpenClawConfig>): void {
    Object.assign(this.config, config);
  }
}

/** Singleton instance */
let defaultService: OpenClawService | null = null;

/**
 * Get the default OpenClawService instance
 */
export function getOpenClawService(config?: OpenClawConfig): OpenClawService {
  if (!defaultService) {
    defaultService = new OpenClawService(config);
  } else if (config) {
    defaultService.updateConfig(config);
  }
  return defaultService;
}

/**
 * Reset the singleton (for testing)
 */
export function resetOpenClawService(): void {
  defaultService = null;
}
