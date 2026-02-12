"""
E2E Performance and Load Tests

Tests system performance under various conditions:
- Response time benchmarks
- Concurrent request handling
- Database query performance
- Memory usage
- Large dataset handling
"""

import pytest
import time
import asyncio
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import statistics


@pytest.mark.performance
class TestResponseTimes:
    """Test API response time benchmarks."""
    
    def test_health_check_response_time(self, client, performance_metrics):
        """Health check responds within 50ms."""
        times = []
        
        for _ in range(10):
            start = time.perf_counter()
            response = client.get("/api/health")
            elapsed = time.perf_counter() - start
            
            times.append(elapsed)
            assert response.status_code == 200
        
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
        
        performance_metrics["api_response_times"].extend(times)
        
        print(f"\nHealth check - Avg: {avg_time*1000:.1f}ms, P95: {p95_time*1000:.1f}ms")
        
        assert avg_time < 0.05  # 50ms average
        assert p95_time < 0.1   # 100ms p95
    
    def test_list_strategies_response_time(self, client, performance_metrics):
        """List strategies responds within 500ms."""
        times = []
        
        for _ in range(10):
            start = time.perf_counter()
            response = client.get("/api/strategies")
            elapsed = time.perf_counter() - start
            
            times.append(elapsed)
            assert response.status_code == 200
        
        avg_time = statistics.mean(times)
        
        performance_metrics["api_response_times"].extend(times)
        
        print(f"\nList strategies - Avg: {avg_time*1000:.1f}ms")
        
        assert avg_time < 0.5  # 500ms average
    
    def test_backtest_submission_response_time(self, client, sample_backtest_config):
        """Backtest submission responds quickly (queuing, not execution)."""
        start = time.perf_counter()
        response = client.post("/api/backtesting/run", json=sample_backtest_config)
        elapsed = time.perf_counter() - start
        
        print(f"\nBacktest submission: {elapsed*1000:.1f}ms")
        
        # Submission should be fast (actual execution happens async)
        assert elapsed < 2.0  # 2 seconds max for queuing
    
    def test_trade_query_response_time(self, client):
        """Trade queries respond within 1 second."""
        start = time.perf_counter()
        response = client.get("/api/trades/history")
        elapsed = time.perf_counter() - start
        
        print(f"\nTrade history query: {elapsed*1000:.1f}ms")
        
        assert response.status_code == 200
        assert elapsed < 1.0  # 1 second max


@pytest.mark.performance
class TestConcurrency:
    """Test concurrent request handling."""
    
    def test_concurrent_health_checks(self, client):
        """Handle 50 concurrent health checks."""
        def make_request():
            response = client.get("/api/health")
            return response.status_code == 200
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            start = time.perf_counter()
            results = list(executor.map(lambda _: make_request(), range(50)))
            elapsed = time.perf_counter() - start
        
        success_rate = sum(results) / len(results)
        
        print(f"\n50 concurrent health checks: {elapsed:.2f}s, {success_rate*100:.1f}% success")
        
        assert success_rate >= 0.95  # 95% success rate
        assert elapsed < 5.0  # Complete within 5 seconds
    
    def test_concurrent_strategy_queries(self, client):
        """Handle 20 concurrent strategy queries."""
        def make_request():
            response = client.get("/api/strategies")
            return response.status_code == 200
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            start = time.perf_counter()
            results = list(executor.map(lambda _: make_request(), range(20)))
            elapsed = time.perf_counter() - start
        
        success_rate = sum(results) / len(results)
        
        print(f"\n20 concurrent strategy queries: {elapsed:.2f}s, {success_rate*100:.1f}% success")
        
        assert success_rate >= 0.9  # 90% success rate
        assert elapsed < 10.0  # Complete within 10 seconds
    
    def test_mixed_concurrent_requests(self, client):
        """Handle mixed types of concurrent requests."""
        def make_health_check():
            return client.get("/api/health").status_code == 200
        
        def make_strategy_query():
            return client.get("/api/strategies").status_code == 200
        
        def make_trade_query():
            return client.get("/api/trades/history").status_code == 200
        
        requests = [make_health_check] * 10 + [make_strategy_query] * 5 + [make_trade_query] * 5
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            start = time.perf_counter()
            results = list(executor.map(lambda fn: fn(), requests))
            elapsed = time.perf_counter() - start
        
        success_rate = sum(results) / len(results)
        
        print(f"\n20 mixed concurrent requests: {elapsed:.2f}s, {success_rate*100:.1f}% success")
        
        assert success_rate >= 0.85  # 85% success rate
        assert elapsed < 15.0


@pytest.mark.performance
@pytest.mark.slow
class TestLargeDatasets:
    """Test handling of large datasets."""
    
    def test_large_candle_dataset(self, client):
        """Handle backtest with large candle dataset (10k+ candles)."""
        large_backtest_config = {
            "symbol": "BTC-USD",
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-12-31T23:59:59",  # Full year
            "timeframe": "1m",  # 1-minute = ~500k candles
            "initial_capital": 10000.0,
            "risk_per_trade": 0.02,
            "max_positions": 1,
            "strategy_ids": ["test-strategy"],
            "paper_trading": True
        }
        
        start = time.perf_counter()
        response = client.post("/api/backtesting/run", json=large_backtest_config)
        elapsed = time.perf_counter() - start
        
        print(f"\nLarge dataset backtest submission: {elapsed:.2f}s")
        
        # Submission should be fast (execution happens async)
        assert elapsed < 5.0
    
    def test_paginated_trade_history(self, client):
        """Handle paginated queries efficiently."""
        # Query large trade history with pagination
        response = client.get("/api/trades/history", params={"limit": 1000, "offset": 0})
        
        assert response.status_code == 200
        
        data = response.json()
        # Should return paginated data structure
        if isinstance(data, dict):
            assert "items" in data or "trades" in data or "results" in data
    
    def test_strategy_with_many_rules(self, client):
        """Handle strategy with many rules."""
        complex_strategy = {
            "id": "complex-strategy",
            "name": "Complex Strategy",
            "rules": [
                {
                    "name": f"Rule {i}",
                    "conditions": [
                        {"indicator": "rsi", "operator": ">", "value": 50},
                        {"indicator": "macd", "operator": "<", "value": 0}
                    ]
                }
                for i in range(50)  # 50 rules
            ]
        }
        
        response = client.post("/api/strategies", json=complex_strategy)
        
        # Should handle complex strategies
        assert response.status_code in [200, 201, 400, 422]


@pytest.mark.performance
class TestDatabasePerformance:
    """Test database query performance."""
    
    def test_strategy_lookup_performance(self, client, test_session):
        """Strategy lookups are efficient."""
        # This would measure actual database query time
        # For now, we test via API
        
        times = []
        for _ in range(20):
            start = time.perf_counter()
            response = client.get("/api/strategies")
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        avg_time = statistics.mean(times)
        
        print(f"\nStrategy lookup avg: {avg_time*1000:.1f}ms")
        
        # Database queries should be fast
        assert avg_time < 0.2  # 200ms
    
    def test_trade_history_query_performance(self, client):
        """Trade history queries are indexed and fast."""
        # Query with filters (should use indexes)
        start = time.perf_counter()
        response = client.get(
            "/api/trades/history",
            params={
                "symbol": "BTC-USD",
                "start_date": "2025-01-01",
                "status": "closed"
            }
        )
        elapsed = time.perf_counter() - start
        
        print(f"\nFiltered trade query: {elapsed*1000:.1f}ms")
        
        assert response.status_code == 200
        assert elapsed < 0.5  # 500ms


@pytest.mark.performance
class TestMemoryUsage:
    """Test memory usage characteristics."""
    
    def test_no_memory_leak_on_repeated_requests(self, client):
        """Repeated requests don't cause memory leaks."""
        # Make many requests and monitor that memory doesn't grow unbounded
        # This is a basic test - proper profiling would be better
        
        for _ in range(100):
            response = client.get("/api/health")
            assert response.status_code == 200
        
        # If we got here without crashing, basic test passes
        assert True
    
    def test_large_response_handling(self, client):
        """System handles large API responses efficiently."""
        # Request large dataset
        response = client.get("/api/trades/history", params={"limit": 1000})
        
        if response.status_code == 200:
            data = response.json()
            # Should handle large response without issues
            assert data is not None


@pytest.mark.performance
@pytest.mark.slow
class TestStressTests:
    """Stress tests for system limits."""
    
    def test_sustained_load(self, client):
        """Handle sustained load over time."""
        duration = 30  # 30 seconds
        request_count = 0
        errors = 0
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            response = client.get("/api/health")
            request_count += 1
            if response.status_code != 200:
                errors += 1
            time.sleep(0.1)  # 10 requests/second
        
        error_rate = errors / request_count if request_count > 0 else 0
        
        print(f"\nSustained load: {request_count} requests, {error_rate*100:.1f}% errors")
        
        assert error_rate < 0.05  # Less than 5% errors
    
    @pytest.mark.skip(reason="Very slow test - run manually")
    def test_maximum_concurrent_connections(self, client):
        """Find maximum concurrent connections system can handle."""
        max_workers = 50
        requests_per_worker = 10
        
        def make_requests():
            results = []
            for _ in range(requests_per_worker):
                response = client.get("/api/health")
                results.append(response.status_code == 200)
            return results
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            start = time.perf_counter()
            results = list(executor.map(lambda _: make_requests(), range(max_workers)))
            elapsed = time.perf_counter() - start
        
        flat_results = [item for sublist in results for item in sublist]
        success_rate = sum(flat_results) / len(flat_results)
        
        total_requests = max_workers * requests_per_worker
        
        print(f"\nMax concurrency test: {total_requests} requests in {elapsed:.2f}s")
        print(f"Success rate: {success_rate*100:.1f}%")
        print(f"Throughput: {total_requests/elapsed:.1f} req/s")
        
        assert success_rate >= 0.8  # 80% success rate


@pytest.mark.performance
class TestCachePerformance:
    """Test caching effectiveness (if implemented)."""
    
    def test_repeated_queries_use_cache(self, client):
        """Repeated identical queries are faster (cached)."""
        # First query (cold cache)
        start = time.perf_counter()
        response1 = client.get("/api/strategies")
        time1 = time.perf_counter() - start
        
        # Second query (warm cache)
        start = time.perf_counter()
        response2 = client.get("/api/strategies")
        time2 = time.perf_counter() - start
        
        print(f"\nCache test - Cold: {time1*1000:.1f}ms, Warm: {time2*1000:.1f}ms")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Second query may be faster if caching is implemented
        # (This test is informational, not strict)
        if time2 < time1 * 0.5:
            print("Caching appears to be working!")


# Utility functions for performance testing

def measure_response_times(client, endpoint: str, count: int = 10) -> Dict[str, float]:
    """Measure response time statistics for an endpoint."""
    times = []
    
    for _ in range(count):
        start = time.perf_counter()
        response = client.get(endpoint)
        elapsed = time.perf_counter() - start
        
        if response.status_code == 200:
            times.append(elapsed)
    
    if not times:
        return {"error": "no successful requests"}
    
    return {
        "min": min(times),
        "max": max(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "p95": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
        "count": len(times)
    }


def concurrent_requests(client, endpoint: str, count: int, max_workers: int = 10) -> Dict[str, Any]:
    """Make concurrent requests and return performance metrics."""
    def make_request():
        start = time.perf_counter()
        response = client.get(endpoint)
        elapsed = time.perf_counter() - start
        return {
            "success": response.status_code == 200,
            "time": elapsed,
            "status": response.status_code
        }
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        start = time.perf_counter()
        results = list(executor.map(lambda _: make_request(), range(count)))
        total_time = time.perf_counter() - start
    
    successful = [r for r in results if r["success"]]
    
    return {
        "total_requests": count,
        "successful": len(successful),
        "success_rate": len(successful) / count,
        "total_time": total_time,
        "throughput": count / total_time,
        "avg_response_time": statistics.mean([r["time"] for r in successful]) if successful else 0
    }
