# System Architecture

Technical deep-dive into the Hyperliquid Trading Bot Suite architecture.

---

## Table of Contents

1. [Overview](#overview)
2. [System Components](#system-components)
3. [Data Flow](#data-flow)
4. [Technology Stack](#technology-stack)
5. [API Design](#api-design)
6. [Database Schema](#database-schema)
7. [Trading Engine](#trading-engine)
8. [Scaling Considerations](#scaling-considerations)

---

## Overview

### Design Philosophy

The Hyperliquid Trading Bot Suite follows a **hybrid AI architecture**:

- **LLM for Learning & Reasoning:** Claude extracts strategies from content and explains trade decisions
- **Fast Pattern Detection:** Python/NumPy engine for real-time pattern matching
- **Knowledge Base:** PostgreSQL stores structured rules and learns from outcomes

**Key Principles:**
1. **Separation of Concerns** - Each component has one responsibility
2. **Fail-Safe Trading** - Multiple layers of risk management
3. **Observability** - Every decision is logged and explainable
4. **Scalability** - Stateless services, horizontal scaling ready

---

## System Components

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                │
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │  Web Dashboard  │  │  Mobile App     │  │  API Clients    │        │
│  │  (Nuxt 3)       │  │  (Future)       │  │  (Scripts)      │        │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘        │
│           │                     │                     │                 │
└───────────┼─────────────────────┼─────────────────────┼─────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           EDGE LAYER                                     │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                       Nginx Reverse Proxy                         │  │
│  │  - SSL Termination                                                │  │
│  │  - Rate Limiting                                                  │  │
│  │  - Load Balancing                                                 │  │
│  │  - Static Asset Serving                                           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                                 │
│                                                                          │
│  ┌──────────────────────┐        ┌──────────────────────┐              │
│  │  Backend API         │───────▶│  WebSocket Server    │              │
│  │  (FastAPI)           │        │  (Real-time data)    │              │
│  │                      │        └──────────────────────┘              │
│  │  ┌────────────────┐  │                                               │
│  │  │ REST Endpoints │  │        ┌──────────────────────┐              │
│  │  ├────────────────┤  │        │  Background Workers  │              │
│  │  │ Auth           │  │        │  (Celery/asyncio)    │              │
│  │  │ Ingestion      │  │        │                       │              │
│  │  │ Trading        │  │        │  - PDF Processing    │              │
│  │  │ Backtesting    │  │        │  - Video Pipeline    │              │
│  │  │ Strategies     │  │        │  - LLM Extraction    │              │
│  │  └────────────────┘  │        │  - Backtest Engine   │              │
│  └──────────────────────┘        └──────────────────────┘              │
│                                                                          │
└────────────────┬───────────────────────────┬────────────────────────────┘
                 │                           │
                 ▼                           ▼
┌────────────────────────────┐  ┌──────────────────────────────┐
│     BUSINESS LOGIC         │  │      EXTERNAL SERVICES        │
│                            │  │                               │
│  ┌──────────────────────┐  │  │  ┌────────────────────────┐  │
│  │ Pattern Detection    │  │  │  │  Claude API            │  │
│  │ Engine               │  │  │  │  (Strategy Extraction) │  │
│  │                      │  │  │  └────────────────────────┘  │
│  │ - Candle Patterns    │  │  │                               │
│  │ - Market Structure   │  │  │  ┌────────────────────────┐  │
│  │ - Cycle Classifier   │  │  │  │  Hyperliquid DEX       │  │
│  │ - Confluence Scorer  │  │  │  │  (Trade Execution)     │  │
│  └──────────────────────┘  │  │  └────────────────────────┘  │
│                            │  │                               │
│  ┌──────────────────────┐  │  │  ┌────────────────────────┐  │
│  │ Trade Reasoner (LLM) │  │  │  │  YouTube/PDFs          │  │
│  └──────────────────────┘  │  │  │  (Content Sources)     │  │
│                            │  │  └────────────────────────┘  │
│  ┌──────────────────────┐  │  │                               │
│  │ Risk Manager         │  │  └──────────────────────────────┘
│  └──────────────────────┘  │
│                            │
│  ┌──────────────────────┐  │
│  │ Position Manager     │  │
│  └──────────────────────┘  │
│                            │
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│                     DATA LAYER                              │
│                                                             │
│  ┌───────────────────┐     ┌────────────────────────────┐  │
│  │  PostgreSQL       │     │  Redis                     │  │
│  │  (Primary DB)     │     │  (Cache + Queue)           │  │
│  │                   │     │                            │  │
│  │  - Strategies     │     │  - Session Data            │  │
│  │  - Trades         │     │  - Rate Limiting           │  │
│  │  - Positions      │     │  - Real-time Data          │  │
│  │  - Learning Log   │     │  - Task Queue              │  │
│  │  - Users          │     │  - WebSocket State         │  │
│  │                   │     │                            │  │
│  │  + pgvector       │     └────────────────────────────┘  │
│  │  (Semantic Search)│                                     │
│  └───────────────────┘                                     │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  File Storage (S3/Local)                             │  │
│  │  - PDF uploads                                        │  │
│  │  - Video files                                        │  │
│  │  - Chart screenshots                                  │  │
│  │  - Backups                                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## System Components

### 1. Ingestion Pipeline

**Purpose:** Transform educational content into structured trading rules.

```
PDF/Video → Content Extraction → LLM Analysis → Structured Rules → Knowledge Base
```

**Components:**

**PDF Processor (`backend/src/ingestion/pdf_processor.py`):**
- Extract text and images from PDF
- Identify chart screenshots
- Preserve context (page numbers, sections)

**Video Pipeline (`backend/src/ingestion/video_pipeline.py`):**
```python
class VideoProcessingPipeline:
    async def process(self, url: str) -> ProcessedVideo:
        # 1. Download video
        video_path = await self.downloader.download(url)
        
        # 2. Extract audio
        audio_path = await self.audio_extractor.extract(video_path)
        
        # 3. Transcribe (Whisper)
        transcript = await self.transcriber.transcribe(audio_path)
        
        # 4. Extract frames (1 per 10 seconds)
        frames = await self.frame_extractor.extract(
            video_path, 
            interval=10
        )
        
        # 5. Deduplicate frames (perceptual hashing)
        unique_frames = await self.deduplicator.dedupe(frames)
        
        # 6. Correlate transcript with frames
        annotated_frames = await self.correlator.correlate(
            transcript,
            unique_frames
        )
        
        return ProcessedVideo(
            transcript=transcript,
            frames=annotated_frames,
            metadata={...}
        )
```

**LLM Extractor (`backend/src/ingestion/llm_extractor.py`):**
```python
class StrategyExtractor:
    async def extract(
        self, 
        content: ProcessedContent
    ) -> List[StrategyRule]:
        """Extract structured trading rules using Claude."""
        
        # Build multimodal prompt
        prompt = self._build_extraction_prompt(content)
        
        # Call Claude API
        response = await self.claude_client.create_message(
            model="claude-3-opus-20240229",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *[{"type": "image", "source": img} 
                      for img in content.images[:5]]  # Max 5 images
                ]
            }]
        )
        
        # Parse response into structured rules
        rules = self._parse_strategy_rules(response.content[0].text)
        
        return rules
```

---

### 2. Knowledge Base

**Purpose:** Store and retrieve strategy rules, trade history, learnings.

**Repository Pattern:**

```python
# backend/src/knowledge/repository.py

class StrategyRepository:
    """CRUD + semantic search for strategy rules."""
    
    async def create(self, rule: StrategyRule) -> str:
        """Store new strategy rule."""
        async with self.session() as db:
            db_rule = StrategyRuleModel(**rule.dict())
            
            # Generate embedding for semantic search
            embedding = await self._generate_embedding(rule.description)
            db_rule.embedding = embedding
            
            db.add(db_rule)
            await db.commit()
            return db_rule.id
    
    async def search_similar(
        self, 
        query: str, 
        limit: int = 5
    ) -> List[StrategyRule]:
        """Find similar strategies using pgvector."""
        query_embedding = await self._generate_embedding(query)
        
        async with self.session() as db:
            # pgvector cosine similarity search
            results = await db.execute(
                """
                SELECT *, 
                       1 - (embedding <=> :query_embedding) as similarity
                FROM strategy_rules
                WHERE 1 - (embedding <=> :query_embedding) > 0.7
                ORDER BY similarity DESC
                LIMIT :limit
                """,
                {"query_embedding": query_embedding, "limit": limit}
            )
            return [self._to_model(r) for r in results]
```

**Caching Layer:**

```python
class CachedRepository:
    """Wrap repository with Redis caching."""
    
    def __init__(self, repo: Repository, redis: Redis):
        self.repo = repo
        self.redis = redis
    
    async def get(self, id: str) -> Optional[Model]:
        # Check cache first
        cached = await self.redis.get(f"strategy:{id}")
        if cached:
            return Model.parse_raw(cached)
        
        # Cache miss - fetch from DB
        result = await self.repo.get(id)
        if result:
            # Cache for 1 hour
            await self.redis.setex(
                f"strategy:{id}",
                3600,
                result.json()
            )
        return result
```

---

### 3. Pattern Detection Engine

**Purpose:** Fast, deterministic pattern matching on price data.

**Architecture:**

```python
# backend/src/detection/confluence_scorer.py

class ConfluenceScorer:
    """Orchestrates multi-timeframe pattern detection."""
    
    def __init__(self):
        self.candle_detector = CandlePatternDetector()
        self.structure_analyzer = MarketStructureAnalyzer()
        self.cycle_classifier = MarketCycleClassifier()
    
    async def analyze(
        self,
        symbol: str,
        timeframes: List[str],
        strategy_rules: List[StrategyRule]
    ) -> ConfluenceScore:
        """Analyze all timeframes and calculate confluence."""
        
        # 1. Load price data for all timeframes
        data = await self._load_multi_timeframe_data(
            symbol, 
            timeframes
        )
        
        # 2. Detect patterns on each timeframe
        patterns = {}
        for tf in timeframes:
            patterns[tf] = await asyncio.gather(
                self.candle_detector.detect(data[tf]),
                self.structure_analyzer.analyze(data[tf]),
                self.cycle_classifier.classify(data[tf])
            )
        
        # 3. Check each strategy rule
        matches = []
        for rule in strategy_rules:
            match = self._check_rule_match(rule, patterns)
            if match:
                matches.append(match)
        
        # 4. Calculate confluence score
        score = self._calculate_confluence(matches, patterns)
        
        return ConfluenceScore(
            score=score,
            matched_rules=matches,
            patterns_by_timeframe=patterns,
            higher_tf_bias=self._determine_bias(patterns),
            entry_timeframe=self._best_entry_tf(matches)
        )
```

**Performance Optimization:**

```python
# Use NumPy for vectorized calculations

import numpy as np
from numba import jit

@jit(nopython=True)
def calculate_wick_ratios(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray
) -> np.ndarray:
    """Calculate upper/lower wick ratios for all candles."""
    bodies = np.abs(closes - opens)
    upper_wicks = highs - np.maximum(opens, closes)
    lower_wicks = np.minimum(opens, closes) - lows
    
    # Avoid division by zero
    wick_ratios = np.where(
        bodies > 0,
        (upper_wicks + lower_wicks) / bodies,
        0
    )
    return wick_ratios

# 10-100x faster than Python loops
```

---

### 4. Trading System

**Trade Reasoner:**

```python
# backend/src/trading/trade_reasoner.py

class TradeReasoner:
    """LLM explains trade decisions in price action terms."""
    
    async def explain_signal(
        self,
        signal: TradeSignal,
        context: PriceActionContext
    ) -> TradeReasoning:
        """Generate human-readable trade explanation."""
        
        prompt = f"""
You are an expert price action trader. Analyze this trade signal and explain
the reasoning in clear, concise terms.

## Signal
- Symbol: {signal.symbol}
- Direction: {signal.direction}
- Entry: {signal.entry_price}
- Stop Loss: {signal.stop_loss}
- Take Profit: {signal.take_profit}

## Higher Timeframe Context (4H)
{context.higher_tf_summary}

## Entry Timeframe Context (15M)
{context.entry_tf_summary}

## Matched Rules
{', '.join(r.name for r in signal.matched_rules)}

## Instructions
Explain:
1. WHY this trade makes sense from a price action perspective
2. WHAT confluence factors support it
3. WHAT are the key risks
4. WHAT price action would invalidate the setup

Keep explanation concise (max 4 sentences per point).
"""
        
        response = await self.claude_client.create_message(
            model="claude-3-sonnet-20240229",  # Faster, cheaper
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return TradeReasoning(
            signal_id=signal.id,
            explanation=response.content[0].text,
            confidence=signal.confluence_score,
            timestamp=datetime.utcnow()
        )
```

**Risk Manager:**

```python
# backend/src/trading/risk_manager.py

class RiskManager:
    """Pre-trade risk validation."""
    
    async def check_trade(
        self, 
        order: OrderRequest,
        account: AccountState
    ) -> RiskCheckResult:
        """All checks must pass before order execution."""
        
        checks = [
            self._check_position_size(order, account),
            self._check_daily_loss_limit(account),
            self._check_max_positions(account),
            self._check_price_sanity(order),
            self._check_leverage_limit(order, account),
            await self._check_market_conditions(order.symbol)
        ]
        
        for check in checks:
            if not check.passed:
                return RiskCheckResult(
                    approved=False,
                    reason=check.reason,
                    details=check.details
                )
        
        return RiskCheckResult(approved=True)
    
    def _check_position_size(
        self, 
        order: OrderRequest,
        account: AccountState
    ) -> CheckResult:
        """Enforce 2% risk per trade."""
        
        # Calculate position size based on stop loss
        stop_distance = abs(order.entry_price - order.stop_loss)
        stop_distance_pct = stop_distance / order.entry_price
        
        # Risk amount
        risk_amount = account.balance * 0.02  # 2%
        
        # Position size = risk / stop distance
        position_size = risk_amount / stop_distance
        
        if order.size > position_size:
            return CheckResult(
                passed=False,
                reason=f"Position size {order.size} exceeds max {position_size:.4f} for 2% risk"
            )
        
        return CheckResult(passed=True)
```

**Position Manager:**

```python
# backend/src/trading/position_manager.py

class PositionManager:
    """Manage position lifecycle with multi-TP exits."""
    
    async def monitor_positions(self):
        """Background task to monitor and manage positions."""
        while True:
            positions = await self.get_open_positions()
            
            for position in positions:
                # Get current price
                current_price = await self.get_market_price(
                    position.symbol
                )
                
                # Check exit conditions
                exit_action = await self._check_exit(
                    position, 
                    current_price
                )
                
                if exit_action:
                    await self._execute_exit(
                        position,
                        exit_action,
                        current_price
                    )
            
            await asyncio.sleep(1)  # Check every second
    
    async def _check_exit(
        self,
        position: Position,
        current_price: Decimal
    ) -> Optional[ExitAction]:
        """Determine if position should exit."""
        
        # Calculate P&L in R multiples
        entry = position.entry_price
        stop_distance = abs(entry - position.stop_loss)
        current_pnl = (current_price - entry) if position.side == "long" else (entry - current_price)
        pnl_r = current_pnl / stop_distance
        
        # Check TP levels
        if pnl_r >= 2.0 and position.tp2_hit == False:
            # Close remaining 50% at TP2
            return ExitAction(
                type="tp2",
                quantity=position.remaining_quantity,
                price=current_price
            )
        
        if pnl_r >= 1.0 and position.tp1_hit == False:
            # Close 50% at TP1, move SL to breakeven
            return ExitAction(
                type="tp1",
                quantity=position.quantity * 0.5,
                price=current_price,
                move_stop_to_breakeven=True
            )
        
        # Check stop loss
        hit_stop = (
            (position.side == "long" and current_price <= position.stop_loss) or
            (position.side == "short" and current_price >= position.stop_loss)
        )
        
        if hit_stop:
            return ExitAction(
                type="stop_loss",
                quantity=position.remaining_quantity,
                price=current_price
            )
        
        return None
```

---

## Data Flow

### Trade Execution Flow

```
1. Price Update
   ↓
2. Pattern Detection Engine
   - Candle patterns detected
   - Market structure analyzed
   - Cycle phase classified
   ↓
3. Confluence Scorer
   - Check all strategy rules
   - Calculate confluence score
   - Generate signal (if threshold met)
   ↓
4. Trade Reasoner (LLM)
   - Explain signal
   - Generate reasoning
   ↓
5. Risk Manager
   - Position size check
   - Daily loss check
   - Max positions check
   - Price sanity check
   ↓
6. Position Manager (if approved)
   - Create order
   - Submit to Hyperliquid
   - Monitor for fills
   ↓
7. Position Monitoring
   - Track P&L
   - Check exit conditions
   - Manage stops/TPs
   ↓
8. Trade Completed
   - Record outcome
   - Update statistics
   - Trigger learning loop
```

### Learning Loop Flow

```
1. Trade Completes
   ↓
2. Outcome Analyzer
   - Compare expected vs actual
   - Identify failure patterns
   - Identify success patterns
   ↓
3. Generate Learning Entry
   - "LE pattern fails in range phase on 4H"
   - "Small wick entries work best in drive phase"
   ↓
4. Update Strategy Confidence
   - Increase confidence for winning patterns
   - Decrease for losing patterns
   ↓
5. Feed into Trade Reasoner
   - Include learnings in context
   - Adjust signal confidence
   ↓
6. A/B Test Variations
   - Test modified rules
   - Track performance delta
```

---

## Technology Stack

### Backend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Framework | FastAPI | REST API, WebSocket support |
| ORM | SQLAlchemy | Database abstraction |
| Database | PostgreSQL 15 + pgvector | Primary data store, semantic search |
| Cache/Queue | Redis | Session storage, rate limiting, task queue |
| LLM | Claude (Anthropic) | Strategy extraction, trade reasoning |
| Pattern Engine | NumPy, Pandas, Numba | Fast numerical computations |
| Video Processing | yt-dlp, ffmpeg, Whisper | YouTube download, frame extraction, transcription |
| PDF Processing | pdfplumber, PyMuPDF | Text and image extraction |
| Image Processing | Pillow, imagehash | Frame deduplication |
| Trading SDK | Hyperliquid SDK | DEX integration |
| Testing | pytest, pytest-asyncio | Unit and integration tests |
| Type Checking | mypy | Static type checking |
| Linting | ruff, black | Code quality |

### Frontend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Nuxt 3 | Vue 3 SSR framework |
| Charts | TradingView Lightweight Charts | Financial charts |
| UI Library | Tailwind CSS | Utility-first CSS |
| Icons | Heroicons | Icon set |
| State Management | Pinia | Vue state management |
| HTTP Client | ofetch | API calls |
| WebSocket | Native WebSocket API | Real-time data |
| Type Checking | TypeScript | Type safety |
| Testing | Vitest | Unit testing |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Containerization | Docker | Application packaging |
| Orchestration | Docker Compose | Multi-container management |
| Reverse Proxy | Nginx | SSL, load balancing, rate limiting |
| SSL Certificates | Let's Encrypt (certbot) | Free SSL |
| Monitoring | Prometheus + Grafana | Metrics and dashboards |
| Logging | Journald / ELK | Centralized logs |
| CI/CD | GitHub Actions | Automated testing and deployment |

---

## API Design

### REST API Structure

```
/api
├── /auth
│   ├── POST   /token                  # Login
│   ├── POST   /refresh                # Refresh token
│   └── POST   /logout                 # Logout
│
├── /ingestion
│   ├── POST   /pdf                    # Upload PDF
│   ├── POST   /video                  # Process video
│   └── GET    /status/{job_id}        # Check ingestion status
│
├── /strategies
│   ├── GET    /                       # List strategies
│   ├── GET    /{id}                   # Get strategy details
│   ├── POST   /                       # Create strategy (manual)
│   ├── PUT    /{id}                   # Update strategy
│   ├── DELETE /{id}                   # Delete strategy
│   └── PATCH  /{id}/toggle            # Enable/disable strategy
│
├── /backtesting
│   ├── POST   /start                  # Start backtest
│   ├── GET    /{id}/status            # Backtest status
│   ├── GET    /{id}/results           # Backtest results
│   ├── DELETE /{id}                   # Cancel backtest
│   └── GET    /                       # List backtests
│
├── /trades
│   ├── GET    /                       # List trades
│   ├── GET    /{id}                   # Get trade details
│   ├── POST   /manual                 # Create manual trade
│   ├── GET    /stats/daily            # Daily statistics
│   ├── GET    /stats/overall          # Overall statistics
│   └── GET    /positions/current      # Current positions
│
├── /positions
│   ├── GET    /                       # List positions
│   ├── GET    /{id}                   # Get position details
│   ├── POST   /{id}/close             # Close position
│   └── POST   /close-all              # Close all positions
│
├── /emergency
│   ├── POST   /circuit-breaker        # Trip circuit breaker
│   ├── POST   /circuit-breaker/reset  # Reset circuit breaker
│   └── POST   /kill-switch            # Emergency shutdown
│
└── /health                            # Health check
```

### WebSocket API

```
/ws

Events (Server → Client):
- candle_update          # New candle data
- signal_generated       # Trading signal detected
- trade_executed         # Trade executed
- position_update        # Position P&L update
- backtest_progress      # Backtest progress
- system_alert           # Important system event

Events (Client → Server):
- subscribe              # Subscribe to symbols
- unsubscribe            # Unsubscribe
- backtest_control       # Control replay (play/pause/speed)
```

---

## Database Schema

### Key Tables

**strategy_rules:**
```sql
CREATE TABLE strategy_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_type VARCHAR(20) NOT NULL,  -- 'pdf' or 'video'
    source_ref VARCHAR(500) NOT NULL,
    entry_type VARCHAR(50) NOT NULL,   -- 'LE', 'small_wick', etc.
    conditions JSONB NOT NULL,
    confluence_required JSONB,
    risk_params JSONB NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    embedding vector(1536)  -- pgvector for semantic search
);

CREATE INDEX idx_strategy_rules_embedding ON strategy_rules 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**trades:**
```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_rule_id UUID REFERENCES strategy_rules(id),
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,  -- 'long' or 'short'
    entry_price NUMERIC(20, 8) NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_price NUMERIC(20, 8),
    exit_time TIMESTAMP,
    exit_reason VARCHAR(50),  -- 'tp1', 'tp2', 'sl', 'breakeven', 'manual'
    quantity NUMERIC(20, 8) NOT NULL,
    outcome VARCHAR(20),  -- 'win', 'loss', 'breakeven', 'pending'
    pnl_usd NUMERIC(20, 8),
    pnl_r NUMERIC(10, 4),  -- P&L in R multiples
    reasoning TEXT,
    price_action_snapshot JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trades_created_at ON trades(created_at DESC);
CREATE INDEX idx_trades_strategy ON trades(strategy_rule_id);
CREATE INDEX idx_trades_outcome ON trades(outcome);
```

**positions:**
```sql
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID REFERENCES trades(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    remaining_quantity NUMERIC(20, 8) NOT NULL,
    entry_price NUMERIC(20, 8) NOT NULL,
    stop_loss NUMERIC(20, 8) NOT NULL,
    take_profit_1 NUMERIC(20, 8),
    take_profit_2 NUMERIC(20, 8),
    tp1_hit BOOLEAN DEFAULT false,
    tp2_hit BOOLEAN DEFAULT false,
    status VARCHAR(20) NOT NULL,  -- 'open', 'closed'
    opened_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_positions_status ON positions(status) WHERE status = 'open';
```

**learning_entries:**
```sql
CREATE TABLE learning_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_rule_id UUID REFERENCES strategy_rules(id),
    insight TEXT NOT NULL,
    supporting_trades UUID[] NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Trading Engine

### Signal Generation

```python
@dataclass
class TradeSignal:
    """Generated when confluence threshold is met."""
    id: str
    symbol: str
    direction: Literal["long", "short"]
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: List[Decimal]  # [TP1, TP2]
    matched_rules: List[StrategyRule]
    confluence_score: float
    higher_tf_bias: str
    entry_timeframe: str
    patterns_detected: Dict[str, List[str]]
    timestamp: datetime
```

### Order Execution

```python
@dataclass
class OrderRequest:
    symbol: str
    side: Literal["buy", "sell"]
    size: Decimal
    order_type: Literal["market", "limit"]
    price: Optional[Decimal] = None  # For limit orders
    stop_loss: Decimal
    take_profit: List[Decimal]
    reduce_only: bool = False
    time_in_force: Literal["GTC", "IOC", "FOK"] = "GTC"
```

---

## Scaling Considerations

### Horizontal Scaling

**Stateless API Servers:**
```yaml
# docker-compose.yml
services:
  backend:
    image: trading-bot-backend
    deploy:
      replicas: 4
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://...
```

**Load Balancing:**
```nginx
upstream backend_cluster {
    least_conn;  # Route to least busy server
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
    server backend-4:8000;
}
```

### Database Scaling

**Read Replicas:**
```python
# Split read/write operations
class DatabaseRouter:
    async def write(self, query):
        return await self.primary_db.execute(query)
    
    async def read(self, query):
        # Round-robin across replicas
        replica = self._select_replica()
        return await replica.execute(query)
```

**Connection Pooling:**
```python
# Increase pool size for high concurrency
DATABASE_POOL_SIZE = 50
DATABASE_MAX_OVERFLOW = 100
```

### Caching Strategy

**Multi-Layer Cache:**
```
L1: Application memory (LRU, 5-minute TTL)
L2: Redis (1-hour TTL)
L3: PostgreSQL
```

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| API Response Time (p95) | < 200ms | Cached reads |
| API Response Time (p95) | < 1s | DB writes |
| Pattern Detection Latency | < 50ms | Per candle update |
| WebSocket Message Latency | < 100ms | Real-time data |
| Backtest Speed | > 100 candles/sec | With all detectors |
| Concurrent Users | 100+ | With 4 API servers |
| Database Connections | < 200 | Per server |
| Memory Usage (backend) | < 4GB | Per instance |

---

**Next:** See `DEPLOYMENT.md` for production deployment instructions.
