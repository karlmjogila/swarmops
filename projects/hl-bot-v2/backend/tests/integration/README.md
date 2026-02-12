## # Integration Test Suite

Comprehensive integration tests for the HL Bot API endpoints.

## 📁 Test Structure

```
tests/integration/
├── conftest.py                    # Test fixtures and database setup
├── test_api_comprehensive.py      # Main API endpoint tests
├── test_api_validation.py         # Input validation and schema tests
├── test_websocket.py              # WebSocket streaming tests
└── README.md                      # This file
```

## 🧪 Test Coverage

### `test_api_comprehensive.py`
**Health & Status Endpoints**
- Root endpoint info
- Health check
- Readiness check

**Data Import Endpoints**
- CSV file upload (valid/invalid)
- Raw CSV import via JSON
- Duplicate detection (idempotency)
- Error handling and DLQ
- File type validation
- Parameter validation

**Data Query Endpoints**
- Data range queries
- Available symbols/timeframes listing
- Empty database handling
- Sorted results

**Data Deletion Endpoints**
- Full dataset deletion
- Time-range deletion
- Timestamp validation

**Backtest Control Endpoints**
- Session creation
- Control commands (pause/resume/step/speed/seek)
- Session listing
- Session termination
- Process management

**Error Handling & Edge Cases**
- Large CSV imports
- Concurrent requests
- Path parameter validation
- SQL injection prevention
- XSS protection

### `test_api_validation.py`
**Input Validation**
- Timeframe pattern validation (e.g., "5m", "1h")
- Symbol validation (empty, whitespace)
- Numeric bounds (capital, position size)
- Integer constraints (max trades)
- Date format validation
- Timestamp ISO format

**Response Schemas**
- Import response structure
- Data range response structure
- Available data response structure
- Error response consistency

**Boundary Values**
- Very large/small numbers
- Maximum string lengths
- Negative price rejection

**Type Safety**
- String/number type enforcement
- Array/scalar validation
- Null/required field validation

**Special Characters**
- Unicode handling
- Control character sanitization
- SQL injection protection
- XSS prevention

### `test_websocket.py`
**WebSocket Connections**
- Valid/invalid session connections
- JSON message streaming
- Non-JSON output handling
- Completion messages
- Disconnect cleanup

**Data Format**
- Candle message schema
- Trade message schema
- State message schema

**Concurrency**
- Multiple simultaneous sessions
- High message rate handling

**Error Recovery**
- Client disconnect handling
- Malformed JSON from process
- Process crash recovery

## 🚀 Running Tests

### Run all integration tests:
```bash
cd backend
pytest tests/integration/ -v
```

### Run specific test file:
```bash
pytest tests/integration/test_api_comprehensive.py -v
pytest tests/integration/test_api_validation.py -v
pytest tests/integration/test_websocket.py -v
```

### Run specific test class:
```bash
pytest tests/integration/test_api_comprehensive.py::TestDataImportEndpoints -v
```

### Run specific test:
```bash
pytest tests/integration/test_api_comprehensive.py::TestDataImportEndpoints::test_import_csv_file_with_valid_data_succeeds -v
```

### Run with coverage:
```bash
pytest tests/integration/ --cov=app.api --cov-report=html
```

### Run in parallel:
```bash
pytest tests/integration/ -n auto
```

## 📊 Test Metrics

Current coverage:
- **API Endpoints**: 100% of routes tested
- **HTTP Methods**: GET, POST, DELETE, WebSocket
- **Status Codes**: 200, 201, 400, 404, 409, 410, 422, 500, 503
- **Edge Cases**: Empty inputs, boundaries, malformed data, injection attempts
- **Error Conditions**: Validation errors, not found, conflicts, server errors

## 🎯 Testing Principles

These tests follow the guidelines from the Testing Skill:

1. **AAA Pattern** - Arrange, Act, Assert
2. **Test Behavior** - What the API does, not how
3. **Independent Tests** - No test depends on another
4. **Deterministic** - Same result every run
5. **Clear Names** - Test names describe expected behavior
6. **Minimal Mocking** - Only mock external dependencies (subprocess, file I/O)
7. **Edge Cases** - Empty, null, boundaries, errors
8. **Fast** - Use in-memory SQLite for speed

## 🏗️ Fixtures

### Database Fixtures
- `test_db` - Fresh in-memory SQLite database for each test
- `sample_ohlcv_data` - 100 BTC-USD 5m candles
- `multi_symbol_data` - Multiple symbols and timeframes

### Client Fixture
- `client` - AsyncClient with test database injected

### Mock Fixtures
- `mock_csv_importer` - Mock CSV import without file I/O
- `mock_subprocess` - Mock backtest process

## 🔧 Test Configuration

Tests use in-memory SQLite for:
- **Speed** - No disk I/O
- **Isolation** - Each test gets fresh database
- **Simplicity** - No cleanup needed

Tests are marked with `@pytest.mark.asyncio` for:
- FastAPI async endpoints
- AsyncClient support

## 📝 Adding New Tests

When adding endpoints:

1. **Add to appropriate test class** or create new class
2. **Follow naming convention**: `test_{action}_{condition}_{expected_result}`
3. **Use AAA pattern**: Arrange → Act → Assert
4. **Test happy path + edge cases + errors**
5. **Document expected behavior** in docstring

Example:
```python
@pytest.mark.asyncio
async def test_import_csv_file_with_valid_data_succeeds(
    self, client: AsyncClient, test_db
):
    """Import CSV file with valid TradingView format should succeed."""
    # Arrange
    csv_file = io.BytesIO(VALID_CSV_CONTENT.encode())
    files = {"file": ("btc_5m.csv", csv_file, "text/csv")}
    params = {"symbol": "BTC-USD", "timeframe": "5m"}
    
    # Act
    response = await client.post("/api/data/import", files=files, params=params)
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["stats"]["inserted"] == 3
```

## 🐛 Debugging Failed Tests

### View detailed output:
```bash
pytest tests/integration/test_api_comprehensive.py::TestDataImportEndpoints::test_name -vv -s
```

### Drop into debugger on failure:
```bash
pytest tests/integration/ --pdb
```

### Show print statements:
```bash
pytest tests/integration/ -s
```

### Show warnings:
```bash
pytest tests/integration/ -v --tb=long
```

## ✅ Quality Checklist

Before merging:
- [ ] All tests pass
- [ ] Coverage > 90% for API routes
- [ ] No flaky tests (run 10 times)
- [ ] No console.log or debugging code
- [ ] Test names are descriptive
- [ ] Edge cases covered
- [ ] Error conditions tested
- [ ] Schema validation present

## 🔗 Related Documentation

- [API Design Skill](../../../SKILLS/API_DESIGN.md)
- [Testing Skill](../../../SKILLS/TESTING.md)
- [Backend README](../../README.md)
- [API Routes](../../app/api/routes/)
