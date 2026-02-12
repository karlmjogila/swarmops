"""
E2E Test Fixtures and Configuration

Provides fixtures for full system integration testing including:
- TestClient for API calls
- Database setup with realistic data
- Mock external services (Hyperliquid, OpenAI)
- WebSocket test clients
"""

import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any
from pathlib import Path
import json
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

from src.api.main import create_app
from src.database.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db_engine():
    """Create in-memory test database."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Remove PostgreSQL-specific constraints for SQLite testing
    for table in Base.metadata.tables.values():
        constraints_to_remove = []
        for constraint in table.constraints:
            if hasattr(constraint, 'sqltext'):
                sqltext = str(constraint.sqltext)
                if 'ARRAY_LENGTH' in sqltext.upper():
                    constraints_to_remove.append(constraint)
        
        for constraint in constraints_to_remove:
            table.constraints.remove(constraint)
    
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(test_db_engine):
    """Create test database session."""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def test_app(test_db_engine):
    """Create FastAPI test application."""
    app = create_app()
    # Override database dependency if needed
    return app


@pytest.fixture(scope="function")
def client(test_app) -> TestClient:
    """Create synchronous test client."""
    return TestClient(test_app)


@pytest.fixture(scope="function")
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for WebSocket and async endpoint testing."""
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def sample_candles() -> list[Dict[str, Any]]:
    """Generate realistic OHLCV candle data for testing."""
    candles = []
    base_time = datetime.now() - timedelta(days=30)
    base_price = 50000.0
    
    for i in range(1000):  # 1000 candles
        timestamp = base_time + timedelta(minutes=i * 5)
        
        # Add some realistic price movement
        volatility = 100.0
        open_price = base_price + (i * 10) + (volatility * (0.5 - (i % 10) / 10))
        close_price = open_price + (volatility * (0.5 - ((i + 1) % 10) / 10))
        high_price = max(open_price, close_price) + (volatility * 0.3)
        low_price = min(open_price, close_price) - (volatility * 0.3)
        volume = 1000000 + (i * 1000)
        
        candles.append({
            "timestamp": timestamp.isoformat(),
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume
        })
    
    return candles


@pytest.fixture(scope="function")
def sample_strategy_rule() -> Dict[str, Any]:
    """Sample strategy rule for testing."""
    return {
        "id": "test-rule-001",
        "name": "Bullish LE Entry",
        "description": "Enter long on liquidity engineering candle in uptrend",
        "conditions": [
            {
                "timeframe": "5m",
                "indicator": "market_structure",
                "operator": "equals",
                "value": "bullish"
            },
            {
                "timeframe": "1m",
                "indicator": "candle_pattern",
                "operator": "in",
                "value": ["le_candle", "small_wick"]
            }
        ],
        "entry_type": "le_candle",
        "setup_type": "breakout",
        "risk_reward_ratio": 2.0,
        "max_position_size": 0.1,
        "stop_loss_atr_multiplier": 1.5
    }


@pytest.fixture(scope="function")
def sample_pdf_content() -> bytes:
    """Generate sample PDF-like content for ingestion testing."""
    # In reality, this would be actual PDF bytes
    # For testing, we'll use a simple text representation
    content = b"""
    %PDF-1.4
    Trading Strategy Rules:
    1. Entry: Wait for LE candle on 1-minute after HTF bias confirmed
    2. Stop Loss: Place below recent swing low
    3. Take Profit: 2:1 risk-reward ratio
    4. Market Cycle: Only trade in Drive phase
    """
    return content


@pytest.fixture(scope="function")
def mock_hyperliquid_responses() -> Dict[str, Any]:
    """Mock responses from Hyperliquid API."""
    return {
        "get_positions": {
            "positions": [
                {
                    "symbol": "BTC-USD",
                    "side": "long",
                    "size": "0.1",
                    "entry_price": "50000.0",
                    "mark_price": "51000.0",
                    "unrealized_pnl": "100.0",
                    "leverage": "5"
                }
            ]
        },
        "place_order": {
            "order_id": "test-order-123",
            "status": "submitted",
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": "0.1",
            "price": "50000.0"
        },
        "get_market_data": {
            "symbol": "BTC-USD",
            "last_price": "50500.0",
            "bid": "50490.0",
            "ask": "50510.0",
            "volume_24h": "1000000000"
        }
    }


@pytest.fixture(scope="function")
def sample_backtest_config() -> Dict[str, Any]:
    """Sample backtest configuration."""
    return {
        "symbol": "BTC-USD",
        "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
        "end_date": datetime.now().isoformat(),
        "timeframe": "5m",
        "initial_capital": 10000.0,
        "risk_per_trade": 0.02,
        "max_positions": 1,
        "strategy_ids": ["test-strategy-001"],
        "paper_trading": True
    }


@pytest.fixture
def cleanup_test_files():
    """Cleanup temporary files created during tests."""
    test_files = []
    
    yield test_files
    
    # Cleanup after test
    for file_path in test_files:
        if Path(file_path).exists():
            Path(file_path).unlink()


@pytest.fixture(scope="function")
def sample_trades() -> list[Dict[str, Any]]:
    """Generate sample trade history for outcome analysis testing."""
    trades = []
    base_time = datetime.now() - timedelta(days=7)
    
    for i in range(20):
        entry_time = base_time + timedelta(hours=i * 6)
        exit_time = entry_time + timedelta(hours=2)
        
        # Mix of winning and losing trades
        is_winner = i % 3 != 0
        entry_price = 50000.0 + (i * 100)
        exit_price = entry_price + (200 if is_winner else -100)
        
        trades.append({
            "id": f"trade-{i:03d}",
            "symbol": "BTC-USD",
            "side": "long",
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": 0.1,
            "entry_time": entry_time.isoformat(),
            "exit_time": exit_time.isoformat(),
            "pnl": (exit_price - entry_price) * 0.1,
            "pnl_percent": ((exit_price - entry_price) / entry_price) * 100,
            "status": "closed",
            "entry_reason": f"LE candle on 1m, bullish HTF bias",
            "exit_reason": "Take profit hit" if is_winner else "Stop loss hit",
            "strategy_id": "test-strategy-001"
        })
    
    return trades


@pytest.fixture
def mock_openai_client(monkeypatch):
    """Mock OpenAI API client for LLM-based operations."""
    class MockOpenAI:
        def __init__(self, *args, **kwargs):
            pass
        
        async def chat_completions_create(self, *args, **kwargs):
            """Mock chat completion response."""
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "rules": [
                                    {
                                        "name": "Bullish LE Entry",
                                        "conditions": ["HTF bullish", "LE candle on 1m"],
                                        "entry_type": "le_candle",
                                        "risk_reward": 2.0
                                    }
                                ]
                            })
                        }
                    }
                ]
            }
    
    # Monkeypatch the OpenAI client
    # monkeypatch.setattr("openai.AsyncOpenAI", MockOpenAI)
    return MockOpenAI


@pytest.fixture
def performance_metrics():
    """Track performance metrics during E2E tests."""
    metrics = {
        "api_response_times": [],
        "database_query_times": [],
        "websocket_latencies": []
    }
    
    yield metrics
    
    # Optional: Print metrics summary after test
    if metrics["api_response_times"]:
        avg_response = sum(metrics["api_response_times"]) / len(metrics["api_response_times"])
        print(f"\nAverage API response time: {avg_response:.3f}s")
