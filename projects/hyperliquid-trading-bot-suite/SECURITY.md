# Security Documentation

**Status:** ✅ **IMPLEMENTATION COMPLETE** - All critical security issues have been addressed. Final testing and production configuration required before handling real funds.

**Last Updated:** 2025-02-11  
**Security Implementation:** See `backend/src/api/security/SECURITY_IMPLEMENTATION.md` for implementation details.

## Quick Reference - What's Implemented

| Security Feature | Status | Location |
|------------------|--------|----------|
| JWT Authentication | ✅ | `backend/src/api/security/auth.py` |
| Role-Based Access Control | ✅ | `backend/src/api/security/auth.py` |
| Private Key Encryption (AES-256-GCM) | ✅ | `backend/src/api/security/key_vault.py` |
| EIP-712 Signatures (not raw keys) | ✅ | `backend/src/api/security/key_vault.py` |
| Redis Rate Limiting | ✅ | `backend/src/api/security/rate_limiter.py` |
| WebSocket Authentication | ✅ | `backend/src/api/security/websocket_auth.py` |
| File Upload Validation (magic bytes) | ✅ | `backend/src/api/routes/ingestion.py` |
| CORS Lockdown | ✅ | `backend/src/api/main.py` |
| Security Headers | ✅ | `backend/src/api/main.py` |
| Account Lockout | ✅ | `backend/src/api/security/auth.py` |
| Decimal/String for Money | ✅ | `backend/src/api/routes/trades.py` |

This document outlines security findings from the code review, mitigations, and security best practices for the Hyperliquid Trading Bot Suite.

---

## Table of Contents

1. [Critical Issues](#critical-issues)
2. [High Priority Issues](#high-priority-issues)
3. [Medium Priority Issues](#medium-priority-issues)
4. [Security Architecture](#security-architecture)
5. [Threat Model](#threat-model)
6. [Security Best Practices](#security-best-practices)
7. [Incident Response](#incident-response)

---

## Implementation Status Summary

| Issue | Status | Implementation |
|-------|--------|----------------|
| CRITICAL #1: Authentication | ✅ IMPLEMENTED | JWT-based auth with RBAC |
| CRITICAL #2: Private Key Exposure | ✅ IMPLEMENTED | AES-256-GCM encrypted vault |
| CRITICAL #3: Hardcoded Credentials | ✅ IMPLEMENTED | Validated env vars |
| HIGH #1: WebSocket Auth | ✅ IMPLEMENTED | Token-based WS auth |
| HIGH #2: Rate Limiting | ✅ IMPLEMENTED | Redis-based rate limiter |
| MEDIUM #1: File Upload Security | ✅ IMPLEMENTED | Magic byte validation |
| MEDIUM #2: CORS Configuration | ✅ IMPLEMENTED | Environment-based config |
| MEDIUM #3: Input Validation | ✅ IMPLEMENTED | Decimal strings for money |

---

## Critical Issues

### ✅ CRITICAL #1: No Authentication/Authorization

**Status:** IMPLEMENTED  
**Risk:** Anyone can place trades, manage strategies, close positions  
**Impact:** Complete system compromise, unauthorized trading, fund theft

**Current State:**
```python
# backend/src/api/main.py
@app.post("/api/trades/manual")  # No authentication!
async def create_manual_trade(trade_data: Dict[str, Any]):
    # Anyone can call this endpoint
    return await position_manager.create_trade(trade_data)
```

**Required Fix:**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # Must be 32+ characters
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# User model
class User(BaseModel):
    username: str
    email: str
    full_name: str
    disabled: bool = False
    roles: list[str] = []

# Token model
class Token(BaseModel):
    access_token: str
    token_type: str

# Authentication functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_from_db(username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Role-based access control
def require_role(required_role: str):
    async def role_checker(user: User = Depends(get_current_active_user)):
        if required_role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return user
    return role_checker

# Login endpoint
@app.post("/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Protect endpoints
@app.post("/api/trades/manual")
async def create_manual_trade(
    trade_data: Dict[str, Any],
    current_user: User = Depends(require_role("trader"))
):
    # Now only authenticated traders can create trades
    return await position_manager.create_trade(trade_data, user=current_user)

# WebSocket authentication
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    try:
        user = await get_current_user(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    await websocket.accept()
    # ... continue with authenticated WebSocket
```

**Implementation Steps:**

1. Create user database schema with roles
2. Implement password hashing with bcrypt
3. Add JWT token generation and validation
4. Protect all API endpoints with `Depends(get_current_active_user)`
5. Implement role-based access control
6. Add WebSocket token authentication
7. Implement session management
8. Add failed login attempt limiting
9. Add password reset flow
10. Add 2FA for high-privilege accounts

---

### ✅ CRITICAL #2: Private Key Exposure (IMPLEMENTED)

**Status:** Insecure Implementation  
**Risk:** Wallet private keys exposed in logs, network traffic, headers  
**Impact:** Complete fund loss, wallet compromise

**Current State:**
```python
# backend/src/trading/hyperliquid_client.py
def _get_auth_headers(self):
    return {
        "Authorization": f"Bearer {self.private_key}",  # NEVER DO THIS!
        "Content-Type": "application/json"
    }
```

**Problems:**
- Private key sent in HTTP headers (logged, cached, exposed)
- No signature-based authentication
- Keys stored in environment variables (accessible to all processes)

**Required Fix:**

```python
from eth_account import Account
from eth_account.messages import encode_typed_data, encode_defunct
from eth_utils import to_checksum_address
from web3 import Web3
import time

class HyperliquidClient:
    def __init__(self, wallet_address: str, key_source: str = "vault"):
        """
        Initialize client with secure key management.
        
        Args:
            wallet_address: Ethereum address (public)
            key_source: "vault" (recommended), "env" (dev only), "hardware" (best)
        """
        self.wallet_address = to_checksum_address(wallet_address)
        self.key_source = key_source
        self._private_key = None  # Never stored in memory long-term
        
    def _get_signing_key(self) -> str:
        """Retrieve private key from secure source."""
        if self.key_source == "vault":
            # HashiCorp Vault, AWS Secrets Manager, etc.
            return self._fetch_from_vault()
        elif self.key_source == "hardware":
            # Ledger, Trezor, etc.
            return self._sign_with_hardware()
        elif self.key_source == "env":
            # Development only - log warning
            logger.warning("Using private key from environment - not for production!")
            return os.getenv("HYPERLIQUID_PRIVATE_KEY")
        else:
            raise ValueError(f"Unknown key source: {self.key_source}")
    
    def _sign_request(self, method: str, path: str, data: Optional[dict] = None) -> dict:
        """
        Sign request using EIP-712 typed data signatures.
        Private key never leaves this function.
        """
        # Create structured message
        timestamp = int(time.time() * 1000)
        message_to_sign = {
            "domain": {
                "name": "Hyperliquid",
                "version": "1",
                "chainId": 421614 if self.testnet else 42161,
            },
            "message": {
                "action": method,
                "path": path,
                "timestamp": timestamp,
                "nonce": secrets.token_hex(16),
            },
            "primaryType": "HyperliquidRequest",
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                ],
                "HyperliquidRequest": [
                    {"name": "action", "type": "string"},
                    {"name": "path", "type": "string"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "nonce", "type": "string"},
                ],
            },
        }
        
        # Get key securely (only exists in memory briefly)
        private_key = self._get_signing_key()
        
        try:
            # Sign message
            encoded_data = encode_typed_data(full_message=message_to_sign)
            signed_message = Account.sign_message(encoded_data, private_key=private_key)
            
            # Return headers with signature (NOT private key)
            return {
                "X-Signature": signed_message.signature.hex(),
                "X-Timestamp": str(timestamp),
                "X-Nonce": message_to_sign["message"]["nonce"],
                "X-Address": self.wallet_address,
                "Content-Type": "application/json",
            }
        finally:
            # Immediately clear private key from memory
            del private_key
            
    async def place_order(self, order: dict) -> dict:
        """Place order with signed request."""
        headers = self._sign_request("POST", "/trade", order)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/trade",
                json=order,
                headers=headers,  # Contains signature, not private key
            )
            response.raise_for_status()
            return response.json()
```

**Vault Integration (HashiCorp Vault):**

```python
import hvac

def _fetch_from_vault(self) -> str:
    """Retrieve private key from HashiCorp Vault."""
    client = hvac.Client(url=os.getenv("VAULT_ADDR"))
    client.token = os.getenv("VAULT_TOKEN")
    
    # Read secret
    secret = client.secrets.kv.v2.read_secret_version(
        path="hyperliquid/trading-bot",
        mount_point="secret"
    )
    
    return secret["data"]["data"]["private_key"]
```

**Hardware Wallet Integration:**

```python
from ledgerblue.comm import getDongle
from ledgerblue.commException import CommException

def _sign_with_hardware(self, message: bytes) -> str:
    """Sign message with Ledger hardware wallet."""
    dongle = getDongle()
    
    # Send message to Ledger for signing
    # User must approve on device
    signature = dongle.exchange(message)
    
    return signature
```

**Implementation Steps:**

1. Remove all private key transmission in headers
2. Implement EIP-712 signature-based authentication
3. Integrate with secure key storage (Vault, AWS Secrets Manager)
4. Add hardware wallet support for production
5. Clear private keys from memory immediately after use
6. Add key rotation procedure
7. Never log private keys or signatures
8. Implement key usage audit trail

---

### ✅ CRITICAL #3: Hardcoded Default Credentials (IMPLEMENTED)

**Status:** Insecure Defaults  
**Risk:** Attackers can access system with default credentials  
**Impact:** Complete system compromise

**Current State:**
```python
# backend/src/config.py
DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/trading_bot"
SECRET_KEY: str = "your-secret-key-change-in-production"
```

**Required Fix:**

```python
from pydantic import SecretStr, field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import sys

class Settings(BaseSettings):
    """Production-ready settings with validation."""
    
    model_config = SettingsConfigDict(
        env_file=None,  # Force explicit env vars
        case_sensitive=True,
        extra="forbid",  # Fail on unknown env vars
    )
    
    # Environment
    ENVIRONMENT: str
    DEBUG: bool = False
    
    # Database - NO DEFAULTS
    DATABASE_URL: SecretStr
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # Security - NO DEFAULTS
    SECRET_KEY: SecretStr
    JWT_SECRET_KEY: SecretStr
    
    # API Keys - NO DEFAULTS
    ANTHROPIC_API_KEY: SecretStr
    
    # Hyperliquid - NO DEFAULTS
    HYPERLIQUID_WALLET_ADDRESS: str
    HYPERLIQUID_TESTNET: bool = True  # Default to testnet (safe)
    
    @field_validator("SECRET_KEY", "JWT_SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: SecretStr) -> SecretStr:
        """Ensure secret keys are secure."""
        value = v.get_secret_value()
        
        # Check for common insecure values
        insecure_values = [
            "your-secret-key-change-in-production",
            "secret",
            "password",
            "12345",
            "test",
            "",
        ]
        
        if value.lower() in insecure_values:
            raise ValueError(
                f"SECRET_KEY contains insecure default value. "
                f"Generate secure key with: openssl rand -hex 32"
            )
        
        # Enforce minimum length
        if len(value) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        
        # Check entropy (basic check)
        unique_chars = len(set(value))
        if unique_chars < 16:
            raise ValueError("SECRET_KEY has insufficient entropy")
        
        return v
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: SecretStr) -> SecretStr:
        """Ensure database URL doesn't contain default credentials."""
        value = v.get_secret_value()
        
        # Check for insecure patterns
        insecure_patterns = [
            "postgres:password@",
            "postgres:postgres@",
            "root:password@",
            "admin:admin@",
        ]
        
        for pattern in insecure_patterns:
            if pattern in value:
                raise ValueError(
                    f"DATABASE_URL contains default credentials. "
                    f"Use secure credentials from secrets manager."
                )
        
        return v
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        allowed = ["development", "test", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of: {allowed}")
        return v

# Initialize settings
try:
    settings = Settings()
except ValidationError as e:
    print("❌ Configuration validation failed:", file=sys.stderr)
    print(e, file=sys.stderr)
    print("\nEnsure all required environment variables are set securely.", file=sys.stderr)
    sys.exit(1)

# Verify production safety
if settings.ENVIRONMENT == "production":
    if settings.DEBUG:
        print("❌ ERROR: DEBUG cannot be enabled in production", file=sys.stderr)
        sys.exit(1)
    
    if settings.HYPERLIQUID_TESTNET:
        print("⚠️  WARNING: HYPERLIQUID_TESTNET=true in production", file=sys.stderr)
        print("   Ensure this is intentional", file=sys.stderr)
```

**Environment Variable Template:**

```bash
# .env.template (for documentation only - never contains real values)
# Copy this to .env and fill with secure values

# Required - No defaults allowed
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
ANTHROPIC_API_KEY=<from-anthropic-console>
HYPERLIQUID_WALLET_ADDRESS=<your-ethereum-address>

# Optional with safe defaults
DEBUG=false
LOG_LEVEL=INFO
HYPERLIQUID_TESTNET=false
```

**Startup Script with Validation:**

```bash
#!/bin/bash
# scripts/start-production.sh

set -e

echo "🔐 Validating production configuration..."

# Check all required env vars are set
required_vars=(
    "ENVIRONMENT"
    "DATABASE_URL"
    "SECRET_KEY"
    "JWT_SECRET_KEY"
    "ANTHROPIC_API_KEY"
    "HYPERLIQUID_WALLET_ADDRESS"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ ERROR: Missing required environment variables:"
    printf '   - %s\n' "${missing_vars[@]}"
    exit 1
fi

# Validate SECRET_KEY strength
if [ ${#SECRET_KEY} -lt 32 ]; then
    echo "❌ ERROR: SECRET_KEY must be at least 32 characters"
    exit 1
fi

# Check for insecure patterns
if [[ "$SECRET_KEY" =~ ^(secret|password|test|12345) ]]; then
    echo "❌ ERROR: SECRET_KEY contains insecure value"
    exit 1
fi

# Warn if testnet in production
if [ "$ENVIRONMENT" = "production" ] && [ "$HYPERLIQUID_TESTNET" = "true" ]; then
    echo "⚠️  WARNING: Running on testnet in production environment"
    read -p "   Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ Configuration validated"
echo "🚀 Starting application..."

# Start application
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**Implementation Steps:**

1. Remove all default credentials from code
2. Add strict validation to Settings class
3. Require all secrets via environment variables
4. Validate secrets at startup (fail fast)
5. Create startup script that validates configuration
6. Document secret generation procedures
7. Implement secrets rotation policy
8. Use secrets manager in production (not env vars)

---

## High Priority Issues

### ✅ HIGH #1: Unauthenticated WebSocket Endpoints (IMPLEMENTED)

**Status:** No authentication  
**Risk:** Anonymous access to live trading data, backtest streams  
**Impact:** Information disclosure, unauthorized monitoring

**Fix:** Implement WebSocket token authentication (see CRITICAL #1)

---

### ✅ HIGH #2: No Rate Limiting (IMPLEMENTED)

**Status:** Not Implemented  
**Risk:** API abuse, DoS attacks, cost amplification  
**Impact:** Service degradation, unexpected costs

**Fix:**

```bash
pip install slowapi redis
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Initialize rate limiter with Redis backend
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",
    strategy="fixed-window",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Apply rate limits per endpoint
@app.post("/api/trades/manual")
@limiter.limit("10/minute")  # Max 10 manual trades per minute
async def create_manual_trade(request: Request, ...):
    ...

@app.post("/api/ingestion/pdf")
@limiter.limit("5/hour")  # Max 5 PDF uploads per hour
async def upload_pdf(request: Request, ...):
    ...

@app.post("/auth/login")
@limiter.limit("5/minute")  # Prevent brute force
async def login(request: Request, ...):
    ...

# User-specific rate limiting (after authentication)
async def get_user_rate_limit_key(request: Request) -> str:
    """Rate limit by user ID instead of IP."""
    user = await get_current_user(request)
    return f"user:{user.id}"

@app.post("/api/backtest/start")
@limiter.limit("10/hour", key_func=get_user_rate_limit_key)
async def start_backtest(request: Request, ...):
    ...
```

---

## Medium Priority Issues

### ✅ MEDIUM #1: File Upload Security Gaps (IMPLEMENTED)

**Current Issues:**
- Only checks file extension (easily spoofed)
- User-provided filenames (path traversal risk)
- No virus scanning

**Fix:** See `DEPLOYMENT.md` Section 2.5 for complete fix

---

### ✅ MEDIUM #2: Overly Permissive CORS (IMPLEMENTED)

**Fix:** See `DEPLOYMENT.md` Section 2.6

---

### ✅ MEDIUM #3: Unvalidated Manual Trade Input (IMPLEMENTED)

**Fix:**

```python
from pydantic import BaseModel, Field, validator
from decimal import Decimal

class ManualTradeRequest(BaseModel):
    symbol: str = Field(..., regex="^[A-Z]+-[A-Z]+$")
    side: Literal["long", "short"]
    size: Decimal = Field(..., gt=0)
    entry_price: Decimal = Field(..., gt=0)
    stop_loss: Decimal = Field(..., gt=0)
    take_profit: list[Decimal] = Field(..., min_items=1, max_items=3)
    
    @validator("stop_loss")
    def validate_stop_loss(cls, v, values):
        """Ensure stop loss is on correct side."""
        if "side" in values and "entry_price" in values:
            entry = values["entry_price"]
            if values["side"] == "long" and v >= entry:
                raise ValueError("Stop loss must be below entry for long")
            if values["side"] == "short" and v <= entry:
                raise ValueError("Stop loss must be above entry for short")
        return v

@app.post("/api/trades/manual")
async def create_manual_trade(trade: ManualTradeRequest, ...):
    # Now validated!
    ...
```

---

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────┐
│                     Internet / Users                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│  Layer 1: Network Security                                  │
│  - Firewall (UFW/Security Groups)                          │
│  - DDoS Protection (Cloudflare)                             │
│  - Rate Limiting (Nginx)                                    │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│  Layer 2: Transport Security                                │
│  - TLS 1.3                                                  │
│  - HSTS                                                      │
│  - Certificate Pinning                                      │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│  Layer 3: Application Security                              │
│  - Authentication (JWT)                                     │
│  - Authorization (RBAC)                                     │
│  - Input Validation                                         │
│  - Output Encoding                                          │
│  - CSRF Protection                                          │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│  Layer 4: Business Logic Security                           │
│  - Risk Limits                                              │
│  - Position Limits                                          │
│  - Circuit Breakers                                         │
│  - Audit Logging                                            │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│  Layer 5: Data Security                                     │
│  - Encryption at Rest                                       │
│  - Encrypted Backups                                        │
│  - Secrets Management                                       │
│  - Secure Key Storage                                       │
└────────────────────────────────────────────────────────────┘
```

---

## Threat Model

### Assets

1. **Hyperliquid Wallet Private Keys** - Most critical, enables fund theft
2. **Trading Capital** - Funds in wallet, positions
3. **API Keys** - Claude API (cost), Hyperliquid API
4. **Strategy Rules** - Proprietary trading logic
5. **Trade History** - Competitive intelligence
6. **User Data** - PII, authentication credentials

### Threat Actors

1. **External Attackers** - Financially motivated, seeking wallet access
2. **Insider Threats** - Employees with system access
3. **Automated Bots** - Credential stuffing, API abuse
4. **Competitors** - Industrial espionage, strategy theft

### Attack Vectors

| Attack Vector | Likelihood | Impact | Mitigation |
|---------------|------------|--------|------------|
| Credential Stuffing | High | Critical | 2FA, rate limiting, strong passwords |
| API Key Theft | High | High | Vault storage, rotation, scope limiting |
| SQL Injection | Medium | Critical | Parameterized queries, ORM |
| XSS | Medium | High | Output encoding, CSP headers |
| Private Key Theft | Medium | Critical | Signature-based auth, hardware wallet |
| DoS/DDoS | High | Medium | Rate limiting, CDN, auto-scaling |
| Phishing | High | Critical | Email validation, 2FA, security training |
| Man-in-the-Middle | Low | Critical | TLS, certificate pinning |
| Insider Abuse | Low | Critical | RBAC, audit logging, segregation of duties |
| Supply Chain | Medium | Critical | Dependency scanning, SBOM |

---

## Security Best Practices

### Development

1. **Never commit secrets to git**
   - Use `.env` files (in `.gitignore`)
   - Use git-secrets pre-commit hook
   - Scan history for leaked secrets

2. **Dependency management**
   - Pin all dependency versions
   - Run `pip-audit` and `npm audit` regularly
   - Review dependencies for CVEs
   - Use Snyk or Dependabot

3. **Code review**
   - Security review for all trading logic
   - Peer review for authentication changes
   - Automated SAST scanning

4. **Testing**
   - Security test cases in test suite
   - Penetration testing before production
   - Regular security audits

### Operations

1. **Secrets management**
   - Use HashiCorp Vault or AWS Secrets Manager
   - Rotate secrets every 90 days
   - Audit secret access
   - Revoke on team member departure

2. **Access control**
   - Principle of least privilege
   - Multi-factor authentication
   - Strong password policy (16+ chars)
   - Regular access reviews

3. **Monitoring**
   - Log all authentication events
   - Alert on failed login attempts (5+ in 5 min)
   - Alert on unusual trading activity
   - Alert on configuration changes

4. **Incident response**
   - Documented runbook
   - Emergency contact list
   - Backup restore procedure
   - Post-mortem process

### Trading Specific

1. **Start small**
   - Paper trading first (6+ months)
   - Testnet with real strategies (3+ months)
   - Mainnet with small positions (1-2% of capital)
   - Scale up gradually

2. **Risk controls**
   - Daily loss limit enforced at system level
   - Position size limits
   - Emergency kill switch
   - Manual approval for large trades

3. **Monitoring**
   - Real-time P&L tracking
   - Anomaly detection on trading patterns
   - Alert on large drawdowns
   - Alert on stuck positions

---

## Incident Response

### Severity Levels

**P0 - Critical (< 1 hour response)**
- Private key compromised
- Unauthorized trades executed
- System completely down

**P1 - High (< 4 hours)**
- Authentication bypass discovered
- API keys leaked
- Large unexpected loss

**P2 - Medium (< 24 hours)**
- Non-critical vulnerability discovered
- Performance degradation
- Monitoring alerts

**P3 - Low (< 1 week)**
- Minor bugs
- Enhancement requests

### Response Procedure

1. **Detection**
   - Alert triggered or manual discovery
   - Initial assessment of impact

2. **Containment**
   - Emergency kill switch if trading-related
   - Block attacker IP if applicable
   - Rotate compromised credentials
   - Isolate affected systems

3. **Eradication**
   - Identify root cause
   - Remove attacker access
   - Patch vulnerability
   - Deploy fix

4. **Recovery**
   - Restore from backup if needed
   - Verify system integrity
   - Resume operations gradually
   - Monitor for repeat

5. **Post-Mortem**
   - Document incident timeline
   - Identify improvements
   - Update runbooks
   - Share learnings with team

### Emergency Contacts

```
Security Team Lead: [Contact]
DevOps On-Call: [Contact]
Infrastructure Team: [Contact]
Executive Notification: [Contact]
Legal/Compliance: [Contact]
```

### Emergency Kill Switch

```python
# Emergency shutdown procedure
# Run this to halt all trading immediately

import asyncio
from src.trading.position_manager import PositionManager
from src.trading.risk_manager import RiskManager

async def emergency_shutdown():
    """Halt all trading and close positions."""
    print("🚨 EMERGENCY SHUTDOWN INITIATED")
    
    # 1. Halt new trades
    risk_manager.circuit_breaker.trip("Emergency shutdown")
    print("✓ Circuit breaker tripped - no new trades")
    
    # 2. Cancel all open orders
    await position_manager.cancel_all_orders(reason="emergency")
    print("✓ All open orders cancelled")
    
    # 3. Close all positions at market (optional)
    positions = await position_manager.get_all_positions()
    for pos in positions:
        await position_manager.close_position(
            pos.id,
            reason="emergency",
            order_type="market"
        )
    print(f"✓ Closed {len(positions)} positions")
    
    # 4. Disable API access
    await disable_api_access()
    print("✓ API access disabled")
    
    print("🛑 EMERGENCY SHUTDOWN COMPLETE")
    print("   Review logs and assess situation before resuming")

# Run it
asyncio.run(emergency_shutdown())
```

---

## Security Checklist

Before production deployment:

### Code
- [ ] All CRITICAL issues resolved
- [ ] All HIGH issues resolved
- [ ] MEDIUM issues mitigated or accepted risk
- [ ] Security code review completed
- [ ] SAST scanning passed
- [ ] Dependency vulnerabilities addressed

### Infrastructure
- [ ] Firewall configured properly
- [ ] SSL/TLS with strong ciphers
- [ ] Secrets in vault, not environment
- [ ] Backup encryption enabled
- [ ] Database encryption at rest

### Authentication
- [ ] JWT authentication implemented
- [ ] Role-based access control
- [ ] Strong password policy
- [ ] 2FA for admin accounts
- [ ] Session timeout configured

### Monitoring
- [ ] Security logging enabled
- [ ] Failed login alerts configured
- [ ] Unusual activity detection
- [ ] Audit trail for all trades
- [ ] Incident response runbook

### Trading
- [ ] Paper trading tested thoroughly
- [ ] Testnet trading verified
- [ ] Risk limits cannot be bypassed
- [ ] Emergency kill switch functional
- [ ] Position limits enforced

---

## Responsible Disclosure

If you discover a security vulnerability:

1. **Do not** disclose publicly
2. Email: security@yourdomain.com
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We aim to respond within 24 hours and resolve within 7 days for critical issues.

---

**Remember:** This system handles real money. Security is not optional. Address all critical issues before production deployment.
