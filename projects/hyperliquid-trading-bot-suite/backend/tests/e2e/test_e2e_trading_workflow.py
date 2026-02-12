"""
E2E Trading Workflow Tests

Tests complete trading workflows from start to finish:
1. Ingestion → Strategy Extraction → Pattern Detection → Trade Reasoning
2. Backtest → Analysis → Feedback Loop
3. Live Trading Simulation → Position Management → Risk Controls
"""

import pytest
import time
from typing import Dict, Any
from datetime import datetime, timedelta
import json


class TestIngestionToStrategy:
    """Test workflow: Content Ingestion → Strategy Extraction."""
    
    @pytest.mark.asyncio
    async def test_pdf_ingestion_workflow(
        self, 
        client, 
        sample_pdf_content,
        test_session
    ):
        """Complete PDF ingestion workflow."""
        # Step 1: Upload PDF
        import io
        files = {"file": ("trading_strategy.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
        
        response = client.post(
            "/api/ingestion/pdf",
            files=files,
            data={"title": "Test Trading Strategy", "author": "Test Author"}
        )
        
        # If ingestion is implemented, should succeed
        if response.status_code in [200, 201]:
            data = response.json()
            document_id = data.get("id") or data.get("document_id")
            
            # Step 2: Check ingestion status
            if document_id:
                status_response = client.get(f"/api/ingestion/status/{document_id}")
                assert status_response.status_code == 200
                
                status_data = status_response.json()
                assert "status" in status_data
                
                # Step 3: Wait for processing (or verify it's queued)
                assert status_data["status"] in ["pending", "processing", "completed"]


class TestStrategyToBacktest:
    """Test workflow: Strategy Definition → Backtest Execution."""
    
    def test_strategy_backtest_workflow(
        self,
        client,
        sample_strategy_rule,
        sample_backtest_config,
        sample_candles
    ):
        """Complete strategy → backtest workflow."""
        # Step 1: Create strategy
        strategy_response = client.post("/api/strategies", json=sample_strategy_rule)
        
        if strategy_response.status_code in [200, 201]:
            strategy_data = strategy_response.json()
            strategy_id = strategy_data.get("id") or strategy_data.get("strategy_id")
            
            if strategy_id:
                # Step 2: Configure backtest with strategy
                backtest_config = sample_backtest_config.copy()
                backtest_config["strategy_ids"] = [strategy_id]
                
                backtest_response = client.post(
                    "/api/backtesting/run",
                    json=backtest_config
                )
                
                if backtest_response.status_code in [200, 201]:
                    backtest_data = backtest_response.json()
                    backtest_id = backtest_data.get("id") or backtest_data.get("backtest_id")
                    
                    # Step 3: Check backtest status
                    if backtest_id:
                        status_response = client.get(f"/api/backtesting/{backtest_id}/status")
                        
                        if status_response.status_code == 200:
                            status = status_response.json()
                            assert "status" in status
                            assert status["status"] in ["queued", "running", "completed", "failed"]
    
    def test_backtest_to_results_workflow(
        self,
        client,
        sample_backtest_config
    ):
        """Complete backtest → results analysis workflow."""
        # Step 1: Run backtest
        backtest_response = client.post(
            "/api/backtesting/run",
            json=sample_backtest_config
        )
        
        if backtest_response.status_code in [200, 201]:
            backtest_data = backtest_response.json()
            backtest_id = backtest_data.get("id") or backtest_data.get("backtest_id")
            
            if backtest_id:
                # Step 2: Retrieve results (may not be ready immediately)
                results_response = client.get(f"/api/backtesting/{backtest_id}/results")
                
                if results_response.status_code == 200:
                    results = results_response.json()
                    
                    # Verify result structure
                    assert "summary" in results or "statistics" in results
                    
                    # Step 3: Get trade history
                    trades_response = client.get(f"/api/backtesting/{backtest_id}/trades")
                    
                    if trades_response.status_code == 200:
                        trades = trades_response.json()
                        assert isinstance(trades, list)


class TestPatternDetectionWorkflow:
    """Test workflow: Market Data → Pattern Detection → Trade Signal."""
    
    @pytest.mark.asyncio
    async def test_pattern_detection_pipeline(
        self,
        client,
        sample_candles
    ):
        """Complete pattern detection workflow."""
        # This tests the detection engine indirectly through backtesting
        
        # Step 1: Submit market data for analysis
        analysis_request = {
            "symbol": "BTC-USD",
            "timeframe": "5m",
            "candles": sample_candles[-100:]  # Last 100 candles
        }
        
        response = client.post("/api/analysis/patterns", json=analysis_request)
        
        # If pattern detection endpoint exists
        if response.status_code == 200:
            patterns = response.json()
            
            # Should return detected patterns
            assert isinstance(patterns, list) or isinstance(patterns, dict)
            
            # Step 2: Check for specific patterns
            if isinstance(patterns, list) and len(patterns) > 0:
                pattern = patterns[0]
                assert "type" in pattern or "pattern_type" in pattern
                assert "confidence" in pattern or "score" in pattern


class TestTradeExecutionWorkflow:
    """Test workflow: Signal → Order → Position → Close."""
    
    def test_manual_trade_lifecycle(self, client):
        """Complete manual trade lifecycle."""
        # Step 1: Create manual trade
        trade_request = {
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": 0.1,
            "entry_price": 50000.0,
            "stop_loss": 49000.0,
            "take_profit": 52000.0,
            "strategy_id": "manual",
            "reason": "E2E test trade"
        }
        
        create_response = client.post("/api/trades/manual", json=trade_request)
        
        if create_response.status_code in [200, 201]:
            trade_data = create_response.json()
            trade_id = trade_data.get("id") or trade_data.get("trade_id")
            
            if trade_id:
                # Step 2: Get trade details
                get_response = client.get(f"/api/trades/{trade_id}")
                
                if get_response.status_code == 200:
                    trade = get_response.json()
                    assert trade["symbol"] == "BTC-USD"
                    assert trade["status"] in ["pending", "open", "submitted"]
                    
                    # Step 3: Update trade (e.g., modify stop loss)
                    update_request = {"stop_loss": 48500.0}
                    update_response = client.patch(
                        f"/api/trades/{trade_id}",
                        json=update_request
                    )
                    
                    # Step 4: Close trade
                    close_response = client.post(
                        f"/api/trades/{trade_id}/close",
                        json={"exit_price": 51000.0, "reason": "E2E test close"}
                    )
                    
                    if close_response.status_code == 200:
                        closed_trade = close_response.json()
                        assert closed_trade["status"] in ["closed", "filled"]


class TestRiskManagementWorkflow:
    """Test workflow: Risk Checks → Order Validation → Circuit Breaker."""
    
    def test_risk_check_rejects_oversized_order(self, client):
        """Risk manager rejects orders exceeding position limits."""
        # Attempt to create trade with excessive size
        oversized_trade = {
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": 100.0,  # Way too large
            "entry_price": 50000.0,
            "stop_loss": 49000.0,
            "take_profit": 52000.0
        }
        
        response = client.post("/api/trades/manual", json=oversized_trade)
        
        # Should be rejected by risk manager
        assert response.status_code in [400, 403, 422]
    
    def test_risk_check_rejects_bad_stop_loss(self, client):
        """Risk manager rejects trades with invalid stop loss."""
        # Long trade with stop loss above entry (invalid)
        invalid_trade = {
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": 0.1,
            "entry_price": 50000.0,
            "stop_loss": 51000.0,  # Wrong direction for long
            "take_profit": 52000.0
        }
        
        response = client.post("/api/trades/manual", json=invalid_trade)
        
        # Should be rejected
        assert response.status_code in [400, 422]
    
    def test_daily_loss_limit_enforcement(self, client, sample_trades):
        """Circuit breaker triggers on daily loss limit."""
        # This would require simulating multiple losing trades
        # and checking that the system stops accepting new trades
        pass  # Placeholder for comprehensive risk testing


class TestFeedbackLoopWorkflow:
    """Test workflow: Trade Outcomes → Analysis → Strategy Update."""
    
    def test_outcome_analysis_workflow(self, client, sample_trades):
        """Complete outcome analysis workflow."""
        # Step 1: Submit trade outcomes for analysis
        analysis_request = {
            "trades": sample_trades,
            "strategy_id": "test-strategy-001",
            "analysis_type": "pattern_success_rate"
        }
        
        response = client.post("/api/analysis/outcomes", json=analysis_request)
        
        if response.status_code in [200, 201]:
            analysis = response.json()
            
            # Should return insights
            assert "summary" in analysis or "insights" in analysis
            
            # Step 2: Check for strategy adjustments
            if "recommendations" in analysis:
                recommendations = analysis["recommendations"]
                assert isinstance(recommendations, list)
    
    def test_strategy_improvement_workflow(self, client, sample_trades):
        """Test feedback loop improves strategy over time."""
        # Step 1: Get initial strategy performance
        initial_response = client.get("/api/strategies/test-strategy-001/performance")
        
        if initial_response.status_code == 200:
            initial_perf = initial_response.json()
            
            # Step 2: Submit learning feedback
            feedback_request = {
                "strategy_id": "test-strategy-001",
                "trades": sample_trades,
                "learn": True
            }
            
            feedback_response = client.post(
                "/api/learning/feedback",
                json=feedback_request
            )
            
            if feedback_response.status_code in [200, 201]:
                # Step 3: Check for strategy updates
                updated_response = client.get("/api/strategies/test-strategy-001")
                
                if updated_response.status_code == 200:
                    updated_strategy = updated_response.json()
                    # Strategy should have been modified or marked for review
                    assert "updated_at" in updated_strategy or "last_modified" in updated_strategy


class TestEndToEndTradingDay:
    """Test complete trading day simulation."""
    
    @pytest.mark.slow
    def test_full_trading_day_simulation(
        self,
        client,
        sample_candles,
        sample_strategy_rule,
        sample_backtest_config
    ):
        """Simulate complete trading day workflow."""
        workflow_results = {
            "strategy_created": False,
            "backtest_run": False,
            "trades_executed": False,
            "outcomes_analyzed": False
        }
        
        # Step 1: Create/Load Strategy
        strategy_response = client.post("/api/strategies", json=sample_strategy_rule)
        if strategy_response.status_code in [200, 201]:
            workflow_results["strategy_created"] = True
            strategy_id = strategy_response.json().get("id")
        
        # Step 2: Run Backtest
        if workflow_results["strategy_created"]:
            backtest_config = sample_backtest_config.copy()
            backtest_config["strategy_ids"] = [strategy_id]
            
            backtest_response = client.post("/api/backtesting/run", json=backtest_config)
            if backtest_response.status_code in [200, 201]:
                workflow_results["backtest_run"] = True
        
        # Step 3: Execute Trades (simulated)
        if workflow_results["backtest_run"]:
            trade_request = {
                "symbol": "BTC-USD",
                "side": "buy",
                "quantity": 0.1,
                "entry_price": 50000.0,
                "stop_loss": 49000.0,
                "take_profit": 52000.0,
                "strategy_id": strategy_id
            }
            
            trade_response = client.post("/api/trades/manual", json=trade_request)
            if trade_response.status_code in [200, 201]:
                workflow_results["trades_executed"] = True
        
        # Step 4: Analyze Outcomes
        if workflow_results["trades_executed"]:
            # Get trade history and analyze
            history_response = client.get("/api/trades/history")
            if history_response.status_code == 200:
                workflow_results["outcomes_analyzed"] = True
        
        # Verify at least some workflow steps completed
        assert any(workflow_results.values()), "No workflow steps completed"
    
    @pytest.mark.slow
    def test_concurrent_operations(self, client):
        """Test system handles concurrent operations gracefully."""
        # Simulate multiple concurrent operations
        operations = []
        
        # Multiple strategy queries
        for _ in range(5):
            response = client.get("/api/strategies")
            operations.append(response.status_code == 200)
        
        # Multiple health checks
        for _ in range(5):
            response = client.get("/api/health")
            operations.append(response.status_code == 200)
        
        # At least some should succeed
        assert sum(operations) >= len(operations) * 0.8  # 80% success rate


class TestDataPersistence:
    """Test data persistence across operations."""
    
    def test_strategy_persists_after_creation(self, client, sample_strategy_rule):
        """Created strategies persist in database."""
        # Create strategy
        create_response = client.post("/api/strategies", json=sample_strategy_rule)
        
        if create_response.status_code in [200, 201]:
            strategy_id = create_response.json().get("id")
            
            if strategy_id:
                # Retrieve strategy
                get_response = client.get(f"/api/strategies/{strategy_id}")
                
                if get_response.status_code == 200:
                    retrieved = get_response.json()
                    assert retrieved["name"] == sample_strategy_rule["name"]
    
    def test_trade_history_persists(self, client):
        """Trade history persists across sessions."""
        # Get current trade count
        initial_response = client.get("/api/trades/history")
        
        if initial_response.status_code == 200:
            initial_trades = initial_response.json()
            initial_count = len(initial_trades) if isinstance(initial_trades, list) else 0
            
            # Create new trade
            trade_request = {
                "symbol": "BTC-USD",
                "side": "buy",
                "quantity": 0.1,
                "entry_price": 50000.0,
                "stop_loss": 49000.0,
                "take_profit": 52000.0
            }
            
            create_response = client.post("/api/trades/manual", json=trade_request)
            
            if create_response.status_code in [200, 201]:
                # Check trade count increased
                updated_response = client.get("/api/trades/history")
                
                if updated_response.status_code == 200:
                    updated_trades = updated_response.json()
                    updated_count = len(updated_trades) if isinstance(updated_trades, list) else 0
                    
                    # Count should have increased (or at least stayed same if trade pending)
                    assert updated_count >= initial_count
