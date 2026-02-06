/**
 * Integration Tests
 * P1-13: Full flow: role → work → session → complete
 */

import { RoleStorage, WorkStorage, SessionStorage } from '../src/storage';
import { OrchestratorService } from '../src/services';
import {
  createTestContext,
  cleanupTestContext,
  runSuite,
  assert,
  assertEqual,
  assertTruthy,
  assertLength,
  TestContext,
} from './setup';

let ctx: TestContext;
let roleStorage: RoleStorage;
let workStorage: WorkStorage;
let sessionStorage: SessionStorage;
let orchestrator: OrchestratorService;

async function beforeAll(): Promise<void> {
  ctx = await createTestContext('integration');
  
  roleStorage = new RoleStorage(ctx.rolesPath);
  workStorage = new WorkStorage(ctx.workDir);
  sessionStorage = new SessionStorage(ctx.sessionsPath);
  orchestrator = new OrchestratorService(workStorage, roleStorage, sessionStorage);
}

async function afterAll(): Promise<void> {
  await cleanupTestContext(ctx);
}

const tests = [
  {
    name: 'should complete full workflow: role → work → session → complete',
    fn: async () => {
      // 1. Create a custom role
      const role = await roleStorage.create({
        name: 'integration-worker',
        description: 'Integration test worker',
        model: 'anthropic/claude-sonnet-4',
        thinking: 'low',
        instructions: 'Execute integration tests',
      });
      
      assertTruthy(role.id, 'Role should be created');
      
      // 2. Create a work item
      const work = await workStorage.create({
        type: 'task',
        roleId: role.id,
        title: 'Integration Test Task',
        description: 'A task for integration testing',
        input: { testData: 'value' },
      });
      
      assertEqual(work.status, 'pending');
      assertEqual(work.roleId, role.id);
      
      // 3. Assign a session to the work
      const assignment = await orchestrator.assignSession({
        roleId: role.id,
        workItemId: work.id,
        label: 'integration-test-session',
        task: 'Execute the integration test task',
      });
      
      assertTruthy(assignment.session, 'Session should be created');
      assertTruthy(assignment.workItem, 'Work item should be returned');
      assertEqual(assignment.role.id, role.id);
      assertEqual(assignment.workItem.status, 'queued'); // Should move to queued
      
      // 4. Start the session's work
      const started = await orchestrator.startSessionWork(assignment.session.sessionKey);
      
      assertTruthy(started, 'Should start work');
      assertEqual(started!.session.status, 'active');
      assertEqual(started!.workItem.status, 'running');
      
      // 5. Record some activity
      await orchestrator.recordActivity(assignment.session.sessionKey, {
        input: 100,
        output: 50,
      });
      
      const updatedSession = await sessionStorage.get(assignment.session.sessionKey);
      assertEqual(updatedSession.tokenUsage.input, 100);
      assertEqual(updatedSession.tokenUsage.output, 50);
      
      // 6. Complete the session
      const completion = await orchestrator.handleSessionComplete(
        assignment.session.sessionKey,
        { result: 'success', message: 'Task completed' },
        { input: 50, output: 25 }
      );
      
      assertEqual(completion.success, true);
      assertEqual(completion.session.status, 'stopped');
      assertEqual(completion.workItem?.status, 'complete');
      assertTruthy(completion.workItem?.output, 'Work should have output');
      
      // 7. Verify final state
      const finalWork = await workStorage.get(work.id);
      assertEqual(finalWork.status, 'complete');
      assertTruthy(finalWork.timestamps.completedAt, 'Should have completedAt');
      
      const events = finalWork.events;
      assert(events.length >= 3, 'Should have multiple events');
      assert(
        events.some(e => e.type === 'session_completed'),
        'Should have session_completed event'
      );
    },
  },
  {
    name: 'should handle session failure',
    fn: async () => {
      // Get built-in builder role
      const roles = await roleStorage.list();
      const builderRole = roles.find(r => r.name === 'builder');
      assertTruthy(builderRole, 'Builder role should exist');
      
      // Create work
      const work = await workStorage.create({
        type: 'task',
        roleId: builderRole!.id,
        title: 'Failing Task',
      });
      
      // Assign session
      const assignment = await orchestrator.assignSession({
        roleId: builderRole!.id,
        workItemId: work.id,
        label: 'failing-session',
        task: 'This will fail',
      });
      
      // Start work
      await orchestrator.startSessionWork(assignment.session.sessionKey);
      
      // Fail the session
      const result = await orchestrator.handleSessionFailed(
        assignment.session.sessionKey,
        'Something went wrong',
        1
      );
      
      assertEqual(result.success, false);
      assertEqual(result.session.status, 'stopped');
      assertEqual(result.session.error, 'Something went wrong');
      assertEqual(result.workItem?.status, 'failed');
      assertEqual(result.workItem?.error, 'Something went wrong');
    },
  },
  {
    name: 'should handle session cancellation',
    fn: async () => {
      const roles = await roleStorage.list();
      const role = roles.find(r => r.name === 'architect');
      
      const work = await workStorage.create({
        type: 'task',
        roleId: role!.id,
        title: 'Cancelled Task',
      });
      
      const assignment = await orchestrator.assignSession({
        roleId: role!.id,
        workItemId: work.id,
        label: 'cancelled-session',
        task: 'Will be cancelled',
      });
      
      await orchestrator.startSessionWork(assignment.session.sessionKey);
      
      const result = await orchestrator.cancelSession(
        assignment.session.sessionKey,
        'User requested cancellation'
      );
      
      assertEqual(result.success, false);
      assertEqual(result.session.status, 'stopped');
      assertEqual(result.workItem?.status, 'cancelled');
    },
  },
  {
    name: 'should get work for session',
    fn: async () => {
      const roles = await roleStorage.list();
      const role = roles[0];
      
      const work = await workStorage.create({
        type: 'task',
        title: 'Get Work Test',
      });
      
      const assignment = await orchestrator.assignSession({
        roleId: role.id,
        workItemId: work.id,
        label: 'get-work-session',
        task: 'Task',
      });
      
      const fetchedWork = await orchestrator.getWorkForSession(assignment.session.sessionKey);
      
      assertTruthy(fetchedWork, 'Should get work item');
      assertEqual(fetchedWork!.id, work.id);
    },
  },
  {
    name: 'should get sessions for work',
    fn: async () => {
      const roles = await roleStorage.list();
      const role = roles[0];
      
      const work = await workStorage.create({
        type: 'task',
        title: 'Get Sessions Test',
      });
      
      await orchestrator.assignSession({
        roleId: role.id,
        workItemId: work.id,
        label: 'session-for-work-1',
        task: 'Task 1',
      });
      
      // Note: In real usage you'd complete one session before starting another
      // For this test we're just verifying the query works
      
      const sessions = await orchestrator.getSessionsForWork(work.id);
      
      assertLength(sessions, 1);
      assertEqual(sessions[0].workItemId, work.id);
    },
  },
  {
    name: 'should get role for session',
    fn: async () => {
      const role = await roleStorage.create({
        name: 'get-role-test',
        description: 'Test role',
      });
      
      const assignment = await orchestrator.assignSession({
        roleId: role.id,
        label: 'get-role-session',
        task: 'Task',
      });
      
      const fetchedRole = await orchestrator.getRoleForSession(assignment.session.sessionKey);
      
      assertEqual(fetchedRole.id, role.id);
      assertEqual(fetchedRole.name, 'get-role-test');
    },
  },
  {
    name: 'should get active session summary',
    fn: async () => {
      const roles = await roleStorage.list();
      const role = roles[0];
      
      const work = await workStorage.create({
        type: 'task',
        title: 'Summary Test',
      });
      
      const assignment = await orchestrator.assignSession({
        roleId: role.id,
        workItemId: work.id,
        label: 'summary-session',
        task: 'Task',
      });
      
      await orchestrator.startSessionWork(assignment.session.sessionKey);
      
      const summary = await orchestrator.getActiveSessionSummary();
      
      assert(summary.length >= 1, 'Should have active sessions');
      
      const found = summary.find(s => s.session.sessionKey === assignment.session.sessionKey);
      assertTruthy(found, 'Should find our session');
      assertTruthy(found!.workItem, 'Should have work item');
      assertTruthy(found!.role, 'Should have role');
    },
  },
  {
    name: 'should cleanup stale sessions',
    fn: async () => {
      const roles = await roleStorage.list();
      const role = roles[0];
      
      // Create a session and immediately stop it
      const assignment = await orchestrator.assignSession({
        roleId: role.id,
        label: 'cleanup-session',
        task: 'Will be cleaned up',
      });
      
      await orchestrator.handleSessionComplete(assignment.session.sessionKey);
      
      // Cleanup with 0ms max age (immediate)
      const result = await orchestrator.cleanup(0, false);
      
      assert(result.prunedSessions >= 1, 'Should prune at least 1 session');
    },
  },
  {
    name: 'should handle parent-child work with sessions',
    fn: async () => {
      const roles = await roleStorage.list();
      const architectRole = roles.find(r => r.name === 'architect');
      const builderRole = roles.find(r => r.name === 'builder');
      
      // Create parent work
      const parentWork = await workStorage.create({
        type: 'pipeline',
        roleId: architectRole!.id,
        title: 'Parent Pipeline',
      });
      
      // Create child work items
      const child1 = await workStorage.create({
        type: 'task',
        roleId: builderRole!.id,
        parentId: parentWork.id,
        title: 'Child Task 1',
      });
      
      const child2 = await workStorage.create({
        type: 'task',
        roleId: builderRole!.id,
        parentId: parentWork.id,
        title: 'Child Task 2',
      });
      
      // Verify parent has children
      const parent = await workStorage.get(parentWork.id);
      assert(parent.childIds.includes(child1.id), 'Parent should have child1');
      assert(parent.childIds.includes(child2.id), 'Parent should have child2');
      
      // Execute first child
      const assignment1 = await orchestrator.assignSession({
        roleId: builderRole!.id,
        workItemId: child1.id,
        label: 'child-1-session',
        task: 'Execute child 1',
      });
      
      await orchestrator.startSessionWork(assignment1.session.sessionKey);
      await orchestrator.handleSessionComplete(assignment1.session.sessionKey, {
        result: 'child1 done',
      });
      
      // Execute second child
      const assignment2 = await orchestrator.assignSession({
        roleId: builderRole!.id,
        workItemId: child2.id,
        label: 'child-2-session',
        task: 'Execute child 2',
      });
      
      await orchestrator.startSessionWork(assignment2.session.sessionKey);
      await orchestrator.handleSessionComplete(assignment2.session.sessionKey, {
        result: 'child2 done',
      });
      
      // Verify both children are complete
      const finalChild1 = await workStorage.get(child1.id);
      const finalChild2 = await workStorage.get(child2.id);
      
      assertEqual(finalChild1.status, 'complete');
      assertEqual(finalChild2.status, 'complete');
      
      // Get children through API
      const children = await workStorage.getChildren(parentWork.id);
      assertLength(children, 2);
      assert(
        children.every(c => c.status === 'complete'),
        'All children should be complete'
      );
    },
  },
  {
    name: 'should track token usage across session lifecycle',
    fn: async () => {
      const roles = await roleStorage.list();
      const role = roles[0];
      
      const work = await workStorage.create({
        type: 'task',
        title: 'Token Tracking Test',
      });
      
      const assignment = await orchestrator.assignSession({
        roleId: role.id,
        workItemId: work.id,
        label: 'token-tracking-session',
        task: 'Track tokens',
      });
      
      await orchestrator.startSessionWork(assignment.session.sessionKey);
      
      // Simulate multiple activities with token usage
      await orchestrator.recordActivity(assignment.session.sessionKey, {
        input: 1000,
        output: 500,
        thinking: 200,
      });
      
      await orchestrator.recordActivity(assignment.session.sessionKey, {
        input: 800,
        output: 400,
        thinking: 150,
      });
      
      const session = await sessionStorage.get(assignment.session.sessionKey);
      
      assertEqual(session.tokenUsage.input, 1800);
      assertEqual(session.tokenUsage.output, 900);
      assertEqual(session.tokenUsage.thinking, 350);
    },
  },
];

export async function runIntegrationTests(): Promise<{ passed: number; failed: number }> {
  await beforeAll();
  try {
    return await runSuite('Integration Tests', tests);
  } finally {
    await afterAll();
  }
}

// Run if executed directly
if (require.main === module) {
  runIntegrationTests().then(({ passed, failed }) => {
    console.log(`\nIntegration: ${passed} passed, ${failed} failed`);
    process.exit(failed > 0 ? 1 : 0);
  });
}
