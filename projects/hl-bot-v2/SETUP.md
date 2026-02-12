# HL-Bot-V2 Setup Guide

Complete installation and configuration guide for local development.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Option 1: Docker Setup](#option-1-docker-setup-recommended)
- [Option 2: Local Development Setup](#option-2-local-development-setup)
- [Configuration](#configuration)
- [Data Import](#data-import)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend tooling |
| PostgreSQL | 14+ | Database |
| Redis | 6+ | Cache & queue |
| Git | 2.30+ | Version control |

### Optional (Recommended)

- **Docker** 20+ & **Docker Compose** 2+ - Simplified deployment
- **Poetry** 1.7+ - Python dependency management
- **pnpm** or **npm** 9+ - Node package manager

### API Keys (Optional)

- **Anthropic API Key** - For LLM features (strategy extraction, reasoning)
- **Hyperliquid API Keys** - For live trading (optional for backtesting)

---

## Option 1: Docker Setup (Recommended)

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/hl-bot-v2.git
cd hl-bot-v2
```

### 2. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

**Minimum required variables:**

```bash
# Database (auto-configured in Docker)
DATABASE_URL=postgresql://hlbot:hlbot@postgres:5432/hlbot

# Redis (auto-configured in Docker)
REDIS_URL=redis://redis:6379/0

# Optional: LLM features
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: Live trading
HYPERLIQUID_API_KEY=your-key
HYPERLIQUID_PRIVATE_KEY=your-private-key
ENABLE_PAPER_MODE=true  # Start with paper trading
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 4. Verify Installation

```bash
# Backend health check
curl http://localhost:8000/health

# Frontend
open http://localhost:3000

# API docs
open http://localhost:8000/docs
```

### 5. Initialize Database

```bash
# Run migrations
docker-compose exec backend poetry run alembic upgrade head

# (Optional) Load sample data
docker-compose exec backend poetry run python -m app.scripts.seed_data
```

**Done!** Your HL-Bot-V2 instance is running.

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

---

## Option 2: Local Development Setup

### 1. Install System Dependencies

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y \
    python3.11 python3.11-venv python3-pip \
    postgresql-14 postgresql-contrib \
    redis-server \
    ffmpeg \
    build-essential \
    libpq-dev

# Install TimescaleDB
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt update
sudo apt install -y timescaledb-2-postgresql-14
```

#### macOS

```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 postgresql@14 redis ffmpeg node

# Install TimescaleDB
brew tap timescale/tap
brew install timescaledb

# Initialize TimescaleDB
timescaledb-tune --quiet --yes
```

### 2. Clone and Setup Repository

```bash
git clone https://github.com/yourusername/hl-bot-v2.git
cd hl-bot-v2
```

### 3. Backend Setup

```bash
cd backend

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Copy environment file
cp ../.env.example ../.env
# Edit .env with your settings

# Run migrations
poetry run alembic upgrade head
```

### 4. Database Setup

```bash
# Start PostgreSQL (if not already running)
# Ubuntu:
sudo systemctl start postgresql
# macOS:
brew services start postgresql

# Create database and user
psql postgres << EOF
CREATE USER hlbot WITH PASSWORD 'hlbot';
CREATE DATABASE hlbot OWNER hlbot;
\c hlbot
CREATE EXTENSION IF NOT EXISTS timescaledb;
EOF

# Verify TimescaleDB
psql -U hlbot -d hlbot -c "SELECT default_version, installed_version FROM pg_available_extensions WHERE name = 'timescaledb';"
```

### 5. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Build (or run dev server)
npm run dev
```

### 6. Redis Setup

```bash
# Start Redis
# Ubuntu:
sudo systemctl start redis
# macOS:
brew services start redis

# Verify
redis-cli ping  # Should return PONG
```

### 7. Start Services

Open 3 terminal windows:

**Terminal 1 - Backend:**
```bash
cd backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Celery Worker (for background jobs):**
```bash
cd backend
poetry run celery -A app.workers.tasks worker --loglevel=info
```

### 8. Verify Installation

- **Frontend**: http://localhost:5173 (Vite default) or http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## Configuration

### Environment Variables

Edit `.env` file in project root:

```bash
# ===== DATABASE =====
DATABASE_URL=postgresql://hlbot:hlbot@localhost:5432/hlbot

# ===== REDIS =====
REDIS_URL=redis://localhost:6379/0

# ===== API KEYS =====
# Anthropic (for LLM features)
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Hyperliquid (for live trading)
HYPERLIQUID_API_KEY=your-api-key
HYPERLIQUID_PRIVATE_KEY=your-private-key
HYPERLIQUID_MAINNET=false  # false = testnet

# ===== FEATURES =====
ENABLE_PAPER_MODE=true
ENABLE_LLM_REASONING=true
ENABLE_TRADE_LOGGING=true

# ===== BACKTEST SETTINGS =====
DEFAULT_INITIAL_BALANCE=10000
DEFAULT_RISK_PER_TRADE=0.02  # 2%
DEFAULT_MAX_POSITIONS=3

# ===== INGESTION =====
WHISPER_MODEL=base  # tiny, base, small, medium, large
VIDEO_CACHE_DIR=./data/cache/videos
PDF_CACHE_DIR=./data/cache/pdfs

# ===== SERVER =====
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ===== LOGGING =====
LOG_LEVEL=INFO
LOG_FILE=./logs/hlbot.log
```

### Backend Configuration

Advanced settings in `backend/app/config.py`:

```python
class Settings(BaseSettings):
    # Customize timeouts, rate limits, etc.
    api_timeout: int = 30
    max_backtest_days: int = 365
    websocket_heartbeat: int = 30
    
    class Config:
        env_file = ".env"
```

---

## Data Import

### Import Historical Data from TradingView

1. **Export data from TradingView:**
   - Open chart → Right-click → Export chart data
   - Save as CSV

2. **Import via API:**
   ```bash
   curl -X POST http://localhost:8000/api/data/import \
     -F "file=@BTCUSD_5m.csv" \
     -F "symbol=BTCUSD" \
     -F "timeframe=5m"
   ```

3. **Import via CLI (alternative):**
   ```bash
   cd backend
   poetry run python -m app.scripts.import_csv \
     --file ../data/csv/BTCUSD_5m.csv \
     --symbol BTCUSD \
     --timeframe 5m
   ```

### Bulk Import

```bash
# Import all CSV files in a directory
cd backend
poetry run python -m app.scripts.bulk_import \
  --directory ../data/csv \
  --pattern "*.csv"
```

### Expected CSV Format

TradingView exports should have columns:
```
time,open,high,low,close,volume
2024-01-01 00:00:00,42000.00,42100.00,41900.00,42050.00,1234.56
```

---

## Troubleshooting

### Database Connection Issues

**Error:** `could not connect to server`

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list                # macOS

# Check connection
psql -U hlbot -d hlbot -c "SELECT 1;"
```

**Error:** `TimescaleDB extension not found`

```bash
# Enable extension
psql -U hlbot -d hlbot -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

### Redis Connection Issues

```bash
# Check Redis is running
redis-cli ping

# If not running
sudo systemctl start redis  # Linux
brew services start redis   # macOS
```

### Poetry/Dependency Issues

```bash
# Clear cache and reinstall
cd backend
poetry cache clear pypi --all
poetry install --no-cache
```

### Frontend Build Issues

```bash
cd frontend

# Clear cache
rm -rf node_modules .svelte-kit
npm install

# Try different port if 3000 is taken
npm run dev -- --port 3001
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000  # Backend
lsof -i :3000  # Frontend

# Kill process
kill -9 <PID>
```

### Docker Issues

```bash
# Reset everything
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# Check logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Celery Worker Not Processing

```bash
# Check Redis connection
redis-cli ping

# Restart worker with verbose logging
cd backend
poetry run celery -A app.workers.tasks worker --loglevel=debug
```

---

## Production Deployment

### Security Checklist

- [ ] Change default database passwords
- [ ] Use strong `SECRET_KEY` in `.env`
- [ ] Enable HTTPS (use reverse proxy like Nginx)
- [ ] Set `CORS_ORIGINS` to specific domains
- [ ] Store API keys in secure vault (not `.env` in repo)
- [ ] Enable database backups
- [ ] Set up monitoring and logging
- [ ] Rate limit API endpoints
- [ ] Review Hyperliquid API permissions

### Docker Production

```bash
# Use production docker-compose
docker-compose -f docker-compose.prod.yml up -d

# With SSL (requires Traefik/Nginx)
docker-compose -f docker-compose.prod.yml -f docker-compose.ssl.yml up -d
```

### Systemd Service (Linux)

**Backend Service** (`/etc/systemd/system/hlbot-backend.service`):

```ini
[Unit]
Description=HL-Bot-V2 Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=hlbot
WorkingDirectory=/opt/hl-bot-v2/backend
Environment="PATH=/home/hlbot/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/hlbot/.local/bin/poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable hlbot-backend
sudo systemctl start hlbot-backend
```

### Backup Strategy

```bash
# Database backup (add to cron)
pg_dump -U hlbot hlbot > backup_$(date +%Y%m%d).sql

# Restore
psql -U hlbot hlbot < backup_20250211.sql
```

---

## Next Steps

1. **Import market data** - See [Data Import](#data-import)
2. **Run a backtest** - Navigate to http://localhost:3000/backtest
3. **Ingest content** - Try YouTube or PDF import
4. **Explore API** - Check out http://localhost:8000/docs
5. **Read the spec** - [IMPLEMENTATION_PLAN.md](specs/IMPLEMENTATION_PLAN.md)

---

## Additional Resources

- **Main README**: [README.md](README.md)
- **Implementation Plan**: [specs/IMPLEMENTATION_PLAN.md](specs/IMPLEMENTATION_PLAN.md)
- **Progress Tracker**: [progress.md](progress.md)
- **API Documentation**: http://localhost:8000/docs (when running)

---

**Need help?** Open an issue on GitHub or check the troubleshooting section above.

*Last updated: 2025-02-11*
