"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hl_bot.config import get_settings
from hl_bot.api.v1 import health, strategies, ingestion, ingest, positions
from hl_bot.trading.position_monitor import PositionMonitor
from hl_bot.trading.position import PositionTracker
from hl_bot.trading.audit_logger import AuditLogger


# Global instances (initialized in lifespan)
_position_monitor: PositionMonitor | None = None


# Setup logging
def setup_logging(level: str = "INFO") -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    global _position_monitor
    
    # Startup
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Initialize position monitoring (if live trading is enabled)
    if settings.enable_live_trading:
        try:
            from hl_bot.trading.hyperliquid import HyperliquidClient
            
            # Initialize Hyperliquid client
            hl_client = HyperliquidClient(
                private_key=settings.hyperliquid_private_key,
                testnet=settings.hyperliquid_testnet,
                audit_log_dir=Path(settings.log_dir) / "trading",
            )
            
            # Initialize position tracker
            position_tracker = PositionTracker()
            
            # Initialize audit logger
            audit_logger = AuditLogger(Path(settings.log_dir) / "trading")
            
            # Initialize position monitor
            _position_monitor = PositionMonitor(
                hyperliquid_client=hl_client,
                position_tracker=position_tracker,
                audit_logger=audit_logger,
                update_interval=1.0,  # Update every second
            )
            
            # Register with API
            positions.set_position_monitor(_position_monitor)
            positions.initialize_position_streaming(_position_monitor)
            
            # Start monitoring
            await _position_monitor.start()
            logger.info("Position monitor started")
            
        except Exception as e:
            logger.error(f"Failed to initialize position monitor: {e}", exc_info=True)
    else:
        logger.info("Live trading disabled, position monitor not started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down gracefully...")
    
    # Stop position monitor
    if _position_monitor and _position_monitor.is_running:
        await _position_monitor.stop()
        logger.info("Position monitor stopped")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="High-level trading bot API",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(strategies.router, prefix="/api/v1", tags=["strategies"])
app.include_router(ingestion.router, prefix="/api/v1", tags=["ingestion"])
app.include_router(ingest.router, prefix="/api", tags=["ingest"])  # Simplified API
app.include_router(positions.router, prefix="/api/v1", tags=["positions"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "HL Trading Bot API",
        "version": "0.1.0",
        "status": "running",
    }
