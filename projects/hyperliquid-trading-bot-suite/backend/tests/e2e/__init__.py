"""
End-to-End Integration Tests

This package contains comprehensive E2E tests for the Hyperliquid Trading Bot Suite.

Test Modules:
- test_e2e_api.py: Full API integration tests
- test_e2e_trading_workflow.py: Complete trading workflows
- test_e2e_websocket.py: WebSocket streaming tests
- test_e2e_security.py: Security-focused tests
- test_e2e_performance.py: Performance and load tests

Run with:
    pytest tests/e2e/ -v
    pytest tests/e2e/ -v -m "not slow"  # Skip slow tests
    pytest tests/e2e/ -v -m performance  # Run only performance tests
"""

__all__ = [
    "conftest",
    "test_e2e_api",
    "test_e2e_trading_workflow",
    "test_e2e_websocket",
    "test_e2e_security",
    "test_e2e_performance",
]
