# Hyperliquid Trading Bot Suite - Implementation Plan

## Executive Summary

An AI-powered trading system that learns strategies from educational content (PDFs, YouTube videos), extracts rules into a structured knowledge base, executes trades via a fast pattern detection engine, and self-improves through outcome feedback.

**Key Innovation:** Hybrid architecture — LLM for learning/reasoning, structured engine for detection/execution.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HYPERLIQUID TRADING BOT SUITE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────┐     ┌─────────────────────┐                       │
│  │   INGESTION LAYER    │     │   KNOWLEDGE BASE    │                       │
│  │                      │     │                     │                       │
│  │  ┌────────────────┐  │     │  ┌───────────────┐  │                       │
│  │  │ PDF Processor  │──┼────▶│  │ Strategy Rules│  │                       │
│  │  └────────────────┘  │     │  │ (Structured)  │  │                       │
│  │  ┌────────────────┐  │     │  └───────────────┘  │                       │
│  │  │ Video Pipeline │──┼────▶│  ┌───────────────┐  │                       │
│  │  │ (YT + Frames)  │  │     │  │ Trade History │  │                       │
│  │  └────────────────┘  │     │  │ + Outcomes    │  │                       │
│  │  ┌────────────────┐  │     │  └───────────────┘  │                       │
│  │  │ LLM Extractor  │──┼────▶│  ┌───────────────┐  │                       │
│  │  │ (Claude)       │  │     │  │ Learning Log  │  │                       │
│  │  └────────────────┘  │     │  │ (What works)  │  │                       │
│  └──────────────────────┘     │  └───────────────┘  │                       │
│                               └──────────┬──────────┘                       │
│                                          │                                  │
│  ┌───────────────────────────────────────▼──────────────────────────────┐  │
│  │                      PATTERN DETECTION ENGINE                         │  │
│  │                           (Python, Fast)                              │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │  │
│  │  │ Candle      │  │ Market       │  │ Confluence   │  │ Signal    │  │  │
│  │  │ Patterns    │  │ Structure    │  │ Scorer       │  │ Generator │  │  │
│  │  └─────────────┘  └──────────────┘  └──────────────┘  └───────────┘  │  │
│  └───────────────────────────────────────┬──────────────────────────────┘  │
│                                          │                                  │
│       ┌──────────────────────────────────┼────────────────────────────┐    │
│       │                                  │                             │    │
│       ▼                                  ▼                             ▼    │
│  ┌─────────────┐                 ┌──────────────┐              ┌──────────┐│
│  │ BACKTESTING │                 │ TRADE        │              │ LIVE     ││
│  │ + REPLAY    │                 │ REASONER     │              │ TRADING  ││
│  │ (Nuxt/TV)   │                 │ (LLM)        │              │ (HL MCP) ││
│  └─────────────┘                 └──────────────┘              └──────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Ingestion Pipeline

**Purpose:** Transform educational content into structured strategy rules.

#### 1.1 PDF Processor
- Extract text and images from PDF documents
- Identify chart screenshots and their context
- Pass to LLM for rule extraction

**Tech:** Python, `pdfplumber`/`PyMuPDF`, PIL

#### 1.2 Video Pipeline
- Accept YouTube URLs or playlist links
- Download and transcribe audio (Whisper)
- Extract frames at 10-second intervals
- Dedupe identical/similar frames (perceptual hashing)
- Correlate transcript timestamps with frames

**Tech:** Python, `yt-dlp`, `whisper`, `ffmpeg`, `imagehash`

#### 1.3 LLM Strategy Extractor
- Analyze text + images together (multimodal)
- Extract structured rules from natural language explanations
- Output: JSON-structured strategy rules

**Tech:** Claude API (Opus for extraction, Sonnet for reasoning)

---

### 2. Knowledge Base

**Purpose:** Store and retrieve strategy rules, trade outcomes, and learnings.

#### 2.1 Strategy Rules Store
Schema:
```typescript
interface StrategyRule {
  id: string;
  name: string;
  source: { type: 'pdf' | 'video'; ref: string; timestamp?: number };
  entryType: 'LE' | 'small_wick' | 'steeper_wick' | 'celery' | 'breakout' | 'fakeout' | 'onion';
  conditions: PatternCondition[];
  confluenceRequired: TimeframeAlignment[];
  riskParams: { riskPercent: number; tpLevels: number[]; slDistance: string };
  confidence: number; // Updated based on outcomes
  createdAt: Date;
  lastUsed: Date;
}

interface PatternCondition {
  type: 'candle' | 'structure' | 'zone' | 'cycle';
  timeframe: '4H' | '1H' | '30M' | '15M' | '5M';
  params: Record<string, any>; // e.g., { wickRatio: '>2', closePosition: 'upper_third' }
}
```

#### 2.2 Trade History Store
Schema:
```typescript
interface TradeRecord {
  id: string;
  strategyRuleId: string;
  asset: string;
  direction: 'long' | 'short';
  entryPrice: number;
  entryTime: Date;
  exitPrice?: number;
  exitTime?: Date;
  exitReason?: 'tp1' | 'tp2' | 'sl' | 'breakeven' | 'momentum';
  outcome: 'win' | 'loss' | 'breakeven' | 'pending';
  pnlR: number; // P&L in R multiples
  reasoning: string; // LLM explanation
  priceActionContext: PriceActionSnapshot;
}

interface PriceActionSnapshot {
  timeframes: Record<string, CandleData[]>;
  structureNotes: string[];
  zoneInteractions: string[];
}
```

#### 2.3 Learning Log
Stores insights from trade outcomes:
```typescript
interface LearningEntry {
  id: string;
  strategyRuleId: string;
  insight: string; // e.g., "LE pattern at 15M fails when 4H is in range phase"
  supportingTrades: string[];
  confidence: number;
  createdAt: Date;
}
```

**Tech:** PostgreSQL + pgvector (for semantic search), Redis (caching)

---

### 3. Pattern Detection Engine

**Purpose:** Fast, rule-based pattern matching on price data.

#### 3.1 Candle Pattern Detector
- LE candle detection (wick ratios, close position, context)
- Small wick, steeper wick patterns
- Celery play detection

#### 3.2 Market Structure Analyzer
- Higher highs/lows, lower highs/lows
- Break of structure (BOS) detection
- Change of character (ChoCH) detection
- Support/resistance zone identification

#### 3.3 Market Cycle Classifier
- Drive phase detection (momentum, strong candles)
- Range phase detection (consolidation, equilibrium)
- Liquidity phase detection (sweeps, stop hunts)

#### 3.4 Confluence Scorer
- Multi-timeframe alignment scoring
- Higher TF bias + lower TF entry validation
- Outputs: confluence score, aligned rules, entry signal

**Tech:** Python, NumPy, Pandas (compiled with Cython for speed)

---

### 4. Trade Reasoner

**Purpose:** LLM explains trade decisions in price action terms.

When a signal triggers:
1. Gather context (all timeframes, structure, zones)
2. Query LLM with context + matched rule
3. Generate explanation: why trade taken, expected PA, risks
4. Log to trade history

**Tech:** Claude API (Sonnet for speed), structured output parsing

---

### 5. Backtesting + Replay Dashboard

**Purpose:** TradingView-style visual replay of strategy performance.

#### 5.1 Data Layer
- Ingest CSV from TradingView exports
- Poll Hyperliquid API for live/historical data
- Cache in PostgreSQL + Redis
- Serve via REST/WebSocket API

#### 5.2 Replay Engine
- Stream candles sequentially (configurable speed)
- Trigger pattern detection on each candle
- Record signals, entries, exits
- Calculate statistics (win rate, profit factor, etc.)

#### 5.3 Frontend Dashboard
- TradingView Lightweight Charts library
- Multi-timeframe chart panels
- Signal/trade markers on chart
- Trade reasoning sidebar
- Performance metrics panel
- Replay controls (play, pause, speed, jump)

**Tech:** Nuxt 3, TradingView Lightweight Charts, Tailwind CSS, WebSockets

---

### 6. Live Trading Integration

**Purpose:** Execute trades on Hyperliquid DEX.

#### 6.1 Hyperliquid MCP Client
- Connect via MCP protocol
- Paper trading mode (simulated)
- Live trading mode (real orders)

#### 6.2 Position Manager
- Multi-TP exit logic (TP1 at 1R, TP2 at 2R)
- Stop loss placement
- Breakeven trailing
- Momentum-based early exit

#### 6.3 Risk Manager
- 2% risk per trade
- Position sizing based on SL distance
- Max concurrent positions
- Daily loss limits

**Tech:** Python, Hyperliquid SDK/MCP, asyncio

---

## Data Flow

### Ingestion Flow
```
PDF/YouTube → Extract Content → LLM Analysis → Structured Rules → Knowledge Base
                    ↓
              Frame + Transcript
              Correlation
```

### Trading Flow
```
Price Data → Pattern Detection → Confluence Check → Signal Generated
                                                          ↓
                                               Trade Reasoner (LLM)
                                                          ↓
                                               Execute Trade (or log in backtest)
                                                          ↓
                                               Update Knowledge Base
                                                          ↓
                                               Learn from Outcome
```

---

## Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Backend Core | Python 3.11+, FastAPI |
| Pattern Engine | Python, NumPy, Pandas, Cython |
| Database | PostgreSQL 15 + pgvector, Redis |
| LLM | Claude API (Opus for extraction, Sonnet for reasoning) |
| Video Processing | yt-dlp, Whisper, FFmpeg, imagehash |
| PDF Processing | pdfplumber, PyMuPDF, Pillow |
| Frontend | Nuxt 3, TradingView Lightweight Charts, Tailwind CSS |
| Real-time | WebSockets (ws), Server-Sent Events |
| Trading | Hyperliquid SDK, MCP Protocol |
| Infrastructure | Docker, Docker Compose |

---

## Directory Structure

```
hyperliquid-trading-bot-suite/
├── backend/
│   ├── src/
│   │   ├── ingestion/
│   │   │   ├── pdf_processor.py
│   │   │   ├── video_pipeline.py
│   │   │   ├── llm_extractor.py
│   │   │   └── __init__.py
│   │   ├── knowledge/
│   │   │   ├── models.py
│   │   │   ├── repository.py
│   │   │   └── __init__.py
│   │   ├── detection/
│   │   │   ├── candle_patterns.py
│   │   │   ├── market_structure.py
│   │   │   ├── cycle_classifier.py
│   │   │   ├── confluence_scorer.py
│   │   │   └── __init__.py
│   │   ├── trading/
│   │   │   ├── reasoner.py
│   │   │   ├── hyperliquid_client.py
│   │   │   ├── position_manager.py
│   │   │   ├── risk_manager.py
│   │   │   └── __init__.py
│   │   ├── backtest/
│   │   │   ├── engine.py
│   │   │   ├── data_loader.py
│   │   │   ├── statistics.py
│   │   │   └── __init__.py
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   ├── websocket.py
│   │   │   └── main.py
│   │   └── config.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── components/
│   │   │   ├── Chart/
│   │   │   ├── TradePanel/
│   │   │   ├── ReplayControls/
│   │   │   └── StrategyManager/
│   │   ├── pages/
│   │   ├── composables/
│   │   └── layouts/
│   ├── nuxt.config.ts
│   └── package.json
├── docker-compose.yml
├── specs/
└── README.md
```

---

## Tasks

### Phase 1: Foundation (Parallel)

- [ ] Set up project structure and configuration @id(project-setup) @role(builder)
  - **Files:** Create directory structure, `backend/pyproject.toml`, `backend/src/config.py`, `docker-compose.yml`
  - **Acceptance:**
    - Python project with Poetry/pip dependencies defined
    - Docker Compose with PostgreSQL, Redis services
    - Environment configuration (`.env.example`)
    - Basic FastAPI app skeleton running

- [ ] Define core data models and types @id(core-models) @role(builder)
  - **Files:** `backend/src/knowledge/models.py`, `backend/src/types/`
  - **Acceptance:**
    - StrategyRule, PatternCondition, TradeRecord, LearningEntry models defined
    - Pydantic models for API validation
    - SQLAlchemy models for database
    - Type exports for all modules

- [ ] Set up database schema and migrations @id(database-setup) @depends(core-models) @role(builder)
  - **Files:** `backend/src/database/`, Alembic migrations
  - **Acceptance:**
    - PostgreSQL schema created via Alembic
    - pgvector extension enabled
    - Redis connection configured
    - Repository base classes implemented

- [ ] Create knowledge base repository layer @id(knowledge-repo) @depends(database-setup) @role(builder)
  - **Files:** `backend/src/knowledge/repository.py`
  - **Acceptance:**
    - CRUD operations for StrategyRule, TradeRecord, LearningEntry
    - Semantic search via pgvector for similar rules
    - Caching layer with Redis
    - Unit tests passing

### Phase 2: Ingestion Pipeline (Parallel after Phase 1)

- [ ] Implement PDF processor @id(pdf-processor) @depends(core-models) @role(builder)
  - **Files:** `backend/src/ingestion/pdf_processor.py`
  - **Acceptance:**
    - Extract text from PDF pages
    - Extract and save images with page/position metadata
    - Handle multi-column layouts
    - Return structured extraction result
    - Unit tests with sample PDFs

- [ ] Implement video pipeline @id(video-pipeline) @depends(core-models) @role(builder)
  - **Files:** `backend/src/ingestion/video_pipeline.py`
  - **Acceptance:**
    - Download YouTube video/playlist via yt-dlp
    - Transcribe audio with Whisper (word-level timestamps)
    - Extract frames every 10 seconds
    - Dedupe similar frames via perceptual hashing
    - Correlate transcript segments with frames
    - Return structured extraction result

- [ ] Implement LLM strategy extractor @id(llm-extractor) @depends(core-models) @role(builder)
  - **Files:** `backend/src/ingestion/llm_extractor.py`
  - **Acceptance:**
    - Accept text + images as input
    - Prompt engineering for strategy rule extraction
    - Parse LLM response into StrategyRule objects
    - Handle extraction failures gracefully
    - Batch processing for efficiency

- [ ] Create ingestion orchestrator @id(ingestion-orchestrator) @depends(pdf-processor,video-pipeline,llm-extractor,knowledge-repo) @role(builder)
  - **Files:** `backend/src/ingestion/orchestrator.py`
  - **Acceptance:**
    - Unified API for PDF and video ingestion
    - Pipeline: extract → analyze → store
    - Progress tracking and resumability
    - Error handling and retry logic
    - Integration tests

### Phase 3: Pattern Detection Engine (Parallel after Phase 1)

- [ ] Implement candle pattern detector @id(candle-patterns) @depends(core-models) @role(builder)
  - **Files:** `backend/src/detection/candle_patterns.py`
  - **Acceptance:**
    - LE candle detection (configurable params)
    - Small wick pattern detection
    - Steeper wick pattern detection
    - Celery play detection
    - All patterns return confidence scores
    - Unit tests with known patterns

- [ ] Implement market structure analyzer @id(market-structure) @depends(core-models) @role(builder)
  - **Files:** `backend/src/detection/market_structure.py`
  - **Acceptance:**
    - Swing high/low detection
    - Higher high/low, lower high/low classification
    - Break of structure (BOS) detection
    - Change of character (ChoCH) detection
    - Support/resistance zone identification
    - Unit tests with historical data

- [ ] Implement market cycle classifier @id(cycle-classifier) @depends(market-structure) @role(builder)
  - **Files:** `backend/src/detection/cycle_classifier.py`
  - **Acceptance:**
    - Drive phase detection
    - Range phase detection
    - Liquidity phase detection
    - Smooth transitions between phases
    - Unit tests with labeled examples

- [ ] Implement confluence scorer @id(confluence-scorer) @depends(candle-patterns,market-structure,cycle-classifier) @role(builder)
  - **Files:** `backend/src/detection/confluence_scorer.py`
  - **Acceptance:**
    - Multi-timeframe data aggregation
    - Higher TF bias determination
    - Lower TF entry validation
    - Confluence score calculation
    - Signal generation with matched rules
    - Integration tests

### Phase 4: Trade Reasoning and Execution (After Phase 3)

- [ ] Implement trade reasoner @id(trade-reasoner) @depends(confluence-scorer,knowledge-repo) @role(builder)
  - **Files:** `backend/src/trading/reasoner.py`
  - **Acceptance:**
    - Gather multi-TF context for signal
    - Query LLM with structured prompt
    - Parse reasoning into trade explanation
    - Include expected price action
    - Include risk assessment
    - Store reasoning in trade record

- [ ] Implement Hyperliquid MCP client @id(hyperliquid-client) @role(builder)
  - **Files:** `backend/src/trading/hyperliquid_client.py`
  - **Acceptance:**
    - Connect to Hyperliquid via MCP
    - Paper trading mode (simulated fills)
    - Live trading mode (real orders)
    - Order types: market, limit, stop
    - Position queries
    - Error handling and reconnection

- [ ] Implement position manager @id(position-manager) @depends(hyperliquid-client) @role(builder)
  - **Files:** `backend/src/trading/position_manager.py`
  - **Acceptance:**
    - Multi-TP exit logic (TP1 at 1R, TP2 at 2R)
    - Stop loss placement and updates
    - Breakeven trailing activation
    - Momentum-based exit detection
    - Position state tracking

- [ ] Implement risk manager @id(risk-manager) @depends(position-manager) @role(builder)
  - **Files:** `backend/src/trading/risk_manager.py`
  - **Acceptance:**
    - 2% risk per trade calculation
    - Position sizing based on SL distance
    - Max concurrent positions enforcement
    - Daily loss limit checks
    - Trade approval/rejection logic

### Phase 5: Backtesting Engine (After Phase 3)

- [ ] Implement data loader @id(data-loader) @depends(core-models) @role(builder)
  - **Files:** `backend/src/backtest/data_loader.py`
  - **Acceptance:**
    - Load TradingView CSV exports
    - Fetch Hyperliquid historical data
    - Multi-timeframe data alignment
    - Data caching and storage
    - Data validation and cleaning

- [ ] Implement backtest engine @id(backtest-engine) @depends(data-loader,confluence-scorer,trade-reasoner) @role(builder)
  - **Files:** `backend/src/backtest/engine.py`
  - **Acceptance:**
    - Sequential candle replay
    - Pattern detection on each candle
    - Signal generation and trade simulation
    - Multi-TP/SL execution simulation
    - Trade logging with timestamps
    - Configurable replay speed

- [ ] Implement backtest statistics @id(backtest-stats) @depends(backtest-engine) @role(builder)
  - **Files:** `backend/src/backtest/statistics.py`
  - **Acceptance:**
    - Win rate calculation
    - Profit factor
    - Max drawdown
    - Sharpe ratio
    - Per-strategy breakdown
    - Equity curve generation

### Phase 6: API Layer (After Phases 4 & 5)

- [ ] Create REST API endpoints @id(rest-api) @depends(ingestion-orchestrator,backtest-engine,risk-manager) @role(builder)
  - **Files:** `backend/src/api/routes/`
  - **Acceptance:**
    - POST /ingest/pdf - Upload and process PDF
    - POST /ingest/video - Submit YouTube URL
    - GET /strategies - List strategy rules
    - GET /strategies/{id} - Get strategy details
    - POST /backtest - Start backtest
    - GET /backtest/{id}/status - Backtest status
    - GET /trades - List trades
    - OpenAPI documentation

- [ ] Implement WebSocket streaming @id(websocket-api) @depends(backtest-engine) @role(builder)
  - **Files:** `backend/src/api/websocket.py`
  - **Acceptance:**
    - Real-time backtest candle streaming
    - Signal notifications
    - Trade execution updates
    - Connection management
    - Heartbeat/reconnection

### Phase 7: Frontend Dashboard (After Phase 6)

- [ ] Set up Nuxt 3 project with TradingView @id(frontend-setup) @role(builder)
  - **Files:** `frontend/` (new Nuxt project)
  - **Acceptance:**
    - Nuxt 3 with TypeScript
    - TradingView Lightweight Charts integrated
    - Tailwind CSS configured
    - Basic layout structure
    - API client configured

- [ ] Create chart component with multi-timeframe @id(chart-component) @depends(frontend-setup) @role(builder)
  - **Files:** `frontend/app/components/Chart/`
  - **Acceptance:**
    - Multi-panel chart layout (4H, 1H, 15M, 5M)
    - Synchronized scrolling/zooming
    - Candle rendering
    - Volume overlay
    - Custom theme matching design

- [ ] Create trade markers and overlays @id(chart-markers) @depends(chart-component) @role(builder)
  - **Files:** `frontend/app/components/Chart/markers/`
  - **Acceptance:**
    - Entry/exit markers
    - TP/SL level lines
    - Support/resistance zones
    - Pattern annotations
    - Signal indicators

- [ ] Create replay controls component @id(replay-controls) @depends(chart-component,websocket-api) @role(builder)
  - **Files:** `frontend/app/components/ReplayControls/`
  - **Acceptance:**
    - Play/pause button
    - Speed selector (1x, 2x, 5x, 10x)
    - Jump to date
    - Progress bar
    - WebSocket integration

- [ ] Create trade panel component @id(trade-panel) @depends(frontend-setup) @role(builder)
  - **Files:** `frontend/app/components/TradePanel/`
  - **Acceptance:**
    - Active trades list
    - Trade history list
    - Trade detail view with reasoning
    - P&L display
    - Strategy attribution

- [ ] Create strategy manager component @id(strategy-manager) @depends(frontend-setup) @role(builder)
  - **Files:** `frontend/app/components/StrategyManager/`
  - **Acceptance:**
    - Strategy list with status
    - Strategy detail view
    - Enable/disable strategies
    - Ingestion status
    - Performance per strategy

- [ ] Create main dashboard page @id(dashboard-page) @depends(chart-component,chart-markers,replay-controls,trade-panel,strategy-manager) @role(builder)
  - **Files:** `frontend/app/pages/index.vue`
  - **Acceptance:**
    - Responsive layout
    - All components integrated
    - Data fetching and state management
    - Real-time updates via WebSocket
    - Dark theme

### Phase 8: Learning System (After Phase 4)

- [ ] Implement outcome analyzer @id(outcome-analyzer) @depends(knowledge-repo,backtest-stats) @role(builder)
  - **Files:** `backend/src/learning/outcome_analyzer.py`
  - **Acceptance:**
    - Analyze trade outcomes by strategy
    - Identify failure patterns
    - Identify success patterns
    - Generate learning entries
    - Update strategy confidence scores

- [ ] Implement feedback loop @id(feedback-loop) @depends(outcome-analyzer,trade-reasoner) @role(builder)
  - **Files:** `backend/src/learning/feedback_loop.py`
  - **Acceptance:**
    - Inject learning context into trade reasoner
    - Adjust signal confidence based on learnings
    - Track improvement over time
    - A/B test strategy variations

### Phase 9: Integration & Polish

- [ ] End-to-end integration testing @id(e2e-testing) @depends(dashboard-page,feedback-loop) @role(builder)
  - **Acceptance:**
    - Ingest sample PDF → generate rules
    - Ingest sample video → generate rules
    - Run backtest with rules → see replay
    - Verify trade reasoning accuracy
    - Verify learning loop updates

- [ ] Security review @id(security-review) @depends(rest-api,hyperliquid-client) @role(security-reviewer)
  - **Acceptance:**
    - API authentication implemented
    - Secrets management reviewed
    - Input validation comprehensive
    - No sensitive data in logs
    - Hyperliquid credentials secured

- [ ] Code review - Backend @id(backend-review) @depends(e2e-testing) @role(reviewer)
  - **Acceptance:**
    - Code quality and consistency
    - Test coverage adequate
    - Error handling complete
    - Documentation present
    - Performance acceptable

- [ ] Code review - Frontend @id(frontend-review) @depends(dashboard-page) @role(reviewer)
  - **Acceptance:**
    - Component structure clean
    - State management appropriate
    - Accessibility basics
    - Responsive design
    - No console errors

- [ ] Documentation and deployment guide @id(documentation) @depends(backend-review,frontend-review) @role(builder)
  - **Files:** `README.md`, `docs/`
  - **Acceptance:**
    - Setup instructions complete
    - API documentation
    - Configuration guide
    - Deployment guide
    - Architecture overview

---

## Task Dependency Graph

```
Phase 1 (Foundation) - Parallel
├── project-setup
├── core-models
├── database-setup ← core-models
└── knowledge-repo ← database-setup

Phase 2 (Ingestion) - Parallel after Phase 1
├── pdf-processor ← core-models
├── video-pipeline ← core-models
├── llm-extractor ← core-models
└── ingestion-orchestrator ← pdf-processor, video-pipeline, llm-extractor, knowledge-repo

Phase 3 (Detection) - Parallel after Phase 1
├── candle-patterns ← core-models
├── market-structure ← core-models
├── cycle-classifier ← market-structure
└── confluence-scorer ← candle-patterns, market-structure, cycle-classifier

Phase 4 (Trading) - After Phase 3
├── trade-reasoner ← confluence-scorer, knowledge-repo
├── hyperliquid-client (parallel)
├── position-manager ← hyperliquid-client
└── risk-manager ← position-manager

Phase 5 (Backtesting) - After Phase 3
├── data-loader ← core-models
├── backtest-engine ← data-loader, confluence-scorer, trade-reasoner
└── backtest-stats ← backtest-engine

Phase 6 (API) - After Phases 4 & 5
├── rest-api ← ingestion-orchestrator, backtest-engine, risk-manager
└── websocket-api ← backtest-engine

Phase 7 (Frontend) - After Phase 6
├── frontend-setup
├── chart-component ← frontend-setup
├── chart-markers ← chart-component
├── replay-controls ← chart-component, websocket-api
├── trade-panel ← frontend-setup
├── strategy-manager ← frontend-setup
└── dashboard-page ← all above

Phase 8 (Learning) - After Phase 4
├── outcome-analyzer ← knowledge-repo, backtest-stats
└── feedback-loop ← outcome-analyzer, trade-reasoner

Phase 9 (Integration)
├── e2e-testing ← dashboard-page, feedback-loop
├── security-review ← rest-api, hyperliquid-client
├── backend-review ← e2e-testing
├── frontend-review ← dashboard-page
└── documentation ← backend-review, frontend-review
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| LLM extraction accuracy | Iterative prompt engineering, human review samples |
| Video processing cost | Smart frame sampling, batch processing, caching |
| Pattern detection accuracy | Extensive backtesting, confidence thresholds |
| Real-time performance | Cython compilation, Redis caching, async processing |
| Hyperliquid API changes | Abstract client interface, paper trading first |

---

## Success Criteria

1. **Ingestion:** Successfully extract strategy rules from 5+ PDFs and 10+ videos
2. **Detection:** Pattern detection matches manual analysis in 80%+ cases
3. **Backtesting:** Complete 1-year backtest in <5 minutes
4. **Learning:** Demonstrable improvement in strategy confidence over time
5. **Live Trading:** Execute paper trades with full reasoning logged

---

## Estimated Timeline

| Phase | Duration | Can Parallelize |
|-------|----------|-----------------|
| Phase 1: Foundation | 3-4 days | Yes (4 tasks) |
| Phase 2: Ingestion | 5-7 days | Yes (3 tasks + integration) |
| Phase 3: Detection | 5-7 days | Yes (3 tasks + integration) |
| Phase 4: Trading | 4-5 days | Partial (2 parallel tracks) |
| Phase 5: Backtesting | 4-5 days | Sequential |
| Phase 6: API | 3-4 days | Yes (2 tasks) |
| Phase 7: Frontend | 7-10 days | Yes (5 parallel tasks) |
| Phase 8: Learning | 3-4 days | Sequential |
| Phase 9: Integration | 5-7 days | Partial |

**Total: ~6-8 weeks with parallel execution**

---

## Next Steps

1. Review this plan with stakeholder
2. Prioritize MVP scope if needed
3. Begin Phase 1 tasks in parallel
4. Set up CI/CD pipeline
5. Schedule regular progress reviews
