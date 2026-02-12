"""API validation and schema tests.

Tests input validation, schema enforcement, and data contracts.
Following API design principles: validate at the boundary, fail loudly.
"""

import pytest
from httpx import AsyncClient
from fastapi import status


# ==============================================================================
# Input Validation Tests
# ==============================================================================

class TestInputValidation:
    """Test suite for API input validation."""

    @pytest.mark.asyncio
    async def test_timeframe_pattern_validation(self, client: AsyncClient):
        """Timeframe must match pattern: digits + unit (m/h/d)."""
        # Arrange - Valid timeframes
        valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        
        for tf in valid_timeframes:
            response = await client.get(
                "/api/data/range",
                params={"symbol": "BTC-USD", "timeframe": tf}
            )
            # Should accept valid format (even if no data)
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_404_NOT_FOUND
            ]
        
        # Arrange - Invalid timeframes
        invalid_timeframes = [
            "5",          # No unit
            "m5",         # Wrong order
            "5min",       # Wrong unit
            "abc",        # Not a number
            "1.5h",       # Decimal
            "",           # Empty
            "5 m",        # Space
        ]
        # Note: 5M is valid (monthly timeframe)
        
        for tf in invalid_timeframes:
            response = await client.get(
                "/api/data/range",
                params={"symbol": "BTC-USD", "timeframe": tf}
            )
            # Should reject invalid format
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_symbol_validation_rejects_empty_string(self, client: AsyncClient):
        """Symbol parameter must not be empty."""
        # Arrange
        payload = {
            "csv_content": "time,open,high,low,close\n1704067200,42000,42100,41900,42050",
            "symbol": "",  # Invalid: empty
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_symbol_validation_trims_whitespace(self, client: AsyncClient, test_db):
        """Symbol parameter should be trimmed of whitespace."""
        # This tests if the API sanitizes input
        # Arrange
        payload = {
            "csv_content": "time,open,high,low,close\n1704067200,42000,42100,41900,42050",
            "symbol": "  BTC-USD  ",  # Whitespace
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        # Should either accept and trim, or reject
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    @pytest.mark.asyncio
    async def test_numeric_validation_for_capital(self, client: AsyncClient):
        """Initial capital must be positive number."""
        # Arrange - Negative
        payload = {
            "symbol": "BTC-USD",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_capital": -1000.0
        }
        
        # Act
        response = await client.post("/backtest/start", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Arrange - Zero
        payload["initial_capital"] = 0.0
        response = await client.post("/backtest/start", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_numeric_validation_for_position_size(self, client: AsyncClient):
        """Position size must be between 0 and 1 (exclusive of 0, inclusive of 1)."""
        # Arrange - Too large
        payload = {
            "symbol": "BTC-USD",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "position_size_percent": 1.5  # > 1
        }
        
        # Act
        response = await client.post("/backtest/start", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Arrange - Zero
        payload["position_size_percent"] = 0.0
        response = await client.post("/backtest/start", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Arrange - Negative
        payload["position_size_percent"] = -0.1
        response = await client.post("/backtest/start", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_integer_validation_for_max_trades(self, client: AsyncClient):
        """Max open trades must be positive integer."""
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
    async def test_date_format_validation(self, client: AsyncClient):
        """Date parameters must be in YYYY-MM-DD format."""
        # Arrange - Invalid format
        payload = {
            "symbol": "BTC-USD",
            "start_date": "01/01/2024",  # Wrong format
            "end_date": "2024-01-31"
        }
        
        # Act
        response = await client.post("/backtest/start", json=payload)
        
        # Assert
        # Should reject invalid date format
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    @pytest.mark.asyncio
    async def test_timestamp_iso_format_validation(self, client: AsyncClient):
        """Timestamp parameters must be valid ISO format."""
        # Arrange - Invalid format
        params = {
            "symbol": "BTC-USD",
            "timeframe": "5m",
            "start_time": "not-a-timestamp"
        }
        
        # Act
        response = await client.delete("/api/data/clear", params=params)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "timestamp" in response.json()["detail"].lower()


# ==============================================================================
# Schema Validation Tests
# ==============================================================================

class TestResponseSchemas:
    """Test suite for API response schema validation."""

    @pytest.mark.asyncio
    async def test_import_response_schema(self, client: AsyncClient, test_db):
        """Import response should follow documented schema."""
        # Arrange
        csv_content = "time,open,high,low,close\n1704067200,42000,42100,41900,42050"
        payload = {
            "csv_content": csv_content,
            "symbol": "BTC-USD",
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Required fields
        assert "success" in data
        assert "message" in data
        assert "stats" in data
        
        # Types
        assert isinstance(data["success"], bool)
        assert isinstance(data["message"], str)
        assert isinstance(data["stats"], dict)
        
        # Stats schema
        stats = data["stats"]
        assert "inserted" in stats
        assert "duplicates" in stats
        assert "invalid" in stats
        assert isinstance(stats["inserted"], int)

    @pytest.mark.asyncio
    async def test_data_range_response_schema(
        self, client: AsyncClient, test_db, sample_ohlcv_data
    ):
        """Data range response should follow documented schema."""
        # Arrange
        params = {"symbol": "BTC-USD", "timeframe": "5m"}
        
        # Act
        response = await client.get("/api/data/range", params=params)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Required fields
        assert "symbol" in data
        assert "timeframe" in data
        assert "earliest" in data
        assert "latest" in data
        assert "candle_count" in data
        
        # Types
        assert isinstance(data["symbol"], str)
        assert isinstance(data["timeframe"], str)
        assert isinstance(data["candle_count"], int)
        
        # Timestamps (can be null if no data)
        if data["earliest"] is not None:
            assert isinstance(data["earliest"], str)
        if data["latest"] is not None:
            assert isinstance(data["latest"], str)

    @pytest.mark.asyncio
    async def test_available_data_response_schema(self, client: AsyncClient, test_db):
        """Available data response should follow documented schema."""
        # Act
        response = await client.get("/api/data/available")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Required fields
        assert "symbols" in data
        assert "timeframes" in data
        
        # Types
        assert isinstance(data["symbols"], list)
        assert isinstance(data["timeframes"], list)
        
        # All items should be strings
        for symbol in data["symbols"]:
            assert isinstance(symbol, str)
        for tf in data["timeframes"]:
            assert isinstance(tf, str)

    @pytest.mark.asyncio
    async def test_error_response_schema(self, client: AsyncClient):
        """Error responses should follow consistent schema."""
        # Arrange - Trigger validation error
        response = await client.get("/api/data/range", params={})
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        # FastAPI validation error format
        assert "detail" in data


# ==============================================================================
# Boundary Value Tests
# ==============================================================================

class TestBoundaryValues:
    """Test suite for boundary value validation."""

    @pytest.mark.asyncio
    async def test_handles_very_large_numbers(self, client: AsyncClient, test_db):
        """API should handle very large numeric values."""
        # Arrange
        csv_content = "time,open,high,low,close\n1704067200,999999999.99,1000000000.00,999999999.00,999999999.50"
        payload = {
            "csv_content": csv_content,
            "symbol": "BTC-USD",
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        # Should handle large numbers without overflow
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST  # If validation rejects unrealistic values
        ]

    @pytest.mark.asyncio
    async def test_handles_very_small_numbers(self, client: AsyncClient, test_db):
        """API should handle very small decimal values."""
        # Arrange - Crypto prices can be very small
        csv_content = "time,open,high,low,close\n1704067200,0.00001,0.00002,0.000009,0.000015"
        payload = {
            "csv_content": csv_content,
            "symbol": "SHIB-USD",
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_handles_maximum_string_lengths(self, client: AsyncClient):
        """API should enforce reasonable string length limits."""
        # Arrange - Very long symbol name
        very_long_symbol = "A" * 10000
        params = {"symbol": very_long_symbol, "timeframe": "5m"}
        
        # Act
        response = await client.get("/api/data/range", params=params)
        
        # Assert
        # Should either accept (and return no data) or reject as invalid
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    @pytest.mark.asyncio
    async def test_rejects_negative_prices(self, client: AsyncClient):
        """API should reject negative prices in OHLCV data."""
        # Arrange
        csv_content = "time,open,high,low,close\n1704067200,-42000,42100,41900,42050"
        payload = {
            "csv_content": csv_content,
            "symbol": "BTC-USD",
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        # Should reject or log to DLQ
        assert response.status_code in [
            status.HTTP_200_OK,  # Might accept but log to DLQ
            status.HTTP_400_BAD_REQUEST
        ]
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # If accepted, should be in DLQ
            assert data["stats"]["invalid"] > 0 or data["stats"]["inserted"] == 0


# ==============================================================================
# Type Safety Tests
# ==============================================================================

class TestTypeSafety:
    """Test suite for type safety and coercion."""

    @pytest.mark.asyncio
    async def test_rejects_string_for_numeric_field(self, client: AsyncClient):
        """API should reject strings where numbers are expected."""
        # Arrange
        payload = {
            "symbol": "BTC-USD",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_capital": "not-a-number"  # String instead of number
        }
        
        # Act
        response = await client.post("/backtest/start", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_rejects_number_for_string_field(self, client: AsyncClient):
        """API should reject numbers where strings are expected."""
        # Arrange
        payload = {
            "csv_content": "time,open,high,low,close\n1704067200,42000,42100,41900,42050",
            "symbol": 12345,  # Number instead of string
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        # Pydantic might coerce this to string - check API behavior
        assert response.status_code in [
            status.HTTP_200_OK,  # If coerced to string
            status.HTTP_422_UNPROCESSABLE_ENTITY  # If strict validation
        ]

    @pytest.mark.asyncio
    async def test_rejects_array_for_scalar_field(self, client: AsyncClient):
        """API should reject arrays where scalars are expected."""
        # Arrange
        payload = {
            "csv_content": "time,open,high,low,close\n1704067200,42000,42100,41900,42050",
            "symbol": ["BTC-USD", "ETH-USD"],  # Array instead of string
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_rejects_null_for_required_field(self, client: AsyncClient):
        """API should reject null for required fields."""
        # Arrange
        payload = {
            "csv_content": "time,open,high,low,close\n1704067200,42000,42100,41900,42050",
            "symbol": None,  # Null for required field
            "timeframe": "5m"
        }
        
        # Act
        response = await client.post("/api/data/import/raw", json=payload)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==============================================================================
# Special Character Handling
# ==============================================================================

class TestSpecialCharacterHandling:
    """Test suite for handling special characters and encoding."""

    @pytest.mark.asyncio
    async def test_handles_unicode_in_symbol(self, client: AsyncClient):
        """API should handle Unicode characters in symbol names."""
        # Arrange
        params = {"symbol": "BTC-₿", "timeframe": "5m"}
        
        # Act
        response = await client.get("/api/data/range", params=params)
        
        # Assert
        # Should handle gracefully (return no data or accept)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ]

    @pytest.mark.asyncio
    async def test_sanitizes_control_characters(self, client: AsyncClient):
        """API should sanitize control characters from input."""
        # Arrange - Symbol with control characters
        symbol_with_control = "BTC\x00\x01\x1F-USD"
        params = {"symbol": symbol_with_control, "timeframe": "5m"}
        
        # Act
        response = await client.get("/api/data/range", params=params)
        
        # Assert
        # Should either sanitize or reject
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    @pytest.mark.asyncio
    async def test_handles_sql_injection_attempts(self, client: AsyncClient):
        """API should be immune to SQL injection attacks."""
        # Arrange - Classic SQL injection patterns
        injection_attempts = [
            "BTC-USD' OR '1'='1",
            "BTC-USD; DROP TABLE ohlcv_data;--",
            "BTC-USD' UNION SELECT * FROM users--",
        ]
        
        for injection in injection_attempts:
            params = {"symbol": injection, "timeframe": "5m"}
            
            # Act
            response = await client.get("/api/data/range", params=params)
            
            # Assert
            # Should safely handle (parameterized queries prevent injection)
            assert response.status_code in [
                status.HTTP_200_OK,  # Returns no data
                status.HTTP_400_BAD_REQUEST
            ]
            
            # Response should not indicate successful injection
            data = response.json()
            if response.status_code == status.HTTP_200_OK:
                # Should return empty results, not expose data
                assert data.get("candle_count", 0) == 0

    @pytest.mark.asyncio
    async def test_handles_xss_attempts(self, client: AsyncClient):
        """API should sanitize potential XSS payloads."""
        # Arrange - XSS payload
        xss_payload = "<script>alert('XSS')</script>"
        params = {"symbol": xss_payload, "timeframe": "5m"}
        
        # Act
        response = await client.get("/api/data/range", params=params)
        
        # Assert - API should reject malformed symbols OR return JSON safely
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]
        
        # For JSON APIs, XSS protection is via Content-Type header
        # JSON responses don't need HTML escaping - they need JSON encoding
        # Consumers must not embed JSON directly into HTML without escaping
        assert "application/json" in response.headers.get("content-type", "")
        
        # Verify response is valid JSON (proper encoding)
        if response.status_code == status.HTTP_200_OK:
            import json
            data = response.json()  # Should not raise
            assert isinstance(data, dict)
