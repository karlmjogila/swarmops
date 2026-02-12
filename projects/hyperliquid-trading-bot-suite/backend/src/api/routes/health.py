"""Health check endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends
import structlog

from ...config import settings, get_settings

router = APIRouter()
logger = structlog.get_logger()


@router.get("/health", summary="Health check")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production"
    }


@router.get("/health/ready", summary="Readiness check")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check - validates all dependencies are available."""
    checks = {
        "database": "unknown",
        "redis": "unknown",
        "anthropic": "configured" if settings.anthropic_api_key else "not_configured",
        "hyperliquid": "configured" if settings.hyperliquid_private_key else "not_configured"
    }
    
    # TODO: Add actual database and redis connectivity checks
    # try:
    #     await check_database_connection()
    #     checks["database"] = "healthy"
    # except Exception as e:
    #     logger.error("Database health check failed", error=str(e))
    #     checks["database"] = "unhealthy"
    
    # try:
    #     await check_redis_connection()
    #     checks["redis"] = "healthy"
    # except Exception as e:
    #     logger.error("Redis health check failed", error=str(e))
    #     checks["redis"] = "unhealthy"
    
    overall_status = "healthy" if all(
        status in ["healthy", "configured"] for status in checks.values()
    ) else "degraded"
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": "2025-02-10T12:00:00Z"  # TODO: Use actual timestamp
    }