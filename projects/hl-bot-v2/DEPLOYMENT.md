# Deployment Guide - HL Bot v2

Complete guide for deploying the HL Bot v2 trading system to production.

---

## 🎯 Prerequisites

- Docker Engine 20.10+ and Docker Compose v2.0+
- 4GB+ RAM, 20GB+ disk space
- Domain name (for production with SSL)
- Anthropic API key

---

## 🚀 Quick Start (Development)

```bash
# 1. Clone and navigate to project
cd /opt/swarmops/projects/hl-bot-v2

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env and add your API keys
nano .env  # or vim, code, etc.

# 4. Start all services
docker-compose up -d

# 5. Check logs
docker-compose logs -f

# 6. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## 🏭 Production Deployment

### Step 1: Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Add user to docker group (logout/login after)
sudo usermod -aG docker $USER

# Create project directory
sudo mkdir -p /opt/hlbot
sudo chown $USER:$USER /opt/hlbot
cd /opt/hlbot

# Clone or copy project files
# git clone <your-repo> .
```

### Step 2: Configure Environment

```bash
# Create production environment file
cp .env.production .env.production

# Edit with secure values
nano .env.production
```

**Required changes:**
- `POSTGRES_PASSWORD` → Strong random password
- `SECRET_KEY` → Generate: `openssl rand -hex 32`
- `JWT_SECRET` → Generate: `openssl rand -hex 32`
- `ANTHROPIC_API_KEY` → Your API key from console.anthropic.com
- `ALLOWED_HOSTS` → Your domain name
- `PUBLIC_API_URL` → https://yourdomain.com/api
- `PUBLIC_WS_URL` → wss://yourdomain.com/ws
- `CORS_ORIGINS` → https://yourdomain.com

### Step 3: SSL Certificates (Optional but Recommended)

#### Option A: Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt install certbot -y

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates to project
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/
sudo chown -R $USER:$USER nginx/ssl
```

#### Option B: Self-Signed (Development/Testing Only)

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem \
  -subj "/CN=localhost"
```

### Step 4: Configure Nginx for SSL

Edit `nginx/conf.d/default.conf`:

```bash
nano nginx/conf.d/default.conf
```

Uncomment the HTTPS server block and update `server_name` to your domain.

### Step 5: Build and Deploy

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Step 6: Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Verify database
docker-compose -f docker-compose.prod.yml exec postgres psql -U hlbot -d hlbot -c "\dt"
```

### Step 7: Health Check

```bash
# Check backend health
curl http://localhost:8000/health

# Check nginx
curl http://localhost/health

# Check all services
docker-compose -f docker-compose.prod.yml ps
```

---

## 📊 Monitoring & Logs

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail 100 backend
```

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Volume usage
docker volume ls
```

### Database Backup

```bash
# Create backup directory
mkdir -p backups

# Manual backup
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U hlbot hlbot > backups/hlbot_$(date +%Y%m%d_%H%M%S).sql

# Automated daily backups (add to crontab)
0 2 * * * cd /opt/hlbot && docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U hlbot hlbot > backups/hlbot_$(date +\%Y\%m\%d).sql
```

### Restore Database

```bash
# Stop services
docker-compose -f docker-compose.prod.yml stop backend celery-worker

# Restore backup
cat backups/hlbot_20250211.sql | \
  docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U hlbot hlbot

# Start services
docker-compose -f docker-compose.prod.yml start backend celery-worker
```

---

## 🔧 Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker-compose -f docker-compose.prod.yml build

# Restart services (zero-downtime with proper load balancer)
docker-compose -f docker-compose.prod.yml up -d

# Run migrations if needed
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Restart Services

```bash
# All services
docker-compose -f docker-compose.prod.yml restart

# Specific service
docker-compose -f docker-compose.prod.yml restart backend
```

### Stop/Start

```bash
# Stop all
docker-compose -f docker-compose.prod.yml down

# Start all
docker-compose -f docker-compose.prod.yml up -d

# Stop and remove volumes (WARNING: deletes data!)
docker-compose -f docker-compose.prod.yml down -v
```

### Clean Up

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Full cleanup (careful!)
docker system prune -a --volumes
```

---

## 🔐 Security Checklist

- [ ] Changed all default passwords in `.env.production`
- [ ] Generated secure `SECRET_KEY` and `JWT_SECRET`
- [ ] SSL/TLS certificates configured
- [ ] Firewall configured (only ports 80, 443, 22 open)
- [ ] `HYPERLIQUID_MAINNET=false` until thoroughly tested
- [ ] Regular database backups scheduled
- [ ] `.env.production` not committed to git
- [ ] `ALLOWED_HOSTS` set to your domain only
- [ ] Non-root users in all containers (already configured)
- [ ] Rate limiting enabled in nginx (already configured)
- [ ] Log rotation configured (already configured)

---

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs

# Check individual service
docker-compose -f docker-compose.prod.yml logs backend

# Validate compose file
docker-compose -f docker-compose.prod.yml config
```

### Database Connection Issues

```bash
# Check postgres is healthy
docker-compose -f docker-compose.prod.yml ps postgres

# Test connection
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U hlbot -d hlbot -c "SELECT 1;"

# Check environment variables
docker-compose -f docker-compose.prod.yml exec backend env | grep DATABASE
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase resource limits in docker-compose.prod.yml
# Or upgrade server resources
```

### Port Conflicts

```bash
# Check what's using port 80
sudo lsof -i :80

# Change port in docker-compose.prod.yml if needed
```

---

## 📈 Performance Tuning

### PostgreSQL

Already optimized in `docker-compose.prod.yml`:
- Increased shared_buffers and effective_cache_size
- Tuned checkpoint and WAL settings
- For larger deployments, increase these further

### Backend

```yaml
# In docker-compose.prod.yml, adjust workers:
command: >
  uvicorn app.main:app
  --host 0.0.0.0
  --port 8000
  --workers 8  # Increase for more CPU cores
  --loop uvloop
```

### Celery

```yaml
# Increase concurrency for more background tasks:
command: >
  celery -A app.workers.tasks worker
  --concurrency=8  # Increase based on workload
```

---

## 🌐 Domain & DNS Setup

1. Point your domain A record to your server IP
2. Wait for DNS propagation (can take up to 48h)
3. Obtain SSL certificate (see Step 3 above)
4. Update nginx configuration with your domain
5. Test: `curl https://yourdomain.com/health`

---

## 📞 Support

- Check logs first: `docker-compose logs -f`
- Review this guide thoroughly
- Check GitHub issues
- Ensure all API keys are valid
- Verify network connectivity

---

**Last Updated:** 2025-02-11  
**Version:** 1.0.0
