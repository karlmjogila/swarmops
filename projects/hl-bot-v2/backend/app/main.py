"""FastAPI application for hl-bot backend."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import data, backtest, sync
from app.config import settings


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API key for /api/ routes."""
    
    # Routes that don't require auth
    EXEMPT_PATHS = {"/", "/health", "/health/db", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next):
        from starlette.responses import JSONResponse
        
        path = request.url.path
        
        # Skip auth for exempt paths
        if path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip auth in development if no API key configured
        api_key = settings.api_key.get_secret_value()
        if not api_key:
            if settings.is_development:
                return await call_next(request)
            else:
                # Production requires API key to be set
                return JSONResponse(
                    status_code=500,
                    content={"detail": "API key not configured"}
                )
        
        # Validate API key for all other routes
        request_api_key = request.headers.get("X-API-Key")
        if not request_api_key or request_api_key != api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"}
            )
        
        return await call_next(request)


# Create FastAPI app
app = FastAPI(
    title="HL Bot API",
    description="AI-Powered Trading Research & Execution System",
    version="0.1.0",
)

# CORS middleware - configured via env var CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# API Key authentication middleware
app.add_middleware(APIKeyAuthMiddleware)

# Include routers
app.include_router(data.router)
app.include_router(backtest.router)
app.include_router(sync.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "HL Bot API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/health/db")
async def health_db():
    """Database health check endpoint."""
    from sqlalchemy import text
    from app.db.session import SessionLocal
    
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
