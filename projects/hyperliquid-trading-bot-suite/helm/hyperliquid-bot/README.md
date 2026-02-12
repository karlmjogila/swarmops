# Hyperliquid Trading Bot Helm Chart

A production-ready Helm chart for deploying the Hyperliquid Trading Bot Suite on Kubernetes.

## Overview

This chart deploys:
- **Backend API** - FastAPI-based trading backend with AI integration
- **Frontend Dashboard** - Nuxt.js-based web interface
- **PostgreSQL** - Database with pgvector support (optional, via Bitnami)
- **Redis** - Caching and pub/sub (optional, via Bitnami)

## Prerequisites

- Kubernetes 1.23+
- Helm 3.0+
- PV provisioner (if persistence enabled)
- Ingress controller (nginx recommended)

## Quick Start

```bash
# Update dependencies
helm dependency update

# Install
helm install hyperliquid-bot . -n trading-bot --create-namespace

# Install with custom values
helm install hyperliquid-bot . -n trading-bot -f my-values.yaml
```

## Configuration

See `values.yaml` for all configurable parameters.

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `backend.enabled` | Enable backend | `true` |
| `backend.replicaCount` | Replicas | `2` |
| `backend.autoscaling.enabled` | Enable HPA | `true` |
| `frontend.enabled` | Enable frontend | `true` |
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.host` | Hostname | `trading.example.com` |
| `postgresql.enabled` | Deploy PostgreSQL | `true` |
| `redis.enabled` | Deploy Redis | `true` |

## Security

For production, use external secrets:
- External Secrets Operator
- Sealed Secrets
- helm-secrets plugin

## Running Tests

```bash
# Install helm-unittest
helm plugin install https://github.com/helm-unittest/helm-unittest.git

# Run tests
helm unittest .

# Lint chart
helm lint .

# Template rendering
helm template test . --debug
```

## License

MIT
