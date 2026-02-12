"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from typing import Optional, List
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    # Database - credentials from env vars only
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "hlbot"
    db_user: str = "hlbot"
    db_password: SecretStr = SecretStr("")  # MUST be set via env var
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Security
    api_key: SecretStr = SecretStr("")  # Required for production
    cors_origins: str = '["http://localhost:3000", "http://localhost:5173"]'
    
    # Environment
    environment: str = "development"
    
    # LLM
    anthropic_api_key: Optional[SecretStr] = None
    
    # ==========================================================================
    # Hyperliquid Data Sync Configuration
    # ==========================================================================
    
    # Timeframes to sync (all supported Hyperliquid intervals)
    hl_sync_timeframes: str = '["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]'
    
    # Default symbols to sync (can be overridden per task)
    hl_sync_symbols: str = '["BTC", "ETH", "SOL", "ARB", "DOGE", "WIF", "PEPE", "HYPE"]'
    
    # Sync schedule interval in seconds (3600 = 1 hour)
    hl_sync_interval_seconds: int = 3600
    
    # Data retention policy: 1m candles retention in days (3 years = 1095 days)
    hl_retention_1m_days: int = 1095  # 3 years
    
    # Other timeframes are kept forever (no retention limit)
    # hl_retention_other_days: None  # Forever
    
    # Cleanup schedule: how often to run retention cleanup (in seconds)
    # Default: once per day (86400 seconds)
    hl_cleanup_interval_seconds: int = 86400
    
    # TimescaleDB chunk interval for 1m data (in days)
    # Smaller chunks = faster drop_chunks() for retention
    hl_chunk_interval_1m_days: int = 1
    
    # TimescaleDB chunk interval for other timeframes (in days)
    hl_chunk_interval_other_days: int = 7
    
    # Compression age: compress chunks older than this many days
    hl_compression_after_days: int = 7
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def database_url(self) -> str:
        """Build database URL from components (never hardcode password)."""
        password = self.db_password.get_secret_value()
        if not password and not self.is_development:
            raise ValueError("DB_PASSWORD must be set in production")
        return f"postgresql://{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        try:
            return json.loads(self.cors_origins)
        except json.JSONDecodeError:
            # Fallback: comma-separated list
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
    
    @property
    def hl_sync_timeframes_list(self) -> List[str]:
        """Parse Hyperliquid sync timeframes from JSON string."""
        try:
            return json.loads(self.hl_sync_timeframes)
        except json.JSONDecodeError:
            return ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
    
    @property
    def hl_sync_symbols_list(self) -> List[str]:
        """Parse Hyperliquid sync symbols from JSON string."""
        try:
            return json.loads(self.hl_sync_symbols)
        except json.JSONDecodeError:
            return ["BTC", "ETH"]


# Global settings instance
settings = Settings()
