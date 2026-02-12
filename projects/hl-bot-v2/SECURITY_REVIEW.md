# Security Review: hl-bot-v2

**Reviewed:** 2025-02-11  
**Reviewer:** Security Reviewer (Automated)  
**Status:** 🔴 REQUEST_CHANGES

## Summary

The **trading components** (Hyperliquid client, risk manager, position tracker) are **well-designed** with proper security controls including circuit breakers, audit logging, decimal precision for money, and rate limiting.

However, the **API layer has CRITICAL security gaps** that must be addressed before any production deployment.

---

## Critical Issues (Must Fix)

### 1. CORS Wildcard Configuration
**File:** `backend/app/main.py:15-20`

```python
# CURRENT - INSECURE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ← CRITICAL VULNERABILITY
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact:** Allows any website to make authenticated requests to your API. Enables:
- Cross-Site Request Forgery (CSRF) attacks
- Data exfiltration by malicious sites
- Credential theft when combined with `allow_credentials=True`

**Fix:**
```python
import os

ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS", 
    "http://localhost:3000,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

### 2. User Input to Subprocess
**File:** `backend/app/api/routes/backtest.py:66-91`

```python
# User-controlled values passed directly to subprocess
cmd = [
    "python",
    "scripts/run_backtest_stream.py",
    "--symbol", request.symbol,        # ← User input
    "--start-date", request.start_date, # ← User input
    "--end-date", request.end_date,     # ← User input
    # ...
]
process = subprocess.Popen(cmd, ...)
```

**Impact:** While `shell=True` is not used (good), malformed inputs could:
- Cause script crashes with crafted strings
- Potentially exploit argument parsing vulnerabilities

**Fix:** Add strict validation before subprocess call:
```python
import re
from datetime import datetime

def validate_symbol(symbol: str) -> str:
    if not re.match(r"^[A-Z]{2,10}-[A-Z]{2,10}$", symbol):
        raise HTTPException(400, "Invalid symbol format. Expected: BTC-USD")
    return symbol

def validate_date(date_str: str) -> str:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise HTTPException(400, "Invalid date format. Expected: YYYY-MM-DD")

# Then in handler:
symbol = validate_symbol(request.symbol)
start_date = validate_date(request.start_date)
end_date = validate_date(request.end_date)
```

---

## High Issues

### 3. No Authentication on API Endpoints
**Files:** All routes in `backend/app/api/routes/`

**Impact:** Anyone can:
- Import data
- Delete all data (`DELETE /api/data/clear`)
- Start/stop backtests
- Access position information

**Fix:** Add authentication middleware:
```python
from fastapi import Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

async def require_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    expected_key = os.environ.get("API_KEY")
    if not expected_key or api_key != expected_key:
        raise HTTPException(401, "Invalid API key")
    return api_key

# Use in routes:
@router.delete("/clear")
async def clear_data(
    ...,
    _: str = Depends(require_api_key),  # Require auth
):
```

---

### 4. Default Database Credentials in Code
**File:** `backend/app/config.py:17`

```python
database_url: str = "postgresql://hlbot:hlbot_dev_password@localhost:5432/hlbot"
```

**Fix:** Remove default or use non-functional placeholder:
```python
database_url: str = Field(
    ...,  # Required, no default
    description="Database connection URL"
)
# OR
database_url: str = "postgresql://user:password@host:5432/database"
```

---

### 5. Environment File May Be Tracked
**File:** `.env` (project root)

The root `.env` file exists and may be tracked in git. While `.gitignore` has patterns, verify it's actually ignored.

**Fix:** 
```bash
# Verify .env is ignored
git check-ignore .env

# If not ignored, add to .gitignore
echo ".env" >> .gitignore
git rm --cached .env  # If already tracked
```

---

## Medium Issues

### 6. Error Messages Leak Internal Details
**Multiple files**

```python
# BAD - Leaks internal paths/errors
raise HTTPException(500, detail=f"Import failed: {str(e)}")
```

**Fix:**
```python
import logging
logger = logging.getLogger(__name__)

# Log full error internally
logger.error(f"Import failed: {e}", exc_info=True)

# Return generic message
raise HTTPException(500, detail="Import failed. Check server logs.")
```

---

### 7. Missing Rate Limiting
**File:** `backend/app/main.py`

No rate limiting middleware. API can be abused.

**Fix:** Add slowapi or custom rate limiter:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/import")
@limiter.limit("10/minute")
async def import_csv_file(...):
```

---

### 8. WebSocket Connections Unlimited
**File:** `backend/app/api/routes/backtest.py`

No connection limits or authentication on WebSocket endpoints.

**Fix:**
```python
MAX_CONNECTIONS = 50

class ConnectionManager:
    def __init__(self, max_connections: int = MAX_CONNECTIONS):
        self.connections = []
        self.max_connections = max_connections
    
    async def connect(self, websocket: WebSocket) -> bool:
        if len(self.connections) >= self.max_connections:
            await websocket.close(code=1008, reason="Too many connections")
            return False
        await websocket.accept()
        self.connections.append(websocket)
        return True
```

---

## Positive Findings ✅

The trading components demonstrate excellent security practices:

1. **Risk Manager (`risk.py`)**
   - Circuit breaker with automatic trip on consecutive errors/losses
   - Daily loss limits (absolute and percentage-based)
   - Position size limits
   - Price sanity checks to prevent fat-finger errors
   - All orders validated through pre-trade checks

2. **Hyperliquid Client (`hyperliquid.py`)**
   - Rate limiting with 30% headroom (70/min vs 100/min limit)
   - Exponential backoff on retries
   - Full audit logging of all operations
   - Decimal precision for all financial calculations
   - WebSocket auto-reconnection

3. **Configuration (`src/hl_bot/config.py`)**
   - Uses `SecretStr` for private keys (won't appear in logs/repr)
   - Loads secrets from environment variables
   - Proper validation with Pydantic

4. **Position Tracking**
   - Proper state management
   - Tracks from fills (not polling)
   - Real-time P&L calculation

5. **General**
   - Comprehensive `.gitignore` for secrets
   - No hardcoded API keys in trading code
   - Proper async/await handling

---

## Remediation Priority

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| 🔴 P0 | CORS wildcard | 10 min | Critical |
| 🔴 P0 | Add API authentication | 2 hr | Critical |
| 🟠 P1 | Validate subprocess inputs | 30 min | High |
| 🟠 P1 | Remove default DB creds | 5 min | High |
| 🟡 P2 | Sanitize error messages | 1 hr | Medium |
| 🟡 P2 | Add rate limiting | 1 hr | Medium |
| 🟢 P3 | WebSocket limits | 30 min | Low |

---

## Conclusion

**DO NOT DEPLOY TO PRODUCTION** until at minimum:
1. ✅ CORS configured with specific origins
2. ✅ API authentication implemented
3. ✅ Subprocess inputs validated

The trading logic is production-ready from a security standpoint. The API layer needs hardening.
