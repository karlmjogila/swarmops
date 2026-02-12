"""FastAPI main application for Hyperliquid Trading Bot Suite."""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

from ..config import settings
from .routes import health, ingestion, strategies, backtesting, trades, websocket
from .routes import auth
from .security.rate_limiter import RateLimitMiddleware, get_rate_limiter

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def get_cors_origins() -> List[str]:
    """
    Get allowed CORS origins based on environment.
    
    In production, this should be strictly limited to known frontend domains.
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        # In production, only allow specific origins
        origins = os.getenv("CORS_ORIGINS", "").split(",")
        origins = [o.strip() for o in origins if o.strip()]
        
        if not origins:
            logger.warning(
                "No CORS_ORIGINS configured in production! "
                "Set CORS_ORIGINS environment variable."
            )
            # Default to no origins in production if not configured
            return []
        
        return origins
    else:
        # In development, allow localhost variations
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Hyperliquid Trading Bot Suite", version=settings.app_version)
    
    # Validate configuration
    try:
        # This will raise an error if SECRET_KEY is not properly configured
        _ = settings.validated_secret_key
        logger.info("Security configuration validated")
    except ValueError as e:
        logger.error(f"Security configuration error: {e}")
        raise
    
    # Initialize rate limiter
    try:
        rate_limiter = await get_rate_limiter()
        logger.info("Rate limiter initialized")
    except Exception as e:
        logger.warning(f"Rate limiter initialization warning: {e}")
    
    # Initialize database connection
    # await init_db()
    
    # Initialize Redis connection
    # await init_redis()
    
    # Initialize background tasks
    # await start_background_tasks()
    
    logger.info("Application startup complete")
    
    yield
    
    logger.info("Application shutdown initiated")
    
    # Cleanup rate limiter
    try:
        rate_limiter = await get_rate_limiter()
        await rate_limiter.disconnect()
    except Exception:
        pass
    
    # Cleanup resources
    # await cleanup_db()
    # await cleanup_redis()
    # await stop_background_tasks()
    
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered trading system that learns strategies from educational content",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        openapi_url="/api/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # Get allowed origins
    allowed_origins = get_cors_origins()
    
    # Add CORS middleware with proper configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        # In production, limit to necessary methods
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        # In production, limit to necessary headers
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
        ],
        # Expose rate limit headers
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ],
        max_age=600,  # Cache preflight for 10 minutes
    )
    
    # Add GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add global rate limiting middleware
    # This applies a base rate limit to all requests
    app.add_middleware(
        RateLimitMiddleware,
        global_limit=1000,  # 1000 requests per minute globally per IP
        window_seconds=60,
        exclude_paths=["/health", "/api/health", "/docs", "/openapi.json", "/redoc"]
    )

    # Add rate limit headers middleware
    @app.middleware("http")
    async def add_rate_limit_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Add rate limit headers if they were set by the rate limiter
        if hasattr(request.state, "rate_limit_remaining"):
            response.headers["X-RateLimit-Limit"] = str(
                getattr(request.state, "rate_limit_limit", 0)
            )
            response.headers["X-RateLimit-Remaining"] = str(
                request.state.rate_limit_remaining
            )
            response.headers["X-RateLimit-Reset"] = str(
                getattr(request.state, "rate_limit_reset", 0)
            )
        
        return response

    # Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Only add HSTS in production with HTTPS
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        
        # Content Security Policy - adjust as needed
        if not settings.debug:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' wss: https:; "
                "frame-ancestors 'none';"
            )
        
        return response

    # Add exception handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc):
        logger.error(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            url=str(request.url),
            method=request.method,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        logger.error(
            "Validation error",
            errors=exc.errors(),
            url=str(request.url),
            method=request.method,
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "details": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(
            "Unhandled exception",
            exc_info=True,  # Captures full stack trace correctly
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            url=str(request.url),
            method=request.method,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )

    # Include routers
    # Public routes (no auth required)
    app.include_router(health.router, prefix="/api", tags=["health"])
    
    # Authentication routes
    app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
    
    # Protected routes (auth required - enforced at route level)
    app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
    app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
    app.include_router(backtesting.router, prefix="/api/backtesting", tags=["backtesting"])
    app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
    
    # WebSocket routes (auth handled within routes)
    app.include_router(websocket.router, prefix="/api/ws", tags=["websocket"])

    return app


# Create app instance
app = create_app()


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "message": "Hyperliquid Trading Bot Suite API",
        "version": settings.app_version,
        "docs": "/api/docs" if settings.debug else "Documentation disabled in production",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers if not settings.reload else 1,
        log_level=settings.log_level.lower(),
    )
