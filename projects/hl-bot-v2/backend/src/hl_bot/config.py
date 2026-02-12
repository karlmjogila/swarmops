"""Application configuration using pydantic-settings."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = "HL Trading Bot"
    debug: bool = Field(default=False, description="Enable debug mode")
    port: int = Field(default=8000, ge=1024, le=65535, description="Server port")
    host: str = Field(default="0.0.0.0", description="Server host")
    
    # Logging
    log_level: str = Field(
        default="info",
        pattern=r"^(debug|info|warning|error|critical)$",
        description="Logging level",
    )
    log_dir: str = Field(default="logs", description="Log directory")

    # Live Trading
    enable_live_trading: bool = Field(
        default=False,
        description="Enable live trading features",
    )
    hyperliquid_private_key: SecretStr = Field(
        default=SecretStr(""),
        description="Hyperliquid wallet private key (EVM format)",
    )
    hyperliquid_testnet: bool = Field(
        default=True,
        description="Use Hyperliquid testnet (False for mainnet)",
    )

    # API Keys (examples - will be configured later)
    # api_key: SecretStr | None = Field(default=None, description="External API key")
    
    # Database (placeholder for future use)
    # database_url: str | None = Field(default=None, description="Database connection URL")

    # Computed properties
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.debug


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the settings singleton instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
