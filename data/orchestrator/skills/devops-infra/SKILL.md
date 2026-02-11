---
name: devops-infra
description: >
  Configure and manage deployment infrastructure including Docker, CI/CD pipelines,
  systemd services, nginx/reverse proxies, environment management, and production
  operations. Trigger this skill for any task involving deployment, containerization,
  server configuration, process management, or infrastructure setup.
triggers:
  - docker
  - dockerfile
  - compose
  - ci
  - cd
  - pipeline
  - deploy
  - deployment
  - systemd
  - nginx
  - reverse proxy
  - ssl
  - tls
  - certificate
  - infrastructure
  - server
  - production
  - staging
---

# DevOps & Infrastructure

Infrastructure is code. Treat it with the same rigor as application code: version it, review it, test it, and automate it. Manual steps are bugs waiting to happen.

## Core Principles

1. **Reproducibility** — Every environment can be rebuilt from scratch using code and configuration alone.
2. **Immutability** — Don't patch running systems. Build new, swap, tear down old.
3. **Observability** — If you can't see it, you can't fix it. Logs, metrics, health checks everywhere.

## Docker

### Dockerfile Best Practices
```dockerfile
# Use specific version tags, never :latest
FROM node:20-alpine AS base

# Set working directory
WORKDIR /app

# Copy dependency files first (cache layer)
COPY package.json pnpm-lock.yaml ./

# Install dependencies (cached unless lockfile changes)
RUN corepack enable && pnpm install --frozen-lockfile --prod

# Copy source code (changes frequently — separate layer)
COPY . .

# Build
FROM base AS build
RUN pnpm install --frozen-lockfile
RUN pnpm build

# Production image — minimal
FROM node:20-alpine AS production
WORKDIR /app

# Non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup
USER appuser

# Copy only what's needed
COPY --from=build --chown=appuser:appgroup /app/.output ./.output
COPY --from=build --chown=appuser:appgroup /app/package.json ./

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:3000/api/health || exit 1

EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
```

### Docker Compose
```yaml
# docker-compose.yml
services:
  app:
    build:
      context: .
      target: production
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - PORT=3000
    env_file:
      - .env.production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    volumes:
      - app-data:/app/data
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  app-data:
```

### Docker Rules
```
- One process per container
- Use .dockerignore (exclude node_modules, .git, .env, etc.)
- Multi-stage builds to minimize image size
- Pin base image versions (node:20.11-alpine, not node:latest)
- Non-root user in production images
- HEALTHCHECK in every service
- Never store secrets in images (use env vars or secret managers)
```

## Systemd Services

### Service File
```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=appuser
Group=appgroup
WorkingDirectory=/opt/myapp

# Environment
EnvironmentFile=/opt/myapp/.env
Environment=NODE_ENV=production
Environment=PORT=3000

# Process management
ExecStart=/usr/bin/node .output/server/index.mjs
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/myapp/data /tmp/myapp
PrivateTmp=yes

# Resource limits
MemoryMax=512M
CPUQuota=80%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=myapp

[Install]
WantedBy=multi-user.target
```

### Systemd Operations
```bash
# Reload after editing service file
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable myapp

# Start/stop/restart
sudo systemctl start myapp
sudo systemctl stop myapp
sudo systemctl restart myapp

# Check status and logs
sudo systemctl status myapp
journalctl -u myapp -f              # Follow logs
journalctl -u myapp --since "1h ago"  # Recent logs
journalctl -u myapp -n 100          # Last 100 lines
```

## Nginx Reverse Proxy

### Configuration
```nginx
# /etc/nginx/sites-available/myapp
upstream app_backend {
    server 127.0.0.1:3000;
    keepalive 32;
}

server {
    listen 80;
    server_name myapp.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name myapp.example.com;

    # SSL (managed by certbot or manual)
    ssl_certificate /etc/letsencrypt/live/myapp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myapp.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy settings
    location / {
        proxy_pass http://app_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support
    location /_ws {
        proxy_pass http://app_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;  # Keep WS alive
    }

    # Static assets with cache
    location /_nuxt/ {
        proxy_pass http://app_backend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Request limits
    client_max_body_size 10M;
}
```

## Environment Management

### .env File Structure
```bash
# .env.production — NEVER commit this file
# Application
NODE_ENV=production
PORT=3000

# Paths
PROJECTS_DIR=/opt/myapp/data/projects
ORCHESTRATOR_DATA_DIR=/opt/myapp/data/orchestrator

# External services
OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789
OPENCLAW_GATEWAY_TOKEN=your-secret-token-here

# Optional
SWARMOPS_API_TOKEN=dashboard-auth-token
LOG_LEVEL=info
```

### Environment Rules
```
- .env files NEVER committed to git (add to .gitignore)
- Use .env.example as a template (no real values)
- Different .env per environment (dev, staging, production)
- Validate all required env vars at startup
- Don't use env vars for complex configuration (use config files)
- Rotate secrets regularly
```

## CI/CD Pipeline

### GitHub Actions Example
```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm test
      - run: pnpm lint

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm build
      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: .output/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/myapp
            git pull origin main
            pnpm install --frozen-lockfile
            pnpm build
            sudo systemctl restart myapp
```

## Health Checks & Monitoring

### Health Endpoint
```typescript
// server/api/health.get.ts
export default defineEventHandler(async () => {
  const checks = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
  }

  // Check critical dependencies
  try {
    await readFile(join(projectsDir, '.health'), 'utf-8').catch(() => 'ok')
    checks.filesystem = 'ok'
  } catch {
    checks.filesystem = 'error'
    checks.status = 'degraded'
  }

  return checks
})
```

### Log Format
```typescript
// Structured logging for production
function log(level: string, message: string, meta?: Record<string, any>) {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    level,
    message,
    ...meta,
  }))
}

// Usage
log('info', 'Project created', { projectName: 'my-app', phase: 'interview' })
log('error', 'Spawn failed', { error: err.message, sessionKey, retryCount: 3 })
```

## Quality Checklist

- [ ] Service runs as non-root user
- [ ] Health check endpoint exists and is monitored
- [ ] Logs are structured (JSON) and rotated
- [ ] Secrets in environment variables, not in code or images
- [ ] Automatic restart on crash (systemd Restart=always)
- [ ] SSL/TLS configured with modern protocols
- [ ] Reverse proxy handles SSL termination and WebSocket upgrade
- [ ] Static assets served with cache headers
- [ ] Resource limits set (memory, CPU)
- [ ] Deployment is automated (no manual SSH steps in production)
- [ ] .env.example documents all required variables
- [ ] Backup strategy for persistent data

## Anti-Patterns

- Running as root in production
- Hardcoded secrets in Dockerfiles or service files
- No health checks — you find out the service is down when users complain
- Manual deployments via SSH ("just run these 5 commands")
- Using `latest` tags for base images
- Storing state in the container filesystem (use volumes or external storage)
- No log rotation — disk fills up, service crashes
- Exposing internal ports directly (no reverse proxy)
- No restart policy — crash once and it stays down
- Copying entire codebase into Docker image (no .dockerignore)
