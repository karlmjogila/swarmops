# HL-Bot-V2: AI-Powered Trading Research & Execution System

> **Transform educational trading content into backtested strategies with visual replay and AI-powered learning**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-green.svg)](https://fastapi.tiangolo.com/)
[![SvelteKit](https://img.shields.io/badge/SvelteKit-2.0+-orange.svg)](https://kit.svelte.dev/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 🎯 Overview

HL-Bot-V2 is an AI-powered trading research platform that bridges the gap between educational content and executable trading strategies. It combines pattern recognition, backtesting with visual replay, and continuous learning through LLM reasoning.

### Key Features

- 📚 **Content Ingestion**: Extract trading strategies from YouTube videos, PDFs, and chart images
- 🔍 **Pattern Detection**: Deterministic candle pattern and market structure analysis
- 📊 **Visual Backtesting**: TradingView-style replay with multi-timeframe charts
- 🧠 **AI Reasoning**: Claude explains trade decisions and learns from outcomes
- 📈 **Live Trading**: Hyperliquid DEX integration via MCP (Model Context Protocol)
- 🎮 **Interactive Replay**: Play/pause/step/seek through historical backtests

---

## 🏗️ Architecture

```
Content (YouTube/PDF) → LLM Extraction → Strategy Rules
                                              ↓
Market Data (CSV) → Pattern Engine → Signals → Backtester
                                                     ↓
                                        Frontend (SvelteKit + TradingView Charts)
                                                     ↓
                                        Trade Reasoner (Claude) → Learning Loop
                                                     ↓
                                        Live Trading (Hyperliquid)
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | SvelteKit + TradingView lightweight-charts | Reactive UI with professional charting |
| **Backend** | FastAPI + Python 3.11+ | Async API with ML ecosystem |
| **Database** | PostgreSQL + TimescaleDB | Time-series optimized storage |
| **Pattern Engine** | NumPy + Pandas | Fast deterministic pattern detection |
| **LLM** | Claude API | Strategy extraction, trade reasoning, learning |
| **Trading** | Hyperliquid Python SDK | Decentralized exchange integration |
| **Processing** | Celery + Redis | Background job processing |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (with TimescaleDB extension)
- Redis 6+
- Docker & Docker Compose (optional, recommended)

### Installation

#### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/hl-bot-v2.git
cd hl-bot-v2

# Copy environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env

# Start the stack
docker-compose up -d

# Access the dashboard
open http://localhost:3000
```

#### Option 2: Local Development

See [SETUP.md](SETUP.md) for detailed installation instructions.

### First Run

1. **Import Market Data**
   ```bash
   # From TradingView CSV export
   curl -X POST http://localhost:8000/api/data/import \
     -F "file=@btcusd_5m.csv" \
     -F "symbol=BTCUSD" \
     -F "timeframe=5m"
   ```

2. **Ingest Trading Content**
   ```bash
   # YouTube video
   curl -X POST http://localhost:8000/api/ingest/youtube \
     -H "Content-Type: application/json" \
     -d '{"url": "https://youtube.com/watch?v=..."}'
   ```

3. **Run a Backtest**
   - Navigate to http://localhost:3000/backtest
   - Select date range and strategy
   - Click "Start Backtest"
   - Use playback controls to replay trades

---

## 📚 Documentation

- **[Setup Guide](SETUP.md)** - Detailed installation and configuration
- **[Implementation Plan](specs/IMPLEMENTATION_PLAN.md)** - Complete technical specification
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)
- **[Progress Tracker](progress.md)** - Current development status

---

## 🎓 Strategy Concepts

This system implements trading concepts from Don Vo / ControllerFX:

### Market Cycles
```
DRIVE → RANGE → LIQUIDITY (repeat)
```

### Multi-Timeframe Confluence
- **4H**: Sets trend bias
- **1H**: Key levels and pullback zones
- **30M**: Structure confirmation (BOS/CHoCH)
- **15M**: Entry patterns
- **5M**: Entry refinement

### Detected Patterns
- **LE Candle**: Liquidity-to-Entry sweep
- **Small Wick**: Strong body, minimal rejection
- **Steeper Wick**: Deep accumulation
- **Celery**: Multiple pressure candles
- **Engulfing**: Full body engulf

### Exit Strategy
```
Entry → TP1 (1R, 50%) → Breakeven → TP2 (2R, 50%) OR Trail
```

---

## 🛠️ Development

### Backend Development

```bash
cd backend

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Start dev server with reload
poetry run uvicorn app.main:app --reload

# Run linting
poetry run ruff check .
poetry run mypy .
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Run tests
npm run test
```

### Database Migrations

```bash
cd backend

# Create new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

---

## 📊 Project Structure

```
hl-bot-v2/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API routes
│   │   ├── core/        # Pattern detection, backtesting
│   │   ├── ingestion/   # Content processors
│   │   ├── llm/         # Claude integration
│   │   ├── trading/     # Hyperliquid client
│   │   └── db/          # Database models
│   ├── tests/
│   └── pyproject.toml
├── frontend/            # SvelteKit frontend
│   ├── src/
│   │   ├── lib/        # Components, stores
│   │   └── routes/     # Pages
│   └── package.json
├── data/               # Market data (CSV imports)
├── specs/              # Documentation
├── docker-compose.yml
└── README.md
```

---

## 🔐 Configuration

Key environment variables (`.env`):

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/hlbot

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
HYPERLIQUID_API_KEY=...
HYPERLIQUID_PRIVATE_KEY=...

# Features
ENABLE_PAPER_MODE=true
ENABLE_LLM_REASONING=true
```

See `.env.example` for full configuration options.

---

## 🎯 Roadmap

### ✅ Phase 1-4: Foundation & Backtesting (MVP)
- [x] Backend setup with FastAPI
- [x] Database with TimescaleDB
- [x] Frontend with SvelteKit
- [ ] Pattern detection engine
- [ ] Backtest runner with WebSocket streaming
- [ ] Visual replay interface

### 🚧 Phase 5-6: Content & Learning
- [ ] YouTube/PDF ingestion
- [ ] LLM strategy extraction
- [ ] Trade reasoning
- [ ] Learning feedback loop

### 📋 Phase 7-9: Frontend & Live Trading
- [ ] Multi-timeframe charts
- [ ] Trade log & decision journal
- [ ] Hyperliquid integration
- [ ] Paper trading mode

### 🔍 Phase 10-11: Polish & Review
- [ ] Docker deployment
- [ ] Comprehensive testing
- [ ] Security review
- [ ] Documentation completion

See [progress.md](progress.md) for detailed task tracking.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards

- **Python**: Follow PEP 8, use type hints, pass Ruff + Mypy
- **TypeScript**: Use strict mode, follow Prettier formatting
- **Tests**: Maintain >80% coverage for new code
- **Commits**: Use conventional commits (feat, fix, docs, etc.)

---

## ⚠️ Disclaimer

This software is for educational and research purposes only. Trading cryptocurrencies involves substantial risk of loss. The authors and contributors are not responsible for any financial losses incurred through use of this software.

**Always:**
- Test thoroughly in paper trading mode
- Start with small position sizes
- Never risk more than you can afford to lose
- Understand that past performance does not guarantee future results

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Don Vo / ControllerFX** - Trading methodology and concepts
- **TradingView** - lightweight-charts library
- **Anthropic** - Claude API for reasoning capabilities
- **Hyperliquid** - Decentralized exchange infrastructure

---

## 📞 Support

- **Documentation**: [specs/IMPLEMENTATION_PLAN.md](specs/IMPLEMENTATION_PLAN.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/hl-bot-v2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/hl-bot-v2/discussions)

---

**Built with ❤️ by the HL-Bot-V2 Team**

*Last updated: 2025-02-11*
