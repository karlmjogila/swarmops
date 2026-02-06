/**
 * Test Runner
 * Runs all test suites and reports results
 */

import { runRolesTests } from './roles.test';
import { runWorkTests } from './work.test';
import { runSessionsTests } from './sessions.test';
import { runIntegrationTests } from './integration.test';

async function main(): Promise<void> {
  console.log('🧪 Running Orchestrator Tests\n');
  console.log('═'.repeat(50));
  
  let totalPassed = 0;
  let totalFailed = 0;
  
  try {
    // Run all test suites
    const rolesResult = await runRolesTests();
    totalPassed += rolesResult.passed;
    totalFailed += rolesResult.failed;
    
    const workResult = await runWorkTests();
    totalPassed += workResult.passed;
    totalFailed += workResult.failed;
    
    const sessionsResult = await runSessionsTests();
    totalPassed += sessionsResult.passed;
    totalFailed += sessionsResult.failed;
    
    const integrationResult = await runIntegrationTests();
    totalPassed += integrationResult.passed;
    totalFailed += integrationResult.failed;
    
  } catch (error) {
    console.error('\n❌ Test suite crashed:', error);
    process.exit(1);
  }
  
  // Print summary
  console.log('\n' + '═'.repeat(50));
  console.log('\n📊 Test Summary\n');
  console.log(`   ✓ ${totalPassed} tests passed`);
  console.log(`   ✗ ${totalFailed} tests failed`);
  console.log(`   Total: ${totalPassed + totalFailed} tests\n`);
  
  if (totalFailed > 0) {
    console.log('❌ Some tests failed');
    process.exit(1);
  } else {
    console.log('✅ All tests passed!');
    process.exit(0);
  }
}

main();
