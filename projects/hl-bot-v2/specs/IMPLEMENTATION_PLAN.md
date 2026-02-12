# HL-Bot-V2: AI-Powered Trading Research & Execution System

## Implementation Plan

**Version:** 1.0  
**Date:** 2025-02-11  
**Status:** SPEC COMPLETE

---

## 1. Executive Summary

An AI-powered trading research platform that:
1. **Ingests educational content** (YouTube videos, PDFs) → LLM extracts strategy rules
2. **Backtests with visual replay** → TradingView-style candle-by-candle streaming
3. **Learns continuously** → Each trade outcome refines strategy effectiveness
4. **Executes live trades** → Hyperliquid DEX via MCP integration

**Core Innovation:** Hybrid architecture where LLMs handle learning/reasoning while a structured engine handles fast pattern detection and execution.

---

## 2. Architecture Overview

### 2.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              HL-BOT-V2 ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                         CONTENT INGESTION LAYER                          │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │   │
│   │  │   YouTube   │  │    PDF      │  │   Image     │  │   LLM Strategy │  │   │
│   │  │  Processor  │  │  Processor  │  │  Analyzer   │  │   Extractor    │  │   │
│   │  │ (yt-dlp +   │  │ (PyMuPDF +  │  │  (Claude    │  │   (Claude)     │  │   │
│   │  │  Whisper)   │  │  pdfplumber)│  │   Vision)   │  │                │  │   │
│   │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └───────┬────────┘  │   │
│   └─────────┼────────────────┼────────────────┼─────────────────┼───────────┘   │
│             └────────────────┴────────────────┴─────────────────┘               │
│                                        │                                         │
│                                        ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                          KNOWLEDGE BASE                                  │   │
│   │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │   │
│   │  │  Strategy Rules  │  │   Trade History  │  │   Learning Journal   │   │   │
│   │  │  (PostgreSQL)    │  │   (TimescaleDB)  │  │   (What works/why)   │   │   │
│   │  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘   │   │
│   └───────────┼─────────────────────┼───────────────────────┼───────────────┘   │
│               └─────────────────────┼───────────────────────┘                    │
│                                     ▼                                            │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                      PATTERN DETECTION ENGINE                            │   │
│   │                         (Python + NumPy)                                 │   │
│   │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐   │   │
│   │  │   Candle    │  │   Market     │  │ Multi-TF    │  │   Signal     │   │   │
│   │  │  Patterns   │  │  Structure   │  │ Confluence  │  │  Generator   │   │   │
│   │  │  Detector   │  │  Analyzer    │  │   Scorer    │  │              │   │   │
│   │  └─────────────┘  └──────────────┘  └─────────────┘  └──────────────┘   │   │
│   └─────────────────────────────────┬───────────────────────────────────────┘   │
│                                     │                                            │
│          ┌──────────────────────────┼──────────────────────────┐                │
│          │                          │                          │                 │
│          ▼                          ▼                          ▼                 │
│   ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐        │
│   │   BACKTESTER    │    │  TRADE REASONER  │    │    LIVE TRADING     │        │
│   │   + VISUAL      │    │     (Claude)     │    │   (Hyperliquid)     │        │
│   │    REPLAY       │    │                  │    │                     │        │
│   │  ┌───────────┐  │    │  - Why this      │    │  ┌───────────────┐  │        │
│   │  │ WebSocket │  │    │    setup?        │    │  │  MCP Server   │  │        │
│   │  │ Streaming │  │    │  - Risk assess   │    │  │  (Tool-based) │  │        │
│   │  └───────────┘  │    │  - Learn from    │    │  └───────────────┘  │        │
│   │  ┌───────────┐  │    │    outcomes      │    │  ┌───────────────┐  │        │
│   │  │ Playback  │  │    │                  │    │  │ Paper/Live    │  │        │
│   │  │ Controls  │  │    │                  │    │  │ Mode Toggle   │  │        │
│   │  └───────────┘  │    │                  │    │  └───────────────┘  │        │
│   └─────────────────┘    └──────────────────┘    └─────────────────────┘        │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                    FRONTEND (SvelteKit + lightweight-charts)             │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │   │
│   │  │  Chart View │  │  Playback   │  │   Trade     │  │   Decision     │  │   │
│   │  │  (Multi-TF) │  │  Controls   │  │    Log      │  │   Journal      │  │   │
│   │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────────┘  │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | SvelteKit | Lightweight, reactive, pairs well with lightweight-charts |
| **Charting** | TradingView lightweight-charts | Open-source, purpose-built for financial data |
| **Backend API** | Python + FastAPI | Async support, ML ecosystem, rapid prototyping |
| **Pattern Engine** | Python + NumPy/Pandas | Fast numerical operations for candle analysis |
| **Database** | PostgreSQL + TimescaleDB | Time-series optimized for OHLCV data |
| **Cache/Realtime** | Redis | WebSocket state, session data, pub/sub |
| **LLM** | Claude API (claude-sonnet-4-20250514) | Vision capabilities, structured output, reasoning |
| **Video Processing** | yt-dlp + Whisper | Download + transcribe YouTube content |
| **PDF Processing** | PyMuPDF + pdfplumber | Text + image extraction |
| **Task Queue** | Celery + Redis | Background processing for ingestion |
| **Live Trading** | Hyperliquid Python SDK | Native DEX integration |

### 2.3 Data Flow

```
1. CONTENT INGESTION
   YouTube URL/PDF → Processor → Extracted Text + Images → Claude → Strategy Rules → DB

2. BACKTEST FLOW  
   Historical Data → Candle-by-Candle → Pattern Engine → Signal → Trade Log
        ↓
   WebSocket → Frontend (real-time chart updates)
        ↓
   Post-Trade → Claude Reasoner → Learning Journal → Strategy Refinement

3. LIVE TRADING FLOW
   Market Data → Pattern Engine → Signal → Claude Reasoner (optional) → 
   → Position Sizer → Hyperliquid MCP → Order → Monitor → Exit
```

---

## 3. Component Breakdown

### 3.1 Content Ingestion Layer

**Purpose:** Extract trading strategy knowledge from educational content.

| Component | Responsibility |
|-----------|---------------|
| `YouTubeProcessor` | Download video, extract audio, transcribe with Whisper, extract frames at key moments |
| `PDFProcessor` | Extract text per page, extract embedded images, OCR if needed |
| `ImageAnalyzer` | Send chart images to Claude Vision for pattern identification |
| `StrategyExtractor` | LLM pipeline that converts raw content → structured strategy rules |

**Output Schema:**
```python
class StrategyRule:
    id: str
    name: str                    # "LE Candle at Support"
    description: str             # Human-readable explanation
    timeframes: list[str]        # ["15M", "5M"]
    market_phase: str            # "range", "drive", "liquidity"
    entry_conditions: list[Condition]
    exit_rules: ExitRules
    risk_params: RiskParams
    source: Source               # Where this rule came from
    effectiveness_score: float   # Updated by learning loop
```

### 3.2 Knowledge Base

**Purpose:** Persistent storage for strategies, trades, and learnings.

| Table | Content |
|-------|---------|
| `strategy_rules` | Extracted rules with conditions and parameters |
| `ohlcv_data` | Historical candle data (TimescaleDB hypertable) |
| `trades` | All backtest + live trades with full context |
| `trade_decisions` | LLM reasoning for each trade |
| `learning_journal` | What worked, what didn't, aggregated insights |
| `market_structure` | Cached structure analysis per symbol/timeframe |

### 3.3 Pattern Detection Engine

**Purpose:** Fast, deterministic pattern matching without LLM latency.

| Module | Function |
|--------|----------|
| `candle_patterns.py` | Detect: LE candle, small wick, steeper wick, celery, engulfing, etc. |
| `market_structure.py` | Identify: swings, BOS, CHoCH, order blocks, FVGs, liquidity pools |
| `support_resistance.py` | Calculate: dynamic S/R levels, demand/supply zones |
| `confluence_scorer.py` | Score multi-timeframe alignment (0-100) |
| `signal_generator.py` | Combine all signals into actionable trade setups |

**Key Design:** All detection is rule-based and fast. LLM is only used for:
- Initial rule extraction from content
- Trade reasoning (optional, can be disabled for speed)
- Post-trade analysis and learning

### 3.4 Backtesting Engine

**Purpose:** Simulate strategy on historical data with visual replay.

| Component | Function |
|-----------|----------|
| `BacktestRunner` | Orchestrates candle-by-candle simulation |
| `PositionManager` | Tracks open positions, P&L, equity curve |
| `RiskManager` | Position sizing, max drawdown checks |
| `StreamManager` | WebSocket broadcasting of state updates |
| `PlaybackController` | Play, pause, step, speed, seek to date |

**WebSocket Events:**
```typescript
type WSEvent = 
  | { type: 'candle', data: Candle }
  | { type: 'signal', data: Signal }
  | { type: 'trade_open', data: Trade }
  | { type: 'trade_update', data: TradeUpdate }
  | { type: 'trade_close', data: TradeClosure }
  | { type: 'portfolio', data: Portfolio }
  | { type: 'decision', data: DecisionLog }
```

### 3.5 Trade Reasoner (LLM)

**Purpose:** Explain why trades are taken and learn from outcomes.

| Function | Description |
|----------|-------------|
| `analyze_setup()` | Given a signal, explain the confluence and risk |
| `assess_risk()` | Flag concerns or low-probability setups |
| `review_outcome()` | After trade closes, analyze what worked/didn't |
| `update_learnings()` | Aggregate insights across trades |

**Learning Loop:**
```
Trade Closed → Claude analyzes outcome → Updates learning_journal →
→ Adjusts rule effectiveness_score → Better future decisions
```

### 3.6 Live Trading (Hyperliquid)

**Purpose:** Execute real trades on Hyperliquid DEX.

| Component | Function |
|-----------|----------|
| `HyperliquidClient` | Wrapper around official SDK |
| `MCPServer` | Expose trading tools for Claude orchestration |
| `OrderManager` | Place, modify, cancel orders |
| `PositionMonitor` | Track open positions, trailing stops |
| `PaperMode` | Simulated execution for testing |

**MCP Tools:**
- `get_market_data` - Fetch current prices and orderbook
- `place_order` - Submit market/limit orders
- `modify_order` - Adjust existing orders
- `cancel_order` - Cancel pending orders
- `get_positions` - List open positions
- `get_account` - Account balance and margin

### 3.7 Frontend Dashboard

**Purpose:** Visual interface for backtesting replay and monitoring.

| View | Features |
|------|----------|
| **Chart View** | Multi-timeframe TradingView charts, trade markers, S/R lines |
| **Playback Controls** | Play/pause, step forward/back, speed slider, date picker |
| **Trade Log** | List of all trades with entry/exit, P&L, reasoning link |
| **Decision Journal** | LLM explanations for each trade |
| **Performance Dashboard** | Equity curve, win rate, Sharpe, drawdown |
| **Strategy Manager** | View/edit extracted rules, toggle rules on/off |
| **Content Ingestion** | Upload PDFs, paste YouTube URLs |

---

## 4. Directory Structure

```
hl-bot-v2/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── config.py               # Settings and env vars
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── backtest.py     # Backtest endpoints
│   │   │   │   ├── content.py      # Ingestion endpoints
│   │   │   │   ├── strategy.py     # Strategy CRUD
│   │   │   │   ├── trades.py       # Trade history
│   │   │   │   └── websocket.py    # WS connection handler
│   │   │   └── deps.py             # Dependency injection
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── patterns/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── candles.py      # Candle pattern detection
│   │   │   │   ├── structure.py    # Market structure
│   │   │   │   ├── zones.py        # S/R, supply/demand
│   │   │   │   └── confluence.py   # Multi-TF scoring
│   │   │   ├── engine/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── backtest.py     # Backtest runner
│   │   │   │   ├── signal.py       # Signal generator
│   │   │   │   ├── position.py     # Position management
│   │   │   │   └── risk.py         # Risk calculations
│   │   │   └── market/
│   │   │       ├── __init__.py
│   │   │       ├── data.py         # OHLCV data handling
│   │   │       └── timeframes.py   # Multi-TF alignment
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── youtube.py          # YouTube processor
│   │   │   ├── pdf.py              # PDF processor
│   │   │   ├── images.py           # Image analyzer
│   │   │   └── extractor.py        # Strategy extraction
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # Claude API wrapper
│   │   │   ├── reasoner.py         # Trade reasoner
│   │   │   └── prompts.py          # Prompt templates
│   │   ├── trading/
│   │   │   ├── __init__.py
│   │   │   ├── hyperliquid.py      # HL client
│   │   │   ├── mcp_server.py       # MCP tool server
│   │   │   └── paper.py            # Paper trading
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py           # SQLAlchemy models
│   │   │   ├── session.py          # DB session
│   │   │   └── migrations/         # Alembic migrations
│   │   └── workers/
│   │       ├── __init__.py
│   │       └── tasks.py            # Celery tasks
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_patterns.py
│   │   ├── test_backtest.py
│   │   └── test_ingestion.py
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   │   ├── Chart.svelte           # TradingView chart wrapper
│   │   │   │   ├── ChartMultiTF.svelte    # Multi-timeframe view
│   │   │   │   ├── PlaybackControls.svelte
│   │   │   │   ├── TradeLog.svelte
│   │   │   │   ├── DecisionJournal.svelte
│   │   │   │   ├── EquityCurve.svelte
│   │   │   │   ├── StrategyManager.svelte
│   │   │   │   └── ContentUploader.svelte
│   │   │   ├── stores/
│   │   │   │   ├── backtest.ts       # Backtest state
│   │   │   │   ├── trades.ts         # Trade state
│   │   │   │   ├── websocket.ts      # WS connection
│   │   │   │   └── chart.ts          # Chart data
│   │   │   ├── utils/
│   │   │   │   ├── chart.ts          # Chart utilities
│   │   │   │   ├── format.ts         # Formatting helpers
│   │   │   │   └── api.ts            # API client
│   │   │   └── types/
│   │   │       └── index.ts          # TypeScript types
│   │   ├── routes/
│   │   │   ├── +layout.svelte
│   │   │   ├── +page.svelte          # Dashboard home
│   │   │   ├── backtest/
│   │   │   │   └── +page.svelte      # Backtest replay
│   │   │   ├── strategies/
│   │   │   │   └── +page.svelte      # Strategy manager
│   │   │   ├── trades/
│   │   │   │   └── +page.svelte      # Trade history
│   │   │   └── ingest/
│   │   │       └── +page.svelte      # Content upload
│   │   └── app.html
│   ├── static/
│   ├── package.json
│   ├── svelte.config.js
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── data/
│   ├── csv/                    # TradingView CSV exports
│   └── cache/                  # Processed data cache
│
├── docker-compose.yml          # Full stack orchestration
├── .env.example
└── README.md
```

---

## 5. Interface Definitions

### 5.1 Core Types (Python)

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class Timeframe(str, Enum):
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

class MarketPhase(str, Enum):
    DRIVE = "drive"
    RANGE = "range"
    LIQUIDITY = "liquidity"

class SignalType(str, Enum):
    LONG = "long"
    SHORT = "short"

class PatternType(str, Enum):
    LE_CANDLE = "le_candle"
    SMALL_WICK = "small_wick"
    STEEPER_WICK = "steeper_wick"
    CELERY = "celery"
    ENGULFING = "engulfing"
    # ... more patterns

class SetupType(str, Enum):
    BREAKOUT = "breakout"
    FAKEOUT = "fakeout"
    ONION = "onion"
    PULLBACK = "pullback"

@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: Timeframe

@dataclass
class Zone:
    price_low: float
    price_high: float
    zone_type: str          # "support", "resistance", "demand", "supply"
    strength: float         # 0-1
    touches: int
    last_touch: datetime

@dataclass
class Signal:
    id: str
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    timeframe: Timeframe
    entry_price: float
    stop_loss: float
    take_profit_1: float    # 1R
    take_profit_2: float    # 2R
    take_profit_3: Optional[float]  # Extended
    confluence_score: float  # 0-100
    patterns_detected: list[PatternType]
    setup_type: SetupType
    market_phase: MarketPhase
    higher_tf_bias: SignalType
    reasoning: Optional[str]  # LLM explanation

@dataclass
class Trade:
    id: str
    signal_id: str
    symbol: str
    side: SignalType
    entry_price: float
    entry_time: datetime
    position_size: float
    stop_loss: float
    take_profits: list[float]
    status: str             # "open", "tp1_hit", "tp2_hit", "stopped", "closed"
    exit_price: Optional[float]
    exit_time: Optional[datetime]
    pnl: Optional[float]
    pnl_percent: Optional[float]
    reasoning: str
    post_analysis: Optional[str]

@dataclass
class Portfolio:
    balance: float
    equity: float
    open_positions: int
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
```

### 5.2 API Endpoints

```yaml
# Backtest
POST   /api/backtest/start         # Start backtest session
POST   /api/backtest/stop          # Stop current backtest
POST   /api/backtest/control       # Play/pause/step/speed/seek
GET    /api/backtest/state         # Current backtest state
WS     /ws/backtest/{session_id}   # Real-time updates

# Content Ingestion
POST   /api/ingest/youtube         # Submit YouTube URL
POST   /api/ingest/pdf             # Upload PDF
GET    /api/ingest/jobs            # List processing jobs
GET    /api/ingest/jobs/{id}       # Job status

# Strategies
GET    /api/strategies             # List all strategies
GET    /api/strategies/{id}        # Get strategy details
POST   /api/strategies             # Create strategy
PATCH  /api/strategies/{id}        # Update strategy
DELETE /api/strategies/{id}        # Delete strategy

# Trades
GET    /api/trades                 # List trades (with filters)
GET    /api/trades/{id}            # Get trade details
GET    /api/trades/{id}/decision   # Get LLM reasoning

# Market Data
GET    /api/data/ohlcv             # Get candle data
POST   /api/data/import            # Import CSV data

# Live Trading
GET    /api/trading/status         # Connection status
POST   /api/trading/connect        # Connect to Hyperliquid
GET    /api/trading/positions      # Current positions
POST   /api/trading/paper-mode     # Toggle paper mode
```

### 5.3 WebSocket Protocol

```typescript
// Client -> Server
type ClientMessage = 
  | { action: 'subscribe', channel: string }
  | { action: 'unsubscribe', channel: string }
  | { action: 'control', command: 'play' | 'pause' | 'step' | 'seek', value?: any }

// Server -> Client
type ServerMessage =
  | { type: 'candle', timeframe: string, data: Candle }
  | { type: 'signal', data: Signal }
  | { type: 'trade_open', data: Trade }
  | { type: 'trade_update', data: Partial<Trade> }
  | { type: 'trade_close', data: Trade }
  | { type: 'portfolio', data: Portfolio }
  | { type: 'decision', tradeId: string, reasoning: string }
  | { type: 'structure', timeframe: string, data: MarketStructure }
  | { type: 'zone', data: Zone }
  | { type: 'error', message: string }
```

---

## 6. Key Strategy Concepts (Don Vo / ControllerFX)

### 6.1 Market Cycles

```
DRIVE → RANGE → LIQUIDITY → (repeat)

DRIVE:    Strong directional move, clear trend
RANGE:    Consolidation between support/resistance  
LIQUIDITY: Sweep of stops/liquidity before reversal
```

### 6.2 Multi-Timeframe Confluence

```
4H: Sets the bias (bullish/bearish trend)
1H: Identifies key levels, pullback zones
30M: Confirms structure (BOS/CHoCH)
15M: Entry timeframe, pattern formation
5M:  Fine-tune entry, manage risk
```

### 6.3 Entry Patterns

| Pattern | Description |
|---------|-------------|
| **LE Candle** | Liquidity-to-Entry: sweep of liquidity followed by strong close |
| **Small Wick** | Minimal rejection wick, strong body |
| **Steeper Wick** | Deep wick rejection, accumulation |
| **Celery** | Multiple small candles building pressure |
| **Engulfing** | Full body engulf of previous candle |

### 6.4 Exit Strategy

```
Entry → 
  TP1 at 1R (50% position) →
  Move SL to breakeven →
  TP2 at 2R (remaining 50%) OR
  Trail with structure (swing highs/lows)
```

---

## 7. Tasks

### Phase 1: Foundation (Parallel)

- [ ] Initialize Python backend project with FastAPI, Poetry, and base structure @id(backend-init) @role(builder)
  - Files: backend/pyproject.toml, backend/app/main.py, backend/app/config.py
  - Acceptance: `poetry install` works, `uvicorn app.main:app` starts server on :8000
  - Est: 2h

- [ ] Set up PostgreSQL + TimescaleDB with Alembic migrations @id(db-setup) @role(builder)
  - Files: backend/app/db/*, docker-compose.yml (db service)
  - Acceptance: DB connects, migrations run, hypertable created for OHLCV
  - Est: 3h

- [ ] Initialize SvelteKit frontend with Tailwind and base layout @id(frontend-init) @role(builder)
  - Files: frontend/*, package.json, svelte.config.js
  - Acceptance: `npm run dev` starts, base layout renders
  - Est: 2h

- [ ] Define all TypeScript and Python type definitions @id(types) @role(builder)
  - Files: backend/app/core/types.py, frontend/src/lib/types/index.ts
  - Acceptance: All types from spec implemented, consistent between FE/BE
  - Est: 2h

### Phase 2: Data Layer (Depends: Phase 1)

- [ ] Implement OHLCV data models and repository @id(data-models) @depends(backend-init,db-setup,types) @role(builder)
  - Files: backend/app/db/models.py, backend/app/core/market/data.py
  - Acceptance: Can store/query candles by symbol, timeframe, date range
  - Est: 3h

- [ ] Create CSV import service for TradingView data @id(csv-import) @depends(data-models) @role(builder)
  - Files: backend/app/api/routes/data.py, backend/app/core/market/importer.py
  - Acceptance: Upload CSV → parsed → stored in DB, supports TV format
  - Est: 2h

- [ ] Implement multi-timeframe data alignment @id(tf-alignment) @depends(data-models) @role(builder)
  - Files: backend/app/core/market/timeframes.py
  - Acceptance: Given 5m data, can resample to 15m/30m/1h/4h correctly
  - Est: 2h

### Phase 3: Pattern Detection Engine (Depends: Phase 2)

- [ ] Implement candle pattern detection @id(candle-patterns) @depends(data-models,types) @role(builder)
  - Files: backend/app/core/patterns/candles.py
  - Acceptance: Detects: LE candle, small wick, steeper wick, celery, engulfing
  - Tests: Unit tests with known patterns
  - Est: 4h

- [ ] Implement market structure analysis @id(market-structure) @depends(data-models,types) @role(builder)
  - Files: backend/app/core/patterns/structure.py
  - Acceptance: Identifies: swing H/L, BOS, CHoCH, order blocks, FVGs
  - Tests: Unit tests with annotated data
  - Est: 5h

- [ ] Implement support/resistance zone detection @id(zones) @depends(data-models,types) @role(builder)
  - Files: backend/app/core/patterns/zones.py
  - Acceptance: Finds S/R levels, demand/supply zones, tracks touches
  - Est: 4h

- [ ] Implement multi-timeframe confluence scorer @id(confluence) @depends(candle-patterns,market-structure,zones,tf-alignment) @role(builder)
  - Files: backend/app/core/patterns/confluence.py
  - Acceptance: Scores 0-100 based on TF alignment, returns breakdown
  - Est: 3h

- [ ] Implement signal generator @id(signal-gen) @depends(confluence) @role(builder)
  - Files: backend/app/core/engine/signal.py
  - Acceptance: Combines all detectors → actionable Signal objects
  - Est: 3h

### Phase 4: Backtesting Engine (Depends: Phase 3)

- [ ] Implement position and risk manager @id(position-mgr) @depends(types,data-models) @role(builder)
  - Files: backend/app/core/engine/position.py, backend/app/core/engine/risk.py
  - Acceptance: Position sizing (2% risk), P&L tracking, multi-TP management
  - Est: 4h

- [ ] Implement backtest runner with candle streaming @id(backtest-runner) @depends(signal-gen,position-mgr) @role(builder)
  - Files: backend/app/core/engine/backtest.py
  - Acceptance: Processes candles sequentially, generates signals, executes trades
  - Est: 5h

- [ ] Implement WebSocket streaming for backtest state @id(ws-stream) @depends(backtest-runner,backend-init) @role(builder)
  - Files: backend/app/api/routes/websocket.py
  - Acceptance: Broadcasts candles, signals, trades, portfolio in real-time
  - Est: 3h

- [ ] Implement playback controls (play/pause/step/speed/seek) @id(playback-ctrl) @depends(backtest-runner,ws-stream) @role(builder)
  - Files: backend/app/core/engine/playback.py, API route extensions
  - Acceptance: All controls work, maintains state across pause/resume
  - Est: 3h

### Phase 5: Content Ingestion (Parallel with Phase 4)

- [ ] Implement YouTube video processor @id(youtube-proc) @depends(backend-init) @role(builder)
  - Files: backend/app/ingestion/youtube.py
  - Acceptance: Download video, extract audio, transcribe with Whisper, extract frames
  - Est: 4h

- [ ] Implement PDF processor @id(pdf-proc) @depends(backend-init) @role(builder)
  - Files: backend/app/ingestion/pdf.py
  - Acceptance: Extract text, extract images, OCR if needed
  - Est: 3h

- [ ] Implement LLM client and strategy extractor @id(llm-extractor) @depends(types) @role(builder)
  - Files: backend/app/llm/client.py, backend/app/llm/prompts.py, backend/app/ingestion/extractor.py
  - Acceptance: Takes content → extracts structured StrategyRule objects
  - Est: 5h

- [ ] Implement image analyzer for chart screenshots @id(image-analyzer) @depends(llm-extractor) @role(builder)
  - Files: backend/app/ingestion/images.py
  - Acceptance: Claude Vision identifies patterns, S/R levels from chart images
  - Est: 3h

- [ ] Create Celery workers for background processing @id(workers) @depends(youtube-proc,pdf-proc,llm-extractor) @role(builder)
  - Files: backend/app/workers/tasks.py, celery config
  - Acceptance: Ingestion jobs run in background, status trackable
  - Est: 2h

### Phase 6: Trade Reasoner & Learning (Depends: Phase 4, 5)

- [ ] Implement trade reasoner LLM component @id(trade-reasoner) @depends(llm-extractor,backtest-runner) @role(builder)
  - Files: backend/app/llm/reasoner.py
  - Acceptance: Given signal → explains reasoning, risk assessment
  - Est: 4h

- [ ] Implement learning journal and feedback loop @id(learning-loop) @depends(trade-reasoner,data-models) @role(builder)
  - Files: backend/app/llm/learner.py, DB tables for learnings
  - Acceptance: Post-trade analysis, updates rule effectiveness scores
  - Est: 5h

### Phase 7: Frontend - Chart & Replay (Depends: Phase 4)

- [ ] Integrate TradingView lightweight-charts @id(tv-charts) @depends(frontend-init) @role(builder)
  - Files: frontend/src/lib/components/Chart.svelte
  - Acceptance: Renders candlestick chart, supports dynamic updates
  - Est: 4h

- [ ] Implement multi-timeframe chart view @id(multi-tf-view) @depends(tv-charts) @role(builder)
  - Files: frontend/src/lib/components/ChartMultiTF.svelte
  - Acceptance: Shows 4H, 1H, 15M, 5M synchronized charts
  - Est: 3h

- [ ] Implement trade markers and annotations @id(chart-markers) @depends(tv-charts) @role(builder)
  - Files: Extensions to Chart.svelte
  - Acceptance: Entry/exit markers, S/R lines, zone shading
  - Est: 3h

- [ ] Implement WebSocket store and real-time updates @id(ws-store) @depends(frontend-init) @role(builder)
  - Files: frontend/src/lib/stores/websocket.ts, frontend/src/lib/stores/backtest.ts
  - Acceptance: Connects to backend WS, updates stores reactively
  - Est: 3h

- [ ] Implement playback controls UI @id(playback-ui) @depends(ws-store) @role(builder)
  - Files: frontend/src/lib/components/PlaybackControls.svelte
  - Acceptance: Play/pause, step, speed slider, date picker - all functional
  - Est: 3h

### Phase 8: Frontend - Additional Views (Depends: Phase 7)

- [ ] Implement trade log component @id(trade-log-ui) @depends(ws-store) @role(builder)
  - Files: frontend/src/lib/components/TradeLog.svelte
  - Acceptance: Lists trades, P&L, links to reasoning
  - Est: 2h

- [ ] Implement decision journal view @id(decision-journal-ui) @depends(trade-log-ui) @role(builder)
  - Files: frontend/src/lib/components/DecisionJournal.svelte
  - Acceptance: Shows LLM reasoning for each trade
  - Est: 2h

- [ ] Implement equity curve chart @id(equity-curve) @depends(tv-charts,ws-store) @role(builder)
  - Files: frontend/src/lib/components/EquityCurve.svelte
  - Acceptance: Line chart of portfolio value over time
  - Est: 2h

- [ ] Implement strategy manager UI @id(strategy-mgr-ui) @depends(frontend-init) @role(builder)
  - Files: frontend/src/lib/components/StrategyManager.svelte, route
  - Acceptance: List, view, toggle rules on/off
  - Est: 3h

- [ ] Implement content uploader UI @id(content-upload-ui) @depends(frontend-init) @role(builder)
  - Files: frontend/src/lib/components/ContentUploader.svelte, route
  - Acceptance: YouTube URL input, PDF upload, job status display
  - Est: 2h

- [ ] Implement main dashboard layout and navigation @id(dashboard-layout) @depends(multi-tf-view,playback-ui,trade-log-ui,equity-curve) @role(builder)
  - Files: frontend/src/routes/+layout.svelte, frontend/src/routes/+page.svelte
  - Acceptance: Full dashboard with all components integrated
  - Est: 3h

### Phase 9: Live Trading (Depends: Phase 3, 4)

- [ ] Implement Hyperliquid client wrapper @id(hl-client) @depends(types) @role(builder)
  - Files: backend/app/trading/hyperliquid.py
  - Acceptance: Connect, fetch data, place/cancel orders
  - Est: 4h

- [ ] Implement MCP server for Claude integration @id(mcp-server) @depends(hl-client) @role(builder)
  - Files: backend/app/trading/mcp_server.py
  - Acceptance: Exposes trading tools, Claude can orchestrate trades
  - Est: 4h

- [ ] Implement paper trading mode @id(paper-mode) @depends(hl-client) @role(builder)
  - Files: backend/app/trading/paper.py
  - Acceptance: Simulates order execution without real funds
  - Est: 3h

- [ ] Implement live position monitor @id(position-monitor) @depends(hl-client,ws-stream) @role(builder)
  - Files: backend/app/trading/monitor.py
  - Acceptance: Tracks open positions, trailing stops, broadcasts updates
  - Est: 3h

### Phase 10: Integration & Polish

- [ ] Create Docker Compose for full stack deployment @id(docker) @depends(backend-init,frontend-init,db-setup) @role(builder)
  - Files: docker-compose.yml, Dockerfiles
  - Acceptance: `docker-compose up` starts entire stack
  - Est: 3h

- [ ] Write comprehensive API tests @id(api-tests) @depends(all-api-routes) @role(builder)
  - Files: backend/tests/test_api_*.py
  - Acceptance: >80% coverage on API routes
  - Est: 4h

- [ ] Write pattern detection unit tests @id(pattern-tests) @depends(candle-patterns,market-structure,zones) @role(builder)
  - Files: backend/tests/test_patterns.py
  - Acceptance: Tests with annotated sample data, edge cases covered
  - Est: 4h

- [ ] Create README and setup documentation @id(docs) @role(builder)
  - Files: README.md, docs/*
  - Acceptance: New developer can set up and run system from docs
  - Est: 2h

### Phase 11: Review

- [ ] Security review of API and trading components @id(sec-review) @depends(hl-client,mcp-server,api-tests) @role(security-reviewer)
  - Focus: API auth, rate limiting, key storage, order validation
  - Est: 4h

- [ ] Code review of pattern detection engine @id(pattern-review) @depends(pattern-tests) @role(reviewer)
  - Focus: Accuracy, performance, edge cases
  - Est: 3h

- [ ] Code review of frontend components @id(frontend-review) @depends(dashboard-layout) @role(reviewer)
  - Focus: UX, performance, accessibility
  - Est: 3h

- [ ] End-to-end integration testing @id(e2e-test) @depends(docker,dashboard-layout,backtest-runner) @role(reviewer)
  - Acceptance: Full backtest flow works from data import to visual replay
  - Est: 4h

---

## 8. Dependency Graph

```
Phase 1 (Foundation) - PARALLEL
├── backend-init
├── db-setup
├── frontend-init
└── types

Phase 2 (Data) - Depends: Phase 1
├── data-models ─────────┐
├── csv-import ──────────┤
└── tf-alignment ────────┘

Phase 3 (Patterns) - Depends: Phase 2
├── candle-patterns ─────┐
├── market-structure ────┼── confluence ── signal-gen
└── zones ───────────────┘

Phase 4 (Backtest) - Depends: Phase 3
├── position-mgr ────────┐
├── backtest-runner ─────┼── ws-stream ── playback-ctrl
└────────────────────────┘

Phase 5 (Ingestion) - PARALLEL with Phase 4
├── youtube-proc ────────┐
├── pdf-proc ────────────┼── workers
└── llm-extractor ───────┤
    └── image-analyzer ──┘

Phase 6 (Learning) - Depends: Phase 4, 5
├── trade-reasoner
└── learning-loop

Phase 7 (Frontend Charts) - Depends: Phase 4
├── tv-charts ───────────┐
├── multi-tf-view ───────┼── chart-markers
├── ws-store ────────────┼── playback-ui
└────────────────────────┘

Phase 8 (Frontend Views) - Depends: Phase 7
├── trade-log-ui
├── decision-journal-ui
├── equity-curve
├── strategy-mgr-ui
├── content-upload-ui
└── dashboard-layout (integrates all)

Phase 9 (Live Trading) - Depends: Phase 3, 4
├── hl-client ───────────┐
├── mcp-server ──────────┤
├── paper-mode ──────────┤
└── position-monitor ────┘

Phase 10 (Integration)
├── docker
├── api-tests
├── pattern-tests
└── docs

Phase 11 (Review)
├── sec-review
├── pattern-review
├── frontend-review
└── e2e-test
```

---

## 9. Risk Assessment

| Risk | Mitigation |
|------|------------|
| Pattern detection accuracy | Start with well-documented patterns, extensive testing with labeled data |
| LLM latency in trading loop | LLM is optional for backtest speed, pattern engine is deterministic |
| Hyperliquid API changes | Abstract behind client interface, paper mode for testing |
| Data quality issues | Validation on import, anomaly detection |
| Scope creep | MVP focuses on backtest + replay, live trading is Phase 9 |

---

## 10. Success Criteria

### MVP (Phases 1-8)
- [ ] Can import TradingView CSV data
- [ ] Can run backtest with visual replay
- [ ] Detects: LE candle, engulfing, S/R zones, market structure
- [ ] Scores multi-timeframe confluence
- [ ] Shows trades on chart with markers
- [ ] Displays P&L and equity curve
- [ ] Playback controls work (play/pause/step/seek)

### Full System (Phases 9-11)
- [ ] Can ingest YouTube videos and extract strategies
- [ ] Can ingest PDFs with chart images
- [ ] LLM explains each trade decision
- [ ] System learns from outcomes, updates rule scores
- [ ] Paper trading works on Hyperliquid
- [ ] Live trading ready (with proper safeguards)

---

## 11. Estimated Timeline

| Phase | Duration | Parallelism |
|-------|----------|-------------|
| 1. Foundation | 2 days | 4 tasks parallel |
| 2. Data Layer | 2 days | 3 tasks parallel |
| 3. Pattern Engine | 4 days | 5 tasks (some parallel) |
| 4. Backtesting | 3 days | sequential |
| 5. Ingestion | 3 days | parallel with Phase 4 |
| 6. Learning | 2 days | after 4+5 |
| 7. Frontend Charts | 3 days | parallel after Phase 4 |
| 8. Frontend Views | 3 days | after Phase 7 |
| 9. Live Trading | 3 days | parallel with Phase 8 |
| 10. Integration | 2 days | after core complete |
| 11. Review | 2 days | final |

**Total Estimate:** ~4-5 weeks with parallel execution

---

*Document generated: 2025-02-11*
*Status: SPEC COMPLETE - Ready for builder execution*
