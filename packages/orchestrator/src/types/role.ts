/**
 * Role type definitions for the Agent Orchestration Platform
 */

/** Supported thinking levels */
export type ThinkingLevel = 'none' | 'low' | 'medium' | 'high';

/** Supported AI models */
export type ModelId = 
  | 'anthropic/claude-opus-4-5'
  | 'anthropic/claude-sonnet-4-5'
  | 'anthropic/claude-sonnet-4'
  | 'openai/gpt-4o'
  | 'openai/o1'
  | 'google/gemini-pro'
  | string; // Allow custom models

/**
 * Role interface - defines an agent's persona and capabilities
 */
export interface Role {
  /** Unique identifier (UUID) */
  id: string;
  /** Human-readable name (1-100 chars) */
  name: string;
  /** Description of the role's purpose */
  description: string;
  /** AI model to use for this role */
  model: ModelId;
  /** Thinking/reasoning level */
  thinking: ThinkingLevel;
  /** System instructions for the agent */
  instructions: string;
  /** Path to markdown file with detailed instructions (overrides instructions field) */
  promptFile?: string;
  /** ISO timestamp of creation */
  createdAt: string;
  /** ISO timestamp of last update */
  updatedAt: string;
  /** Whether this is a built-in role */
  builtin?: boolean;
}

/**
 * Input for creating a new role
 */
export interface RoleCreateInput {
  name: string;
  description?: string;
  model?: ModelId;
  thinking?: ThinkingLevel;
  instructions?: string;
  promptFile?: string;
}

/**
 * Input for updating an existing role
 */
export interface RoleUpdateInput {
  name?: string;
  description?: string;
  model?: ModelId;
  thinking?: ThinkingLevel;
  instructions?: string;
  promptFile?: string;
}

/**
 * Default values for optional role fields
 */
export const DEFAULT_ROLE_VALUES: Required<Omit<RoleCreateInput, 'name'>> = {
  description: '',
  model: 'anthropic/claude-sonnet-4',
  thinking: 'low',
  instructions: '',
  promptFile: '',
};

/**
 * Built-in role presets
 */
export const BUILTIN_ROLES: Omit<Role, 'id' | 'createdAt' | 'updatedAt'>[] = [
  {
    name: 'architect',
    description: 'High-level system design and planning. Breaks down complex problems into actionable tasks.',
    model: 'anthropic/claude-opus-4-5',
    thinking: 'high',
    instructions: `You are the Architect role. Your responsibilities:
- Analyze requirements and design system architecture
- Break down complex problems into smaller, manageable tasks
- Create technical specifications and design documents
- Review and validate technical approaches
- Ensure consistency across the codebase

Focus on the big picture while maintaining attention to detail.
Ask clarifying questions before making major design decisions.`,
    builtin: true,
  },
  {
    name: 'builder',
    description: 'Implementation and coding. Executes tasks defined by the architect.',
    model: 'anthropic/claude-sonnet-4',
    thinking: 'low',
    instructions: `You are the Builder role. Your responsibilities:
- Implement features and functionality based on specifications
- Write clean, maintainable, well-documented code
- Follow established patterns and conventions
- Create unit tests for new functionality
- Handle edge cases and error conditions

Execute tasks efficiently and report progress.
Ask for clarification if specifications are unclear.`,
    builtin: true,
  },
  {
    name: 'reviewer',
    description: 'Code review and quality assurance. Validates implementations meet standards.',
    model: 'anthropic/claude-sonnet-4',
    thinking: 'medium',
    instructions: `You are the Reviewer role. Your responsibilities:
- Review code for correctness, performance, and maintainability
- Identify potential bugs, security issues, and edge cases
- Ensure code follows project conventions and best practices
- Suggest improvements and optimizations
- Validate test coverage and quality

Be thorough but constructive in feedback.
Prioritize issues by severity and impact.`,
    builtin: true,
  },
];
