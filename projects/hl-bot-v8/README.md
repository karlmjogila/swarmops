# HL-Bot v8

**AI-Powered Hyperliquid Trading Research & Execution System**

[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()
[![Node.js](https://img.shields.io/badge/node-%3E%3D20.0.0-brightgreen.svg)]()
[![TypeScript](https://img.shields.io/badge/typescript-5.x-blue.svg)]()
[![Rust](https://img.shields.io/badge/rust-stable-orange.svg)]()

A comprehensive trading platform that combines AI-powered content analysis, deterministic pattern detection, multi-timeframe confluence scoring, and automated trade execution on Hyperliquid — all with human oversight and continuous learning.

## 🚀 Key Features

### Content Ingestion
- **YouTube** — Download and transcribe trading videos via yt-dlp + Whisper
- **PDF** — Extract text and images from trading documents
- **Charts** — Analyze chart images with Claude Vision

### Strategy Extraction
- AI-powered strategy parsing from transcripts
- Machine-readable entry/exit conditions
- Confidence scoring and reasoning

### Pattern Detection (Rust/WASM)
- High-performance deterministic engine (10k candles in <100ms)
- Candlestick patterns: Engulfing, Doji, Hammer, Morning/Evening Star, etc.
- Market structure: Break of Structure (BOS), Change of Character (CHoCH)
- Support/Resistance zone detection with strength scoring

### Multi-Timeframe Confluence
- Weighted scoring across 15m, 1H, 4H, 1D
- Signal generation with AI reasoning
- Configurable thresholds and filters

### Backtest Engine
- TradingView-style visual replay via WebSocket
- Event-driven simulation (no lookahead bias)
- Full metrics: Win rate, Sharpe/Sortino, max drawdown, profit factor

### Trade Execution
- **Paper trading** — Test strategies risk-free
- **Live trading** — Execute on Hyperliquid (requires approval)
- Risk management: Position limits, daily loss limits, circuit breakers
- Full audit trail

### Continuous Learning
- AI-powered trade analysis and feedback
- Strategy refinement recommendations
- Learning journal with insights and action items

## 🏗️ Architecture

```
Frontend (SvelteKit) ─── REST + WebSocket ─── API (Fastify)
                                                   │
         ┌────────────┬────────────┬────────────┬──┴──────────┐
         ▼            ▼            ▼            ▼             ▼
    Content      Strategy     Pattern      Backtest       Trade
    Ingestion    Extractor    Engine       Engine         Executor
    (yt-dlp,     (Claude)     (Rust/WASM)  (Replay,       (HL SDK,
     Whisper)                              Streaming)     Risk Mgmt)
         │            │            │            │             │
         └────────────┴────────────┴────────────┴─────────────┘
                                   │
              PostgreSQL/TimescaleDB + Redis + S3
```

## 📦 Project Structure

```
hl-bot-v8/
├── apps/
│   ├── api/                # Fastify API server
│   └── web/                # SvelteKit frontend
├── packages/
│   ├── shared/             # Shared TypeScript types
│   ├── pattern-engine/     # Rust/WASM pattern detection
│   └── hyperliquid-sdk/    # Hyperliquid SDK wrapper
├── infrastructure/
│   └── docker/             # Docker Compose setup
├── docs/                   # Documentation
└── specs/                  # Architecture specifications
```

## 🛠️ Quick Start

### Prerequisites

- Node.js ≥20.0.0
- pnpm ≥8.0.0
- Rust (for pattern engine)
- Docker & Docker Compose

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd hl-bot-v8

# Install dependencies
pnpm install

# Start infrastructure (PostgreSQL, Redis, MinIO)
cd infrastructure/docker
docker-compose up -d
cd ../..

# Run database migrations (Flyway)
pnpm --filter @hl-bot/api run db:migrate

# Check migration status
pnpm --filter @hl-bot/api run db:info

# Build the pattern engine
cd packages/pattern-engine
wasm-pack build --target web
cd ../..

# Start development servers
pnpm dev
```

### Environment Variables

Create `.env` files in `apps/api/` and `apps/web/`:

```env
# apps/api/.env
DATABASE_URL=postgresql://hlbot:hlbot_dev_password@localhost:5432/hlbot
REDIS_URL=redis://:hlbot_redis_dev@localhost:6379
JWT_SECRET=your-secret-key
ANTHROPIC_API_KEY=sk-ant-...
```

See [DEVELOPMENT.md](./docs/DEVELOPMENT.md) for full configuration.

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](./docs/ARCHITECTURE.md) | System design and components |
| [API Reference](./docs/API.md) | REST & WebSocket API documentation |
| [Development](./docs/DEVELOPMENT.md) | Development setup and workflow |
| [Deployment](./docs/DEPLOYMENT.md) | Production deployment guide |
| [Contributing](./docs/CONTRIBUTING.md) | Contribution guidelines |

## 🧪 Testing

```bash
# Run all tests
pnpm test

# Run specific package tests
pnpm --filter @hl-bot/api test
pnpm --filter @hl-bot/pattern-engine test

# With coverage
pnpm --filter @hl-bot/api test:coverage
```

## 🔒 Security

- JWT-based authentication with token refresh
- Rate limiting on all endpoints
- Input validation with Zod schemas
- SQL injection prevention (parameterized queries)
- Prototype pollution protection
- XSS prevention via input sanitization
- Strategy approval workflow for live trading
- Full audit logging

## 📊 Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | SvelteKit, TailwindCSS, TradingView Lightweight Charts |
| API | Fastify, TypeScript |
| Pattern Engine | Rust → WebAssembly |
| LLM | Claude API (Anthropic) |
| Database | PostgreSQL + TimescaleDB |
| Cache/Queue | Redis + BullMQ |
| Transcription | OpenAI Whisper |
| Exchange | Hyperliquid SDK |

## 🗺️ Roadmap

- [x] Content ingestion pipeline
- [x] Strategy extraction via LLM
- [x] Pattern detection engine (Rust/WASM)
- [x] Signal generation with confluence
- [x] Backtest engine with replay
- [x] Trade execution (paper + live)
- [x] Learning service
- [x] Frontend foundation
- [x] Frontend features
- [ ] E2E tests
- [ ] Performance optimization
- [ ] Final security audit

## 📄 License

Proprietary — All rights reserved.

---

Built with 🦀 Rust, 🟦 TypeScript, and ❤️
