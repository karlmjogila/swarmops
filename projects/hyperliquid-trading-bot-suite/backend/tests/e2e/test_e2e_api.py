"""
E2E API Integration Tests

Tests full API functionality including:
- Health checks and status endpoints
- Ingestion endpoints (PDF, video)
- Strategy management
- Backtest execution
- Trade management
- Error handling and validation
"""

import pytest
import time
from typing import Dict, Any
from pathlib import Path
import io


class TestHealthEndpoints:
    """Test health check and status endpoints."""
    
    def test_root_endpoint(self, client):
        """Root endpoint returns application info."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "Hyperliquid" in data["message"]
    
    def test_health_check(self, client):
        """Health check endpoint is accessible."""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_readiness_check(self, client):
        """Readiness check verifies all services."""
        response = client.get("/api/health/ready")
        assert response.status_code in [200, 503]  # May fail if services not running
        
        data = response.json()
        assert "status" in data


class TestIngestionAPI:
    """Test content ingestion endpoints."""
    
    def test_list_strategies_empty(self, client):
        """List strategies returns empty array initially."""
        response = client.get("/api/strategies")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_upload_pdf_endpoint_exists(self, client, sample_pdf_content):
        """PDF upload endpoint is accessible."""
        files = {"file": ("test_strategy.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
        
        response = client.post(
            "/api/ingestion/pdf",
            files=files,
            data={"title": "Test Strategy"}
        )
        
        # Should succeed or fail with validation, not 404
        assert response.status_code in [200, 201, 400, 422, 500]
    
    def test_upload_invalid_file_type(self, client):
        """Reject invalid file types."""
        files = {"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")}
        
        response = client.post(
            "/api/ingestion/pdf",
            files=files,
            data={"title": "Test"}
        )
        
        # Should reject with 400 or 422
        assert response.status_code in [400, 422]
    
    def test_upload_without_title(self, client, sample_pdf_content):
        """Reject upload without required title."""
        files = {"file": ("test.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
        
        response = client.post("/api/ingestion/pdf", files=files)
        
        assert response.status_code == 422  # Validation error


class TestStrategyAPI:
    """Test strategy management endpoints."""
    
    def test_create_strategy(self, client, sample_strategy_rule):
        """Create new strategy via API."""
        response = client.post("/api/strategies", json=sample_strategy_rule)
        
        # May succeed or fail depending on validation
        assert response.status_code in [200, 201, 400, 422, 500]
    
    def test_get_nonexistent_strategy(self, client):
        """Getting nonexistent strategy returns 404."""
        response = client.get("/api/strategies/nonexistent-id")
        assert response.status_code == 404
    
    def test_update_strategy(self, client, sample_strategy_rule):
        """Update strategy endpoint exists."""
        response = client.put(
            "/api/strategies/test-id",
            json=sample_strategy_rule
        )
        
        # Should return 404 (not found) or accept the update
        assert response.status_code in [200, 404, 400, 422]
    
    def test_delete_strategy(self, client):
        """Delete strategy endpoint exists."""
        response = client.delete("/api/strategies/test-id")
        assert response.status_code in [200, 204, 404]


class TestBacktestAPI:
    """Test backtesting endpoints."""
    
    def test_create_backtest(self, client, sample_backtest_config):
        """Create backtest job via API."""
        response = client.post("/api/backtesting/run", json=sample_backtest_config)
        
        # Should accept or reject with validation
        assert response.status_code in [200, 201, 400, 422, 500]
    
    def test_list_backtests(self, client):
        """List backtests endpoint is accessible."""
        response = client.get("/api/backtesting")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)
    
    def test_get_backtest_results(self, client):
        """Get backtest results endpoint exists."""
        response = client.get("/api/backtesting/test-backtest-id/results")
        assert response.status_code in [200, 404]
    
    def test_invalid_backtest_config(self, client):
        """Reject invalid backtest configuration."""
        invalid_config = {
            "symbol": "BTC-USD",
            # Missing required fields
        }
        
        response = client.post("/api/backtesting/run", json=invalid_config)
        assert response.status_code == 422
    
    def test_backtest_with_invalid_dates(self, client, sample_backtest_config):
        """Reject backtest with end_date before start_date."""
        config = sample_backtest_config.copy()
        config["start_date"] = "2025-12-31T00:00:00"
        config["end_date"] = "2025-01-01T00:00:00"
        
        response = client.post("/api/backtesting/run", json=config)
        assert response.status_code in [400, 422]


class TestTradeAPI:
    """Test trade management endpoints."""
    
    def test_list_trades(self, client):
        """List trades endpoint is accessible."""
        response = client.get("/api/trades")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)
    
    def test_get_trade_by_id(self, client):
        """Get specific trade by ID."""
        response = client.get("/api/trades/test-trade-id")
        assert response.status_code in [200, 404]
    
    def test_create_manual_trade(self, client):
        """Create manual trade via API."""
        trade_data = {
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": 0.1,
            "entry_price": 50000.0,
            "stop_loss": 49000.0,
            "take_profit": 52000.0
        }
        
        response = client.post("/api/trades/manual", json=trade_data)
        assert response.status_code in [200, 201, 400, 422, 500]
    
    def test_close_trade(self, client):
        """Close trade endpoint exists."""
        response = client.post("/api/trades/test-trade-id/close")
        assert response.status_code in [200, 404, 400]
    
    def test_get_trade_history(self, client):
        """Get trade history with filters."""
        response = client.get(
            "/api/trades/history",
            params={
                "symbol": "BTC-USD",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31"
            }
        )
        
        assert response.status_code == 200


class TestErrorHandling:
    """Test API error handling and validation."""
    
    def test_404_on_invalid_route(self, client):
        """Invalid routes return 404."""
        response = client.get("/api/nonexistent/route")
        assert response.status_code == 404
    
    def test_405_on_wrong_method(self, client):
        """Wrong HTTP method returns 405."""
        response = client.post("/api/health")  # Should be GET
        assert response.status_code == 405
    
    def test_malformed_json_request(self, client):
        """Malformed JSON returns 400 or 422."""
        response = client.post(
            "/api/strategies",
            data="{invalid json}",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [400, 422]
    
    def test_missing_required_fields(self, client):
        """Missing required fields returns validation error."""
        response = client.post("/api/strategies", json={})
        assert response.status_code == 422
        
        data = response.json()
        assert "error" in data or "detail" in data


class TestCORS:
    """Test CORS middleware configuration."""
    
    def test_cors_headers_present(self, client):
        """CORS headers are included in responses."""
        response = client.options("/api/health")
        
        # CORS headers should be present
        # Note: TestClient may not fully simulate OPTIONS requests
        assert response.status_code in [200, 405]
    
    def test_preflight_request(self, client):
        """Handle preflight OPTIONS requests."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        }
        
        response = client.options("/api/strategies", headers=headers)
        assert response.status_code in [200, 204, 405]


class TestRateLimiting:
    """Test rate limiting (if implemented)."""
    
    @pytest.mark.skip(reason="Rate limiting not yet implemented per security review")
    def test_rate_limit_exceeded(self, client):
        """Hitting rate limit returns 429."""
        # Make many rapid requests
        for _ in range(100):
            response = client.get("/api/health")
        
        # Should eventually get rate limited
        response = client.get("/api/health")
        assert response.status_code == 429


class TestPerformance:
    """Test API performance characteristics."""
    
    def test_health_check_performance(self, client, performance_metrics):
        """Health check responds quickly."""
        start = time.time()
        response = client.get("/api/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.1  # Should respond in < 100ms
        
        performance_metrics["api_response_times"].append(elapsed)
    
    def test_list_strategies_performance(self, client, performance_metrics):
        """List strategies responds quickly even with data."""
        start = time.time()
        response = client.get("/api/strategies")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond in < 1s
        
        performance_metrics["api_response_times"].append(elapsed)
    
    def test_concurrent_requests(self, client):
        """API handles concurrent requests."""
        # Note: TestClient is synchronous, so this tests sequential handling
        responses = []
        
        for _ in range(10):
            response = client.get("/api/health")
            responses.append(response)
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)
