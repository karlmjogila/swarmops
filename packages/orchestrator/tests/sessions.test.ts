/**
 * Session Storage Tests
 * P1-13: Track, lifecycle, link to work, cleanup
 */

import { SessionStorage, NotFoundError } from '../src/storage';
import {
  createTestContext,
  cleanupTestContext,
  runSuite,
  assert,
  assertEqual,
  assertThrows,
  assertTruthy,
  assertLength,
  TestContext,
  wait,
} from './setup';

let ctx: TestContext;

async function beforeAll(): Promise<void> {
  ctx = await createTestContext('sessions');
}

async function afterAll(): Promise<void> {
  await cleanupTestContext(ctx);
}

const tests = [
  {
    name: 'should track a new session',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      const session = await storage.track({
        roleId: 'role-123',
        label: 'Test Session',
        task: 'Do something',
      });
      
      assertTruthy(session.sessionKey, 'Should have sessionKey');
      assertTruthy(session.sessionId, 'Should have sessionId');
      assertEqual(session.roleId, 'role-123');
      assertEqual(session.label, 'Test Session');
      assertEqual(session.status, 'starting');
      assertEqual(session.tokenUsage.input, 0);
      assertEqual(session.tokenUsage.output, 0);
      assertEqual(session.tokenUsage.thinking, 0);
      assertTruthy(session.spawnedAt, 'Should have spawnedAt');
      assertTruthy(session.lastActivityAt, 'Should have lastActivityAt');
    },
  },
  {
    name: 'should track session with custom key',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      const session = await storage.track(
        {
          roleId: 'role-456',
          label: 'Custom Key Session',
          task: 'Task',
        },
        'custom:key:123'
      );
      
      assertEqual(session.sessionKey, 'custom:key:123');
    },
  },
  {
    name: 'should track session with work item',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      const session = await storage.track({
        roleId: 'role-789',
        workItemId: 'work-123',
        label: 'Work Session',
        task: 'Execute work',
      });
      
      assertEqual(session.workItemId, 'work-123');
    },
  },
  {
    name: 'should get session by key',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      const created = await storage.track({
        roleId: 'role-get',
        label: 'Get Test',
        task: 'Task',
      });
      
      const fetched = await storage.get(created.sessionKey);
      
      assertEqual(fetched.sessionKey, created.sessionKey);
      assertEqual(fetched.label, 'Get Test');
    },
  },
  {
    name: 'should list sessions',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      storage.invalidateCache();
      
      await storage.track({ roleId: 'r1', label: 'List 1', task: 't' });
      await storage.track({ roleId: 'r2', label: 'List 2', task: 't' });
      
      const result = await storage.list();
      
      assert(result.sessions.length >= 2, 'Should have at least 2 sessions');
    },
  },
  {
    name: 'should filter by status',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      storage.invalidateCache();
      
      const session = await storage.track({
        roleId: 'r-status',
        label: 'Status Test',
        task: 't',
      });
      
      await storage.markActive(session.sessionKey);
      
      const activeResult = await storage.list({ status: 'active' });
      const startingResult = await storage.list({ status: 'starting' });
      
      assertTruthy(
        activeResult.sessions.find(s => s.sessionKey === session.sessionKey),
        'Should find in active results'
      );
      assert(
        !startingResult.sessions.find(s => s.sessionKey === session.sessionKey),
        'Should not be in starting results'
      );
    },
  },
  {
    name: 'should filter by roleId',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      storage.invalidateCache();
      
      await storage.track({ roleId: 'unique-role', label: 'Role Filter', task: 't' });
      
      const result = await storage.list({ roleId: 'unique-role' });
      
      assert(result.sessions.length >= 1, 'Should find role session');
      assert(
        result.sessions.every(s => s.roleId === 'unique-role'),
        'All results should have correct roleId'
      );
    },
  },
  {
    name: 'should filter by workItemId',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      storage.invalidateCache();
      
      await storage.track({
        roleId: 'r',
        workItemId: 'work-filter-123',
        label: 'Work Filter',
        task: 't',
      });
      
      const result = await storage.list({ workItemId: 'work-filter-123' });
      
      assert(result.sessions.length >= 1, 'Should find work session');
    },
  },
  {
    name: 'should filter by label contains',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      storage.invalidateCache();
      
      await storage.track({
        roleId: 'r',
        label: 'Unique-Label-XYZ',
        task: 't',
      });
      
      const result = await storage.list({ labelContains: 'XYZ' });
      
      assert(result.sessions.length >= 1, 'Should find by label');
    },
  },
  {
    name: 'should update session status',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      const session = await storage.track({
        roleId: 'r-update',
        label: 'Update Test',
        task: 't',
      });
      
      const updated = await storage.update(session.sessionKey, {
        status: 'active',
      });
      
      assertEqual(updated.status, 'active');
    },
  },
  {
    name: 'should update token usage',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      const session = await storage.track({
        roleId: 'r-tokens',
        label: 'Token Test',
        task: 't',
      });
      
      const updated = await storage.update(session.sessionKey, {
        tokenUsage: { input: 100, output: 50, thinking: 25 },
      });
      
      assertEqual(updated.tokenUsage.input, 100);
      assertEqual(updated.tokenUsage.output, 50);
      assertEqual(updated.tokenUsage.thinking, 25);
    },
  },
  {
    name: 'should add to token usage',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      const session = await storage.track({
        roleId: 'r-add-tokens',
        label: 'Add Tokens',
        task: 't',
      });
      
      await storage.addTokenUsage(session.sessionKey, { input: 50 });
      const updated = await storage.addTokenUsage(session.sessionKey, { 
        input: 30, 
        output: 20 
      });
      
      assertEqual(updated.tokenUsage.input, 80);
      assertEqual(updated.tokenUsage.output, 20);
    },
  },
  {
    name: 'should mark lifecycle states',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      const session = await storage.track({
        roleId: 'r-lifecycle',
        label: 'Lifecycle Test',
        task: 't',
      });
      
      let s = await storage.markActive(session.sessionKey);
      assertEqual(s.status, 'active');
      
      s = await storage.markIdle(session.sessionKey);
      assertEqual(s.status, 'idle');
      
      s = await storage.markStopping(session.sessionKey);
      assertEqual(s.status, 'stopping');
      
      s = await storage.markStopped(session.sessionKey, 0);
      assertEqual(s.status, 'stopped');
      assertEqual(s.exitCode, 0);
    },
  },
  {
    name: 'should mark stopped with error',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      const session = await storage.track({
        roleId: 'r-error',
        label: 'Error Test',
        task: 't',
      });
      
      const stopped = await storage.markStopped(session.sessionKey, 1, 'Something went wrong');
      
      assertEqual(stopped.status, 'stopped');
      assertEqual(stopped.exitCode, 1);
      assertEqual(stopped.error, 'Something went wrong');
    },
  },
  {
    name: 'should remove session',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      const session = await storage.track({
        roleId: 'r-remove',
        label: 'Remove Test',
        task: 't',
      });
      
      await storage.remove(session.sessionKey);
      
      await assertThrows(
        () => storage.get(session.sessionKey),
        NotFoundError
      );
    },
  },
  {
    name: 'should prune stopped sessions',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      storage.invalidateCache();
      
      const session = await storage.track({
        roleId: 'r-prune',
        label: 'Prune Test',
        task: 't',
      });
      
      await storage.markStopped(session.sessionKey);
      
      const pruned = await storage.pruneStopped();
      
      assert(pruned >= 1, 'Should prune at least 1 session');
      
      await assertThrows(
        () => storage.get(session.sessionKey),
        NotFoundError
      );
    },
  },
  {
    name: 'should get active sessions',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      storage.invalidateCache();
      
      const active = await storage.track({
        roleId: 'r-active',
        label: 'Active Session',
        task: 't',
      });
      await storage.markActive(active.sessionKey);
      
      const stopped = await storage.track({
        roleId: 'r-stopped',
        label: 'Stopped Session',
        task: 't',
      });
      await storage.markStopped(stopped.sessionKey);
      
      const activeSessions = await storage.getActiveSessions();
      
      assertTruthy(
        activeSessions.find(s => s.sessionKey === active.sessionKey),
        'Should include active session'
      );
      assert(
        !activeSessions.find(s => s.sessionKey === stopped.sessionKey),
        'Should not include stopped session'
      );
    },
  },
  {
    name: 'should check if session is active',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      const session = await storage.track({
        roleId: 'r-isactive',
        label: 'Is Active Test',
        task: 't',
      });
      
      let isActive = await storage.isActive(session.sessionKey);
      assertEqual(isActive, true);
      
      await storage.markStopped(session.sessionKey);
      
      isActive = await storage.isActive(session.sessionKey);
      assertEqual(isActive, false);
    },
  },
  {
    name: 'should throw NotFoundError for non-existent session',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      await assertThrows(
        () => storage.get('non-existent-key'),
        NotFoundError
      );
    },
  },
  {
    name: 'should prevent duplicate session keys',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      
      await storage.track(
        { roleId: 'r', label: 'Dup 1', task: 't' },
        'duplicate-key'
      );
      
      await assertThrows(
        () => storage.track(
          { roleId: 'r', label: 'Dup 2', task: 't' },
          'duplicate-key'
        )
      );
    },
  },
  {
    name: 'should support pagination',
    fn: async () => {
      const storage = new SessionStorage(ctx.sessionsPath);
      storage.invalidateCache();
      
      for (let i = 0; i < 5; i++) {
        await storage.track({ roleId: 'r-page', label: `Page ${i}`, task: 't' });
      }
      
      const page1 = await storage.list({ limit: 2, offset: 0 });
      const page2 = await storage.list({ limit: 2, offset: 2 });
      
      assertLength(page1.sessions, 2);
      assertEqual(page1.hasMore, true);
      assertLength(page2.sessions, 2);
    },
  },
];

export async function runSessionsTests(): Promise<{ passed: number; failed: number }> {
  await beforeAll();
  try {
    return await runSuite('Session Storage Tests', tests);
  } finally {
    await afterAll();
  }
}

// Run if executed directly
if (require.main === module) {
  runSessionsTests().then(({ passed, failed }) => {
    console.log(`\nSessions: ${passed} passed, ${failed} failed`);
    process.exit(failed > 0 ? 1 : 0);
  });
}
