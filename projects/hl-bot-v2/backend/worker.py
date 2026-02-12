#!/usr/bin/env python3
"""Celery worker entry point.

Starts Celery workers for processing background tasks.

Usage:
    # Start worker for all queues
    celery -A app.celery_app worker -l info

    # Start worker for specific queue
    celery -A app.celery_app worker -Q youtube -l info
    celery -A app.celery_app worker -Q data -l info        # Hyperliquid sync
    celery -A app.celery_app worker -Q maintenance -l info # Cleanup tasks

    # Start worker with concurrency
    celery -A app.celery_app worker --concurrency=2 -l info

    # Start Celery beat scheduler (for periodic tasks)
    # This is REQUIRED for scheduled tasks to run!
    celery -A app.celery_app beat -l info

    # Or run both worker and beat together
    celery -A app.celery_app worker -B -l info

Scheduled Tasks (via Celery Beat):
    - sync-hyperliquid-hourly: Fetches all timeframes every hour
    - cleanup-old-candles-daily: Deletes 1m candles older than 3 years (3 AM UTC)
    - timescaledb-maintenance-weekly: Compresses chunks (Sunday 4 AM UTC)
"""

import logging
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.celery_app import celery_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s: %(levelname)s/%(name)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


def main():
    """Start Celery worker."""
    logger.info("Starting Celery worker for hl-bot")
    logger.info(f"Broker: {celery_app.conf.broker_url}")
    logger.info(f"Backend: {celery_app.conf.result_backend}")
    
    # The worker is started via celery CLI, this is just a reference
    # Actual command: celery -A app.celery_app worker -l info
    logger.info(
        "To start the worker, run:\n"
        "  celery -A app.celery_app worker -l info\n"
        "\n"
        "Or for specific queues:\n"
        "  celery -A app.celery_app worker -Q youtube,pdf,llm -l info\n"
        "\n"
        "To start the beat scheduler:\n"
        "  celery -A app.celery_app beat -l info"
    )


if __name__ == "__main__":
    main()
