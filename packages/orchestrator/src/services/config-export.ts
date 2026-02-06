/**
 * Config Export/Import Service
 * P4-3: Export roles, pipelines as JSON and import them back
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { Role, RoleCreateInput, ThinkingLevel } from '../types/role';
import { Pipeline, PipelineCreateInput, PipelineStep, PipelineStepInput } from '../types/pipeline';
import { getRoleStorage, RoleStorage } from '../storage/roles';
import { getPipelineStorage, PipelineStorage } from '../storage';
import { timestamp, generateId } from '../storage/base';
import { WebhookConfig, WebhookCreateInput, getWebhookService, WebhookService } from './webhooks';

/**
 * Ensure directory exists
 */
async function ensureDir(dir: string): Promise<void> {
  await fs.mkdir(dir, { recursive: true });
}

/**
 * Export format version for compatibility checking
 */
const EXPORT_VERSION = '1.0';

/**
 * Export manifest metadata
 */
export interface ExportManifest {
  version: string;
  exportedAt: string;
  exportedBy?: string;
  description?: string;
  checksum?: string;
}

/**
 * Full export bundle
 */
export interface ExportBundle {
  manifest: ExportManifest;
  roles?: ExportedRole[];
  pipelines?: ExportedPipeline[];
  webhooks?: ExportedWebhook[];
}

/**
 * Exported role configuration
 */
export interface ExportedRoleConfig {
  name: string;
  description: string;
  model: string;
  thinking: ThinkingLevel;
  instructions: string;
  builtin?: boolean;
}

/**
 * Exported role (without auto-generated fields)
 */
export interface ExportedRole {
  /** Original ID (for reference tracking) */
  originalId: string;
  /** Role configuration */
  config: ExportedRoleConfig;
}

/**
 * Exported pipeline step configuration
 */
export interface ExportedPipelineStepConfig {
  id: string;
  name: string;
  roleId: string;
  action: string;
  input?: Record<string, unknown>;
  outputSchema?: string;
  convergence?: {
    maxIterations: number;
    minScore?: number;
    successCriteria?: string;
    reviewerRoleId?: string;
    selfReview?: boolean;
  };
  optional?: boolean;
  condition?: string;
  timeoutMs?: number;
  retryCount?: number;
  order: number;
}

/**
 * Exported pipeline configuration
 */
export interface ExportedPipelineConfig {
  name: string;
  description: string;
  steps: ExportedPipelineStepConfig[];
  inputSchema?: Record<string, unknown>;
  defaultConvergence?: {
    maxIterations: number;
    minScore?: number;
    successCriteria?: string;
    reviewerRoleId?: string;
    selfReview?: boolean;
  };
  autoContinue: boolean;
  stopOnFailure: boolean;
  tags?: string[];
}

/**
 * Exported pipeline (without auto-generated fields)
 */
export interface ExportedPipeline {
  /** Original ID (for reference tracking) */
  originalId: string;
  /** Pipeline configuration */
  config: ExportedPipelineConfig;
  /** Referenced role IDs (for dependency tracking) */
  referencedRoleIds: string[];
}

/**
 * Exported webhook (without auto-generated fields)
 */
export interface ExportedWebhook {
  /** Original ID (for reference tracking) */
  originalId: string;
  /** Webhook configuration */
  config: Omit<WebhookConfig, 'id' | 'createdAt' | 'updatedAt'>;
}

/**
 * Export options
 */
export interface ExportOptions {
  /** Include roles in export */
  includeRoles?: boolean;
  /** Include pipelines in export */
  includePipelines?: boolean;
  /** Include webhooks in export */
  includeWebhooks?: boolean;
  /** Specific role IDs to export */
  roleIds?: string[];
  /** Specific pipeline IDs to export */
  pipelineIds?: string[];
  /** Specific webhook IDs to export */
  webhookIds?: string[];
  /** Include role dependencies for pipelines */
  includeRoleDependencies?: boolean;
  /** Description for the export */
  description?: string;
  /** User identifier */
  exportedBy?: string;
}

/**
 * Import options
 */
export interface ImportOptions {
  /** Import roles from bundle */
  importRoles?: boolean;
  /** Import pipelines from bundle */
  importPipelines?: boolean;
  /** Import webhooks from bundle */
  importWebhooks?: boolean;
  /** Merge strategy for existing items */
  mergeStrategy?: 'skip' | 'replace' | 'merge';
  /** Remap role IDs (oldId -> newId) */
  roleIdMapping?: Map<string, string>;
  /** Dry run (validate without importing) */
  dryRun?: boolean;
  /** Validate references */
  validateReferences?: boolean;
}

/**
 * Import result
 */
export interface ImportResult {
  success: boolean;
  errors: string[];
  warnings: string[];
  imported: {
    roles: number;
    pipelines: number;
    webhooks: number;
  };
  skipped: {
    roles: number;
    pipelines: number;
    webhooks: number;
  };
  /** Mapping of original IDs to new IDs */
  idMapping: {
    roles: Map<string, string>;
    pipelines: Map<string, string>;
    webhooks: Map<string, string>;
  };
}

/**
 * Config Export/Import Service
 */
export class ConfigExportService {
  private roleStorage: RoleStorage;
  private pipelineStorage: PipelineStorage;
  private webhookService: WebhookService;

  constructor(
    roleStorage?: RoleStorage,
    pipelineStorage?: PipelineStorage,
    webhookService?: WebhookService
  ) {
    this.roleStorage = roleStorage ?? getRoleStorage();
    this.pipelineStorage = pipelineStorage ?? getPipelineStorage();
    this.webhookService = webhookService ?? getWebhookService();
  }

  // ==========================================
  // Export Methods
  // ==========================================

  /**
   * Export configurations to a bundle
   */
  async export(options: ExportOptions = {}): Promise<ExportBundle> {
    const bundle: ExportBundle = {
      manifest: {
        version: EXPORT_VERSION,
        exportedAt: timestamp(),
        exportedBy: options.exportedBy,
        description: options.description,
      },
    };

    // Export roles
    if (options.includeRoles !== false) {
      bundle.roles = await this.exportRoles(options.roleIds);
    }

    // Collect referenced role IDs from pipelines
    const referencedRoleIds = new Set<string>();

    // Export pipelines
    if (options.includePipelines !== false) {
      bundle.pipelines = await this.exportPipelines(options.pipelineIds);
      
      // Collect role dependencies
      for (const pipeline of bundle.pipelines) {
        for (const roleId of pipeline.referencedRoleIds) {
          referencedRoleIds.add(roleId);
        }
      }
    }

    // Include role dependencies if requested
    if (options.includeRoleDependencies && referencedRoleIds.size > 0) {
      const existingRoleIds = new Set(bundle.roles?.map(r => r.originalId) ?? []);
      const missingRoleIds = [...referencedRoleIds].filter(id => !existingRoleIds.has(id));
      
      if (missingRoleIds.length > 0) {
        const additionalRoles = await this.exportRoles(missingRoleIds);
        bundle.roles = [...(bundle.roles ?? []), ...additionalRoles];
      }
    }

    // Export webhooks
    if (options.includeWebhooks) {
      bundle.webhooks = await this.exportWebhooks(options.webhookIds);
    }

    // Generate checksum
    bundle.manifest.checksum = this.generateChecksum(bundle);

    return bundle;
  }

  /**
   * Export roles
   */
  private async exportRoles(roleIds?: string[]): Promise<ExportedRole[]> {
    const allRoles = await this.roleStorage.list();
    const roles = roleIds
      ? allRoles.filter(r => roleIds.includes(r.id))
      : allRoles;

    return roles.map(role => ({
      originalId: role.id,
      config: {
        name: role.name,
        description: role.description,
        model: role.model,
        thinking: role.thinking,
        instructions: role.instructions,
        builtin: role.builtin,
      },
    }));
  }

  /**
   * Export pipelines
   */
  private async exportPipelines(pipelineIds?: string[]): Promise<ExportedPipeline[]> {
    const allPipelines = (await this.pipelineStorage.list()).pipelines;
    const pipelines = pipelineIds
      ? allPipelines.filter(p => pipelineIds.includes(p.id))
      : allPipelines;

    return pipelines.map(pipeline => {
      // Collect referenced role IDs
      const referencedRoleIds = new Set<string>();
      for (const step of pipeline.steps) {
        referencedRoleIds.add(step.roleId);
      }

      return {
        originalId: pipeline.id,
        config: {
          name: pipeline.name,
          description: pipeline.description,
          steps: pipeline.steps.map(step => ({
            id: step.id,
            name: step.name,
            roleId: step.roleId,
            action: step.action,
            input: step.input,
            outputSchema: step.outputSchema,
            convergence: step.convergence,
            optional: step.optional,
            condition: step.condition,
            timeoutMs: step.timeoutMs,
            retryCount: step.retryCount,
            order: step.order,
          })),
          inputSchema: pipeline.inputSchema,
          defaultConvergence: pipeline.defaultConvergence,
          autoContinue: pipeline.autoContinue,
          stopOnFailure: pipeline.stopOnFailure,
          tags: pipeline.tags,
        },
        referencedRoleIds: [...referencedRoleIds],
      };
    });
  }

  /**
   * Export webhooks
   */
  private async exportWebhooks(webhookIds?: string[]): Promise<ExportedWebhook[]> {
    const webhooks = await this.webhookService.list();
    const filtered = webhookIds
      ? webhooks.filter(w => webhookIds.includes(w.id))
      : webhooks;

    return filtered.map(webhook => ({
      originalId: webhook.id,
      config: {
        name: webhook.name,
        url: webhook.url,
        method: webhook.method,
        events: webhook.events,
        headers: webhook.headers,
        secret: webhook.secret,
        enabled: webhook.enabled,
        retry: webhook.retry,
        pipelineIds: webhook.pipelineIds,
        roleIds: webhook.roleIds,
      },
    }));
  }

  /**
   * Export to JSON string
   */
  async exportToJson(options: ExportOptions = {}): Promise<string> {
    const bundle = await this.export(options);
    return JSON.stringify(bundle, null, 2);
  }

  /**
   * Export to file
   */
  async exportToFile(filePath: string, options: ExportOptions = {}): Promise<void> {
    const json = await this.exportToJson(options);
    await fs.writeFile(filePath, json, 'utf-8');
  }

  // ==========================================
  // Import Methods
  // ==========================================

  /**
   * Import configurations from a bundle
   */
  async import(bundle: ExportBundle, options: ImportOptions = {}): Promise<ImportResult> {
    const result: ImportResult = {
      success: true,
      errors: [],
      warnings: [],
      imported: { roles: 0, pipelines: 0, webhooks: 0 },
      skipped: { roles: 0, pipelines: 0, webhooks: 0 },
      idMapping: {
        roles: new Map(),
        pipelines: new Map(),
        webhooks: new Map(),
      },
    };

    // Validate version
    if (!this.isVersionCompatible(bundle.manifest.version)) {
      result.errors.push(`Incompatible export version: ${bundle.manifest.version}`);
      result.success = false;
      return result;
    }

    // Validate checksum if present
    if (bundle.manifest.checksum) {
      const expectedChecksum = this.generateChecksum({
        ...bundle,
        manifest: { ...bundle.manifest, checksum: undefined },
      });
      if (expectedChecksum !== bundle.manifest.checksum) {
        result.warnings.push('Checksum mismatch - bundle may have been modified');
      }
    }

    const mergeStrategy = options.mergeStrategy ?? 'skip';
    const roleIdMapping = options.roleIdMapping ?? new Map<string, string>();

    // Import roles first (pipelines depend on them)
    if (options.importRoles !== false && bundle.roles) {
      for (const exportedRole of bundle.roles) {
        try {
          const newId = await this.importRole(exportedRole, mergeStrategy, options.dryRun);
          if (newId) {
            result.idMapping.roles.set(exportedRole.originalId, newId);
            roleIdMapping.set(exportedRole.originalId, newId);
            result.imported.roles++;
          } else {
            result.skipped.roles++;
          }
        } catch (error) {
          const msg = `Failed to import role "${exportedRole.config.name}": ${error}`;
          result.errors.push(msg);
        }
      }
    }

    // Import pipelines (after roles)
    if (options.importPipelines !== false && bundle.pipelines) {
      for (const exportedPipeline of bundle.pipelines) {
        try {
          // Validate role references
          if (options.validateReferences !== false) {
            const missingRoles: string[] = [];
            for (const roleId of exportedPipeline.referencedRoleIds) {
              const mappedId = roleIdMapping.get(roleId) ?? roleId;
              try {
                await this.roleStorage.get(mappedId);
              } catch {
                missingRoles.push(roleId);
              }
            }
            if (missingRoles.length > 0) {
              result.warnings.push(
                `Pipeline "${exportedPipeline.config.name}" references missing roles: ${missingRoles.join(', ')}`
              );
            }
          }

          const newId = await this.importPipeline(
            exportedPipeline, 
            mergeStrategy, 
            roleIdMapping,
            options.dryRun
          );
          if (newId) {
            result.idMapping.pipelines.set(exportedPipeline.originalId, newId);
            result.imported.pipelines++;
          } else {
            result.skipped.pipelines++;
          }
        } catch (error) {
          const msg = `Failed to import pipeline "${exportedPipeline.config.name}": ${error}`;
          result.errors.push(msg);
        }
      }
    }

    // Import webhooks
    if (options.importWebhooks && bundle.webhooks) {
      for (const exportedWebhook of bundle.webhooks) {
        try {
          // Remap pipeline/role IDs in filters
          const remappedWebhook = this.remapWebhookReferences(
            exportedWebhook,
            result.idMapping.roles,
            result.idMapping.pipelines
          );

          const newId = await this.importWebhook(remappedWebhook, mergeStrategy, options.dryRun);
          if (newId) {
            result.idMapping.webhooks.set(exportedWebhook.originalId, newId);
            result.imported.webhooks++;
          } else {
            result.skipped.webhooks++;
          }
        } catch (error) {
          const msg = `Failed to import webhook "${exportedWebhook.config.name}": ${error}`;
          result.errors.push(msg);
        }
      }
    }

    result.success = result.errors.length === 0;
    return result;
  }

  /**
   * Import a single role
   */
  private async importRole(
    exportedRole: ExportedRole,
    mergeStrategy: 'skip' | 'replace' | 'merge',
    dryRun?: boolean
  ): Promise<string | null> {
    // Check for existing role with same name
    const existingRoles = await this.roleStorage.list();
    const existing = existingRoles.find(r => r.name === exportedRole.config.name);

    if (existing) {
      if (mergeStrategy === 'skip') {
        return null;
      }
      
      if (dryRun) {
        return existing.id;
      }

      if (mergeStrategy === 'replace') {
        await this.roleStorage.delete(existing.id);
      } else if (mergeStrategy === 'merge') {
        // Merge keeps existing, updates fields from import
        const updated = await this.roleStorage.update(existing.id, exportedRole.config);
        return updated.id;
      }
    }

    if (dryRun) {
      return generateId();
    }

    const created = await this.roleStorage.create(exportedRole.config as RoleCreateInput);
    return created.id;
  }

  /**
   * Import a single pipeline
   */
  private async importPipeline(
    exportedPipeline: ExportedPipeline,
    mergeStrategy: 'skip' | 'replace' | 'merge',
    roleIdMapping: Map<string, string>,
    dryRun?: boolean
  ): Promise<string | null> {
    // Remap role IDs in steps
    const remappedSteps: PipelineStepInput[] = exportedPipeline.config.steps.map(step => ({
      ...step,
      roleId: roleIdMapping.get(step.roleId) ?? step.roleId,
    }));

    // Check for existing pipeline with same name
    const existingPipelines = (await this.pipelineStorage.list()).pipelines;
    const existing = existingPipelines.find(p => p.name === exportedPipeline.config.name);

    if (existing) {
      if (mergeStrategy === 'skip') {
        return null;
      }

      if (dryRun) {
        return existing.id;
      }

      if (mergeStrategy === 'replace') {
        await this.pipelineStorage.delete(existing.id);
      } else if (mergeStrategy === 'merge') {
        const updated = await this.pipelineStorage.update(existing.id, {
          ...exportedPipeline.config,
          steps: remappedSteps,
        });
        return updated.id;
      }
    }

    if (dryRun) {
      return generateId();
    }

    const created = await this.pipelineStorage.create({
      ...exportedPipeline.config,
      steps: remappedSteps,
    } as PipelineCreateInput);
    return created.id;
  }

  /**
   * Import a single webhook
   */
  private async importWebhook(
    exportedWebhook: ExportedWebhook,
    mergeStrategy: 'skip' | 'replace' | 'merge',
    dryRun?: boolean
  ): Promise<string | null> {
    // Check for existing webhook with same name
    const existingWebhooks = await this.webhookService.list();
    const existing = existingWebhooks.find(w => w.name === exportedWebhook.config.name);

    if (existing) {
      if (mergeStrategy === 'skip') {
        return null;
      }

      if (dryRun) {
        return existing.id;
      }

      if (mergeStrategy === 'replace') {
        await this.webhookService.delete(existing.id);
      } else if (mergeStrategy === 'merge') {
        const updated = await this.webhookService.update(existing.id, exportedWebhook.config);
        return updated.id;
      }
    }

    if (dryRun) {
      return generateId();
    }

    const created = await this.webhookService.create(exportedWebhook.config as WebhookCreateInput);
    return created.id;
  }

  /**
   * Remap webhook pipeline/role references
   */
  private remapWebhookReferences(
    exportedWebhook: ExportedWebhook,
    roleMapping: Map<string, string>,
    pipelineMapping: Map<string, string>
  ): ExportedWebhook {
    return {
      ...exportedWebhook,
      config: {
        ...exportedWebhook.config,
        pipelineIds: exportedWebhook.config.pipelineIds?.map(
          id => pipelineMapping.get(id) ?? id
        ),
        roleIds: exportedWebhook.config.roleIds?.map(
          id => roleMapping.get(id) ?? id
        ),
      },
    };
  }

  /**
   * Import from JSON string
   */
  async importFromJson(json: string, options: ImportOptions = {}): Promise<ImportResult> {
    const bundle = JSON.parse(json) as ExportBundle;
    return this.import(bundle, options);
  }

  /**
   * Import from file
   */
  async importFromFile(filePath: string, options: ImportOptions = {}): Promise<ImportResult> {
    const json = await fs.readFile(filePath, 'utf-8');
    return this.importFromJson(json, options);
  }

  // ==========================================
  // Utility Methods
  // ==========================================

  /**
   * Validate an export bundle
   */
  async validate(bundle: ExportBundle): Promise<{
    valid: boolean;
    errors: string[];
    warnings: string[];
  }> {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check version
    if (!bundle.manifest?.version) {
      errors.push('Missing manifest version');
    } else if (!this.isVersionCompatible(bundle.manifest.version)) {
      errors.push(`Incompatible version: ${bundle.manifest.version}`);
    }

    // Validate roles
    if (bundle.roles) {
      for (const role of bundle.roles) {
        if (!role.config.name) {
          errors.push(`Role missing name (originalId: ${role.originalId})`);
        }
        if (!role.config.instructions) {
          warnings.push(`Role "${role.config.name}" has no instructions`);
        }
      }
    }

    // Validate pipelines
    if (bundle.pipelines) {
      const roleIds = new Set(bundle.roles?.map(r => r.originalId) ?? []);

      for (const pipeline of bundle.pipelines) {
        if (!pipeline.config.name) {
          errors.push(`Pipeline missing name (originalId: ${pipeline.originalId})`);
        }
        if (!pipeline.config.steps?.length) {
          warnings.push(`Pipeline "${pipeline.config.name}" has no steps`);
        }

        // Check role references
        for (const step of pipeline.config.steps ?? []) {
          if (!roleIds.has(step.roleId)) {
            warnings.push(
              `Pipeline "${pipeline.config.name}" step "${step.name}" references role not in bundle: ${step.roleId}`
            );
          }
        }
      }
    }

    // Validate webhooks
    if (bundle.webhooks) {
      for (const webhook of bundle.webhooks) {
        if (!webhook.config.name) {
          errors.push(`Webhook missing name (originalId: ${webhook.originalId})`);
        }
        if (!webhook.config.url) {
          errors.push(`Webhook "${webhook.config.name}" missing URL`);
        }
        try {
          new URL(webhook.config.url);
        } catch {
          errors.push(`Webhook "${webhook.config.name}" has invalid URL: ${webhook.config.url}`);
        }
      }
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Check if export version is compatible
   */
  private isVersionCompatible(version: string): boolean {
    const [major] = version.split('.');
    const [currentMajor] = EXPORT_VERSION.split('.');
    return major === currentMajor;
  }

  /**
   * Generate checksum for bundle
   */
  private generateChecksum(bundle: ExportBundle): string {
    // Simple hash based on content
    const content = JSON.stringify({
      roles: bundle.roles,
      pipelines: bundle.pipelines,
      webhooks: bundle.webhooks,
    });
    
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(16).padStart(8, '0');
  }

  /**
   * Get export statistics
   */
  async getExportStats(): Promise<{
    roles: number;
    pipelines: number;
    webhooks: number;
  }> {
    const roles = (await this.roleStorage.list()).length;
    const pipelines = (await this.pipelineStorage.list()).total;
    const webhooks = (await this.webhookService.list()).length;

    return { roles, pipelines, webhooks };
  }
}

/** Singleton instance */
let defaultService: ConfigExportService | null = null;

/**
 * Get the default ConfigExportService instance
 */
export function getConfigExportService(): ConfigExportService {
  if (!defaultService) {
    defaultService = new ConfigExportService();
  }
  return defaultService;
}

/**
 * Reset the singleton (for testing)
 */
export function resetConfigExportService(): void {
  defaultService = null;
}
