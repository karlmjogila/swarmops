"""
Hyperliquid Trading Bot Suite Backend

AI-powered trading system that learns strategies from educational content,
extracts rules into a structured knowledge base, and executes trades via 
a hybrid LLM + fast pattern detection engine.
"""

__version__ = "0.1.0"
__author__ = "Hyperliquid Bot Team"
__email__ = "bot@example.com"

# from .config import settings, get_settings  # Commented out to avoid pydantic dependency for now
from .types import *

__all__ = [
    "__version__", 
    "__author__", 
    "__email__",
    "settings", 
    "get_settings"
]