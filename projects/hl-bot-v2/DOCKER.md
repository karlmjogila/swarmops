# Docker Guide - HL Bot v2

Complete Docker setup and usage guide for the HL Bot v2 trading system.

---

## 📦 What's Included

The Docker setup provides a complete, production-ready stack:

- **PostgreSQL + TimescaleDB** - Time-series optimized database
- **Redis** - Caching and Celery message broker
- **FastAPI Backend** - Python trading engine
- **Celery Workers** - Background task processing
- **Celery Beat** - Scheduled tasks
- **SvelteKit Frontend** - Web UI
- **Nginx** - Reverse proxy (production only)

---

## 🚀 Quick Start

### Option 1: Using the Start Script (Recommended)

```bash
# Development mode
./docker-start.sh dev

# Production mode
./docker-start.sh prod
```

### Option 2: Using Make

```bash
# Development
make dev

# Production
make prod

# View all commands
make help
```

### Option 3: Docker Compose Directly

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🏗️ Architecture

### Development Stack

```
┌─────────────────────────────────────────┐
│  Host Machine                            │
│  ┌─────────────────────────────────┐    │
│  │  Docker Network: hlbot-network  │    │
│  │                                 │    │
│  │  ┌──────────┐  ┌─────────────┐ │    │
│  │  │Frontend  │  │   Backend   │ │    │
│  │  │:3000     │  │   :8000     │ │    │
│  │  └──────────┘  └─────────────┘ │    │
│  │       │              │          │    │
│  │  ┌────┴──────────────┴────┐    │    │
│  │  │  PostgreSQL + Redis    │    │    │
│  │  │  :5432        :6379    │    │    │
│  │  └────────────────────────┘    │    │
│  │                                 │    │
│  │  ┌──────────┐  ┌─────────────┐ │    │
│  │  │ Celery   │  │ Celery Beat │ │    │
│  │  │ Worker   │  │             │ │    │
│  │  └──────────┘  └─────────────┘ │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### Production Stack

```
┌─────────────────────────────────────────┐
│  Host Machine                            │
│  ┌─────────────────────────────────┐    │
│  │  Docker Network: hlbot-network  │    │
│  │                                 │    │
│  │  ┌──────────────────────────┐   │    │
│  │  │  Nginx Reverse Proxy     │   │    │
│  │  │  :80 :443                │   │    │
│  │  └────────┬────────────┬────┘   │    │
│  │           │            │         │    │
│  │  ┌────────▼──┐   ┌────▼──────┐  │    │
│  │  │Frontend   │   │Backend    │  │    │
│  │  │           │   │           │  │    │
│  │  └───────────┘   └───────────┘  │    │
│  │                       │          │    │
│  │  ┌────────────────────┴────┐    │    │
│  │  │PostgreSQL + Redis       │    │    │
│  │  └─────────────────────────┘    │    │
│  │                                 │    │
│  │  ┌────────┐  ┌────────────────┐│    │
│  │  │Celery  │  │  Celery Beat   ││    │
│  │  │Worker  │  │                ││    │
│  │  └────────┘  └────────────────┘│    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

---

## 🔧 Configuration

### Environment Files

- `.env` - Development configuration
- `.env.production` - Production configuration
- `.env.example` - Template with all options

### Docker Compose Files

- `docker-compose.yml` - Development setup
- `docker-compose.prod.yml` - Production setup
- `docker-compose.override.yml` - Local customizations (optional)

### Creating Local Overrides

```bash
cp docker-compose.override.yml.example docker-compose.override.yml
# Edit docker-compose.override.yml for local customizations
```

---

## 📝 Common Commands

### Development

```bash
# Start services
make dev
# or
docker-compose up -d

# View logs
make dev-logs
# or
docker-compose logs -f

# Stop services
make dev-down
# or
docker-compose down

# Rebuild and restart
make dev-build
# or
docker-compose up -d --build
```

### Production

```bash
# Start services
make prod
# or
docker-compose -f docker-compose.prod.yml up -d

# View logs
make prod-logs
# or
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
make prod-down
# or
docker-compose -f docker-compose.prod.yml down
```

### Database

```bash
# Run migrations
make migrate-dev        # Development
make migrate            # Production

# Create new migration
make migrate-new
# Enter migration name when prompted

# Database backup
make backup

# Database restore
make restore BACKUP_FILE=backups/hlbot_20250211.sql
```

### Maintenance

```bash
# Restart all services
make restart

# Show container status
make ps
# or
docker-compose ps

# View resource usage
docker stats

# Shell into backend container
make shell-backend
# or
docker-compose exec backend /bin/bash

# Shell into database
make shell-db
# or
docker-compose exec postgres psql -U hlbot -d hlbot
```

---

## 🔍 Debugging

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail 100 backend

# Follow new logs only
docker-compose logs -f --tail 0
```

### Inspect Container

```bash
# Container details
docker inspect hlbot-backend

# Resource usage
docker stats hlbot-backend

# Running processes
docker top hlbot-backend
```

### Network Debugging

```bash
# List networks
docker network ls

# Inspect network
docker network inspect hlbot-network

# Test connectivity between containers
docker-compose exec backend ping postgres
docker-compose exec backend curl redis:6379
```

### Volume Inspection

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect hlbot_postgres_data

# Check volume size
docker system df -v
```

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find what's using the port
sudo lsof -i :3000
sudo lsof -i :8000

# Kill the process or change port in docker-compose.yml
```

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Validate compose file
docker-compose config

# Check Docker daemon
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker
```

### Database Connection Failed

```bash
# Check postgres is running
docker-compose ps postgres

# Check postgres logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U hlbot -d hlbot -c "SELECT 1;"

# Verify DATABASE_URL in .env matches postgres credentials
```

### Out of Disk Space

```bash
# Check disk usage
docker system df

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Full cleanup (BE CAREFUL!)
docker system prune -a --volumes
```

### Permission Issues

```bash
# Fix volume permissions
docker-compose exec backend chown -R appuser:appuser /app/data
docker-compose exec backend chown -R appuser:appuser /app/logs
```

---

## 🔐 Security Best Practices

### Development
- ✅ Use `.env` file (never commit it!)
- ✅ Use weak passwords (they're local only)
- ✅ Expose ports to localhost

### Production
- ✅ Use `.env.production` with strong passwords
- ✅ Generate secure secrets: `openssl rand -hex 32`
- ✅ Use SSL/TLS certificates
- ✅ Don't expose database ports
- ✅ Enable firewall (only 80, 443, 22)
- ✅ Regular backups
- ✅ Non-root users (already configured)
- ✅ Resource limits (already configured)
- ✅ Log rotation (already configured)

---

## 📊 Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Check all service health
docker-compose ps

# Detailed health status
make health
```

### Resource Usage

```bash
# Live stats
docker stats

# Container status
make status

# Disk usage
docker system df -v
```

---

## 🚨 Emergency Procedures

### Complete Reset

```bash
# Stop everything
docker-compose down -v

# Remove all hl-bot images
docker images | grep hlbot | awk '{print $3}' | xargs docker rmi

# Clean Docker system
docker system prune -a --volumes

# Start fresh
./docker-start.sh dev
```

### Rollback

```bash
# Stop current version
docker-compose down

# Restore database backup
make restore BACKUP_FILE=backups/hlbot_20250210.sql

# Deploy previous version
git checkout <previous-commit>
docker-compose up -d --build
```

---

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL in Docker](https://hub.docker.com/_/postgres)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/docker/)

---

**Last Updated:** 2025-02-11  
**Version:** 1.0.0
