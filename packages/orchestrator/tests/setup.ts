/**
 * Test Setup & Utilities
 * P1-13: Common test helpers, temp directory management
 */

import { promises as fs } from 'fs';
import * as path from 'path';
import * as os from 'os';

/**
 * Test context with temp directories
 */
export interface TestContext {
  /** Root temp directory for this test run */
  tempDir: string;
  /** Path for roles.json */
  rolesPath: string;
  /** Path for work ledger directory */
  workDir: string;
  /** Path for sessions file */
  sessionsPath: string;
}

/**
 * Create a unique temp directory for tests
 */
export async function createTestContext(testName: string): Promise<TestContext> {
  const tempDir = path.join(os.tmpdir(), `orchestrator-test-${testName}-${Date.now()}`);
  
  await fs.mkdir(tempDir, { recursive: true });
  
  const rolesPath = path.join(tempDir, 'roles.json');
  const workDir = path.join(tempDir, 'work');
  const sessionsPath = path.join(tempDir, 'sessions', 'active.json');
  
  // Create subdirectories
  await fs.mkdir(workDir, { recursive: true });
  await fs.mkdir(path.dirname(sessionsPath), { recursive: true });
  
  return {
    tempDir,
    rolesPath,
    workDir,
    sessionsPath,
  };
}

/**
 * Clean up temp directory after tests
 */
export async function cleanupTestContext(ctx: TestContext): Promise<void> {
  try {
    await fs.rm(ctx.tempDir, { recursive: true, force: true });
  } catch {
    // Ignore errors during cleanup
  }
}

/**
 * Simple assertion helper
 */
export function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

/**
 * Assert equality
 */
export function assertEqual<T>(actual: T, expected: T, message?: string): void {
  const actualStr = JSON.stringify(actual);
  const expectedStr = JSON.stringify(expected);
  
  if (actualStr !== expectedStr) {
    throw new Error(
      `${message ? message + ': ' : ''}Expected ${expectedStr}, got ${actualStr}`
    );
  }
}

/**
 * Assert that a value is truthy
 */
export function assertTruthy<T>(value: T, message?: string): void {
  if (!value) {
    throw new Error(
      `${message ? message + ': ' : ''}Expected truthy value, got ${value}`
    );
  }
}

/**
 * Assert that a function throws
 */
export async function assertThrows(
  fn: () => Promise<unknown> | unknown,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  errorType?: new (...args: any[]) => Error,
  messageContains?: string
): Promise<void> {
  let threw = false;
  let error: Error | undefined;
  
  try {
    await fn();
  } catch (e) {
    threw = true;
    error = e as Error;
  }
  
  if (!threw) {
    throw new Error('Expected function to throw, but it did not');
  }
  
  if (errorType && !(error instanceof errorType)) {
    throw new Error(`Expected error of type ${errorType.name}, got ${error?.constructor?.name}`);
  }
  
  if (messageContains && !error?.message.includes(messageContains)) {
    throw new Error(
      `Expected error message to contain "${messageContains}", got "${error?.message}"`
    );
  }
}

/**
 * Assert array length
 */
export function assertLength(arr: unknown[], expected: number, message?: string): void {
  if (arr.length !== expected) {
    throw new Error(
      `${message ? message + ': ' : ''}Expected array length ${expected}, got ${arr.length}`
    );
  }
}

/**
 * Run a test and report result
 */
export async function runTest(
  name: string,
  fn: () => Promise<void>
): Promise<{ name: string; passed: boolean; error?: Error }> {
  try {
    await fn();
    console.log(`  ✓ ${name}`);
    return { name, passed: true };
  } catch (error) {
    console.log(`  ✗ ${name}`);
    console.log(`    ${(error as Error).message}`);
    return { name, passed: false, error: error as Error };
  }
}

/**
 * Run a test suite
 */
export async function runSuite(
  suiteName: string,
  tests: Array<{ name: string; fn: () => Promise<void> }>
): Promise<{ passed: number; failed: number }> {
  console.log(`\n${suiteName}`);
  console.log('─'.repeat(suiteName.length));
  
  let passed = 0;
  let failed = 0;
  
  for (const test of tests) {
    const result = await runTest(test.name, test.fn);
    if (result.passed) {
      passed++;
    } else {
      failed++;
    }
  }
  
  return { passed, failed };
}

/**
 * Wait for a specified number of milliseconds
 */
export function wait(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
