# Hyperliquid Trading Bot Suite

An AI-powered trading system that learns strategies from educational content (PDFs, YouTube videos), extracts rules into a structured knowledge base, and executes trades via a hybrid LLM + fast pattern detection engine.

## 🎯 Key Features

- **📚 Content Ingestion**: Extract trading strategies from PDFs and YouTube videos
- **🧠 AI Strategy Extraction**: Use Claude to analyze content and extract structured rules
- **⚡ Fast Pattern Detection**: High-performance Python engine for real-time market analysis
- **📊 Advanced Backtesting**: TradingView-style replay with detailed performance metrics
- **🎛️ Beautiful Dashboard**: Nuxt 3 frontend with TradingView charts
- **🔄 Self-Learning**: Continuous improvement through outcome feedback
- **⚖️ Risk Management**: Built-in position sizing and risk controls
- **🔗 Hyperliquid Integration**: Direct trading on Hyperliquid DEX

## 🏗️ Architecture

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

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+ (with pgvector)
- Redis

### 1. Clone and Setup

```bash
git clone <repository-url>
cd hyperliquid-trading-bot-suite

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### 2. Start with Docker Compose

```bash
# Start all services (PostgreSQL, Redis, Backend, Frontend)
docker-compose up -d

# Check logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 3. Manual Development Setup

```bash
# Backend setup
cd backend
pip install -e .[dev,performance]
uvicorn src.api.main:app --reload

# Frontend setup (in another terminal)
cd frontend
npm install
npm run dev
```

### 4. Access the Application

- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **PgAdmin** (optional): http://localhost:5050

## 📝 Configuration

### Environment Variables

Key settings in `.env`:

```bash
# LLM Configuration
ANTHROPIC_API_KEY=your_anthropic_key_here
CLAUDE_EXTRACTION_MODEL=claude-3-opus-20240229
CLAUDE_REASONING_MODEL=claude-3-sonnet-20240229

# Hyperliquid
HYPERLIQUID_PRIVATE_KEY=your_private_key_here
HYPERLIQUID_TESTNET=true

# Trading Settings
MAX_RISK_PER_TRADE=0.02
MAX_CONCURRENT_POSITIONS=5
MIN_CONFLUENCE_SCORE=0.7

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/trading_bot
REDIS_URL=redis://localhost:6379
```

## 📊 Usage Guide

### 1. Ingest Educational Content

**Upload PDF Documents:**
```bash
curl -X POST "http://localhost:8000/api/ingestion/pdf" \
  -F "file=@trading_strategy.pdf" \
  -F "extract_images=true"
```

**Process YouTube Videos:**
```bash
curl -X POST "http://localhost:8000/api/ingestion/video" \
  -F "url=https://www.youtube.com/watch?v=VIDEO_ID" \
  -F "extract_frames=true"
```

### 2. View Extracted Strategies

```bash
# List all strategies
curl "http://localhost:8000/api/strategies"

# Get strategy details
curl "http://localhost:8000/api/strategies/{strategy_id}"
```

### 3. Run Backtests

```bash
curl -X POST "http://localhost:8000/api/backtesting/start" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Run",
    "symbol": "BTC-USD",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "strategy_ids": ["strategy_123"]
  }'
```

### 4. Monitor Live Trading

```bash
# Get current positions
curl "http://localhost:8000/api/trades/positions/current"

# Get trading statistics
curl "http://localhost:8000/api/trades/stats/overall"
```

## 🧩 Project Structure

```
hyperliquid-trading-bot-suite/
├── backend/                     # Python FastAPI backend
│   ├── src/
│   │   ├── api/                # REST API endpoints
│   │   ├── ingestion/          # PDF/video processing
│   │   ├── knowledge/          # Strategy storage & retrieval
│   │   ├── detection/          # Pattern detection engine
│   │   ├── trading/            # Trade execution & reasoning
│   │   ├── backtest/           # Backtesting engine
│   │   └── config.py           # Configuration management
│   ├── tests/                  # Unit and integration tests
│   └── pyproject.toml          # Python dependencies
├── frontend/                   # Nuxt 3 dashboard
│   ├── app/
│   │   ├── components/         # Vue components
│   │   ├── pages/              # Route pages
│   │   └── layouts/            # Page layouts
│   └── package.json            # Node.js dependencies
├── docker-compose.yml          # Multi-service setup
└── .env.example               # Configuration template
```

## 🎛️ Key Components

### 1. Ingestion Pipeline

- **PDF Processor**: Extracts text and charts from trading PDFs
- **Video Pipeline**: Downloads YouTube videos, transcribes audio, extracts frames
- **LLM Extractor**: Uses Claude to analyze content and extract structured strategy rules

### 2. Pattern Detection Engine

- **Candle Patterns**: LE candles, small wicks, steeper wicks, celery plays
- **Market Structure**: Higher highs/lows, break of structure, support/resistance
- **Market Cycles**: Drive, range, and liquidity phases
- **Confluence Scorer**: Multi-timeframe alignment and signal strength

### 3. Knowledge Base

- **Strategy Rules**: Structured storage of extracted trading rules
- **Trade History**: Complete record of all trades with outcomes
- **Learning Log**: Insights from trade analysis for continuous improvement

### 4. Trading System

- **Trade Reasoner**: LLM-powered trade decision explanations
- **Position Manager**: Multi-TP exits, stop loss management
- **Risk Manager**: 2% risk per trade, position sizing, daily limits

### 5. Frontend Dashboard

- **Multi-timeframe Charts**: TradingView Lightweight Charts integration
- **Strategy Manager**: Enable/disable strategies, view performance
- **Backtest Replay**: Visual replay of strategy performance
- **Trade Panel**: Live trades, history, and detailed analysis

## 🔧 Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

### Code Quality

```bash
# Backend linting
cd backend
black src/
ruff src/
mypy src/

# Frontend linting
cd frontend
npm run lint
```

### Database Migrations

```bash
cd backend
alembic upgrade head
```

## 📈 Trading Strategy Types

The system can learn and execute various strategy types:

### Entry Types
- **LE Candle**: Large wick-to-body ratio with specific close position
- **Small Wick**: Precise entries with minimal wicks
- **Steeper Wick**: Momentum continuation patterns
- **Celery Play**: Range extreme reversals

### Setup Types
- **Breakout**: Structure breaks with momentum
- **Fakeout**: False breakout reversals
- **Onion**: Range extreme plays with confluence

### Market Cycles
- **Drive Phase**: Strong momentum with trending moves
- **Range Phase**: Consolidation between support/resistance
- **Liquidity Phase**: Stop hunts and sweep plays

## 🛡️ Risk Management

- **Position Sizing**: 2% risk per trade based on stop loss distance
- **Multi-TP Exits**: TP1 at 1R, TP2 at 2R, breakeven at 0.5R
- **Daily Limits**: Maximum 5% daily loss limit
- **Concurrent Positions**: Maximum 5 positions at once
- **Confluence Requirements**: Minimum confluence score before entry

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Trading cryptocurrencies involves substantial risk of loss. Past performance is not indicative of future results. Use at your own risk and never trade with money you cannot afford to lose.

## 🙋‍♂️ Support

- **Documentation**: Check the `/docs` folder for detailed guides
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join our GitHub Discussions for questions

---

**Built with ❤️ using Python, FastAPI, Vue 3, Nuxt 3, and Claude AI**