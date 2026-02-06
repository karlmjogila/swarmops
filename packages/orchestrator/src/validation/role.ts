/**
 * Role validation logic
 */

import type { RoleCreateInput, RoleUpdateInput, ThinkingLevel, ModelId } from '../types';
import { DEFAULT_ROLE_VALUES } from '../types';

/**
 * Validation error class
 */
export class ValidationError extends Error {
  public field?: string;

  constructor(message: string, field?: string) {
    super(message);
    this.name = 'ValidationError';
    this.field = field;
  }
}

/** Valid thinking levels */
const VALID_THINKING_LEVELS: ThinkingLevel[] = ['none', 'low', 'medium', 'high'];

/** Known/supported model IDs */
const KNOWN_MODELS: ModelId[] = [
  'anthropic/claude-opus-4-5',
  'anthropic/claude-sonnet-4-5',
  'anthropic/claude-sonnet-4',
  'openai/gpt-4o',
  'openai/o1',
  'google/gemini-pro',
];

/** Name constraints */
const NAME_MIN_LENGTH = 1;
const NAME_MAX_LENGTH = 100;

/** Instructions constraints */
const INSTRUCTIONS_MAX_LENGTH = 50000;

/**
 * Validate a role name
 */
export function validateName(name: unknown, required: boolean = true): string | undefined {
  if (name === undefined || name === null) {
    if (required) {
      throw new ValidationError('Name is required', 'name');
    }
    return undefined;
  }

  if (typeof name !== 'string') {
    throw new ValidationError('Name must be a string', 'name');
  }

  const trimmed = name.trim();

  if (trimmed.length < NAME_MIN_LENGTH) {
    throw new ValidationError(`Name must be at least ${NAME_MIN_LENGTH} character(s)`, 'name');
  }

  if (trimmed.length > NAME_MAX_LENGTH) {
    throw new ValidationError(`Name must be at most ${NAME_MAX_LENGTH} characters`, 'name');
  }

  // Name should be alphanumeric with hyphens/underscores (like identifiers)
  if (!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(trimmed)) {
    throw new ValidationError(
      'Name must start with a letter and contain only letters, numbers, hyphens, and underscores',
      'name'
    );
  }

  return trimmed;
}

/**
 * Validate description
 */
export function validateDescription(description: unknown): string | undefined {
  if (description === undefined || description === null) {
    return undefined;
  }

  if (typeof description !== 'string') {
    throw new ValidationError('Description must be a string', 'description');
  }

  return description.trim();
}

/**
 * Validate model ID
 */
export function validateModel(model: unknown): ModelId | undefined {
  if (model === undefined || model === null) {
    return undefined;
  }

  if (typeof model !== 'string') {
    throw new ValidationError('Model must be a string', 'model');
  }

  const trimmed = model.trim();

  // Warn but allow unknown models (for flexibility)
  if (!KNOWN_MODELS.includes(trimmed as ModelId)) {
    console.warn(`Unknown model: ${trimmed}. Known models: ${KNOWN_MODELS.join(', ')}`);
  }

  // Basic format validation (provider/model-name)
  if (!trimmed.includes('/') || trimmed.split('/').some(part => !part)) {
    throw new ValidationError('Model must be in format "provider/model-name"', 'model');
  }

  return trimmed as ModelId;
}

/**
 * Validate thinking level
 */
export function validateThinking(thinking: unknown): ThinkingLevel | undefined {
  if (thinking === undefined || thinking === null) {
    return undefined;
  }

  if (typeof thinking !== 'string') {
    throw new ValidationError('Thinking must be a string', 'thinking');
  }

  if (!VALID_THINKING_LEVELS.includes(thinking as ThinkingLevel)) {
    throw new ValidationError(
      `Thinking must be one of: ${VALID_THINKING_LEVELS.join(', ')}`,
      'thinking'
    );
  }

  return thinking as ThinkingLevel;
}

/**
 * Validate instructions
 */
export function validateInstructions(instructions: unknown): string | undefined {
  if (instructions === undefined || instructions === null) {
    return undefined;
  }

  if (typeof instructions !== 'string') {
    throw new ValidationError('Instructions must be a string', 'instructions');
  }

  if (instructions.length > INSTRUCTIONS_MAX_LENGTH) {
    throw new ValidationError(
      `Instructions must be at most ${INSTRUCTIONS_MAX_LENGTH} characters`,
      'instructions'
    );
  }

  return instructions;
}

/**
 * Validate promptFile path
 */
export function validatePromptFile(promptFile: unknown): string | undefined {
  if (promptFile === undefined || promptFile === null || promptFile === '') {
    return undefined;
  }

  if (typeof promptFile !== 'string') {
    throw new ValidationError('promptFile must be a string', 'promptFile');
  }

  const trimmed = promptFile.trim();

  // Basic path validation - must end in .md
  if (!trimmed.endsWith('.md')) {
    throw new ValidationError('promptFile must be a .md file', 'promptFile');
  }

  // No path traversal
  if (trimmed.includes('..')) {
    throw new ValidationError('promptFile cannot contain path traversal', 'promptFile');
  }

  return trimmed;
}

/**
 * Validate role creation input
 */
export function validateRoleCreate(input: unknown): RoleCreateInput {
  if (!input || typeof input !== 'object') {
    throw new ValidationError('Request body must be an object');
  }

  const obj = input as Record<string, unknown>;

  const name = validateName(obj.name, true)!;
  const description = validateDescription(obj.description);
  const model = validateModel(obj.model);
  const thinking = validateThinking(obj.thinking);
  const instructions = validateInstructions(obj.instructions);
  const promptFile = validatePromptFile(obj.promptFile);

  return {
    name,
    description: description ?? DEFAULT_ROLE_VALUES.description,
    model: model ?? DEFAULT_ROLE_VALUES.model,
    thinking: thinking ?? DEFAULT_ROLE_VALUES.thinking,
    instructions: instructions ?? DEFAULT_ROLE_VALUES.instructions,
    promptFile,
  };
}

/**
 * Validate role update input
 */
export function validateRoleUpdate(input: unknown): RoleUpdateInput {
  if (!input || typeof input !== 'object') {
    throw new ValidationError('Request body must be an object');
  }

  const obj = input as Record<string, unknown>;

  // For updates, all fields are optional
  const result: RoleUpdateInput = {};

  const name = validateName(obj.name, false);
  if (name !== undefined) result.name = name;

  const description = validateDescription(obj.description);
  if (description !== undefined) result.description = description;

  const model = validateModel(obj.model);
  if (model !== undefined) result.model = model;

  const thinking = validateThinking(obj.thinking);
  if (thinking !== undefined) result.thinking = thinking;

  const instructions = validateInstructions(obj.instructions);
  if (instructions !== undefined) result.instructions = instructions;

  const promptFile = validatePromptFile(obj.promptFile);
  if (promptFile !== undefined) result.promptFile = promptFile;

  // At least one field must be provided
  if (Object.keys(result).length === 0) {
    throw new ValidationError('At least one field must be provided for update');
  }

  return result;
}

/**
 * Check if a value is a valid role ID (UUID format)
 */
export function isValidId(id: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(id);
}
