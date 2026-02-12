# REST API Documentation

## Overview

The Hyperliquid Trading Bot Suite REST API provides comprehensive endpoints for:
- **Ingestion**: Upload and process PDFs and YouTube videos to extract trading strategies
- **Strategies**: Manage strategy rules in the knowledge base
- **Backtesting**: Run backtests and analyze historical performance
- **Trading**: Monitor positions, execute trades, and manage risk

All endpoints follow consistent patterns for error handling, validation, and response structure.

## Base URL

```
http://localhost:8000/api
```

## API Design Principles

1. **Consistency**: All endpoints follow the same naming conventions and response structures
2. **Validation**: Comprehensive input validation with clear error messages
3. **Async Processing**: Long-running tasks (ingestion, backtesting) run in background
4. **Pagination**: List endpoints support pagination with consistent metadata
5. **Error Handling**: Structured error responses with HTTP status codes and details

---

## Ingestion Endpoints

### POST /ingestion/pdf
Upload and process a PDF document to extract trading strategies.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/ingestion/pdf" \
  -F "file=@trading_strategy.pdf" \
  -F "extract_images=true"
```

**Response (202 Accepted):**
```json
{
  "task_id": "pdf_a1b2c3d4e5f6",
  "status": "pending",
  "message": "PDF 'trading_strategy.pdf' queued for processing"
}
```

**Processing Steps:**
1. Extract text and images from PDF
2. Analyze content with LLM (Claude)
3. Extract structured strategy rules
4. Store rules in knowledge base

---

### POST /ingestion/video
Process a YouTube video to extract trading strategies.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/ingestion/video" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=example",
    "extract_frames": true
  }'
```

**Response (202 Accepted):**
```json
{
  "task_id": "video_f6e5d4c3b2a1",
  "status": "pending",
  "message": "Video 'https://www.youtube.com/watch?v=example' queued for processing"
}
```

**Processing Steps:**
1. Download video and extract audio
2. Transcribe audio using Whisper
3. Extract frames at 10-second intervals
4. Analyze transcript + frames with LLM
5. Extract and store strategy rules

---

### GET /ingestion/status/{task_id}
Get the status of an ingestion task.

**Request:**
```bash
curl "http://localhost:8000/api/ingestion/status/pdf_a1b2c3d4e5f6"
```

**Response:**
```json
{
  "task_id": "pdf_a1b2c3d4e5f6",
  "status": "completed",
  "progress": 1.0,
  "message": "Successfully extracted 12 rules",
  "rules_extracted": 12,
  "errors": [],
  "created_at": "2024-02-10T12:00:00Z",
  "completed_at": "2024-02-10T12:05:30Z"
}
```

**Status Values:**
- `pending`: Task queued but not started
- `processing`: Task in progress
- `completed`: Task finished successfully
- `failed`: Task encountered an error

---

### GET /ingestion/tasks
List all ingestion tasks.

**Request:**
```bash
curl "http://localhost:8000/api/ingestion/tasks?status=completed&limit=20"
```

**Query Parameters:**
- `status` (optional): Filter by status (pending, processing, completed, failed)
- `limit` (optional): Maximum tasks to return (1-100, default: 50)

**Response:**
```json
[
  {
    "task_id": "pdf_a1b2c3d4e5f6",
    "status": "completed",
    "progress": 1.0,
    "message": "Successfully extracted 12 rules",
    "rules_extracted": 12,
    "errors": [],
    "created_at": "2024-02-10T12:00:00Z",
    "completed_at": "2024-02-10T12:05:30Z"
  }
]
```

---

### DELETE /ingestion/tasks/{task_id}
Delete an ingestion task and its data.

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/ingestion/tasks/pdf_a1b2c3d4e5f6"
```

**Response:**
```json
{
  "message": "Task deleted successfully",
  "task_id": "pdf_a1b2c3d4e5f6"
}
```

---

## Strategy Endpoints

### GET /strategies
List all strategy rules in the knowledge base.

**Request:**
```bash
curl "http://localhost:8000/api/strategies?min_confidence=0.7&source_type=pdf&limit=20&offset=0"
```

**Query Parameters:**
- `enabled_only` (optional): Only return enabled strategies
- `min_confidence` (optional): Minimum confidence threshold (0.0-1.0)
- `source_type` (optional): Filter by source (pdf, video)
- `entry_type` (optional): Filter by entry type
- `limit` (optional): Maximum strategies to return (1-100, default: 50)
- `offset` (optional): Number of strategies to skip (for pagination)

**Response:**
```json
{
  "data": [
    {
      "id": "strategy_123",
      "name": "LE Candle at Support",
      "description": "Look for LE candle forming at support zone",
      "entry_type": "LE",
      "conditions": [...],
      "confluence_required": [...],
      "risk_params": {
        "risk_percent": 0.02,
        "tp_levels": [1.0, 2.0],
        "sl_distance": "1ATR"
      },
      "confidence": 0.85,
      "source_type": "pdf",
      "source_ref": "ICT_Mentorship_2022.pdf",
      "created_at": "2024-02-10T12:00:00Z",
      "last_used": "2024-02-10T14:30:00Z",
      "win_rate": 0.72,
      "total_trades": 45,
      "enabled": true,
      "tags": ["ict", "support", "le-candle"]
    }
  ],
  "meta": {
    "total": 125,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

---

### POST /strategies
Create a new strategy rule manually.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/strategies" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Custom LE Strategy",
    "description": "My custom LE candle strategy",
    "entry_type": "LE",
    "conditions": [...],
    "confluence_required": [...],
    "risk_params": {
      "risk_percent": 0.02,
      "tp_levels": [1.0, 2.0],
      "sl_distance": "1ATR"
    },
    "source_type": "manual",
    "source_ref": "user_created",
    "tags": ["custom"]
  }'
```

**Response (201 Created):**
```json
{
  "id": "strategy_456",
  "name": "Custom LE Strategy",
  ...
}
```

---

### GET /strategies/{strategy_id}
Get detailed information about a specific strategy.

**Request:**
```bash
curl "http://localhost:8000/api/strategies/strategy_123"
```

**Response:**
```json
{
  "id": "strategy_123",
  "name": "LE Candle at Support",
  "description": "Look for LE candle forming at support zone",
  ...
}
```

---

### PUT /strategies/{strategy_id}
Update an existing strategy.

**Request:**
```bash
curl -X PUT "http://localhost:8000/api/strategies/strategy_123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated LE Strategy",
    ...
  }'
```

**Response:**
```json
{
  "id": "strategy_123",
  "name": "Updated LE Strategy",
  ...
}
```

---

### GET /strategies/{strategy_id}/performance
Get detailed performance metrics for a strategy.

**Request:**
```bash
curl "http://localhost:8000/api/strategies/strategy_123/performance"
```

**Response:**
```json
{
  "strategy_id": "strategy_123",
  "total_trades": 45,
  "winning_trades": 32,
  "losing_trades": 13,
  "win_rate": 0.711,
  "profit_factor": 2.3,
  "avg_win_r": 1.5,
  "avg_loss_r": -0.95,
  "max_consecutive_losses": 3,
  "avg_r_multiple": 0.82,
  "total_pnl_r": 36.9
}
```

---

### DELETE /strategies/{strategy_id}
Delete a strategy from the knowledge base.

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/strategies/strategy_123"
```

**Response:**
```json
{
  "message": "Strategy deleted successfully",
  "strategy_id": "strategy_123"
}
```

**Note:** Cannot delete strategies with associated trades (returns 409 Conflict).

---

## Backtesting Endpoints

### POST /backtesting/start
Start a new backtest with the specified configuration.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/backtesting/start" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q1 2024 Backtest",
    "symbol": "BTC-USD",
    "timeframes": ["4H", "1H", "15M", "5M"],
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-03-31T23:59:59Z",
    "initial_capital": 10000,
    "strategy_ids": ["strategy_123", "strategy_456"],
    "max_concurrent_positions": 5,
    "risk_per_trade": 0.02
  }'
```

**Response (202 Accepted):**
```json
{
  "backtest_id": "bt_a1b2c3d4e5f6",
  "status": "pending",
  "message": "Backtest 'Q1 2024 Backtest' queued for execution"
}
```

---

### POST /backtesting/upload-data
Upload historical price data for backtesting.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/backtesting/upload-data?symbol=BTC-USD&timeframe=1H" \
  -F "file=@btc_usd_1h.csv"
```

**CSV Format:**
```csv
timestamp,open,high,low,close,volume
2024-01-01 00:00:00,50000,51000,49500,50500,1000
2024-01-01 01:00:00,50500,51200,50300,50800,1200
```

**Response:**
```json
{
  "message": "Data uploaded for BTC-USD 1H",
  "rows_processed": 2160,
  "file_path": "data/historical/BTC-USD/1H.csv"
}
```

---

### GET /backtesting
List all backtests with their current status.

**Request:**
```bash
curl "http://localhost:8000/api/backtesting?status=completed&limit=20&offset=0"
```

**Query Parameters:**
- `status` (optional): Filter by status (pending, running, completed, failed)
- `limit` (optional): Maximum backtests to return (1-100, default: 50)
- `offset` (optional): Number of backtests to skip

**Response:**
```json
{
  "data": [
    {
      "backtest_id": "bt_a1b2c3d4e5f6",
      "name": "Q1 2024 Backtest",
      "status": "completed",
      "progress": 1.0,
      "config": {...},
      "total_trades": 87,
      "winning_trades": 62,
      "win_rate": 0.713,
      "profit_factor": 2.1,
      "total_return": 3250,
      "total_return_pct": 32.5,
      "max_drawdown": -850,
      "max_drawdown_pct": -8.5,
      "sharpe_ratio": 1.8,
      "avg_r_multiple": 0.75,
      "created_at": "2024-02-10T12:00:00Z",
      "started_at": "2024-02-10T12:00:05Z",
      "completed_at": "2024-02-10T12:15:30Z"
    }
  ],
  "meta": {
    "total": 15,
    "limit": 20,
    "offset": 0,
    "has_more": false
  }
}
```

---

### GET /backtesting/{backtest_id}
Get detailed information about a specific backtest.

**Request:**
```bash
curl "http://localhost:8000/api/backtesting/bt_a1b2c3d4e5f6"
```

**Response:**
```json
{
  "backtest_id": "bt_a1b2c3d4e5f6",
  "name": "Q1 2024 Backtest",
  "status": "completed",
  "progress": 1.0,
  ...
}
```

---

### GET /backtesting/{backtest_id}/trades
Get all trades from a backtest.

**Request:**
```bash
curl "http://localhost:8000/api/backtesting/bt_a1b2c3d4e5f6/trades?limit=100&offset=0"
```

**Query Parameters:**
- `limit` (optional): Maximum trades to return (1-500, default: 100)
- `offset` (optional): Number of trades to skip

**Response:**
```json
{
  "data": [
    {
      "trade_id": "trade_789",
      "strategy_id": "strategy_123",
      "strategy_name": "LE Candle at Support",
      "symbol": "BTC-USD",
      "direction": "long",
      "entry_time": "2024-01-15T14:30:00Z",
      "entry_price": 48500,
      "exit_time": "2024-01-16T08:15:00Z",
      "exit_price": 49200,
      "exit_reason": "tp1",
      "quantity": 0.2,
      "pnl": 140,
      "pnl_r": 1.2,
      "confluence_score": 0.85,
      "reasoning": "LE candle formed at 4H support with 1H bullish structure..."
    }
  ],
  "meta": {
    "total": 87,
    "limit": 100,
    "offset": 0,
    "has_more": false
  }
}
```

---

### GET /backtesting/{backtest_id}/equity-curve
Get equity curve data for plotting.

**Request:**
```bash
curl "http://localhost:8000/api/backtesting/bt_a1b2c3d4e5f6/equity-curve"
```

**Response:**
```json
{
  "backtest_id": "bt_a1b2c3d4e5f6",
  "initial_capital": 10000,
  "equity_curve": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "equity": 10000,
      "drawdown": 0,
      "drawdown_pct": 0
    },
    {
      "timestamp": "2024-01-15T14:30:00Z",
      "equity": 10140,
      "drawdown": 0,
      "drawdown_pct": 0
    },
    ...
  ]
}
```

---

### DELETE /backtesting/{backtest_id}
Delete a backtest and all associated data.

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/backtesting/bt_a1b2c3d4e5f6"
```

**Response:**
```json
{
  "message": "Backtest deleted successfully",
  "backtest_id": "bt_a1b2c3d4e5f6"
}
```

---

## Trading Endpoints

### GET /trades
List trades with optional filtering.

**Request:**
```bash
curl "http://localhost:8000/api/trades?status=active&symbol=BTC-USD&limit=50&offset=0"
```

**Query Parameters:**
- `status` (optional): Filter by status (pending, active, closed)
- `symbol` (optional): Filter by symbol
- `strategy_id` (optional): Filter by strategy
- `limit` (optional): Maximum trades to return (1-100, default: 50)
- `offset` (optional): Number of trades to skip

**Response:**
```json
[
  {
    "id": "trade_xyz",
    "strategy_id": "strategy_123",
    "strategy_name": "LE Candle at Support",
    "symbol": "BTC-USD",
    "direction": "long",
    "entry_price": 49500,
    "entry_time": "2024-02-10T14:00:00Z",
    "exit_price": null,
    "exit_time": null,
    "exit_reason": null,
    "quantity": 0.2,
    "pnl": 0,
    "pnl_r": 0,
    "status": "active",
    "reasoning": "LE candle at 4H support...",
    "confluence_score": 0.82,
    "stop_loss": 48900,
    "take_profit_1": 50100,
    "take_profit_2": 50700,
    "created_at": "2024-02-10T14:00:00Z"
  }
]
```

---

### GET /trades/{trade_id}
Get detailed information about a specific trade.

**Request:**
```bash
curl "http://localhost:8000/api/trades/trade_xyz"
```

**Response:**
```json
{
  "id": "trade_xyz",
  "strategy_id": "strategy_123",
  ...
}
```

---

### GET /trades/positions/current
Get all current open positions.

**Request:**
```bash
curl "http://localhost:8000/api/trades/positions/current"
```

**Response:**
```json
[
  {
    "symbol": "BTC-USD",
    "direction": "long",
    "size": 0.2,
    "entry_price": 49500,
    "current_price": 49800,
    "unrealized_pnl": 60,
    "unrealized_pnl_r": 0.5,
    "stop_loss": 48900,
    "take_profit_1": 50100,
    "take_profit_2": 50700,
    "trade_id": "trade_xyz"
  }
]
```

---

### GET /trades/stats/overall
Get comprehensive trading performance statistics.

**Request:**
```bash
curl "http://localhost:8000/api/trades/stats/overall"
```

**Response:**
```json
{
  "total_trades": 150,
  "winning_trades": 108,
  "losing_trades": 42,
  "win_rate": 0.72,
  "profit_factor": 2.4,
  "total_pnl": 4520,
  "total_pnl_r": 98.5,
  "max_drawdown": -950,
  "max_consecutive_losses": 4,
  "current_streak": 3,
  "avg_win_r": 1.45,
  "avg_loss_r": -0.92
}
```

---

### PUT /trades/{trade_id}/close
Close an active trade manually.

**Request:**
```bash
curl -X PUT "http://localhost:8000/api/trades/trade_xyz/close?reason=manual"
```

**Response:**
```json
{
  "message": "Trade closed manually",
  "trade_id": "trade_xyz",
  "exit_reason": "manual"
}
```

---

### GET /trades/portfolio/summary
Get overall portfolio summary and statistics.

**Request:**
```bash
curl "http://localhost:8000/api/trades/portfolio/summary"
```

**Response:**
```json
{
  "portfolio_value": 14520,
  "total_pnl": 4520,
  "total_pnl_percent": 45.2,
  "open_positions": 3,
  "long_positions": 2,
  "short_positions": 1,
  "positions_in_profit": 2,
  "positions_in_loss": 1
}
```

---

## Error Responses

All endpoints return structured error responses with appropriate HTTP status codes:

### 400 Bad Request
```json
{
  "error": "Validation failed",
  "details": [
    {
      "field": "start_date",
      "message": "start_date must be before end_date"
    }
  ]
}
```

### 404 Not Found
```json
{
  "error": "Strategy 'strategy_123' not found",
  "status_code": 404
}
```

### 409 Conflict
```json
{
  "error": "Cannot delete strategy with 45 associated trades. Archive it instead.",
  "status_code": 409
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "status_code": 500
}
```

---

## Rate Limiting

Currently no rate limiting is enforced. In production, implement rate limiting based on:
- IP address
- API key (when authentication is added)
- Endpoint sensitivity

---

## Authentication

**Current Status:** No authentication required (development mode)

**Production Requirements:**
- Add JWT-based authentication
- API keys for programmatic access
- Role-based access control (RBAC)

---

## OpenAPI Documentation

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

---

## Testing

### Health Check
```bash
curl "http://localhost:8000/api/health"
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development"
}
```

### Readiness Check
```bash
curl "http://localhost:8000/api/health/ready"
```

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "anthropic": "configured",
    "hyperliquid": "configured"
  },
  "timestamp": "2024-02-10T12:00:00Z"
}
```

---

## Next Steps

1. **Implement WebSocket API** for real-time updates
2. **Add Authentication** (JWT tokens, API keys)
3. **Add Rate Limiting** to prevent abuse
4. **Implement Caching** (Redis) for frequently accessed data
5. **Add Request Logging** for audit trail
6. **Create Client Libraries** (Python, TypeScript)
7. **Write Integration Tests** for all endpoints
8. **Deploy to Production** with proper monitoring

---

## Support

For issues or questions:
- Check the OpenAPI documentation at `/api/docs`
- Review the source code in `backend/src/api/routes/`
- Check application logs for detailed error information
