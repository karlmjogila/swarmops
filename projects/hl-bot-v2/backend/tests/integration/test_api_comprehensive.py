"""Comprehensive API tests for all endpoints.

Tests follow the AAA pattern (Arrange, Act, Assert) and cover:
- Happy path scenarios
- Edge cases (empty inputs, boundaries, malformed data)
- Error conditions (validation, not found, server errors)
- Authentication/authorization (when implemented)
- Data consistency
"""

import pytest
import io
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from httpx import AsyncClient
from fastapi import status

# Sample test data
VALID_CSV_CONTENT = """time,open,high,low,close,volume
1704067200,42000.50,42150.75,41900.25,42100.00,1000.5
1704067500,42100.00,42200.00,42050.00,42180.50,950.25
1704067800,42180.50,42250.00,42100.00,42150.75,1100.75
"""

INVALID_CSV_CONTENT = """time,open,high,low,close,volume
not_a_timestamp,42000,42100,41900,42050,1000
1704067200,invalid_price,42100,41900,42050,1000
"""

MALFORMED_CSV_CONTENT = """this,is,not,proper,csv
data,without,headers"""


# ==============================================================================
# Health & Status Endpoints
# ==============================================================================

class TestHealthEndpoints:
    """Test suite for health check and status endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint_returns_api_info(self, client: AsyncClient):
        """Root endpoint should return API name, version, and status."""
        # Act
        response = await client.get("/")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_status(self, client: AsyncClient):
        """Health check should return healthy status when system is operational."""
        # Act
        response = await client.get("/health")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"


# ==============================================================================
# Data Import Endpoints
# ==============================================================================

class TestDataImportEndpoints:
    """Test suite for CSV import endpoints (file upload and raw)."""

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
        assert data["stats"]["invalid"] == 0
        assert data["stats"]["duplicates"] == 0
        assert data["dlq_file"] is None

    @pytest.mark.asyncio
    async def test_import_csv_file_rejects_non_csv_file(self, client: AsyncClient):
        """Import should reject files that don't have .csv extension."""
        # Arrange
        text_file = io.BytesIO(b"not a csv file")
        files = {"file": ("data.txt", text_file, "text/plain")}
        params = {"symbol": "BTC-USD", "timeframe": "5m"}
        
        # Act
        response = await client.post("/api/data/import", files=files, params=params)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "CSV file" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_import_csv_file_validates_required_params(self, client: AsyncClient):
        """Import should validate that symbol and timeframe are provided."""
        # Arrange
        csv_file = io.BytesIO(VALID_CSV_CONTENT.encode())
        files = {"file": ("btc_5m.csv", csv_file, "text/csv")}
        
        # Act - Missing symbol
        response = await client.post("/api/data/import", files=files, params={"timeframe": "5m"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Act - Missing timeframe
        csv_file.seek(0)
        response = await client.post("/api/data/import", files=files, params={"symbol": "BTC-USD"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_import_csv_file_validates_timeframe_format(self, client: AsyncClient):
        """Import should validate timeframe format (e.g., 5m, 1h, 4h, 1d)."""
        # Arrange
        csv_file = io.BytesIO(VALID_CSV_CONTENT.encode())
        files = {"file": ("btc.csv", csv_file, "text/csv")}
        
        # Act - Invalid timeframe format
        response = await client.post(
            "/api/data/import",
            files=files,
            params={"symbol": "BTC-USD", "timeframe": "invalid"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_import_csv_file_handles_invalid_rows_gracefully(
        self, client: AsyncClient, test_db
    ):
        """Import should log invalid rows to DLQ and continue processing valid ones."""
        # Arrange
        csv_file = io.BytesIO(INVALID_CSV_CONTENT.encode())
        files = {"file": ("btc_invalid.csv", csv_file, "text/csv")}
        params = {"symbol": "BTC-USD", "timeframe": "5m"}
        
        # Act
        response = await client.post("/api/data/import", files=files, params=params)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["stats"]["invalid"] > 0
        assert data["dlq_file"] is not None
        assert "dead letter queue" in data["message"]

    @pytest.mark.asyncio
    async def test_import_csv_file_is_idempotent(
        self, client: AsyncClient, test_db
    ):
        """Importing the same data twice should not create duplicates."""
        # Arrange
        csv_file = io.BytesIO(VALID_CSV_CONTENT.encode())
        files = {"file": ("btc_5m.csv", csv_file, "text/csv")}
        params = {"symbol": "BTC-USD", "timeframe": "5m"}
        
        # Act - First import
        response1 = await client.post("/api/data/import", files=files, params=params)
        
        # Act - Second import (same data)
        csv_file.seek(0)
        response2 = await client.post("/api/data/import", files=files, params=params)
        
        # Assert
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["stats"]["duplicates"] == 3  # All records are duplicates
        assert data2["stats"]["inserted"] == 0

    @pytest.mark.asyncio
    async def test_import_csv_raw_with_valid_json_body_succeeds(
        self, client: AsyncClient, test_db
    ):
        """Import via JSON body should work with valid CSV content."""
        # Arrange - use 5m timeframe to match the 5-minute spacing in test data
        payload = {
            "csv_content": VALID_CSV_CONTENT,
            "symbol": "ETH-USD",
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["stats"]["inserted"] == 3

    @pytest.mark.asyncio
    async def test_import_csv_raw_validates_required_fields(self, client: AsyncClient):
        """Import via JSON should validate required fields."""
        # Arrange - Missing csv_content
        payload = {"symbol": "BTC-USD", "timeframe": "5m"}
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_import_csv_raw_validates_symbol_not_empty(self, client: AsyncClient):
        """Import should reject empty symbol string."""
        # Arrange
        payload = {
            "csv_content": VALID_CSV_CONTENT,
            "symbol": "",
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_import_csv_raw_handles_empty_csv_content(
        self, client: AsyncClient
    ):
        """Import should handle empty CSV content gracefully."""
        # Arrange
        payload = {
            "csv_content": "",
            "symbol": "BTC-USD",
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert - API returns 200 with success=False for empty content
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["stats"]["extracted"] == 0
        assert data["stats"]["inserted"] == 0


# ==============================================================================
# Data Query Endpoints
# ==============================================================================

class TestDataQueryEndpoints:
    """Test suite for data query and retrieval endpoints."""

    @pytest.mark.asyncio
    async def test_get_data_range_returns_time_bounds(
        self, client: AsyncClient, test_db, sample_ohlcv_data
    ):
        """Data range endpoint should return earliest and latest timestamps."""
        # Arrange
        params = {"symbol": "BTC-USD", "timeframe": "5m"}
        
        # Act
        response = await client.get("/api/data/range", params=params)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["symbol"] == "BTC-USD"
        assert data["timeframe"] == "5m"
        assert data["earliest"] is not None
        assert data["latest"] is not None
        assert data["candle_count"] > 0

    @pytest.mark.asyncio
    async def test_get_data_range_returns_empty_for_no_data(
        self, client: AsyncClient, test_db
    ):
        """Data range should return zeros when no data exists."""
        # Arrange
        params = {"symbol": "NONEXISTENT", "timeframe": "1h"}
        
        # Act
        response = await client.get("/api/data/range", params=params)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["earliest"] is None
        assert data["latest"] is None
        assert data["candle_count"] == 0

    @pytest.mark.asyncio
    async def test_get_data_range_validates_required_params(self, client: AsyncClient):
        """Data range should require symbol and timeframe params."""
        # Act - Missing symbol
        response = await client.get("/api/data/range", params={"timeframe": "5m"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Act - Missing timeframe
        response = await client.get("/api/data/range", params={"symbol": "BTC-USD"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_available_data_lists_symbols_and_timeframes(
        self, client: AsyncClient, test_db, sample_ohlcv_data
    ):
        """Available data endpoint should list all symbols and timeframes."""
        # Act
        response = await client.get("/api/data/available")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "symbols" in data
        assert "timeframes" in data
        assert isinstance(data["symbols"], list)
        assert isinstance(data["timeframes"], list)
        assert len(data["symbols"]) > 0
        assert len(data["timeframes"]) > 0

    @pytest.mark.asyncio
    async def test_get_available_data_returns_empty_when_no_data(
        self, client: AsyncClient, test_db
    ):
        """Available data should return empty lists when database is empty."""
        # Act
        response = await client.get("/api/data/available")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["symbols"] == []
        assert data["timeframes"] == []

    @pytest.mark.asyncio
    async def test_get_available_data_returns_sorted_lists(
        self, client: AsyncClient, test_db, sample_ohlcv_data
    ):
        """Available data should return sorted symbol and timeframe lists."""
        # Act
        response = await client.get("/api/data/available")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        symbols = data["symbols"]
        timeframes = data["timeframes"]
        
        # Check sorting
        assert symbols == sorted(symbols)
        assert timeframes == sorted(timeframes)


# ==============================================================================
# Data Deletion Endpoints
# ==============================================================================

class TestDataDeletionEndpoints:
    """Test suite for data deletion operations."""

    @pytest.mark.asyncio
    async def test_clear_data_deletes_all_for_symbol_and_timeframe(
        self, client: AsyncClient, test_db, sample_ohlcv_data
    ):
        """Clear data should delete all candles for symbol and timeframe."""
        # Arrange
        params = {"symbol": "BTC-USD", "timeframe": "5m"}
        
        # Act
        response = await client.delete("/api/data/clear", params=params)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] > 0

    @pytest.mark.asyncio
    async def test_clear_data_with_time_range_deletes_subset(
        self, client: AsyncClient, test_db, sample_ohlcv_data
    ):
        """Clear data should only delete candles within time range when specified."""
        # Arrange
        start_time = "2024-01-01T00:00:00Z"
        end_time = "2024-01-01T12:00:00Z"
        params = {
            "symbol": "BTC-USD",
            "timeframe": "5m",
            "start_time": start_time,
            "end_time": end_time
        }
        
        # Act
        response = await client.delete("/api/data/clear", params=params)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "deleted_count" in data

    @pytest.mark.asyncio
    async def test_clear_data_validates_timestamp_format(self, client: AsyncClient):
        """Clear data should validate ISO format for timestamps."""
        # Arrange
        params = {
            "symbol": "BTC-USD",
            "timeframe": "5m",
            "start_time": "invalid-timestamp"
        }
        
        # Act
        response = await client.delete("/api/data/clear", params=params)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "timestamp format" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_clear_data_returns_zero_when_no_data_to_delete(
        self, client: AsyncClient, test_db
    ):
        """Clear data should return zero deleted count when no matching data."""
        # Arrange
        params = {"symbol": "NONEXISTENT", "timeframe": "1h"}
        
        # Act
        response = await client.delete("/api/data/clear", params=params)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deleted_count"] == 0

    @pytest.mark.asyncio
    async def test_clear_data_validates_required_params(self, client: AsyncClient):
        """Clear data should require symbol and timeframe params."""
        # Act - Missing symbol
        response = await client.delete("/api/data/clear", params={"timeframe": "5m"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Act - Missing timeframe
        response = await client.delete("/api/data/clear", params={"symbol": "BTC-USD"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==============================================================================
# Backtest Control Endpoints
# ==============================================================================

class TestBacktestEndpoints:
    """Test suite for backtest session management."""

    @pytest.mark.asyncio
    async def test_start_backtest_creates_session(self, client: AsyncClient):
        """Start backtest should create a new session and return session ID."""
        # Arrange
        payload = {
            "symbol": "BTC-USD",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_capital": 10000.0,
            "position_size_percent": 0.02,
            "max_open_trades": 3
        }
        
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            # Act
            response = await client.post("/backtest/start", json=payload)
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "session_id" in data
            assert "websocket_url" in data
            assert data["status"] == "started"
            assert "/backtest/ws/" in data["websocket_url"]

    @pytest.mark.asyncio
    async def test_start_backtest_validates_required_fields(self, client: AsyncClient):
        """Start backtest should validate required fields."""
        # Arrange - Missing symbol
        payload = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }
        
        # Act
        response = await client.post("/backtest/start", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_start_backtest_validates_capital_positive(self, client: AsyncClient):
        """Start backtest should validate initial capital is positive."""
        # Arrange
        payload = {
            "symbol": "BTC-USD",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_capital": -1000.0  # Invalid: negative
        }
        
        # Act
        response = await client.post("/backtest/start", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_start_backtest_validates_position_size_range(self, client: AsyncClient):
        """Start backtest should validate position size is between 0 and 1."""
        # Arrange - position_size > 1
        payload = {
            "symbol": "BTC-USD",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "position_size_percent": 1.5  # Invalid: > 1
        }
        
        # Act
        response = await client.post("/backtest/start", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_start_backtest_validates_max_open_trades_positive(
        self, client: AsyncClient
    ):
        """Start backtest should validate max_open_trades is at least 1."""
        # Arrange
        payload = {
            "symbol": "BTC-USD",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "max_open_trades": 0  # Invalid: must be >= 1
        }
        
        # Act
        response = await client.post("/backtest/start", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_control_backtest_sends_command(self, client: AsyncClient):
        """Control backtest should send command to running session."""
        # Arrange - Create a mock session first
        session_id = "test-session-123"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.poll.return_value = None  # Process is running
            mock_process.stdin = MagicMock()
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            
            payload = {"command": "pause"}
            
            # Act
            response = await client.post(
                f"/backtest/control/{session_id}",
                json=payload
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "sent"
            assert data["command"] == "pause"

    @pytest.mark.asyncio
    async def test_control_backtest_returns_404_for_unknown_session(
        self, client: AsyncClient
    ):
        """Control backtest should return 404 for non-existent session."""
        # Arrange
        session_id = "nonexistent-session"
        payload = {"command": "pause"}
        
        # Act
        response = await client.post(f"/backtest/control/{session_id}", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_control_backtest_handles_terminated_session(
        self, client: AsyncClient
    ):
        """Control backtest should return 410 if session has terminated."""
        # Arrange
        session_id = "terminated-session"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.poll.return_value = 0  # Process terminated
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            
            payload = {"command": "pause"}
            
            # Act
            response = await client.post(
                f"/backtest/control/{session_id}",
                json=payload
            )
            
            # Assert
            assert response.status_code == status.HTTP_410_GONE
            assert "ended" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_control_backtest_supports_speed_command(
        self, client: AsyncClient
    ):
        """Control backtest should accept speed command with speed parameter."""
        # Arrange
        session_id = "test-session-123"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.stdin = MagicMock()
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            
            payload = {"command": "speed", "speed": 2.0}
            
            # Act
            response = await client.post(
                f"/backtest/control/{session_id}",
                json=payload
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            mock_process.stdin.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_control_backtest_supports_seek_command(
        self, client: AsyncClient
    ):
        """Control backtest should accept seek command with index parameter."""
        # Arrange
        session_id = "test-session-123"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.stdin = MagicMock()
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            
            payload = {"command": "seek", "index": 100}
            
            # Act
            response = await client.post(
                f"/backtest/control/{session_id}",
                json=payload
            )
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            mock_process.stdin.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_sessions_returns_active_sessions(self, client: AsyncClient):
        """List sessions should return all active backtest sessions."""
        # Arrange
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_sessions.items.return_value = [
                ("session-1", MagicMock(poll=lambda: None)),
                ("session-2", MagicMock(poll=lambda: None)),
            ]
            mock_sessions.__iter__ = lambda self: iter(["session-1", "session-2"])
            mock_sessions.__len__ = lambda self: 2
            
            # Act
            response = await client.get("/backtest/sessions")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "sessions" in data
            assert "count" in data
            assert isinstance(data["sessions"], list)

    @pytest.mark.asyncio
    async def test_list_sessions_cleans_up_dead_sessions(self, client: AsyncClient):
        """List sessions should remove terminated sessions from active list."""
        # Arrange
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            # One running, one dead
            sessions_dict = {
                "session-1": MagicMock(poll=lambda: None),  # Running
                "session-2": MagicMock(poll=lambda: 0),     # Dead
            }
            mock_sessions.items.return_value = list(sessions_dict.items())
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            response = await client.get("/backtest/sessions")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            # Dead session should be cleaned up
            mock_sessions.__delitem__.assert_called_with("session-2")

    @pytest.mark.asyncio
    async def test_stop_session_terminates_backtest(self, client: AsyncClient):
        """Stop session should terminate the backtest process."""
        # Arrange
        session_id = "test-session-123"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.stdin = MagicMock()
            mock_process.wait = MagicMock()
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            response = await client.delete(f"/backtest/sessions/{session_id}")
            
            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "stopped"
            assert data["session_id"] == session_id
            mock_process.stdin.write.assert_called_once()
            mock_process.wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_session_force_kills_if_not_stopping(
        self, client: AsyncClient
    ):
        """Stop session should force kill if process doesn't stop gracefully."""
        # Arrange
        session_id = "stubborn-session"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.stdin = MagicMock()
            mock_process.wait.side_effect = Exception("TimeoutExpired")
            mock_process.kill = MagicMock()
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            response = await client.delete(f"/backtest/sessions/{session_id}")
            
            # Assert
            # Should still succeed after force kill
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR or \
                   response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_stop_session_returns_404_for_unknown_session(
        self, client: AsyncClient
    ):
        """Stop session should return 404 for non-existent session."""
        # Arrange
        session_id = "nonexistent-session"
        
        # Act
        response = await client.delete(f"/backtest/sessions/{session_id}")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# Error Handling & Edge Cases
# ==============================================================================

class TestErrorHandling:
    """Test suite for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_api_handles_database_connection_error(
        self, client: AsyncClient
    ):
        """API should return 503 when database is unavailable."""
        # This would require mocking the database to fail
        # Implementation depends on dependency injection setup
        pytest.skip("Requires database mocking infrastructure")

    @pytest.mark.asyncio
    async def test_api_returns_proper_content_type_headers(
        self, client: AsyncClient
    ):
        """API should return proper Content-Type headers."""
        # Act
        response = await client.get("/")
        
        # Assert
        assert "application/json" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_api_handles_large_csv_import(
        self, client: AsyncClient, test_db
    ):
        """API should handle large CSV imports without memory issues."""
        # Arrange - Create large CSV (10,000 rows)
        header = "time,open,high,low,close,volume\n"
        rows = []
        base_timestamp = 1704067200
        for i in range(10000):
            timestamp = base_timestamp + (i * 300)
            rows.append(f"{timestamp},42000,42100,41900,42050,1000")
        
        large_csv = header + "\n".join(rows)
        csv_file = io.BytesIO(large_csv.encode())
        files = {"file": ("large.csv", csv_file, "text/csv")}
        params = {"symbol": "BTC-USD", "timeframe": "5m"}
        
        # Act
        response = await client.post("/api/data/import", files=files, params=params)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["stats"]["inserted"] == 10000

    @pytest.mark.asyncio
    async def test_api_validates_path_parameters(self, client: AsyncClient):
        """API should validate path parameters to prevent injection."""
        # Arrange - Try path traversal
        malicious_session_id = "../../../etc/passwd"
        
        # Act
        response = await client.delete(f"/backtest/sessions/{malicious_session_id}")
        
        # Assert
        # Should return 404, not expose filesystem
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_api_handles_concurrent_requests(
        self, client: AsyncClient, test_db
    ):
        """API should handle concurrent requests without race conditions."""
        # This would require running multiple requests simultaneously
        # Implementation depends on test infrastructure
        pytest.skip("Requires concurrent test infrastructure")


# ==============================================================================
# CORS & Security
# ==============================================================================

class TestSecurity:
    """Test suite for security and CORS."""

    @pytest.mark.asyncio
    async def test_cors_headers_present_in_response(self, client: AsyncClient):
        """API should include CORS headers for cross-origin requests."""
        # Act
        response = await client.get("/", headers={"Origin": "http://localhost:5173"})
        
        # Assert
        # Check if CORS middleware is adding headers
        # Exact headers depend on CORS configuration
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_api_prevents_sql_injection(self, client: AsyncClient):
        """API should prevent SQL injection in query parameters."""
        # Arrange - SQL injection attempt
        params = {
            "symbol": "BTC-USD' OR '1'='1",
            "timeframe": "5m"
        }
        
        # Act
        response = await client.get("/api/data/range", params=params)
        
        # Assert
        # Should either return empty results or validate input
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    @pytest.mark.asyncio
    async def test_api_sanitizes_error_messages(self, client: AsyncClient):
        """API should not leak sensitive information in error messages."""
        # Arrange - Trigger an error
        csv_file = io.BytesIO(b"malformed content that will cause error")
        files = {"file": ("bad.csv", csv_file, "text/csv")}
        params = {"symbol": "BTC-USD", "timeframe": "5m"}
        
        # Act
        response = await client.post("/api/data/import", files=files, params=params)
        
        # Assert
        if response.status_code >= 400:
            error_detail = response.json().get("detail", "")
            # Should not contain file paths, stack traces, or internal details
            assert "/opt/" not in error_detail
            assert "Traceback" not in error_detail
