# Development Guide

This guide covers setting up and working with the Hyperliquid Trading Bot Suite development environment.

## Quick Start

```bash
# Clone and enter the project
git clone <repository-url>
cd hyperliquid-trading-bot-suite

# Set up development environment
./scripts/setup-dev.sh

# Start development servers
make dev

# Open in browser
open http://localhost:3000  # Frontend
open http://localhost:8000/docs  # API Documentation
```

## Prerequisites

- **Docker & Docker Compose** - For running databases and services
- **Python 3.11+** - Backend development
- **Node.js 18+** - Frontend development
- **Git** - Version control

Optional but recommended:
- **pre-commit** - Git hooks for code quality
- **VS Code** - IDE with extensions for Python, Vue, TypeScript

## Project Structure

```
hyperliquid-trading-bot-suite/
├── backend/               # Python FastAPI backend
│   ├── src/              # Source code
│   ├── tests/            # Test files
│   ├── pyproject.toml    # Python dependencies and config
│   └── requirements.txt  # pip requirements
├── frontend/             # Nuxt 3 frontend
│   ├── components/       # Vue components
│   ├── pages/           # Nuxt pages
│   ├── stores/          # Pinia stores
│   └── package.json     # Node.js dependencies
├── scripts/             # Development scripts
├── .github/             # GitHub Actions CI/CD
└── docker-compose.yml   # Production services
```

## Environment Configuration

The project uses multiple environment files:

- `.env.example` - Template with all available options
- `.env.development` - Development-specific settings
- `.env.test` - Test environment settings
- `.env` - Your local environment (created from development)

**Important:** Never commit `.env` files with real API keys!

## Development Workflow

### Starting Development

```bash
# Start all services
make dev

# Or individually:
make dev-backend    # Start backend only
make dev-frontend   # Start frontend only
make dev-db        # Start databases only
```

### Code Quality

The project enforces code quality through:

- **Pre-commit hooks** - Run linting/formatting before commits
- **ESLint** - JavaScript/TypeScript linting
- **Black + Ruff** - Python formatting and linting
- **MyPy** - Python type checking
- **Prettier** - Code formatting

```bash
# Run all code quality checks
make lint

# Fix auto-fixable issues
make lint-fix

# Type checking
make type-check
```

### Testing

```bash
# Run all tests
make test

# Backend tests only
make test-backend

# Frontend tests only  
make test-frontend

# With coverage
make test-coverage
```

### Database Management

```bash
# Create new migration
make migration name="add_new_table"

# Apply migrations
make migrate

# Reset database (development only)
make db-reset
```

## Configuration Files Explained

### Backend Configuration

- **`pyproject.toml`** - Python project configuration, dependencies, and tool settings
- **`pytest.ini`** - Test configuration and markers
- **`tsconfig.json`** - TypeScript configuration (for any TS utilities)

### Frontend Configuration

- **`package.json`** - Node.js dependencies and scripts
- **`nuxt.config.ts`** - Nuxt framework configuration
- **`tailwind.config.js`** - Tailwind CSS customization
- **`tsconfig.json`** - TypeScript configuration
- **`.eslintrc.js`** - ESLint rules
- **`vitest.config.ts`** - Test configuration

### Development Tools

- **`.editorconfig`** - Consistent editor settings
- **`.prettierrc.json`** - Code formatting rules
- **`.pre-commit-config.yaml`** - Git hooks configuration
- **`docker-compose.dev.yml`** - Development service overrides

### CI/CD

- **`.github/workflows/ci.yml`** - Automated testing and security scanning

## Available Make Commands

```bash
make help           # Show all available commands
make dev           # Start development environment
make build         # Build for production
make test          # Run all tests
make lint          # Run all linters
make clean         # Clean build artifacts
make reset         # Reset development environment
```

## IDE Setup

### VS Code Recommended Extensions

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker",
    "Vue.volar",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode"
  ]
}
```

### VS Code Settings

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true,
    "source.organizeImports": true
  },
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true
}
```

## Troubleshooting

### Common Issues

**Database connection errors:**
```bash
# Ensure databases are running
docker-compose up -d postgres redis

# Check logs
docker-compose logs postgres
```

**Port conflicts:**
```bash
# Check what's using the port
lsof -i :8000
lsof -i :3000

# Kill the process or change ports in .env
```

**Node.js module issues:**
```bash
# Clear cache and reinstall
rm -rf frontend/node_modules frontend/.nuxt
cd frontend && npm install
```

**Python dependency issues:**
```bash
# Recreate virtual environment
rm -rf backend/venv
cd backend && python -m venv venv && source venv/bin/activate
pip install -e .
```

### Debugging

**Backend debugging:**
- Add `import pdb; pdb.set_trace()` for breakpoints
- Use VS Code debugger with launch configurations
- Check logs: `docker-compose logs backend`

**Frontend debugging:**
- Use browser dev tools
- Vue DevTools extension
- Console logs in development mode

### Performance Issues

**Slow startup:**
- Check Docker resource allocation
- Ensure SSD storage for Docker
- Consider running databases natively in development

**Hot reload not working:**
- Check file watching limits on Linux: `fs.inotify.max_user_watches`
- Ensure volumes are properly mounted in docker-compose

## Security Considerations

- Never commit real API keys or passwords
- Use `.env.example` as template, never commit `.env`
- Rotate test keys regularly
- Use testnet for Hyperliquid in development
- Review dependencies regularly for vulnerabilities

## Contributing

1. Create a feature branch: `git checkout -b feature/amazing-feature`
2. Make your changes with proper tests
3. Ensure all checks pass: `make lint test`
4. Commit with clear messages
5. Push and create a Pull Request

Pre-commit hooks will run automatically to ensure code quality.