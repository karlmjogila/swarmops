#!/usr/bin/env node

/**
 * Orchestrator CLI
 * P1-14: Command-line interface for managing roles, work, and sessions
 */

import { getRoleStorage, getWorkStorage, getSessionStorage } from '../storage';
import type { Role, WorkItem, TrackedSession, WorkStatus } from '../types';

// ANSI colors for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  red: '\x1b[31m',
  gray: '\x1b[90m',
};

/**
 * Print help message
 */
function printHelp(): void {
  console.log(`
${colors.bright}Orchestrator CLI${colors.reset}
Agent orchestration platform for managing roles, work, and sessions.

${colors.cyan}USAGE:${colors.reset}
  orchestrator <command> <subcommand> [options]

${colors.cyan}COMMANDS:${colors.reset}

  ${colors.bright}roles${colors.reset}
    list                         List all roles
    show <id>                    Show role details
    create                       Create a new role
      --name <name>              Role name (required)
      --model <model>            AI model to use
      --instructions <text>      System instructions
      --description <text>       Role description
      --thinking <level>         Thinking level (none|low|medium|high)

  ${colors.bright}work${colors.reset}
    list                         List work items
      --status <status>          Filter by status (pending|queued|running|complete|failed|cancelled)
      --type <type>              Filter by type (task|pipeline|batch|review|converge)
      --role <id>                Filter by role ID
      --limit <n>                Limit results
    show <id>                    Show work item details
    create                       Create a new work item
      --role <id>                Role ID to assign
      --title <title>            Work title (required)
      --description <text>       Work description
      --type <type>              Work type (default: task)

  ${colors.bright}sessions${colors.reset}
    list                         List sessions
      --active                   Show only active sessions
      --role <id>                Filter by role ID
      --limit <n>                Limit results
    show <key>                   Show session details

${colors.cyan}EXAMPLES:${colors.reset}
  orchestrator roles list
  orchestrator roles show abc123
  orchestrator roles create --name "coder" --model "anthropic/claude-sonnet-4"
  orchestrator work list --status pending
  orchestrator work create --role abc123 --title "Implement feature"
  orchestrator sessions list --active
`);
}

/**
 * Parse command line arguments
 */
function parseArgs(args: string[]): { positional: string[]; flags: Record<string, string | boolean> } {
  const positional: string[] = [];
  const flags: Record<string, string | boolean> = {};
  
  let i = 0;
  while (i < args.length) {
    const arg = args[i];
    
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const next = args[i + 1];
      
      if (next && !next.startsWith('--')) {
        flags[key] = next;
        i += 2;
      } else {
        flags[key] = true;
        i += 1;
      }
    } else {
      positional.push(arg);
      i += 1;
    }
  }
  
  return { positional, flags };
}

/**
 * Format a date string for display
 */
function formatDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString();
}

/**
 * Format status with color
 */
function formatStatus(status: string): string {
  const statusColors: Record<string, string> = {
    pending: colors.yellow,
    queued: colors.blue,
    running: colors.cyan,
    converging: colors.cyan,
    complete: colors.green,
    failed: colors.red,
    cancelled: colors.gray,
    starting: colors.yellow,
    active: colors.green,
    idle: colors.gray,
    stopping: colors.yellow,
    stopped: colors.gray,
  };
  
  const color = statusColors[status] || colors.reset;
  return `${color}${status}${colors.reset}`;
}

/**
 * Print a role
 */
function printRole(role: Role, verbose = false): void {
  console.log(`${colors.bright}${role.name}${colors.reset}${role.builtin ? ` ${colors.dim}(built-in)${colors.reset}` : ''}`);
  console.log(`  ID: ${colors.dim}${role.id}${colors.reset}`);
  console.log(`  Model: ${role.model}`);
  console.log(`  Thinking: ${role.thinking}`);
  
  if (role.description) {
    console.log(`  Description: ${role.description}`);
  }
  
  if (verbose && role.instructions) {
    console.log(`  Instructions:\n    ${role.instructions.split('\n').join('\n    ')}`);
  }
  
  console.log(`  Created: ${formatDate(role.createdAt)}`);
  console.log(`  Updated: ${formatDate(role.updatedAt)}`);
}

/**
 * Print a work item
 */
function printWork(work: WorkItem, verbose = false): void {
  console.log(`${colors.bright}${work.title}${colors.reset}`);
  console.log(`  ID: ${colors.dim}${work.id}${colors.reset}`);
  console.log(`  Type: ${work.type}`);
  console.log(`  Status: ${formatStatus(work.status)}`);
  
  if (work.roleId) {
    console.log(`  Role: ${work.roleId}`);
  }
  
  if (work.parentId) {
    console.log(`  Parent: ${work.parentId}`);
  }
  
  if (work.childIds.length > 0) {
    console.log(`  Children: ${work.childIds.length}`);
  }
  
  if (work.description) {
    console.log(`  Description: ${work.description}`);
  }
  
  console.log(`  Iterations: ${work.iterations}`);
  console.log(`  Created: ${formatDate(work.timestamps.createdAt)}`);
  
  if (work.timestamps.startedAt) {
    console.log(`  Started: ${formatDate(work.timestamps.startedAt)}`);
  }
  
  if (work.timestamps.completedAt) {
    console.log(`  Completed: ${formatDate(work.timestamps.completedAt)}`);
  }
  
  if (work.error) {
    console.log(`  ${colors.red}Error: ${work.error}${colors.reset}`);
  }
  
  if (verbose) {
    console.log(`  Events: ${work.events.length}`);
    for (const event of work.events.slice(-5)) {
      console.log(`    - [${event.type}] ${event.message}`);
    }
    
    if (work.input) {
      console.log(`  Input: ${JSON.stringify(work.input)}`);
    }
    
    if (work.output) {
      console.log(`  Output: ${JSON.stringify(work.output)}`);
    }
  }
}

/**
 * Print a session
 */
function printSession(session: TrackedSession, verbose = false): void {
  console.log(`${colors.bright}${session.label}${colors.reset}`);
  console.log(`  Key: ${colors.dim}${session.sessionKey}${colors.reset}`);
  console.log(`  Status: ${formatStatus(session.status)}`);
  console.log(`  Role: ${session.roleId}`);
  
  if (session.workItemId) {
    console.log(`  Work Item: ${session.workItemId}`);
  }
  
  console.log(`  Tokens: in=${session.tokenUsage.input} out=${session.tokenUsage.output} think=${session.tokenUsage.thinking}`);
  console.log(`  Spawned: ${formatDate(session.spawnedAt)}`);
  console.log(`  Last Activity: ${formatDate(session.lastActivityAt)}`);
  
  if (session.error) {
    console.log(`  ${colors.red}Error: ${session.error}${colors.reset}`);
  }
  
  if (session.exitCode !== undefined) {
    console.log(`  Exit Code: ${session.exitCode}`);
  }
  
  if (verbose && session.task) {
    console.log(`  Task: ${session.task}`);
  }
}

// ============================================
// Command handlers
// ============================================

async function handleRoles(args: string[]): Promise<void> {
  const { positional, flags } = parseArgs(args);
  const subcommand = positional[0];
  const storage = getRoleStorage();
  
  switch (subcommand) {
    case 'list': {
      const roles = await storage.list();
      console.log(`${colors.bright}Roles (${roles.length})${colors.reset}\n`);
      for (const role of roles) {
        printRole(role);
        console.log();
      }
      break;
    }
    
    case 'show': {
      const id = positional[1];
      if (!id) {
        console.error('Error: Role ID required');
        process.exit(1);
      }
      
      try {
        const role = await storage.get(id);
        printRole(role, true);
      } catch (e) {
        console.error(`Error: ${(e as Error).message}`);
        process.exit(1);
      }
      break;
    }
    
    case 'create': {
      const name = flags.name as string;
      if (!name) {
        console.error('Error: --name is required');
        process.exit(1);
      }
      
      try {
        const role = await storage.create({
          name,
          model: (flags.model as string) || undefined,
          description: (flags.description as string) || undefined,
          instructions: (flags.instructions as string) || undefined,
          thinking: (flags.thinking as 'none' | 'low' | 'medium' | 'high') || undefined,
        });
        
        console.log(`${colors.green}✓ Role created${colors.reset}\n`);
        printRole(role, true);
      } catch (e) {
        console.error(`Error: ${(e as Error).message}`);
        process.exit(1);
      }
      break;
    }
    
    default:
      console.error(`Unknown subcommand: ${subcommand}`);
      console.error('Use: orchestrator roles [list|show|create]');
      process.exit(1);
  }
}

async function handleWork(args: string[]): Promise<void> {
  const { positional, flags } = parseArgs(args);
  const subcommand = positional[0];
  const storage = getWorkStorage();
  
  switch (subcommand) {
    case 'list': {
      const result = await storage.list({
        status: flags.status as WorkStatus | undefined,
        type: flags.type as 'task' | 'pipeline' | 'batch' | 'review' | 'converge' | undefined,
        roleId: flags.role as string | undefined,
        limit: flags.limit ? parseInt(flags.limit as string, 10) : undefined,
      });
      
      console.log(`${colors.bright}Work Items (${result.total})${colors.reset}\n`);
      for (const work of result.items) {
        printWork(work);
        console.log();
      }
      
      if (result.hasMore) {
        console.log(`${colors.dim}... and more (use --limit to see more)${colors.reset}`);
      }
      break;
    }
    
    case 'show': {
      const id = positional[1];
      if (!id) {
        console.error('Error: Work item ID required');
        process.exit(1);
      }
      
      try {
        const work = await storage.get(id);
        printWork(work, true);
      } catch (e) {
        console.error(`Error: ${(e as Error).message}`);
        process.exit(1);
      }
      break;
    }
    
    case 'create': {
      const title = flags.title as string;
      if (!title) {
        console.error('Error: --title is required');
        process.exit(1);
      }
      
      try {
        const work = await storage.create({
          type: (flags.type as 'task' | 'pipeline' | 'batch' | 'review' | 'converge') || 'task',
          roleId: flags.role as string | undefined,
          title,
          description: flags.description as string | undefined,
        });
        
        console.log(`${colors.green}✓ Work item created${colors.reset}\n`);
        printWork(work, true);
      } catch (e) {
        console.error(`Error: ${(e as Error).message}`);
        process.exit(1);
      }
      break;
    }
    
    default:
      console.error(`Unknown subcommand: ${subcommand}`);
      console.error('Use: orchestrator work [list|show|create]');
      process.exit(1);
  }
}

async function handleSessions(args: string[]): Promise<void> {
  const { positional, flags } = parseArgs(args);
  const subcommand = positional[0];
  const storage = getSessionStorage();
  
  switch (subcommand) {
    case 'list': {
      const result = await storage.list({
        status: flags.active ? ['starting', 'active', 'idle'] : undefined,
        roleId: flags.role as string | undefined,
        limit: flags.limit ? parseInt(flags.limit as string, 10) : undefined,
      });
      
      console.log(`${colors.bright}Sessions (${result.total})${colors.reset}\n`);
      for (const session of result.sessions) {
        printSession(session);
        console.log();
      }
      
      if (result.hasMore) {
        console.log(`${colors.dim}... and more (use --limit to see more)${colors.reset}`);
      }
      break;
    }
    
    case 'show': {
      const key = positional[1];
      if (!key) {
        console.error('Error: Session key required');
        process.exit(1);
      }
      
      try {
        const session = await storage.get(key);
        printSession(session, true);
      } catch (e) {
        console.error(`Error: ${(e as Error).message}`);
        process.exit(1);
      }
      break;
    }
    
    default:
      console.error(`Unknown subcommand: ${subcommand}`);
      console.error('Use: orchestrator sessions [list|show]');
      process.exit(1);
  }
}

// ============================================
// Main entry point
// ============================================

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  
  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    printHelp();
    process.exit(0);
  }
  
  const command = args[0];
  const commandArgs = args.slice(1);
  
  try {
    switch (command) {
      case 'roles':
        await handleRoles(commandArgs);
        break;
      
      case 'work':
        await handleWork(commandArgs);
        break;
      
      case 'sessions':
        await handleSessions(commandArgs);
        break;
      
      default:
        console.error(`Unknown command: ${command}`);
        console.error('Use: orchestrator [roles|work|sessions]');
        process.exit(1);
    }
  } catch (error) {
    console.error(`Error: ${(error as Error).message}`);
    process.exit(1);
  }
}

main();
