# HL Trading Bot - Backend

High-level trading bot API built with FastAPI, Poetry, and best practices.

## Project Structure

```
backend/
├── src/hl_bot/          # Application source code
│   ├── api/             # API route handlers
│   │   └── v1/          # API version 1
│   ├── models/          # Pydantic models
│   ├── services/        # Business logic
│   ├── repositories/    # Data access layer
│   └── utils/           # Shared utilities
├── tests/               # Test suite
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── pyproject.toml      # Poetry configuration
└── .env.example        # Example environment variables
```

## Setup

### Prerequisites

- Python 3.11+
- Poetry (installed automatically via installer)

### Installation

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Activate virtual environment:**
   ```bash
   poetry shell
   ```

## Development

### Run the server

```bash
poetry run uvicorn hl_bot.main:app --reload --port 8000
```

The API will be available at:
- **API:** http://localhost:8000
- **Interactive docs:** http://localhost:8000/docs
- **Alternative docs:** http://localhost:8000/redoc

### Run tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=hl_bot --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_config.py

# Run with verbose output
poetry run pytest -v
```

### Code quality

```bash
# Format code
poetry run ruff format .

# Lint code
poetry run ruff check .

# Type check
poetry run mypy src/hl_bot
```

## API Endpoints

### Health Check
- `GET /` - Root endpoint
- `GET /api/v1/health` - Health check with status
- `GET /api/v1/ready` - Readiness probe

## Configuration

Configuration is managed via environment variables and pydantic-settings.
See `.env.example` for available options.

### Key Settings

- `DEBUG`: Enable debug mode (default: false)
- `PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: info)

## Architecture

This project follows clean architecture principles:

1. **API Layer** (`api/`) - FastAPI route handlers, request/response
2. **Service Layer** (`services/`) - Business logic, framework-agnostic
3. **Repository Layer** (`repositories/`) - Data access, storage abstraction
4. **Models** (`models/`) - Pydantic models for validation

## Best Practices

- **Type hints everywhere** - Every function has type annotations
- **Pydantic validation** - All external input validated at the boundary
- **Async/await** - Async for I/O operations
- **Dependency injection** - FastAPI dependencies for clean code
- **Structured logging** - JSON-formatted logs for production
- **Comprehensive testing** - Unit and integration tests

## Development Guidelines

1. **Never use `Any`** - Always specify concrete types
2. **Validate at boundaries** - Use Pydantic for all external input
3. **Service layer is pure** - No framework dependencies in services
4. **Test async code** - Use `pytest-asyncio` for async tests
5. **Handle errors explicitly** - Custom exception hierarchy
6. **Log structured data** - Use the StructuredLogger utility

## Next Steps

- [ ] Add database integration
- [ ] Implement trading endpoints
- [ ] Add authentication/authorization
- [ ] Set up CI/CD pipeline
- [ ] Add monitoring and metrics
- [ ] Implement rate limiting
- [ ] Add WebSocket support for real-time updates
