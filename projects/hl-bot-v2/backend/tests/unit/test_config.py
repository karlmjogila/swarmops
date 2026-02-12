"""Unit tests for configuration module."""

import pytest

from hl_bot.config import Settings, get_settings


def test_settings_defaults():
    """Test that settings have correct default values."""
    settings = Settings()
    
    assert settings.app_name == "HL Trading Bot"
    assert settings.debug is False
    assert settings.port == 8000
    assert settings.host == "0.0.0.0"
    assert settings.log_level == "info"


def test_settings_is_production():
    """Test is_production property."""
    settings = Settings(debug=False)
    assert settings.is_production is True
    
    settings = Settings(debug=True)
    assert settings.is_production is False


def test_get_settings_singleton():
    """Test that get_settings returns the same instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2
