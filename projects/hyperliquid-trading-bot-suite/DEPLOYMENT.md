# Deployment Guide

Complete production deployment guide for the Hyperliquid Trading Bot Suite.

⚠️ **CRITICAL:** This system handles real money. Review the [Security Checklist](#security-checklist) before production deployment.

---

## Table of Contents

1. [Pre-Deployment](#pre-deployment)
2. [Security Hardening](#security-hardening)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Application Deployment](#application-deployment)
5. [Post-Deployment](#post-deployment)
6. [Monitoring & Operations](#monitoring--operations)
7. [Backup & Recovery](#backup--recovery)

---

## Pre-Deployment

### Requirements

**Server Requirements:**
- **OS:** Ubuntu 22.04 LTS or newer
- **CPU:** 4+ cores (8+ recommended for high-frequency trading)
- **RAM:** 16GB minimum (32GB recommended)
- **Storage:** 100GB SSD (500GB+ for extended history)
- **Network:** Low-latency connection to Hyperliquid

**Software Requirements:**
- Docker 24.0+
- Docker Compose v2.20+
- Nginx 1.24+ (reverse proxy)
- Certbot (SSL certificates)

**Accounts & Keys:**
- Anthropic API key (Claude)
- Hyperliquid wallet with funded account
- Domain name (for SSL)
- Server with SSH access

### Pre-Flight Checklist

Before deploying, ensure:

- [ ] Code review findings addressed (see `progress.md`)
- [ ] All tests passing (`make test`)
- [ ] Security audit completed
- [ ] API keys and secrets prepared
- [ ] Backup strategy defined
- [ ] Monitoring infrastructure ready
- [ ] Rollback plan documented
- [ ] Team briefed on deployment process

---

## Security Hardening

⚠️ **CRITICAL SECURITY FIXES REQUIRED** — Address these before production:

### 1. Authentication & Authorization

The application currently **has no authentication**. Implement before deployment:

```python
# backend/src/api/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validate JWT token and return user."""
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
        return username
    except JWTError:
        raise credentials_exception

# Apply to all routes
@router.post("/trades/manual", dependencies=[Depends(get_current_user)])
async def create_manual_trade(...):
    ...
```

**Required Changes:**
- Implement JWT-based authentication
- Add role-based access control (admin, trader, viewer)
- Protect all API endpoints
- WebSocket authentication via token
- Session management with secure cookies

### 2. Private Key Handling

**NEVER** send raw private keys in HTTP headers:

```python
# backend/src/trading/hyperliquid_client.py
from eth_account import Account
from eth_account.messages import encode_typed_data

class HyperliquidClient:
    def _sign_request(self, method: str, path: str, data: dict) -> dict:
        """Sign request using EIP-712 signatures."""
        # Create structured message
        message = encode_typed_data(
            domain={"name": "Hyperliquid", "version": "1"},
            message={"method": method, "path": path, "timestamp": int(time.time())},
            types={"EIP712Domain": [...], "Request": [...]},
        )
        
        # Sign with private key (never transmitted)
        signed = Account.sign_message(message, private_key=self._private_key)
        
        return {
            "X-Signature": signed.signature.hex(),
            "X-Timestamp": message["timestamp"],
            "X-Address": self.wallet_address,
        }
```

**Required Changes:**
- Implement EIP-712 signature-based authentication
- Store private keys in secure vault (HashiCorp Vault, AWS Secrets Manager)
- Never log or transmit raw private keys
- Use hardware wallets for production

### 3. Environment Variables

Remove hardcoded defaults and require secure configuration:

```python
# backend/src/config.py
from pydantic import SecretStr, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # No defaults for sensitive values
    ANTHROPIC_API_KEY: SecretStr
    HYPERLIQUID_PRIVATE_KEY: SecretStr
    SECRET_KEY: SecretStr
    DATABASE_URL: SecretStr
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if v.get_secret_value() in ["your-secret-key-change-in-production", ""]:
            raise ValueError("SECRET_KEY must be set to a secure value")
        if len(v.get_secret_value()) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v
    
    class Config:
        env_file = None  # Force explicit env var setting
        case_sensitive = True
```

**Required Changes:**
- Remove all default credentials
- Validate all secrets at startup
- Use environment-specific configuration
- Implement secrets rotation

### 4. Rate Limiting

Add rate limiting to prevent abuse:

```bash
pip install slowapi
```

```python
# backend/src/api/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/trades/manual")
@limiter.limit("10/minute")  # Max 10 manual trades per minute
async def create_manual_trade(request: Request, ...):
    ...
```

**Required Changes:**
- Add rate limiting to all endpoints
- Different limits per endpoint type
- User-specific rate limits
- IP-based fallback limits

### 5. File Upload Security

Harden file upload validation:

```python
# backend/src/api/routes/ingestion.py
import magic
import hashlib
from pathlib import Path

ALLOWED_MIME_TYPES = {
    "application/pdf": [".pdf"],
    "video/mp4": [".mp4"],
    "video/webm": [".webm"],
}

async def validate_upload(file: UploadFile) -> Path:
    """Validate file type and save securely."""
    # Read file header
    header = await file.read(2048)
    await file.seek(0)
    
    # Validate magic bytes
    mime = magic.from_buffer(header, mime=True)
    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"Invalid file type: {mime}")
    
    # Generate secure filename
    file_hash = hashlib.sha256(header).hexdigest()[:16]
    safe_name = f"{file_hash}{ALLOWED_MIME_TYPES[mime][0]}"
    
    # Save outside webroot
    upload_dir = Path("/var/lib/trading-bot/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / safe_name
    
    # Scan with ClamAV if available
    # ... virus scanning logic ...
    
    return file_path
```

**Required Changes:**
- Validate magic bytes, not extensions
- Generate random filenames
- Store outside webroot
- Implement virus scanning
- Size limits enforced

### 6. CORS Configuration

Restrict CORS to specific origins:

```python
# backend/src/api/main.py
from fastapi.middleware.cors import CORSMiddleware

# Production CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://trading.yourdomain.com",
        "https://dashboard.yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID"],
)
```

---

## Infrastructure Setup

### 1. Server Provisioning

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install Nginx
sudo apt install nginx certbot python3-certbot-nginx -y

# Create application user
sudo useradd -r -s /bin/false trading-bot
sudo mkdir -p /opt/trading-bot
sudo chown trading-bot:trading-bot /opt/trading-bot
```

### 2. Firewall Configuration

```bash
# Configure UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Block direct access to application ports
# Traffic must go through Nginx
sudo ufw deny 8000
sudo ufw deny 3000
```

### 3. Nginx Configuration

Create `/etc/nginx/sites-available/trading-bot`:

```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;

# Backend API
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# Frontend
upstream frontend {
    server 127.0.0.1:3000;
    keepalive 32;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name trading.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name trading.yourdomain.com;

    # SSL Configuration (managed by certbot)
    ssl_certificate /etc/letsencrypt/live/trading.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/trading.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;

    # Max upload size
    client_max_body_size 100M;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }

    # Backend API
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://backend/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }

    # Authentication endpoints (stricter rate limiting)
    location /api/auth/ {
        limit_req zone=auth_limit burst=3 nodelay;
        
        proxy_pass http://backend/api/auth/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://backend/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Health check (no rate limiting)
    location /api/health {
        proxy_pass http://backend/api/health;
        access_log off;
    }

    # API Documentation (restrict in production)
    location /api/docs {
        # auth_basic "API Documentation";
        # auth_basic_user_file /etc/nginx/.htpasswd;
        
        proxy_pass http://backend/api/docs;
        proxy_set_header Host $host;
    }

    # Static files from frontend
    location /_nuxt/ {
        proxy_pass http://frontend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable site and get SSL certificate:

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/trading-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d trading.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### 4. Database Setup

For production, use managed database service (AWS RDS, Digital Ocean, etc.) or dedicated server:

```bash
# Install PostgreSQL 15 with pgvector
sudo apt install postgresql-15 postgresql-contrib-15 -y

# Install pgvector extension
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
sudo apt install postgresql-server-dev-15 -y
make
sudo make install

# Configure PostgreSQL
sudo -u postgres psql << EOF
CREATE DATABASE trading_bot;
CREATE USER trading_user WITH ENCRYPTED PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE trading_bot TO trading_user;
\c trading_bot
CREATE EXTENSION vector;
EOF

# Configure remote access (if needed)
sudo nano /etc/postgresql/15/main/postgresql.conf
# listen_addresses = 'localhost'  # Or specific IP

sudo nano /etc/postgresql/15/main/pg_hba.conf
# Add: hostssl trading_bot trading_user <app-server-ip>/32 scram-sha-256

sudo systemctl restart postgresql
```

### 5. Redis Setup

```bash
# Install Redis
sudo apt install redis-server -y

# Configure for production
sudo nano /etc/redis/redis.conf

# Key settings:
# bind 127.0.0.1
# requirepass secure_redis_password_here
# maxmemory 2gb
# maxmemory-policy allkeys-lru
# save 900 1
# save 300 10
# save 60 10000

sudo systemctl restart redis
```

---

## Application Deployment

### 1. Clone Repository

```bash
cd /opt/trading-bot
sudo -u trading-bot git clone https://github.com/your-org/hyperliquid-trading-bot-suite.git .
```

### 2. Configure Environment

```bash
# Create production environment file
sudo -u trading-bot nano /opt/trading-bot/.env.production

# Add configuration (see template below)
```

**Production `.env.production` template:**

```bash
# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Server
HOST=0.0.0.0
PORT=8000

# Database (use managed service in production)
DATABASE_URL=postgresql+asyncpg://trading_user:secure_password@db-server:5432/trading_bot
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_ECHO=false

# Redis
REDIS_URL=redis://:secure_redis_password@redis-server:6379/0
REDIS_MAX_CONNECTIONS=50

# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=60

# API Keys (from secure vault)
ANTHROPIC_API_KEY=<from-vault>
OPENAI_API_KEY=<from-vault>

# Hyperliquid
HYPERLIQUID_PRIVATE_KEY=<from-vault-or-hardware-wallet>
HYPERLIQUID_WALLET_ADDRESS=0x...
HYPERLIQUID_TESTNET=false
HYPERLIQUID_API_URL=https://api.hyperliquid.xyz

# Trading Configuration
MAX_RISK_PER_TRADE=0.01  # 1% in production (conservative)
MAX_CONCURRENT_POSITIONS=3
MAX_DAILY_LOSS_PERCENT=0.03  # 3% daily loss limit
MIN_CONFLUENCE_SCORE=0.75
PAPER_TRADING_MODE=false

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# File Upload
MAX_FILE_SIZE=52428800  # 50MB
MAX_VIDEO_DURATION=1800  # 30 minutes
MAX_PDF_PAGES=50
UPLOAD_DIR=/var/lib/trading-bot/uploads
TEMP_DIR=/var/lib/trading-bot/temp

# Frontend
NUXT_PUBLIC_API_BASE_URL=https://trading.yourdomain.com/api
NUXT_PUBLIC_WS_URL=wss://trading.yourdomain.com/ws

# Monitoring
SENTRY_DSN=<optional-error-tracking>
PROMETHEUS_ENABLED=true
```

Generate secure keys:

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate JWT_SECRET_KEY
openssl rand -hex 32
```

### 3. Build Docker Images

```bash
cd /opt/trading-bot

# Build production images
sudo docker-compose -f docker-compose.yml build --no-cache

# Or use pre-built images from registry
# sudo docker-compose -f docker-compose.yml pull
```

### 4. Database Migrations

```bash
# Run migrations
sudo docker-compose run --rm backend alembic upgrade head

# Verify
sudo docker-compose run --rm backend alembic current
```

### 5. Start Services

```bash
# Start all services
sudo docker-compose -f docker-compose.yml up -d

# Check status
sudo docker-compose ps

# Check logs
sudo docker-compose logs -f backend
sudo docker-compose logs -f frontend
```

### 6. Systemd Service (Alternative to docker-compose)

For more control, create systemd services:

`/etc/systemd/system/trading-bot-backend.service`:

```ini
[Unit]
Description=Hyperliquid Trading Bot Backend
After=docker.service postgresql.service redis.service
Requires=docker.service
PartOf=trading-bot.target

[Service]
Type=simple
User=trading-bot
WorkingDirectory=/opt/trading-bot
EnvironmentFile=/opt/trading-bot/.env.production

# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/trading-bot /var/lib/trading-bot

# Resource limits
MemoryMax=8G
CPUQuota=400%

# Restart policy
Restart=always
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=300

ExecStart=/usr/bin/docker-compose -f docker-compose.yml up backend
ExecStop=/usr/bin/docker-compose -f docker-compose.yml stop backend

StandardOutput=journal
StandardError=journal
SyslogIdentifier=trading-bot-backend

[Install]
WantedBy=trading-bot.target
```

Similar for frontend, create trading-bot.target:

```bash
sudo systemctl enable trading-bot-backend.service
sudo systemctl enable trading-bot-frontend.service
sudo systemctl start trading-bot.target
```

---

## Post-Deployment

### 1. Smoke Tests

```bash
# Health check
curl https://trading.yourdomain.com/api/health

# Expected response:
# {"status": "healthy", "database": "connected", "redis": "connected"}

# API documentation
curl https://trading.yourdomain.com/api/docs
# Should require authentication

# Frontend
curl -I https://trading.yourdomain.com/
# Should return 200 OK
```

### 2. Create Admin User

```bash
# Create first admin user
sudo docker-compose exec backend python -m scripts.create_admin \
  --email admin@yourdomain.com \
  --password <secure-password>
```

### 3. Verify Trading Connection

```bash
# Test Hyperliquid connection (paper trading first!)
sudo docker-compose exec backend python -m scripts.test_hyperliquid

# Check output for successful connection
```

### 4. Load Initial Strategies

```bash
# Upload sample strategies
curl -X POST https://trading.yourdomain.com/api/ingestion/pdf \
  -H "Authorization: Bearer <token>" \
  -F "file=@sample_strategy.pdf"
```

---

## Monitoring & Operations

### 1. Log Aggregation

Configure centralized logging:

```yaml
# docker-compose.yml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service,environment"
        tag: "{{.Name}}/{{.ID}}"
```

Ship logs to ELK, Datadog, or CloudWatch:

```bash
# Example: Ship to Loki
docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions
```

### 2. Metrics & Monitoring

Expose Prometheus metrics:

```python
# backend/src/api/main.py
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

Configure Prometheus scraping:

```yaml
# /etc/prometheus/prometheus.yml
scrape_configs:
  - job_name: 'trading-bot'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    bearer_token: '<secure-token>'
```

### 3. Alerting

Configure alerts for critical events:

```yaml
# /etc/prometheus/alerts.yml
groups:
  - name: trading_bot
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      - alert: DailyLossLimitReached
        expr: trading_daily_loss_percent > 0.03
        annotations:
          summary: "Daily loss limit reached - trading halted"
          
      - alert: PositionStuck
        expr: trading_position_duration_minutes > 1440
        annotations:
          summary: "Position open for > 24 hours"
```

### 4. Health Monitoring

Set up external monitoring (UptimeRobot, Pingdom, etc.):

- **Endpoint:** `https://trading.yourdomain.com/api/health`
- **Interval:** 1 minute
- **Alert:** Email/SMS on failure

---

## Backup & Recovery

### 1. Database Backups

```bash
# Create backup script
sudo nano /opt/trading-bot/scripts/backup-db.sh
```

```bash
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/trading-bot"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/trading_bot_$DATE.sql.gz"

mkdir -p $BACKUP_DIR

# Backup database
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -U $DB_USER -d trading_bot | gzip > $BACKUP_FILE

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

Automate with cron:

```bash
sudo crontab -e

# Backup database daily at 2 AM
0 2 * * * /opt/trading-bot/scripts/backup-db.sh >> /var/log/trading-bot/backup.log 2>&1

# Backup to S3 weekly
0 3 * * 0 aws s3 sync /var/backups/trading-bot s3://your-bucket/backups/
```

### 2. Configuration Backups

```bash
# Backup configuration and environment
tar -czf /var/backups/trading-bot/config_$(date +%Y%m%d).tar.gz \
  /opt/trading-bot/.env.production \
  /opt/trading-bot/docker-compose.yml \
  /etc/nginx/sites-available/trading-bot
```

### 3. Restore Procedure

```bash
# Stop application
sudo systemctl stop trading-bot.target

# Restore database
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d trading_bot < backup.sql

# Restore configuration
tar -xzf config_backup.tar.gz -C /

# Start application
sudo systemctl start trading-bot.target

# Verify
curl https://trading.yourdomain.com/api/health
```

---

## Security Checklist

Before going live, verify:

### Authentication & Authorization
- [ ] JWT authentication implemented on all endpoints
- [ ] Role-based access control (RBAC) configured
- [ ] WebSocket authentication via token
- [ ] Session timeout configured (60 minutes)
- [ ] Password hashing with bcrypt
- [ ] Failed login attempt limiting

### Secrets Management
- [ ] No hardcoded credentials in code
- [ ] Private keys in secure vault (not environment variables)
- [ ] Secrets rotation procedure documented
- [ ] `.env` files never committed to git
- [ ] Development vs production secrets separated

### Network Security
- [ ] Firewall configured (UFW or cloud security groups)
- [ ] Only ports 80, 443, 22 open to internet
- [ ] Application ports (8000, 3000) blocked from internet
- [ ] All traffic over HTTPS
- [ ] TLS 1.2+ only
- [ ] HSTS enabled

### Application Security
- [ ] Rate limiting on all endpoints
- [ ] File upload validation (magic bytes)
- [ ] CORS restricted to specific origins
- [ ] CSP headers configured
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)

### Trading Security
- [ ] Daily loss limits enforced
- [ ] Position size limits enforced
- [ ] Emergency kill switch implemented
- [ ] Paper trading tested thoroughly
- [ ] Testnet trading verified
- [ ] Risk manager cannot be bypassed
- [ ] Circuit breaker functional

### Operations
- [ ] Logging configured (no sensitive data logged)
- [ ] Monitoring and alerting active
- [ ] Backup automation configured
- [ ] Restore procedure tested
- [ ] Incident response plan documented
- [ ] On-call rotation defined

### Compliance
- [ ] Terms of service accepted
- [ ] Privacy policy in place
- [ ] User data handling compliant
- [ ] Audit trail enabled
- [ ] Regulatory requirements reviewed

---

## Rollback Plan

If deployment fails:

1. **Immediate rollback:**
   ```bash
   # Stop new version
   sudo docker-compose down
   
   # Checkout previous version
   git checkout <previous-stable-tag>
   
   # Rebuild and start
   sudo docker-compose up -d
   ```

2. **Database rollback:**
   ```bash
   # Downgrade migrations
   sudo docker-compose exec backend alembic downgrade <previous-version>
   ```

3. **Verify rollback:**
   ```bash
   curl https://trading.yourdomain.com/api/health
   ```

---

## Production Checklist Summary

Before launch:

- [ ] Security fixes implemented (authentication, private key handling, etc.)
- [ ] Infrastructure provisioned and hardened
- [ ] SSL certificates installed and auto-renewal configured
- [ ] Database and Redis configured for production
- [ ] Environment variables set securely
- [ ] Services started and health checks passing
- [ ] Monitoring and alerting configured
- [ ] Backups automated and tested
- [ ] Documentation complete
- [ ] Team trained on operations
- [ ] Incident response plan ready
- [ ] Legal/compliance reviewed

**DO NOT SKIP THE SECURITY FIXES** — The application is not safe for production without addressing the critical issues outlined in the security review.

---

## Support

For deployment issues:
- Check logs: `sudo docker-compose logs -f`
- Review health endpoint: `curl https://your-domain/api/health`
- Consult operations runbook: `docs/OPERATIONS.md`
- Contact DevOps team

**Remember:** Trading with real money is risky. Start with paper trading, then testnet, then small positions before scaling up.
