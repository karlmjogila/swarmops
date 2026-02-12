# Contributing to HL-Bot-V2

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Areas for Contribution](#areas-for-contribution)

---

## Code of Conduct

### Our Standards

- **Be respectful** - Treat everyone with respect and professionalism
- **Be collaborative** - Work together, share knowledge
- **Be constructive** - Provide helpful feedback
- **Be patient** - Remember that contributors have varying experience levels

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Spam or promotional content
- Publishing others' private information
- Any conduct inappropriate in a professional setting

---

## Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/hl-bot-v2.git
cd hl-bot-v2

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/hl-bot-v2.git
```

### 2. Set Up Development Environment

Follow the [SETUP.md](SETUP.md) guide for detailed instructions.

```bash
# Backend
cd backend
poetry install
poetry run pytest  # Verify tests pass

# Frontend
cd ../frontend
npm install
npm run test  # Verify tests pass
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

**Branch naming conventions:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements
- `chore/` - Maintenance tasks

---

## Development Workflow

### 1. Make Changes

- Write clean, readable code
- Follow code standards (see below)
- Add tests for new functionality
- Update documentation as needed

### 2. Test Locally

```bash
# Backend tests
cd backend
poetry run pytest
poetry run ruff check .
poetry run mypy .

# Frontend tests
cd frontend
npm run test
npm run lint
npm run typecheck
```

### 3. Commit Changes

Use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git add .
git commit -m "feat: add pattern detection for steeper wick"
```

**Commit message format:**
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting, missing semicolons, etc.
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance

**Examples:**
```bash
git commit -m "feat(patterns): implement steeper wick detection"
git commit -m "fix(backtest): correct P&L calculation for partial exits"
git commit -m "docs(setup): add troubleshooting section"
git commit -m "test(engine): add tests for multi-timeframe alignment"
```

### 4. Keep Your Branch Updated

```bash
git fetch upstream
git rebase upstream/main
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## Code Standards

### Python (Backend)

**Style Guide:**
- Follow [PEP 8](https://pep8.org/)
- Use type hints for all functions
- Maximum line length: 100 characters
- Use docstrings for modules, classes, and functions

**Example:**
```python
from typing import List, Optional
from datetime import datetime

def detect_le_candle(
    candles: List[Candle],
    lookback: int = 5,
    min_body_percent: float = 0.7
) -> Optional[LECandle]:
    """
    Detect Liquidity-to-Entry (LE) candle pattern.
    
    Args:
        candles: List of candle data
        lookback: Number of candles to analyze
        min_body_percent: Minimum body size as percentage of range
        
    Returns:
        LECandle object if pattern detected, None otherwise
    """
    # Implementation
    pass
```

**Linting:**
```bash
# Run Ruff (linter + formatter)
poetry run ruff check .
poetry run ruff format .

# Type checking
poetry run mypy .
```

### TypeScript/JavaScript (Frontend)

**Style Guide:**
- Use TypeScript strict mode
- Prefer functional components
- Use meaningful variable names
- Maximum line length: 100 characters

**Example:**
```typescript
interface TradeSignal {
  id: string;
  timestamp: Date;
  symbol: string;
  signalType: 'long' | 'short';
  entryPrice: number;
  stopLoss: number;
  confluenceScore: number;
}

export function calculateRiskReward(
  signal: TradeSignal,
  takeProfit: number
): number {
  const risk = Math.abs(signal.entryPrice - signal.stopLoss);
  const reward = Math.abs(takeProfit - signal.entryPrice);
  return reward / risk;
}
```

**Linting:**
```bash
# ESLint + Prettier
npm run lint
npm run format

# Type checking
npm run typecheck
```

### File Organization

**Backend:**
```
backend/app/
├── api/           # API routes only
├── core/          # Business logic
├── db/            # Database models
├── llm/           # LLM integrations
└── utils/         # Shared utilities
```

**Frontend:**
```
frontend/src/
├── lib/
│   ├── components/  # Reusable UI components
│   ├── stores/      # Svelte stores (state management)
│   ├── utils/       # Helper functions
│   └── types/       # TypeScript types
└── routes/          # Pages
```

---

## Testing

### Backend Tests

**Structure:**
```python
# tests/test_patterns.py
import pytest
from app.core.patterns.candles import detect_le_candle

def test_detect_le_candle_valid():
    """Test LE candle detection with valid pattern."""
    candles = [...]  # Test data
    result = detect_le_candle(candles)
    assert result is not None
    assert result.type == 'LE_CANDLE'

def test_detect_le_candle_invalid():
    """Test LE candle detection with no pattern."""
    candles = [...]  # Test data with no pattern
    result = detect_le_candle(candles)
    assert result is None
```

**Run tests:**
```bash
cd backend

# All tests
poetry run pytest

# Specific file
poetry run pytest tests/test_patterns.py

# With coverage
poetry run pytest --cov=app --cov-report=html

# Watch mode
poetry run pytest --watch
```

### Frontend Tests

**Example (Vitest):**
```typescript
// src/lib/utils/risk.test.ts
import { describe, it, expect } from 'vitest';
import { calculateRiskReward } from './risk';

describe('calculateRiskReward', () => {
  it('should calculate 2:1 risk-reward correctly', () => {
    const signal = {
      entryPrice: 100,
      stopLoss: 98,
      // ... other fields
    };
    const takeProfit = 104;
    
    expect(calculateRiskReward(signal, takeProfit)).toBe(2);
  });
});
```

**Run tests:**
```bash
cd frontend

# All tests
npm run test

# Watch mode
npm run test:watch

# Coverage
npm run test:coverage
```

### Test Coverage

Aim for:
- **>80% coverage** for new code
- **100% coverage** for critical paths (trading logic, risk management)
- Edge cases and error conditions

---

## Pull Request Process

### 1. Before Submitting

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated (if needed)
- [ ] No merge conflicts with main
- [ ] Commit messages follow conventions

### 2. PR Description

Use this template:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing performed
- [ ] All tests pass

## Related Issues
Fixes #123

## Screenshots (if applicable)
[Add screenshots for UI changes]

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

### 3. Review Process

- Maintainers will review within 2-3 business days
- Address feedback promptly
- Keep discussions respectful and constructive
- Be patient - reviews take time

### 4. After Approval

- Squash commits if requested
- Maintainers will merge your PR
- Your contribution will be credited

---

## Areas for Contribution

### High Priority

- **Pattern Detection** - Implement new candle patterns
- **Market Structure** - Enhance BOS/CHoCH detection
- **Frontend Components** - Improve UI/UX
- **Testing** - Increase test coverage
- **Documentation** - Expand guides and examples

### Good First Issues

Look for issues labeled:
- `good first issue`
- `help wanted`
- `documentation`
- `beginner friendly`

### Feature Requests

Check the [Roadmap](README.md#roadmap) and [Issues](https://github.com/yourusername/hl-bot-v2/issues) for planned features.

Have a new idea? Open an issue to discuss before implementing!

---

## Communication

### Questions

- **General questions**: [GitHub Discussions](https://github.com/yourusername/hl-bot-v2/discussions)
- **Bug reports**: [GitHub Issues](https://github.com/yourusername/hl-bot-v2/issues)
- **Feature requests**: [GitHub Issues](https://github.com/yourusername/hl-bot-v2/issues)

### Reporting Bugs

**Include:**
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Environment (OS, Python/Node versions)
- Logs/screenshots

**Template:**
```markdown
**Description**
Clear description of the bug

**To Reproduce**
1. Step one
2. Step two
3. ...

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happened

**Environment**
- OS: Ubuntu 22.04
- Python: 3.11
- Node: 18.17

**Logs**
```
Paste relevant logs here
```
```

---

## Recognition

Contributors will be:
- Listed in [CONTRIBUTORS.md](CONTRIBUTORS.md)
- Credited in release notes
- Mentioned in documentation (for significant contributions)

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Questions?

If you have questions about contributing, open a discussion on GitHub or reach out to the maintainers.

Thank you for contributing to HL-Bot-V2! 🚀

---

*Last updated: 2025-02-11*
