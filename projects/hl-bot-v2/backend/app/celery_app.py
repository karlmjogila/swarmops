"""Celery application configuration for background task processing.

Handles YouTube video processing, PDF document processing, LLM-based
strategy extraction, and Hyperliquid data synchronization as asynchronous
background tasks.
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from app.config import settings

# Initialize Celery app
celery_app = Celery(
    "hl_bot",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Retry if worker dies
    task_track_started=True,  # Track when tasks start
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results in Redis
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time (for heavy tasks)
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
    
    # Retry settings
    task_default_retry_delay=60,  # Retry after 60 seconds
    task_max_retries=3,
    
    # Time limits
    task_soft_time_limit=1800,  # 30 minutes soft limit
    task_time_limit=2400,  # 40 minutes hard limit
    
    # Queues
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("youtube", routing_key="youtube.*"),
        Queue("pdf", routing_key="pdf.*"),
        Queue("llm", routing_key="llm.*"),
        Queue("data", routing_key="data.*"),
        Queue("maintenance", routing_key="maintenance.*"),
    ),
    
    # Routes
    task_routes={
        "app.workers.tasks.process_youtube_video": {"queue": "youtube"},
        "app.workers.tasks.process_youtube_playlist": {"queue": "youtube"},
        "app.workers.tasks.process_pdf_document": {"queue": "pdf"},
        "app.workers.tasks.extract_trading_strategy": {"queue": "llm"},
        "app.workers.tasks.analyze_chart_image": {"queue": "llm"},
        "app.workers.tasks.sync_hyperliquid_data": {"queue": "data"},
        "app.workers.tasks.sync_hyperliquid_bulk": {"queue": "data"},
        "app.workers.tasks.sync_all_hyperliquid_data": {"queue": "data"},
        "app.workers.tasks.sync_hyperliquid_hourly": {"queue": "data"},
        "app.workers.tasks.cleanup_old_candles": {"queue": "maintenance"},
        "app.workers.tasks.run_timescaledb_maintenance": {"queue": "maintenance"},
    },
    
    # Beat schedule (for periodic tasks)
    beat_schedule={
        # =====================================================================
        # Cache Cleanup Tasks
        # =====================================================================
        "cleanup-youtube-cache": {
            "task": "app.workers.tasks.cleanup_youtube_cache",
            "schedule": 86400.0,  # Once per day
        },
        "cleanup-pdf-cache": {
            "task": "app.workers.tasks.cleanup_pdf_cache",
            "schedule": 86400.0,  # Once per day
        },
        
        # =====================================================================
        # Hyperliquid Data Sync - HOURLY
        # Fetches all timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M
        # =====================================================================
        "sync-hyperliquid-hourly": {
            "task": "app.workers.tasks.sync_hyperliquid_hourly",
            "schedule": float(settings.hl_sync_interval_seconds),  # Default: 3600 (1 hour)
            "options": {"queue": "data"},
        },
        
        # =====================================================================
        # Data Retention Cleanup - DAILY
        # Deletes 1m candles older than 3 years using TimescaleDB drop_chunks()
        # =====================================================================
        "cleanup-old-candles-daily": {
            "task": "app.workers.tasks.cleanup_old_candles",
            "schedule": crontab(hour=3, minute=0),  # Run at 3:00 AM UTC daily
            "options": {"queue": "maintenance"},
        },
        
        # =====================================================================
        # TimescaleDB Maintenance - WEEKLY
        # Runs compression and other maintenance tasks
        # =====================================================================
        "timescaledb-maintenance-weekly": {
            "task": "app.workers.tasks.run_timescaledb_maintenance",
            "schedule": crontab(hour=4, minute=0, day_of_week=0),  # Sunday 4:00 AM UTC
            "options": {"queue": "maintenance"},
        },
    },
)

# Optional: Configure logging
celery_app.conf.worker_log_format = (
    "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
)
celery_app.conf.worker_task_log_format = (
    "[%(asctime)s: %(levelname)s/%(processName)s] "
    "[%(task_name)s(%(task_id)s)] %(message)s"
)
