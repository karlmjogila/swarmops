# Operations Manual

Day-to-day operations guide for the Hyperliquid Trading Bot Suite.

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Monitoring](#monitoring)
3. [Maintenance](#maintenance)
4. [Troubleshooting](#troubleshooting)
5. [Emergency Procedures](#emergency-procedures)
6. [Performance Tuning](#performance-tuning)

---

## Daily Operations

### Morning Routine

```bash
#!/bin/bash
# scripts/morning-check.sh

echo "🌅 Daily System Health Check - $(date)"
echo "========================================"

# 1. Check service status
echo "📊 Service Status:"
systemctl status trading-bot-backend --no-pager | head -5
systemctl status trading-bot-frontend --no-pager | head -5

# 2. Check system resources
echo -e "\n💾 System Resources:"
df -h / /var/lib/trading-bot | grep -v tmpfs
free -h | grep Mem

# 3. Check database connections
echo -e "\n🗄️  Database:"
psql -h localhost -U trading_user -d trading_bot -c "SELECT count(*) as open_positions FROM positions WHERE status='open';" -t

# 4. Check recent errors
echo -e "\n⚠️  Recent Errors (last hour):"
journalctl -u trading-bot-backend --since "1 hour ago" | grep -i error | tail -5

# 5. Check trading status
echo -e "\n💹 Trading Status:"
curl -s http://localhost:8000/api/health | jq .

# 6. Check daily P&L
echo -e "\n📈 Daily P&L:"
curl -s http://localhost:8000/api/trades/stats/daily | jq .

# 7. Check backup status
echo -e "\n💾 Last Backup:"
ls -lh /var/backups/trading-bot/*.sql.gz | tail -1

echo -e "\n✅ Morning check complete"
```

### Things to Check Daily

1. **System Health**
   - All services running
   - No critical errors in logs
   - Database connections healthy
   - Redis responsive

2. **Trading Performance**
   - Daily P&L within expected range
   - No stuck positions (open > 24h)
   - Win rate trending as expected
   - No unusual trading patterns

3. **Resource Usage**
   - Disk space > 20% free
   - Memory usage < 80%
   - CPU usage reasonable
   - Database query performance

4. **Security**
   - No failed login attempts
   - No suspicious API activity
   - SSL certificate valid (> 30 days)
   - Backup completed successfully

---

## Monitoring

### Key Metrics

**System Metrics:**
```promql
# CPU Usage
100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory Usage
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100

# Disk Usage
(node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_free_bytes{mountpoint="/"}) / node_filesystem_size_bytes{mountpoint="/"} * 100

# API Response Time (p95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error Rate
rate(http_requests_total{status=~"5.."}[5m])
```

**Trading Metrics:**
```promql
# Open Positions
trading_positions_open

# Daily P&L
trading_pnl_daily_total

# Win Rate
trading_trades_won / trading_trades_total

# Average Trade Duration
rate(trading_trade_duration_seconds_sum[1h]) / rate(trading_trade_duration_seconds_count[1h])

# Risk Utilization
trading_capital_at_risk / trading_capital_total
```

### Alert Rules

**Critical Alerts (immediate action):**

```yaml
groups:
  - name: critical
    rules:
      - alert: ServiceDown
        expr: up{job="trading-bot"} == 0
        for: 1m
        annotations:
          summary: "Trading bot is down"
          
      - alert: DailyLossLimitReached
        expr: trading_pnl_daily_percent < -0.03
        annotations:
          summary: "Daily loss limit (3%) reached"
          description: "Current daily loss: {{ $value | humanizePercentage }}"
          
      - alert: PositionStuck
        expr: trading_position_duration_minutes > 1440
        annotations:
          summary: "Position open for > 24 hours"
          description: "Position {{ $labels.symbol }} stuck"
          
      - alert: DatabaseConnectionFailed
        expr: database_connections_failed_total > 10
        for: 5m
        annotations:
          summary: "Database connection failures"
```

**Warning Alerts (review within 1 hour):**

```yaml
  - name: warnings
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      - alert: SlowAPIResponse
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 10m
        annotations:
          summary: "API response time > 2s"
          
      - alert: LowDiskSpace
        expr: (node_filesystem_free_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) < 0.2
        for: 5m
        annotations:
          summary: "Disk space < 20%"
```

### Dashboards

**Main Operations Dashboard (Grafana):**

Panels:
1. System Status (Green/Red indicators)
2. API Request Rate (Graph)
3. Error Rate (Graph)
4. Open Positions (Count)
5. Daily P&L (Bar chart)
6. Active Strategies (Table)
7. Recent Trades (Table)
8. Resource Usage (Gauges)

**Trading Performance Dashboard:**

Panels:
1. Cumulative P&L (Line chart)
2. Win Rate by Strategy (Bar chart)
3. Position Distribution (Pie chart)
4. Trade Duration Distribution (Histogram)
5. Risk Utilization (Gauge)
6. Confluence Score Distribution (Histogram)
7. Best/Worst Performers (Table)

### Log Analysis

**Useful log queries:**

```bash
# Find all trades in last hour
journalctl -u trading-bot-backend --since "1 hour ago" | grep "trade_executed"

# Find errors by frequency
journalctl -u trading-bot-backend --since "1 day ago" | grep ERROR | sort | uniq -c | sort -rn

# Find slow API calls
journalctl -u trading-bot-backend | grep "duration" | awk '$NF > 1000' | tail -20

# Find authentication failures
journalctl -u trading-bot-backend | grep "authentication_failed"

# Watch live logs
journalctl -u trading-bot-backend -f | grep -E "(ERROR|WARNING|trade_)"
```

---

## Maintenance

### Weekly Tasks

**Every Monday:**

1. **Review Performance**
   ```bash
   # Generate weekly report
   python scripts/generate_report.py --period week --output /tmp/weekly_report.html
   ```

2. **Check Disk Usage**
   ```bash
   # Clean old logs (> 30 days)
   journalctl --vacuum-time=30d
   
   # Clean old backups (> 60 days)
   find /var/backups/trading-bot -name "*.sql.gz" -mtime +60 -delete
   
   # Clean temp files
   find /var/lib/trading-bot/temp -type f -mtime +7 -delete
   ```

3. **Update Strategies**
   - Review strategy performance
   - Disable underperforming strategies
   - Adjust risk parameters if needed

4. **Review Security Logs**
   ```bash
   # Failed authentication attempts
   grep "authentication_failed" /var/log/trading-bot/security.log | wc -l
   
   # Unusual API activity
   grep "rate_limit_exceeded" /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | sort -rn
   ```

### Monthly Tasks

**First of the Month:**

1. **Dependency Updates**
   ```bash
   # Check for updates
   cd /opt/trading-bot/backend
   pip list --outdated
   
   cd /opt/trading-bot/frontend
   npm outdated
   
   # Update non-breaking changes
   # Review changelogs first!
   ```

2. **Security Scan**
   ```bash
   # Vulnerability scanning
   cd /opt/trading-bot/backend
   pip-audit
   
   cd /opt/trading-bot/frontend
   npm audit
   
   # Container scanning
   docker scan trading-bot-backend:latest
   docker scan trading-bot-frontend:latest
   ```

3. **SSL Certificate Check**
   ```bash
   # Check expiry
   echo | openssl s_client -servername trading.yourdomain.com -connect trading.yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
   
   # Renew if < 30 days
   sudo certbot renew --dry-run
   ```

4. **Database Maintenance**
   ```bash
   # Vacuum and analyze
   psql -h localhost -U trading_user -d trading_bot -c "VACUUM ANALYZE;"
   
   # Check table sizes
   psql -h localhost -U trading_user -d trading_bot -c "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC;"
   
   # Reindex if needed
   psql -h localhost -U trading_user -d trading_bot -c "REINDEX DATABASE trading_bot;"
   ```

5. **Backup Test**
   ```bash
   # Test restore on separate server
   ./scripts/test-backup-restore.sh
   ```

### Quarterly Tasks

**Every 3 Months:**

1. **Security Audit**
   - Review access controls
   - Rotate API keys and secrets
   - Review firewall rules
   - Penetration testing

2. **Performance Review**
   - Analyze trading performance
   - Review risk management effectiveness
   - Identify improvement opportunities

3. **Capacity Planning**
   - Review growth trends
   - Plan for scaling if needed
   - Optimize database queries

4. **Disaster Recovery Test**
   - Test full system restore
   - Verify backups are complete
   - Update DR documentation

---

## Troubleshooting

### Common Issues

#### Issue: Service Won't Start

**Symptoms:**
- `systemctl start trading-bot-backend` fails
- "Address already in use" error

**Diagnosis:**
```bash
# Check if port is already in use
sudo lsof -i :8000

# Check service status
systemctl status trading-bot-backend

# Check logs
journalctl -u trading-bot-backend -n 50
```

**Resolution:**
```bash
# Kill process on port
sudo kill -9 $(lsof -t -i:8000)

# Or change port in .env
PORT=8001

# Restart service
sudo systemctl restart trading-bot-backend
```

---

#### Issue: Database Connection Errors

**Symptoms:**
- "Connection refused" or "Too many connections"
- Slow API responses

**Diagnosis:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connections
psql -h localhost -U trading_user -d trading_bot -c "SELECT count(*) FROM pg_stat_activity;"

# Check for locks
psql -h localhost -U trading_user -d trading_bot -c "SELECT * FROM pg_locks WHERE granted = false;"
```

**Resolution:**
```bash
# Increase max connections (if needed)
sudo nano /etc/postgresql/15/main/postgresql.conf
# max_connections = 200

# Restart PostgreSQL
sudo systemctl restart postgresql

# Kill idle connections
psql -h localhost -U postgres -d trading_bot -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < current_timestamp - interval '10 minutes';"
```

---

#### Issue: High Memory Usage

**Symptoms:**
- System sluggish
- OOM errors in logs

**Diagnosis:**
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Check container memory
docker stats trading-bot-backend
```

**Resolution:**
```bash
# Restart service to clear memory
sudo systemctl restart trading-bot-backend

# Increase memory limit (docker-compose.yml)
services:
  backend:
    mem_limit: 8g
    mem_reservation: 4g

# Tune Python memory (if needed)
PYTHONMALLOC=malloc
MALLOC_TRIM_THRESHOLD_=100000
```

---

#### Issue: Position Stuck / Won't Close

**Symptoms:**
- Position shows "open" but should be closed
- Stop loss or take profit not triggering

**Diagnosis:**
```bash
# Check position in database
psql -h localhost -U trading_user -d trading_bot -c "SELECT * FROM positions WHERE status='open' ORDER BY created_at DESC LIMIT 5;"

# Check recent trades
curl http://localhost:8000/api/trades?limit=10 | jq .

# Check Hyperliquid position
python scripts/check_hyperliquid_position.py --symbol BTC-USD
```

**Resolution:**
```bash
# Manually close via API
curl -X POST http://localhost:8000/api/trades/positions/{position_id}/close \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "manual_close"}'

# Or via database (emergency only)
psql -h localhost -U trading_user -d trading_bot -c "UPDATE positions SET status='closed', exit_reason='manual' WHERE id='...'; "
```

---

#### Issue: Backtest Not Running

**Symptoms:**
- Backtest stuck at "running"
- No data streaming to frontend

**Diagnosis:**
```bash
# Check backtest status
curl http://localhost:8000/api/backtesting/{backtest_id}/status | jq .

# Check background tasks
ps aux | grep backtest

# Check logs for errors
journalctl -u trading-bot-backend | grep backtest | tail -50
```

**Resolution:**
```bash
# Cancel stuck backtest
curl -X DELETE http://localhost:8000/api/backtesting/{backtest_id}

# Restart backend
sudo systemctl restart trading-bot-backend

# Try again with smaller date range
```

---

### Performance Issues

#### Slow API Responses

**Diagnosis:**
```bash
# Check slow queries
psql -h localhost -U trading_user -d trading_bot -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check API metrics
curl http://localhost:8000/metrics | grep http_request_duration

# Profile with py-spy (if installed)
sudo py-spy top --pid $(pgrep -f uvicorn)
```

**Optimization:**
```sql
-- Add missing indexes
CREATE INDEX idx_trades_created_at ON trades(created_at DESC);
CREATE INDEX idx_positions_status ON positions(status) WHERE status = 'open';

-- Analyze query plans
EXPLAIN ANALYZE SELECT * FROM trades WHERE created_at > NOW() - INTERVAL '1 day';
```

---

### Recovery Procedures

#### Full System Restore

```bash
#!/bin/bash
# scripts/restore-system.sh

set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file.sql.gz>"
    exit 1
fi

echo "🔄 Starting system restore from $BACKUP_FILE"

# 1. Stop services
echo "Stopping services..."
sudo systemctl stop trading-bot-backend
sudo systemctl stop trading-bot-frontend

# 2. Drop and recreate database
echo "Restoring database..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U postgres -c "DROP DATABASE IF EXISTS trading_bot;"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U postgres -c "CREATE DATABASE trading_bot;"

# 3. Restore data
gunzip -c $BACKUP_FILE | PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U trading_user -d trading_bot

# 4. Run migrations (if needed)
cd /opt/trading-bot/backend
alembic upgrade head

# 5. Restart services
echo "Starting services..."
sudo systemctl start trading-bot-backend
sudo systemctl start trading-bot-frontend

# 6. Verify
sleep 5
curl http://localhost:8000/api/health

echo "✅ Restore complete"
```

---

## Emergency Procedures

### Emergency Shutdown

**When to use:**
- Suspected security breach
- Uncontrolled losses
- System malfunction causing bad trades

**Procedure:**
```bash
# 1. Trip circuit breaker (halts new trades)
curl -X POST http://localhost:8000/api/emergency/circuit-breaker \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 2. Cancel all open orders
curl -X POST http://localhost:8000/api/trades/orders/cancel-all \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 3. Close all positions (if needed)
curl -X POST http://localhost:8000/api/trades/positions/close-all \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"reason": "emergency_shutdown"}'

# 4. Stop services
sudo systemctl stop trading-bot-backend

# 5. Investigate issue
journalctl -u trading-bot-backend --since "1 hour ago" | less

# 6. After fix, reset circuit breaker
curl -X POST http://localhost:8000/api/emergency/circuit-breaker/reset \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Rollback Deployment

```bash
# 1. Stop current version
cd /opt/trading-bot
sudo systemctl stop trading-bot-backend

# 2. Checkout previous version
git log --oneline | head -5  # Find previous commit
git checkout <previous-commit>

# 3. Rollback database migrations
cd backend
alembic downgrade -1

# 4. Rebuild and restart
docker-compose build backend
sudo systemctl start trading-bot-backend

# 5. Verify
curl http://localhost:8000/api/health
```

---

## Performance Tuning

### Database Optimization

```sql
-- Optimize PostgreSQL for trading workload
-- /etc/postgresql/15/main/postgresql.conf

-- Memory
shared_buffers = 4GB              -- 25% of RAM
effective_cache_size = 12GB       -- 75% of RAM
work_mem = 64MB
maintenance_work_mem = 1GB

-- Connections
max_connections = 200
max_prepared_transactions = 200

-- Write performance
wal_buffers = 16MB
checkpoint_completion_target = 0.9
checkpoint_timeout = 15min
max_wal_size = 2GB

-- Query performance
random_page_cost = 1.1  -- SSD
effective_io_concurrency = 200

-- Restart after changes
sudo systemctl restart postgresql
```

### Redis Optimization

```bash
# /etc/redis/redis.conf

# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence (balance durability vs performance)
save 900 1      # Save if 1 key changed in 15 min
save 300 10     # Save if 10 keys changed in 5 min
save 60 10000   # Save if 10k keys changed in 1 min

# Performance
tcp-backlog 511
timeout 300
tcp-keepalive 60

# Restart
sudo systemctl restart redis
```

### Application Tuning

```python
# backend/src/config.py

# Database connection pool
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 40
DATABASE_POOL_RECYCLE = 3600
DATABASE_POOL_PRE_PING = True

# Redis connection pool
REDIS_MAX_CONNECTIONS = 50
REDIS_SOCKET_KEEPALIVE = True
REDIS_SOCKET_TIMEOUT = 5

# API workers
UVICORN_WORKERS = 4  # CPU cores
UVICORN_WORKER_CLASS = "uvicorn.workers.UvicornWorker"

# Background task concurrency
MAX_CONCURRENT_BACKTESTS = 2
MAX_CONCURRENT_INGESTIONS = 3
```

---

## Useful Scripts

### Check System Health

```bash
#!/bin/bash
# scripts/health-check.sh

check_service() {
    if systemctl is-active --quiet $1; then
        echo "✅ $1 is running"
        return 0
    else
        echo "❌ $1 is not running"
        return 1
    fi
}

check_port() {
    if nc -z localhost $1; then
        echo "✅ Port $1 is open"
        return 0
    else
        echo "❌ Port $1 is not accessible"
        return 1
    fi
}

check_disk() {
    usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $usage -lt 80 ]; then
        echo "✅ Disk usage: ${usage}%"
        return 0
    else
        echo "⚠️  Disk usage: ${usage}% (high!)"
        return 1
    fi
}

echo "System Health Check"
echo "==================="

check_service "trading-bot-backend"
check_service "trading-bot-frontend"
check_service "postgresql"
check_service "redis"
check_port 8000
check_port 3000
check_port 5432
check_port 6379
check_disk

# API health
response=$(curl -s http://localhost:8000/api/health)
if echo $response | jq -e '.status == "healthy"' > /dev/null; then
    echo "✅ API is healthy"
else
    echo "❌ API is unhealthy: $response"
fi
```

### Generate Performance Report

```python
# scripts/generate_report.py
#!/usr/bin/env python3
"""Generate trading performance report."""

import sys
import asyncio
from datetime import datetime, timedelta
from src.database.models import async_session
from src.backtest.statistics import calculate_statistics

async def generate_report(period_days=7):
    """Generate performance report for last N days."""
    start_date = datetime.now() - timedelta(days=period_days)
    
    async with async_session() as session:
        # Get trades
        trades = await session.execute(
            "SELECT * FROM trades WHERE created_at > $1",
            start_date
        )
        trades = trades.fetchall()
        
        # Calculate stats
        stats = calculate_statistics(trades)
        
        # Print report
        print(f"Performance Report ({period_days} days)")
        print("=" * 50)
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Win Rate: {stats['win_rate']:.2%}")
        print(f"Profit Factor: {stats['profit_factor']:.2f}")
        print(f"Total P&L: ${stats['total_pnl']:.2f}")
        print(f"Average Trade: ${stats['avg_trade_pnl']:.2f}")
        print(f"Best Trade: ${stats['best_trade']:.2f}")
        print(f"Worst Trade: ${stats['worst_trade']:.2f}")
        print(f"Max Drawdown: {stats['max_drawdown']:.2%}")

if __name__ == "__main__":
    period = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    asyncio.run(generate_report(period))
```

---

## Contact & Escalation

**On-Call Rotation:**
- Week 1: [Engineer A]
- Week 2: [Engineer B]  
- Week 3: [Engineer C]

**Escalation Path:**
1. On-call engineer (respond < 1 hour for P0)
2. Team lead (if no response in 1 hour)
3. Engineering manager (critical issues only)

**Emergency Contacts:**
- On-Call Phone: [Number]
- Team Slack: #trading-bot-alerts
- Email: ops@yourdomain.com

**External Services:**
- Hosting Provider: [Support URL]
- Database Provider: [Support URL]
- CDN/Security: [Support URL]

---

**Remember:** When in doubt, err on the side of caution. Emergency shutdown is always available if something seems wrong.
