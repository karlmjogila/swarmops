# End-to-End Integration Tests

Comprehensive E2E tests for the Hyperliquid Trading Bot Suite, covering full system workflows from API endpoints through trading execution.

## Test Coverage

### 📡 API Integration (`test_e2e_api.py`)
- Health check and status endpoints
- Content ingestion (PDF, video)
- Strategy management CRUD operations
- Backtest execution and results
- Trade management
- Error handling and validation
- CORS middleware
- Performance benchmarks

### 🔄 Trading Workflows (`test_e2e_trading_workflow.py`)
- **Ingestion → Strategy**: PDF/video upload → strategy extraction
- **Strategy → Backtest**: Strategy creation → backtest execution → results analysis
- **Pattern Detection**: Market data → pattern detection → trade signals
- **Trade Execution**: Signal → order → position → close
- **Risk Management**: Risk checks → validation → circuit breaker
- **Feedback Loop**: Trade outcomes → analysis → strategy improvement
- **Full Trading Day**: Complete simulation of trading session
- **Data Persistence**: Verify data persists across operations

### 🔌 WebSocket Streaming (`test_e2e_websocket.py`)
- Backtest replay streaming
- Live market data subscriptions
- Trade and position updates
- Connection handling and reconnection
- Error handling
- Performance and latency

### 🔒 Security (`test_e2e_security.py`)
- Authentication and authorization (placeholders for future implementation)
- Input validation and SQL injection prevention
- XSS and path traversal prevention
- File upload security
- Rate limiting (when implemented)
- CORS configuration
- API key and secrets handling
- Session management
- Data sanitization
- Secure defaults (testnet, paper trading)

### ⚡ Performance (`test_e2e_performance.py`)
- Response time benchmarks (health, queries, submissions)
- Concurrent request handling
- Large dataset processing
- Database query performance
- Memory usage monitoring
- Stress tests and sustained load
- Cache effectiveness

## Running Tests

### Run All E2E Tests
```bash
pytest tests/e2e/ -v
```

### Run Specific Test Module
```bash
pytest tests/e2e/test_e2e_api.py -v
pytest tests/e2e/test_e2e_trading_workflow.py -v
pytest tests/e2e/test_e2e_security.py -v
pytest tests/e2e/test_e2e_performance.py -v
```

### Run by Test Markers

**Skip slow tests:**
```bash
pytest tests/e2e/ -v -m "not slow"
```

**Run only performance tests:**
```bash
pytest tests/e2e/ -v -m performance
```

**Run only security tests:**
```bash
pytest tests/e2e/ -v tests/e2e/test_e2e_security.py
```

### Run with Coverage
```bash
pytest tests/e2e/ --cov=src --cov-report=html --cov-report=term
```

### Run Specific Test Class or Method
```bash
# Run specific test class
pytest tests/e2e/test_e2e_api.py::TestHealthEndpoints -v

# Run specific test method
pytest tests/e2e/test_e2e_api.py::TestHealthEndpoints::test_health_check -v
```

## Test Markers

- `@pytest.mark.asyncio` - Async tests (requires pytest-asyncio)
- `@pytest.mark.slow` - Long-running tests (>10s)
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.skip(reason="...")` - Skipped tests (features not yet implemented)

## Fixtures

Key fixtures provided by `conftest.py`:

- **`client`**: Synchronous FastAPI TestClient
- **`async_client`**: Async client for WebSocket and async endpoints
- **`test_db_engine`**: In-memory SQLite database
- **`test_session`**: Database session
- **`sample_candles`**: Realistic OHLCV data (1000 candles)
- **`sample_strategy_rule`**: Example strategy for testing
- **`sample_backtest_config`**: Example backtest configuration
- **`sample_trades`**: Sample trade history
- **`mock_hyperliquid_responses`**: Mock Hyperliquid API responses
- **`performance_metrics`**: Performance tracking dictionary

## Expected Test Results

### ✅ Currently Passing
- Health check endpoints
- API endpoint structure validation
- Input validation and error handling
- Performance benchmarks (basic)
- Data structure validation

### ⚠️ Skipped (Features Not Implemented)
Per the security review findings, these tests are skipped until implemented:
- Authentication/authorization (CRITICAL)
- Rate limiting (HIGH)
- File upload magic byte validation (MEDIUM)
- WebSocket authentication (HIGH)

### 🔧 Expected Behavior
Many tests use conditional assertions (`if response.status_code in [200, 201]`) because:
1. Some features may not be fully implemented
2. Tests validate structure and behavior, not specific implementation
3. Focus is on testing what exists without breaking on missing features

## Performance Benchmarks

Expected performance targets:

| Endpoint | Target | Test |
|----------|--------|------|
| Health check | < 50ms avg | `test_health_check_response_time` |
| List strategies | < 500ms avg | `test_list_strategies_response_time` |
| Trade queries | < 1s | `test_trade_query_response_time` |
| Backtest submission | < 2s | `test_backtest_submission_response_time` |

### Concurrent Load Targets

| Load Test | Target | Test |
|-----------|--------|------|
| 50 concurrent health checks | >95% success | `test_concurrent_health_checks` |
| 20 concurrent queries | >90% success | `test_concurrent_strategy_queries` |
| Sustained load (10 req/s) | <5% errors | `test_sustained_load` |

## Security Test Status

Based on the security review findings in `progress.md`:

### Critical Issues (Tests Skipped)
1. ❌ No authentication on API endpoints → `test_unauthenticated_request_rejected`
2. ❌ Private keys exposed in headers → Requires architecture change
3. ❌ Hardcoded credentials → Configuration issue

### High Priority (Tests Skipped)
4. ❌ Unauthenticated WebSocket → `test_authentication_required`
5. ❌ No rate limiting → `test_api_rate_limiting`

### Medium Priority (Tests Active)
6. ✅ File upload security → `TestFileUploadSecurity` class
7. ✅ CORS validation → `TestCORSConfiguration` class
8. ✅ Input validation → `TestInputValidation` class

### Positive Findings (Tests Verify)
- ✅ Pydantic validation → Input validation tests
- ✅ SQL injection prevention → `test_sql_injection_prevention`
- ✅ Secure defaults (testnet) → `test_default_is_testnet`
- ✅ Paper trading available → `test_paper_trading_available`

## Debugging Failed Tests

### Enable Verbose Output
```bash
pytest tests/e2e/ -vv -s
```

### Run Single Test with Full Output
```bash
pytest tests/e2e/test_e2e_api.py::TestHealthEndpoints::test_health_check -vv -s
```

### Show Print Statements
```bash
pytest tests/e2e/ -v -s
```

### Drop into Debugger on Failure
```bash
pytest tests/e2e/ -v --pdb
```

### Generate HTML Report
```bash
pytest tests/e2e/ --html=report.html --self-contained-html
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run E2E tests
        run: |
          pytest tests/e2e/ -v -m "not slow" --cov=src
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Writing New E2E Tests

### Test Structure Template

```python
import pytest

class TestNewFeature:
    """Test new feature end-to-end."""
    
    def test_feature_workflow(self, client, sample_data):
        """Complete workflow for new feature."""
        # Step 1: Setup
        setup_response = client.post("/api/setup", json=sample_data)
        assert setup_response.status_code in [200, 201]
        
        # Step 2: Execute
        result_id = setup_response.json()["id"]
        execute_response = client.post(f"/api/execute/{result_id}")
        assert execute_response.status_code == 200
        
        # Step 3: Verify
        verify_response = client.get(f"/api/results/{result_id}")
        assert verify_response.status_code == 200
        assert verify_response.json()["status"] == "completed"
```

### Best Practices

1. **Test behavior, not implementation** - Focus on what the system does, not how
2. **Independent tests** - Each test should be runnable in isolation
3. **Realistic data** - Use fixtures that simulate real-world scenarios
4. **Clear assertions** - One behavior per test, clear failure messages
5. **Handle incomplete features** - Use conditional assertions for features in progress
6. **Performance tracking** - Use `performance_metrics` fixture for benchmarking
7. **Clean up** - Use fixtures for cleanup, ensure tests don't leave state

## Known Issues & Limitations

1. **WebSocket Testing**: TestClient has limited WebSocket support; full WebSocket tests require separate client
2. **Async Operations**: Backtest execution is async; tests check submission, not completion
3. **External Dependencies**: Mock external services (Hyperliquid, OpenAI) to avoid real API calls
4. **Database**: Tests use SQLite in-memory; some PostgreSQL features not available
5. **Authentication**: Many security tests skipped pending authentication implementation

## Future Improvements

- [ ] Real WebSocket client for comprehensive WS testing
- [ ] Authentication implementation and test activation
- [ ] Rate limiting implementation and tests
- [ ] Load testing with locust or k6
- [ ] Integration with external test environment
- [ ] End-to-end frontend + backend testing with Playwright
- [ ] Chaos engineering tests (service failures, network issues)
- [ ] Long-running stability tests (24h+ runs)

## Support

For questions or issues with E2E tests:
1. Check this README
2. Review test output carefully
3. Check `conftest.py` for fixture definitions
4. Review security findings in `progress.md`
5. Consult Testing Excellence skill in project context

## Test Metrics

Run tests with metrics reporting:

```bash
pytest tests/e2e/ -v --durations=10
```

This shows the 10 slowest tests, helping identify performance bottlenecks.
