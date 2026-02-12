"""Structured logging utilities."""

import json
import logging
from datetime import UTC, datetime
from typing import Any


class StructuredLogger:
    """Structured logger that outputs JSON-formatted logs."""

    def __init__(self, name: str):
        """Initialize the structured logger.
        
        Args:
            name: Logger name (typically __name__)
        """
        self._logger = logging.getLogger(name)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message.
        
        Args:
            message: The log message
            **kwargs: Additional fields to include in the log entry
        """
        self._log("info", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message.
        
        Args:
            message: The log message
            **kwargs: Additional fields to include in the log entry
        """
        self._log("warning", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message.
        
        Args:
            message: The log message
            **kwargs: Additional fields to include in the log entry
        """
        self._log("error", message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message.
        
        Args:
            message: The log message
            **kwargs: Additional fields to include in the log entry
        """
        self._log("debug", message, **kwargs)

    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        """Internal method to format and emit log entries.
        
        Args:
            level: Log level (info, warning, error, debug)
            message: The log message
            **kwargs: Additional fields to include
        """
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "message": message,
            **kwargs,
        }
        log_method = getattr(self._logger, level)
        log_method(json.dumps(entry))


def get_logger(name: str) -> StructuredLogger:
    """Get or create a structured logger.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Structured logger instance
    """
    return StructuredLogger(name)
