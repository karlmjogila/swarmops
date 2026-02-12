"""Configuration settings for the Hyperliquid Trading Bot Suite."""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    app_name: str = "Hyperliquid Trading Bot Suite"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/trading_bot",
        description="PostgreSQL database URL"
    )
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis cache URL"
    )
    redis_db: int = 0
    redis_max_connections: int = 10

    # LLM Configuration
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key for Claude"
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    
    # Claude model configurations
    claude_extraction_model: str = "claude-3-opus-20240229"  # For complex extraction
    claude_reasoning_model: str = "claude-3-sonnet-20240229"  # For fast reasoning
    claude_max_tokens: int = 4000
    claude_temperature: float = 0.1

    # Hyperliquid
    hyperliquid_api_url: str = "https://api.hyperliquid.xyz"
    hyperliquid_private_key: Optional[str] = Field(
        default=None,
        description="Hyperliquid private key (hex format)"
    )
    hyperliquid_testnet: bool = True  # Start in testnet mode
    hyperliquid_wallet_address: Optional[str] = None

    # Trading Configuration
    max_risk_per_trade: float = Field(
        default=0.02,
        description="Maximum risk per trade as percentage of account"
    )
    max_concurrent_positions: int = 5
    max_daily_loss_percent: float = 0.05
    default_tp1_r: float = 1.0  # TP1 at 1R
    default_tp2_r: float = 2.0  # TP2 at 2R
    breakeven_r: float = 0.5    # Move SL to breakeven at 0.5R

    # Pattern Detection
    min_confluence_score: float = 0.7
    pattern_lookback_candles: int = 100
    structure_lookback_candles: int = 200

    # Video Processing
    whisper_model: str = "base"  # base, small, medium, large
    frame_extract_interval: int = 10  # seconds
    similarity_threshold: float = 0.9  # for frame deduplication
    max_video_duration: int = 3600  # 1 hour max

    # PDF Processing
    max_pdf_pages: int = 100
    image_extract_dpi: int = 150

    # File Storage
    upload_dir: str = "uploads"
    temp_dir: str = "temp"
    data_dir: str = "data"
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # Security
    secret_key: str = Field(
        default="",
        description="Secret key for JWT tokens (REQUIRED - set via SECRET_KEY env var)"
    )
    access_token_expire_minutes: int = 30
    
    @property
    def validated_secret_key(self) -> str:
        """Get secret key, raising error if not properly configured."""
        if not self.secret_key or self.secret_key == "your-secret-key-change-in-production":
            raise ValueError(
                "SECRET_KEY environment variable must be set to a secure random value. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(self.secret_key) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long for security"
            )
        return self.secret_key
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # WebSocket
    websocket_heartbeat_interval: int = 30  # seconds

    @property
    def database_dsn(self) -> str:
        """Get database DSN for SQLAlchemy."""
        return self.database_url

    @property
    def redis_dsn(self) -> str:
        """Get Redis DSN."""
        return f"{self.redis_url}/{self.redis_db}"

    def get_anthropic_client_config(self) -> dict:
        """Get Anthropic client configuration."""
        return {
            "api_key": self.anthropic_api_key,
            "max_retries": 3,
            "timeout": 60.0,
        }

    def get_openai_client_config(self) -> dict:
        """Get OpenAI client configuration."""
        return {
            "api_key": self.openai_api_key,
            "max_retries": 3,
            "timeout": 60.0,
        }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development environment settings."""
    debug: bool = True
    log_level: str = "DEBUG"
    reload: bool = True
    database_echo: bool = True


class ProductionSettings(Settings):
    """Production environment settings."""
    debug: bool = False
    log_level: str = "WARNING"
    reload: bool = False
    workers: int = 4
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validate secret key in production
        _ = self.validated_secret_key


class TestSettings(Settings):
    """Test environment settings."""
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/trading_bot_test"
    redis_url: str = "redis://localhost:6379/1"
    debug: bool = True
    log_level: str = "DEBUG"


def get_settings_for_env(env: str = None) -> Settings:
    """Get settings based on environment."""
    if env is None:
        env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "test":
        return TestSettings()
    else:
        return DevelopmentSettings()


class HyperliquidConfig:
    """Configuration for Hyperliquid client."""
    
    def __init__(
        self,
        private_key: Optional[str] = None,
        wallet_address: Optional[str] = None,
        testnet: bool = True,
        base_url: Optional[str] = None,
        websocket_url: Optional[str] = None,
        connection_timeout: int = 30,
        heartbeat_interval: int = 30
    ):
        """
        Initialize Hyperliquid configuration.
        
        Args:
            private_key: Private key for authentication (hex format)
            wallet_address: Wallet address for the account
            testnet: Whether to use testnet (default: True)
            base_url: Custom base URL (optional)
            websocket_url: Custom WebSocket URL (optional)
            connection_timeout: Connection timeout in seconds
            heartbeat_interval: WebSocket heartbeat interval in seconds
        """
        self.private_key = private_key or settings.hyperliquid_private_key
        self.wallet_address = wallet_address or settings.hyperliquid_wallet_address
        self.testnet = testnet if testnet is not None else settings.hyperliquid_testnet
        self.connection_timeout = connection_timeout
        self.heartbeat_interval = heartbeat_interval
        
        # Set URLs based on testnet flag
        if base_url:
            self.base_url = base_url
        else:
            if self.testnet:
                self.base_url = "https://api-testnet.hyperliquid.xyz"
            else:
                self.base_url = settings.hyperliquid_api_url
        
        if websocket_url:
            self.websocket_url = websocket_url
        else:
            if self.testnet:
                self.websocket_url = "wss://api-testnet.hyperliquid.xyz/ws"
            else:
                self.websocket_url = "wss://api.hyperliquid.xyz/ws"
    
    @classmethod
    def from_settings(cls, settings_obj: Settings = None) -> "HyperliquidConfig":
        """Create configuration from application settings."""
        if settings_obj is None:
            settings_obj = settings
        
        return cls(
            private_key=settings_obj.hyperliquid_private_key,
            wallet_address=settings_obj.hyperliquid_wallet_address,
            testnet=settings_obj.hyperliquid_testnet
        )
    
    @classmethod
    def for_paper_trading(cls) -> "HyperliquidConfig":
        """Create configuration for paper trading (no credentials needed)."""
        return cls(
            private_key=None,
            wallet_address=None,
            testnet=True
        )
    
    def validate_for_live_trading(self) -> None:
        """Validate configuration for live trading."""
        if not self.private_key:
            raise ValueError("Private key is required for live trading")
        if not self.wallet_address:
            raise ValueError("Wallet address is required for live trading")
        
        # Basic validation of private key format (should be hex)
        if not isinstance(self.private_key, str) or not all(c in '0123456789abcdefABCDEF' for c in self.private_key):
            raise ValueError("Private key must be in hexadecimal format")
        
        # Basic validation of wallet address format
        if not isinstance(self.wallet_address, str) or not self.wallet_address.startswith('0x'):
            raise ValueError("Wallet address must start with '0x'")
    
    def __repr__(self) -> str:
        """String representation hiding sensitive data."""
        return (
            f"HyperliquidConfig("
            f"testnet={self.testnet}, "
            f"base_url='{self.base_url}', "
            f"has_private_key={bool(self.private_key)}, "
            f"has_wallet_address={bool(self.wallet_address)})"
        )