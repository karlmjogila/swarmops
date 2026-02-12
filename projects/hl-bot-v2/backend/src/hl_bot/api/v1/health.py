"""Health check endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hl_bot.config import Settings
from hl_bot.dependencies import get_settings_cached

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: datetime
    version: str
    environment: str


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings_cached),
) -> HealthResponse:
    """
    Health check endpoint.
    
    Returns the current status of the application.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC),
        version="0.1.0",
        environment="development" if settings.debug else "production",
    )


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """
    Readiness check endpoint.
    
    Returns whether the application is ready to serve requests.
    """
    # TODO: Add checks for database connectivity, external services, etc.
    return {"status": "ready"}
