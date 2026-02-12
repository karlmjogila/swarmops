"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test the root endpoint."""
    response = await client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "HL Bot API"
    assert data["version"] == "0.1.0"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_docs_available(client: AsyncClient):
    """Test that API docs endpoint is available."""
    response = await client.get("/docs")
    
    # OpenAPI docs should redirect or return HTML
    assert response.status_code in (200, 307)
