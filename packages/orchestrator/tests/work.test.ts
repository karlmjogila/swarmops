/**
 * Work Storage Tests
 * P1-13: Work creation, state transitions, events, queries, parent-child
 */

import { WorkStorage, InvalidTransitionError, NotFoundError } from '../src/storage';
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
} from './setup';

let ctx: TestContext;

async function beforeAll(): Promise<void> {
  ctx = await createTestContext('work');
}

async function afterAll(): Promise<void> {
  await cleanupTestContext(ctx);
}

const tests = [
  {
    name: 'should create a work item',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      
      const work = await storage.create({
        type: 'task',
        title: 'Test Task',
        description: 'A test task',
        input: { key: 'value' },
        tags: ['test', 'unit'],
        priority: 5,
      });
      
      assertTruthy(work.id, 'Work should have an ID');
      assertEqual(work.type, 'task');
      assertEqual(work.status, 'pending');
      assertEqual(work.title, 'Test Task');
      assertEqual(work.description, 'A test task');
      assertEqual(work.iterations, 0);
      assertLength(work.events, 1);
      assertEqual(work.events[0].type, 'created');
      assertEqual(work.priority, 5);
      assertTruthy(work.timestamps.createdAt, 'Should have createdAt');
      assertTruthy(work.timestamps.updatedAt, 'Should have updatedAt');
    },
  },
  {
    name: 'should get a work item by ID',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      
      const created = await storage.create({
        type: 'task',
        title: 'Get Test',
      });
      
      const fetched = await storage.get(created.id);
      
      assertEqual(fetched.id, created.id);
      assertEqual(fetched.title, 'Get Test');
    },
  },
  {
    name: 'should list work items',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      storage.invalidateCache();
      
      await storage.create({ type: 'task', title: 'List 1' });
      await storage.create({ type: 'pipeline', title: 'List 2' });
      await storage.create({ type: 'batch', title: 'List 3' });
      
      const result = await storage.list();
      
      assert(result.items.length >= 3, 'Should have at least 3 items');
      assert(result.total >= 3, 'Total should be at least 3');
    },
  },
  {
    name: 'should filter by status',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      storage.invalidateCache();
      
      const work = await storage.create({ type: 'task', title: 'Status Filter Test' });
      await storage.updateStatus(work.id, 'queued');
      
      const pendingResult = await storage.list({ status: 'pending' });
      const queuedResult = await storage.list({ status: 'queued' });
      
      assert(
        !pendingResult.items.find(w => w.id === work.id),
        'Should not be in pending results'
      );
      assertTruthy(
        queuedResult.items.find(w => w.id === work.id),
        'Should be in queued results'
      );
    },
  },
  {
    name: 'should filter by type',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      storage.invalidateCache();
      
      await storage.create({ type: 'review', title: 'Review Item' });
      
      const result = await storage.list({ type: 'review' });
      
      assert(result.items.length >= 1, 'Should have at least 1 review item');
      assert(
        result.items.every(w => w.type === 'review'),
        'All items should be reviews'
      );
    },
  },
  {
    name: 'should transition status: pending -> queued -> running -> complete',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      
      let work = await storage.create({ type: 'task', title: 'State Transition Test' });
      assertEqual(work.status, 'pending');
      
      work = await storage.updateStatus(work.id, 'queued');
      assertEqual(work.status, 'queued');
      
      work = await storage.updateStatus(work.id, 'running');
      assertEqual(work.status, 'running');
      assertTruthy(work.timestamps.startedAt, 'Should have startedAt');
      
      work = await storage.updateStatus(work.id, 'complete');
      assertEqual(work.status, 'complete');
      assertTruthy(work.timestamps.completedAt, 'Should have completedAt');
    },
  },
  {
    name: 'should reject invalid state transitions',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      
      const work = await storage.create({ type: 'task', title: 'Invalid Transition' });
      
      await assertThrows(
        () => storage.updateStatus(work.id, 'complete'),
        InvalidTransitionError
      );
    },
  },
  {
    name: 'should append events',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      
      const work = await storage.create({ type: 'task', title: 'Event Test' });
      
      const updated = await storage.appendEvent(work.id, {
        type: 'custom',
        message: 'Something happened',
        data: { detail: 'value' },
      });
      
      assertLength(updated.events, 2); // created + custom
      assertEqual(updated.events[1].type, 'custom');
      assertEqual(updated.events[1].message, 'Something happened');
    },
  },
  {
    name: 'should cancel work',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      
      let work = await storage.create({ type: 'task', title: 'Cancel Test' });
      work = await storage.updateStatus(work.id, 'queued');
      work = await storage.updateStatus(work.id, 'running');
      
      work = await storage.cancel(work.id, 'User cancelled');
      
      assertEqual(work.status, 'cancelled');
      assertTruthy(work.error, 'Should have error message');
      assertTruthy(work.timestamps.completedAt, 'Should have completedAt');
    },
  },
  {
    name: 'should handle parent-child relationships',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      
      const parent = await storage.create({
        type: 'pipeline',
        title: 'Parent Work',
      });
      
      const child1 = await storage.create({
        type: 'task',
        title: 'Child 1',
        parentId: parent.id,
      });
      
      const child2 = await storage.create({
        type: 'task',
        title: 'Child 2',
        parentId: parent.id,
      });
      
      assertEqual(child1.parentId, parent.id);
      assertEqual(child2.parentId, parent.id);
      
      // Fetch parent to check childIds were updated
      const fetchedParent = await storage.get(parent.id);
      assert(fetchedParent.childIds.includes(child1.id), 'Parent should have child1');
      assert(fetchedParent.childIds.includes(child2.id), 'Parent should have child2');
      
      // Test getChildren
      const children = await storage.getChildren(parent.id);
      assertLength(children, 2);
    },
  },
  {
    name: 'should set output',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      
      const work = await storage.create({ type: 'task', title: 'Output Test' });
      
      const updated = await storage.setOutput(work.id, {
        result: 'success',
        data: [1, 2, 3],
      });
      
      assertTruthy(updated.output, 'Should have output');
      assertEqual((updated.output as Record<string, unknown>).result, 'success');
    },
  },
  {
    name: 'should increment iterations',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      
      let work = await storage.create({ type: 'task', title: 'Iteration Test' });
      assertEqual(work.iterations, 0);
      
      work = await storage.incrementIterations(work.id);
      assertEqual(work.iterations, 1);
      
      work = await storage.incrementIterations(work.id);
      assertEqual(work.iterations, 2);
    },
  },
  {
    name: 'should throw NotFoundError for non-existent work',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      
      await assertThrows(
        () => storage.get('non-existent-id'),
        NotFoundError
      );
    },
  },
  {
    name: 'should support pagination',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      storage.invalidateCache();
      
      // Create several items
      for (let i = 0; i < 5; i++) {
        await storage.create({ type: 'task', title: `Pagination ${i}` });
      }
      
      const page1 = await storage.list({ limit: 2, offset: 0 });
      const page2 = await storage.list({ limit: 2, offset: 2 });
      
      assertLength(page1.items, 2);
      assertEqual(page1.hasMore, true);
      assertLength(page2.items, 2);
    },
  },
  {
    name: 'should filter by tag',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      storage.invalidateCache();
      
      await storage.create({ 
        type: 'task', 
        title: 'Tagged Item',
        tags: ['special', 'important'],
      });
      
      const result = await storage.list({ tag: 'special' });
      
      assert(result.items.length >= 1, 'Should find tagged items');
      assert(
        result.items.some(w => w.tags?.includes('special')),
        'Results should include special tag'
      );
    },
  },
  {
    name: 'should handle multiple status filter',
    fn: async () => {
      const storage = new WorkStorage(ctx.workDir);
      storage.invalidateCache();
      
      await storage.create({ type: 'task', title: 'Multi Status 1' });
      const work2 = await storage.create({ type: 'task', title: 'Multi Status 2' });
      await storage.updateStatus(work2.id, 'queued');
      
      const result = await storage.list({ status: ['pending', 'queued'] });
      
      assert(result.items.length >= 2, 'Should find items with either status');
    },
  },
];

export async function runWorkTests(): Promise<{ passed: number; failed: number }> {
  await beforeAll();
  try {
    return await runSuite('Work Storage Tests', tests);
  } finally {
    await afterAll();
  }
}

// Run if executed directly
if (require.main === module) {
  runWorkTests().then(({ passed, failed }) => {
    console.log(`\nWork: ${passed} passed, ${failed} failed`);
    process.exit(failed > 0 ? 1 : 0);
  });
}
