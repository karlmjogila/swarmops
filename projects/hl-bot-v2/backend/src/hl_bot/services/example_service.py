"""Example service demonstrating business logic patterns."""

import logging
from typing import Any

from hl_bot.config import Settings

logger = logging.getLogger(__name__)


class ExampleService:
    """Example service for demonstrating patterns.
    
    Services contain business logic and coordinate between repositories
    and external services. They should be framework-agnostic.
    """

    def __init__(self, settings: Settings):
        """Initialize the service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self._logger = logger

    async def process_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process data with business logic.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed data
            
        Raises:
            ValueError: If data is invalid
        """
        self._logger.info("Processing data", extra={"data_keys": list(data.keys())})
        
        # Example business logic
        if not data:
            raise ValueError("Data cannot be empty")
            
        result = {
            "processed": True,
            "input_size": len(data),
            "timestamp": "2024-01-01T00:00:00Z",
        }
        
        return result
