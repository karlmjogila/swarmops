/**
 * Role Storage Tests
 * P1-13: CRUD operations, validation, built-in protection
 */

import { RoleStorage, ConflictError, NotFoundError } from '../src/storage';
import {
  createTestContext,
  cleanupTestContext,
  runSuite,
  assert,
  assertEqual,
  assertThrows,
  assertTruthy,
  TestContext,
} from './setup';

let ctx: TestContext;

async function beforeAll(): Promise<void> {
  ctx = await createTestContext('roles');
}

async function afterAll(): Promise<void> {
  await cleanupTestContext(ctx);
}

const tests = [
  {
    name: 'should create a new role',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      const role = await storage.create({
        name: 'test-role',
        description: 'A test role',
        model: 'anthropic/claude-sonnet-4',
        thinking: 'low',
        instructions: 'Test instructions',
      });
      
      assertTruthy(role.id, 'Role should have an ID');
      assertEqual(role.name, 'test-role');
      assertEqual(role.description, 'A test role');
      assertEqual(role.model, 'anthropic/claude-sonnet-4');
      assertEqual(role.thinking, 'low');
      assertTruthy(role.createdAt, 'Role should have createdAt');
      assertTruthy(role.updatedAt, 'Role should have updatedAt');
    },
  },
  {
    name: 'should list all roles including built-ins',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      const roles = await storage.list();
      
      // Should have built-in roles plus any we created
      assert(roles.length >= 3, 'Should have at least 3 built-in roles');
      
      const builtinNames = roles.filter(r => r.builtin).map(r => r.name);
      assert(builtinNames.includes('architect'), 'Should have architect role');
      assert(builtinNames.includes('builder'), 'Should have builder role');
      assert(builtinNames.includes('reviewer'), 'Should have reviewer role');
    },
  },
  {
    name: 'should get a role by ID',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      const created = await storage.create({
        name: 'get-test-role',
        description: 'Test getting by ID',
      });
      
      const fetched = await storage.get(created.id);
      
      assertEqual(fetched.id, created.id);
      assertEqual(fetched.name, 'get-test-role');
    },
  },
  {
    name: 'should get a role by name',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      await storage.create({
        name: 'named-role',
        description: 'Named role test',
      });
      
      const fetched = await storage.getByName('named-role');
      
      assertTruthy(fetched, 'Should find role by name');
      assertEqual(fetched!.name, 'named-role');
      
      // Case insensitive
      const fetchedUpper = await storage.getByName('NAMED-ROLE');
      assertTruthy(fetchedUpper, 'Should find role by name (case insensitive)');
    },
  },
  {
    name: 'should update a role',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      const created = await storage.create({
        name: 'update-test-role',
      });
      
      const updated = await storage.update(created.id, {
        description: 'Updated description',
        model: 'anthropic/claude-opus-4-5',
        thinking: 'high',
      });
      
      assertEqual(updated.id, created.id);
      assertEqual(updated.name, 'update-test-role');
      assertEqual(updated.description, 'Updated description');
      assertEqual(updated.model, 'anthropic/claude-opus-4-5');
      assertEqual(updated.thinking, 'high');
      assert(updated.updatedAt > created.updatedAt, 'updatedAt should be newer');
    },
  },
  {
    name: 'should delete a role',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      const created = await storage.create({
        name: 'delete-test-role',
      });
      
      await storage.delete(created.id);
      
      await assertThrows(
        () => storage.get(created.id),
        NotFoundError
      );
    },
  },
  {
    name: 'should prevent duplicate names',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      await storage.create({
        name: 'unique-role',
      });
      
      await assertThrows(
        () => storage.create({ name: 'unique-role' }),
        ConflictError,
        'already exists'
      );
    },
  },
  {
    name: 'should prevent deleting built-in roles',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      const roles = await storage.list();
      const builtin = roles.find(r => r.builtin);
      
      assertTruthy(builtin, 'Should have a built-in role');
      
      await assertThrows(
        () => storage.delete(builtin!.id),
        ConflictError,
        'built-in'
      );
    },
  },
  {
    name: 'should prevent renaming built-in roles',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      const roles = await storage.list();
      const builtin = roles.find(r => r.builtin);
      
      await assertThrows(
        () => storage.update(builtin!.id, { name: 'new-name' }),
        ConflictError,
        'built-in'
      );
    },
  },
  {
    name: 'should allow updating built-in role properties other than name',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      const roles = await storage.list();
      const builtin = roles.find(r => r.builtin);
      
      const updated = await storage.update(builtin!.id, {
        description: 'Custom description',
        instructions: 'Custom instructions',
      });
      
      assertEqual(updated.description, 'Custom description');
      assertEqual(updated.instructions, 'Custom instructions');
    },
  },
  {
    name: 'should throw NotFoundError for non-existent role',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      await assertThrows(
        () => storage.get('non-existent-id'),
        NotFoundError
      );
    },
  },
  {
    name: 'should check name availability',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      await storage.create({
        name: 'availability-test',
      });
      
      const available = await storage.isNameAvailable('new-unique-name');
      assertEqual(available, true);
      
      const notAvailable = await storage.isNameAvailable('availability-test');
      assertEqual(notAvailable, false);
    },
  },
  {
    name: 'should apply default values when creating role',
    fn: async () => {
      const storage = new RoleStorage(ctx.rolesPath);
      
      const role = await storage.create({
        name: 'defaults-test',
      });
      
      assertEqual(role.model, 'anthropic/claude-sonnet-4');
      assertEqual(role.thinking, 'low');
      assertEqual(role.description, '');
      assertEqual(role.instructions, '');
    },
  },
];

export async function runRolesTests(): Promise<{ passed: number; failed: number }> {
  await beforeAll();
  try {
    return await runSuite('Role Storage Tests', tests);
  } finally {
    await afterAll();
  }
}

// Run if executed directly
if (require.main === module) {
  runRolesTests().then(({ passed, failed }) => {
    console.log(`\nRoles: ${passed} passed, ${failed} failed`);
    process.exit(failed > 0 ? 1 : 0);
  });
}
