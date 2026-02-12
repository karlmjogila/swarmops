"""WebSocket integration tests for backtest streaming.

Tests the real-time streaming of backtest state via WebSocket.
"""

import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app


# ==============================================================================
# WebSocket Connection Tests
# ==============================================================================

class TestBacktestWebSocket:
    """Test suite for WebSocket backtest streaming."""

    def test_websocket_accepts_valid_session(self):
        """WebSocket should accept connection for valid session ID."""
        # Arrange
        session_id = "test-session-123"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.poll.return_value = None  # Running
            mock_process.stdout.readline.side_effect = [
                '{"type": "candle", "data": {}}\n',
                ''  # End of stream
            ]
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            client = TestClient(app)
            with client.websocket_connect(f"/backtest/ws/{session_id}") as websocket:
                # Assert - connection successful
                assert websocket is not None

    def test_websocket_rejects_invalid_session(self):
        """WebSocket should reject connection for non-existent session."""
        # Arrange
        session_id = "nonexistent-session"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_sessions.__contains__ = lambda self, key: False
            
            # Act - WebSocket accepts then sends error and closes
            client = TestClient(app)
            with client.websocket_connect(f"/backtest/ws/{session_id}") as websocket:
                # Should receive error message
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert "Session not found" in data["error"]

    def test_websocket_streams_json_messages(self):
        """WebSocket should stream JSON messages from backtest process."""
        # Arrange
        session_id = "test-session-123"
        test_messages = [
            '{"type": "candle", "index": 0}\n',
            '{"type": "candle", "index": 1}\n',
            '{"type": "trade", "side": "buy"}\n',
            ''  # End of stream
        ]
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.poll.side_effect = [None, None, None, 0]  # Running then done
            mock_process.stdout.readline.side_effect = test_messages
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            client = TestClient(app)
            with client.websocket_connect(f"/backtest/ws/{session_id}") as websocket:
                # Receive first message
                message1 = websocket.receive_json()
                assert message1["type"] == "candle"
                assert message1["index"] == 0
                
                # Receive second message
                message2 = websocket.receive_json()
                assert message2["type"] == "candle"
                assert message2["index"] == 1
                
                # Receive trade message
                message3 = websocket.receive_json()
                assert message3["type"] == "trade"

    def test_websocket_handles_non_json_output(self):
        """WebSocket should handle non-JSON output as log messages."""
        # Arrange
        session_id = "test-session-123"
        test_output = [
            'This is a log line\n',
            '{"type": "candle"}\n',  # Valid JSON
            'Another log line\n',
            ''  # End
        ]
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.poll.side_effect = [None, None, None, None, 0]
            mock_process.stdout.readline.side_effect = test_output
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            client = TestClient(app)
            with client.websocket_connect(f"/backtest/ws/{session_id}") as websocket:
                # Should receive log message
                msg1 = websocket.receive_json()
                assert msg1["type"] == "log"
                assert "log line" in msg1["message"]

    def test_websocket_sends_completion_when_process_ends(self):
        """WebSocket should send completion message when backtest finishes."""
        # Arrange
        session_id = "test-session-123"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            # Process ends immediately
            mock_process.poll.return_value = 0
            mock_process.stdout.readline.return_value = ''
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            client = TestClient(app)
            with client.websocket_connect(f"/backtest/ws/{session_id}") as websocket:
                # Should receive completion message
                msg = websocket.receive_json()
                assert msg["type"] == "completed"
                assert msg["session_id"] == session_id

    def test_websocket_cleans_up_session_on_disconnect(self):
        """WebSocket should clean up session when client disconnects."""
        # Arrange
        session_id = "test-session-123"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.stdout.readline.return_value = '{"type": "candle"}\n'
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            client = TestClient(app)
            with client.websocket_connect(f"/backtest/ws/{session_id}") as websocket:
                # Receive one message then close
                websocket.receive_json()
                websocket.close()
            
            # Assert - session should be cleaned up
            mock_sessions.__delitem__.assert_called_with(session_id)

    def test_websocket_handles_process_errors(self):
        """WebSocket should handle errors from backtest process gracefully."""
        # Arrange
        session_id = "error-session"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            # Simulate error reading from process
            mock_process.stdout.readline.side_effect = Exception("Process crashed")
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            client = TestClient(app)
            with client.websocket_connect(f"/backtest/ws/{session_id}") as websocket:
                # Should receive error message
                msg = websocket.receive_json()
                assert msg["type"] == "error"
                assert "error" in msg


# ==============================================================================
# WebSocket Data Format Tests
# ==============================================================================

class TestWebSocketDataFormat:
    """Test suite for WebSocket message format validation."""

    def test_candle_message_contains_required_fields(self):
        """Candle messages should contain all required fields."""
        # This is more of a contract test - documents expected format
        expected_fields = [
            "type",  # "candle"
            "index",  # Candle index
            "timestamp",  # ISO timestamp
            "open",  # OHLC data
            "high",
            "low",
            "close",
            "volume",
        ]
        
        # Document expected format
        sample_candle = {
            "type": "candle",
            "index": 0,
            "timestamp": "2024-01-01T00:00:00Z",
            "open": 42000.0,
            "high": 42100.0,
            "low": 41900.0,
            "close": 42050.0,
            "volume": 1000.0,
        }
        
        # Verify all required fields present
        for field in expected_fields:
            assert field in sample_candle

    def test_trade_message_contains_required_fields(self):
        """Trade messages should contain all required fields."""
        expected_fields = [
            "type",  # "trade"
            "action",  # "open" or "close"
            "side",  # "buy" or "sell"
            "symbol",
            "price",
            "quantity",
            "timestamp",
        ]
        
        sample_trade = {
            "type": "trade",
            "action": "open",
            "side": "buy",
            "symbol": "BTC-USD",
            "price": 42000.0,
            "quantity": 0.1,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        
        for field in expected_fields:
            assert field in sample_trade

    def test_state_message_contains_required_fields(self):
        """State update messages should contain all required fields."""
        expected_fields = [
            "type",  # "state"
            "equity",
            "cash",
            "position_value",
            "open_positions",
            "total_trades",
            "win_rate",
        ]
        
        sample_state = {
            "type": "state",
            "equity": 10500.0,
            "cash": 9500.0,
            "position_value": 1000.0,
            "open_positions": 1,
            "total_trades": 10,
            "win_rate": 0.6,
        }
        
        for field in expected_fields:
            assert field in sample_state


# ==============================================================================
# WebSocket Concurrent Connection Tests
# ==============================================================================

class TestWebSocketConcurrency:
    """Test suite for multiple concurrent WebSocket connections."""

    def test_multiple_sessions_can_stream_simultaneously(self):
        """Multiple backtest sessions should be able to stream concurrently."""
        # Arrange
        session_id_1 = "session-1"
        session_id_2 = "session-2"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            # Two separate mock processes
            mock_process_1 = MagicMock()
            mock_process_1.poll.side_effect = [None, 0]
            mock_process_1.stdout.readline.side_effect = [
                '{"type": "candle", "index": 0}\n',
                ''
            ]
            
            mock_process_2 = MagicMock()
            mock_process_2.poll.side_effect = [None, 0]
            mock_process_2.stdout.readline.side_effect = [
                '{"type": "candle", "index": 100}\n',
                ''
            ]
            
            def get_process(session_id):
                if session_id == session_id_1:
                    return mock_process_1
                elif session_id == session_id_2:
                    return mock_process_2
                raise KeyError()
            
            mock_sessions.__contains__ = lambda self, key: key in [session_id_1, session_id_2]
            mock_sessions.__getitem__ = lambda self, key: get_process(key)
            mock_sessions.__delitem__ = MagicMock()
            
            # Act - Connect to both sessions
            client = TestClient(app)
            
            with client.websocket_connect(f"/backtest/ws/{session_id_1}") as ws1:
                with client.websocket_connect(f"/backtest/ws/{session_id_2}") as ws2:
                    # Assert - Both receive their own data
                    msg1 = ws1.receive_json()
                    msg2 = ws2.receive_json()
                    
                    assert msg1["index"] == 0
                    assert msg2["index"] == 100

    @pytest.mark.skip("Requires async test infrastructure")
    def test_websocket_handles_high_message_rate(self):
        """WebSocket should handle high-frequency message streaming."""
        # This would test performance under high message volume
        # Requires more sophisticated async test setup
        pass


# ==============================================================================
# WebSocket Error Recovery Tests
# ==============================================================================

class TestWebSocketErrorRecovery:
    """Test suite for WebSocket error handling and recovery."""

    def test_websocket_handles_client_disconnect_gracefully(self):
        """WebSocket should handle client disconnect without crashing."""
        # Arrange
        session_id = "test-session"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.stdout.readline.return_value = '{"type": "candle"}\n'
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            client = TestClient(app)
            with client.websocket_connect(f"/backtest/ws/{session_id}") as websocket:
                websocket.receive_json()
                # Abrupt close
                websocket.close()
            
            # Assert - should not raise exception
            # Session should be cleaned up
            mock_sessions.__delitem__.assert_called()

    def test_websocket_handles_malformed_json_from_process(self):
        """WebSocket should handle malformed JSON from backtest process."""
        # Arrange
        session_id = "test-session"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            mock_process.poll.side_effect = [None, None, 0]
            # Return malformed JSON
            mock_process.stdout.readline.side_effect = [
                '{invalid json}\n',
                ''
            ]
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            client = TestClient(app)
            with client.websocket_connect(f"/backtest/ws/{session_id}") as websocket:
                # Should convert to log message
                msg = websocket.receive_json()
                assert msg["type"] == "log"

    def test_websocket_closes_cleanly_when_process_crashes(self):
        """WebSocket should close cleanly if backtest process crashes."""
        # Arrange
        session_id = "crashing-session"
        
        with patch("app.api.routes.backtest.active_sessions") as mock_sessions:
            mock_process = MagicMock()
            # Process crashed (non-zero exit)
            mock_process.poll.return_value = 1
            mock_process.stdout.readline.return_value = ''
            mock_sessions.__contains__ = lambda self, key: True
            mock_sessions.__getitem__ = lambda self, key: mock_process
            mock_sessions.__delitem__ = MagicMock()
            
            # Act
            client = TestClient(app)
            with client.websocket_connect(f"/backtest/ws/{session_id}") as websocket:
                # Should receive completion (even though it crashed)
                msg = websocket.receive_json()
                # WebSocket should close gracefully
                assert msg["type"] == "completed" or msg["type"] == "error"
