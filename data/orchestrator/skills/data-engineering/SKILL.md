---
name: data-engineering
description: >
  Build reliable, scalable data pipelines with proper validation, idempotent processing,
  error handling, and storage patterns. Covers ETL/ELT design, time-series data, stream
  processing, data quality monitoring, and file-based data management. Trigger this skill
  for any task involving data pipelines, ETL, data processing, data validation, data storage,
  CSV/JSON/Parquet files, data transformation, or data quality.
triggers:
  - pipeline
  - etl
  - elt
  - data processing
  - data validation
  - data quality
  - csv
  - parquet
  - jsonl
  - transform
  - ingest
  - extract
  - load
  - time series
  - batch
  - stream
  - backfill
  - partition
  - schema
  - normalize
  - aggregate
---

# Data Engineering Excellence

Data pipelines are the plumbing of software — invisible when working, catastrophic when broken. Build pipelines that are idempotent, observable, and recoverable. Every record should be traceable from source to destination, and every failure should be retryable without data loss or duplication.

## Core Principles

1. **Idempotent by design** — Running the same pipeline twice with the same input produces the same output. No duplicates, no missing data.
2. **Schema is a contract** — Validate data shape at every boundary. Upstream changes should fail loudly at ingestion, not silently corrupt downstream.
3. **Fail fast, recover gracefully** — Bad records go to a dead letter queue. Good records keep flowing. Never let one bad row kill the entire pipeline.

## Pipeline Architecture

### Batch vs Stream
```python
# Batch: Process data in scheduled intervals (hourly, daily)
# Use when: latency tolerance > minutes, data arrives in dumps, need full reprocessing
#
# Stream: Process data as it arrives in real-time
# Use when: latency requirements < seconds, continuous data source, event-driven
#
# Hybrid: Stream for real-time, batch for corrections and backfill
# This is the most common pattern in practice.
```

### Pipeline Structure
```python
# Every pipeline follows: Extract → Validate → Transform → Load

async def run_pipeline(
    source: DataSource,
    sink: DataSink,
    run_id: str,
    date_partition: str,
) -> PipelineResult:
    """
    A single pipeline run. Must be idempotent:
    running this twice for the same date_partition produces identical output.
    """
    stats = PipelineStats(run_id=run_id)

    # 1. Extract — pull raw data
    raw_records = await source.extract(date_partition)
    stats.extracted = len(raw_records)

    # 2. Validate — enforce schema and data quality
    valid_records, invalid_records = validate_batch(raw_records)
    stats.valid = len(valid_records)
    stats.invalid = len(invalid_records)

    # 3. Handle invalid records — dead letter queue
    if invalid_records:
        await dead_letter_queue.write(invalid_records, run_id=run_id)
        logger.warning(f"Sent {len(invalid_records)} records to DLQ")

    # 4. Transform
    transformed = [transform_record(r) for r in valid_records]

    # 5. Load — write atomically (overwrite partition for idempotency)
    await sink.write(transformed, partition=date_partition, mode="overwrite")
    stats.loaded = len(transformed)

    logger.info("Pipeline complete", **stats.to_dict())
    return PipelineResult(stats=stats)
```

## Data Validation

### Schema Enforcement with Pydantic
```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class TradeRecord(BaseModel):
    """Schema for a single trade — validates at ingestion boundary."""
    trade_id: str = Field(min_length=1)
    symbol: str = Field(pattern=r"^[A-Z0-9_-]+$")
    side: str = Field(pattern=r"^(buy|sell)$")
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    timestamp: datetime
    exchange: str

    @field_validator("timestamp")
    @classmethod
    def timestamp_not_future(cls, v: datetime) -> datetime:
        if v > datetime.utcnow():
            raise ValueError("Timestamp cannot be in the future")
        return v


def validate_batch(
    records: list[dict],
) -> tuple[list[TradeRecord], list[dict]]:
    """Validate a batch. Never throw — sort into valid and invalid."""
    valid: list[TradeRecord] = []
    invalid: list[dict] = []

    for raw in records:
        try:
            valid.append(TradeRecord.model_validate(raw))
        except Exception as e:
            invalid.append({
                "record": raw,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            })

    return valid, invalid
```

### Data Quality Checks
```python
@dataclass
class QualityCheck:
    name: str
    passed: bool
    detail: str = ""


def check_data_quality(records: list[TradeRecord]) -> list[QualityCheck]:
    """Run quality checks on validated data."""
    checks = []

    # Completeness — are we missing expected data?
    checks.append(QualityCheck(
        name="record_count",
        passed=len(records) > 0,
        detail=f"Got {len(records)} records",
    ))

    # Uniqueness — no duplicate trade IDs
    trade_ids = [r.trade_id for r in records]
    duplicates = len(trade_ids) - len(set(trade_ids))
    checks.append(QualityCheck(
        name="unique_trade_ids",
        passed=duplicates == 0,
        detail=f"Found {duplicates} duplicates",
    ))

    # Freshness — most recent record should be recent
    if records:
        latest = max(r.timestamp for r in records)
        age_minutes = (datetime.utcnow() - latest).total_seconds() / 60
        checks.append(QualityCheck(
            name="data_freshness",
            passed=age_minutes < 60,
            detail=f"Latest record is {age_minutes:.0f} minutes old",
        ))

    # Value range — no obviously wrong prices
    if records:
        prices = [r.price for r in records]
        checks.append(QualityCheck(
            name="price_range",
            passed=all(0.001 < p < 1_000_000 for p in prices),
            detail=f"Price range: {min(prices):.4f} - {max(prices):.4f}",
        ))

    return checks
```

## Idempotent Processing

### Partition-Based Idempotency
```python
# The key pattern: write to a partition, overwrite on retry

async def load_daily_trades(trades: list[dict], date: str) -> None:
    """
    Idempotent: running this twice for the same date overwrites,
    producing identical output.
    """
    partition_path = f"data/trades/date={date}"

    # Write to temp, then atomic rename
    temp_path = f"{partition_path}.tmp.{uuid4()}"
    await write_parquet(trades, temp_path)
    await atomic_replace(temp_path, partition_path)


# For databases: use UPSERT (INSERT ON CONFLICT UPDATE)
async def upsert_trades(trades: list[TradeRecord], db) -> None:
    """Idempotent: same trade_id → update, new trade_id → insert."""
    await db.execute("""
        INSERT INTO trades (trade_id, symbol, side, price, quantity, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (trade_id) DO UPDATE SET
            price = EXCLUDED.price,
            quantity = EXCLUDED.quantity,
            updated_at = now()
    """, [(t.trade_id, t.symbol, t.side, t.price, t.quantity, t.timestamp)
          for t in trades])
```

### Checkpointing
```python
class PipelineCheckpoint:
    """Track pipeline progress for resumable processing."""

    def __init__(self, checkpoint_path: str):
        self._path = checkpoint_path

    async def get_last_processed(self) -> str | None:
        try:
            data = json.loads(await aiofiles.read(self._path))
            return data.get("last_processed")
        except FileNotFoundError:
            return None

    async def save(self, last_processed: str) -> None:
        await atomic_write(self._path, json.dumps({
            "last_processed": last_processed,
            "updated_at": datetime.utcnow().isoformat(),
        }))


# Usage — resume from where we left off
checkpoint = PipelineCheckpoint("checkpoints/trade_pipeline.json")
last = await checkpoint.get_last_processed()
records = await source.extract(after=last)
# ... process ...
await checkpoint.save(records[-1].trade_id)
```

## Dead Letter Queue

```python
from pathlib import Path
import json
import aiofiles


class DeadLetterQueue:
    """
    Store failed records for later inspection and reprocessing.
    Never lose data — even bad data has diagnostic value.
    """

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def write(self, records: list[dict], run_id: str) -> None:
        path = self._base_dir / f"dlq-{run_id}.jsonl"
        async with aiofiles.open(path, "a") as f:
            for record in records:
                await f.write(json.dumps(record) + "\n")

    async def reprocess(self, run_id: str) -> list[dict]:
        """Read back failed records for reprocessing attempt."""
        path = self._base_dir / f"dlq-{run_id}.jsonl"
        records = []
        async with aiofiles.open(path) as f:
            async for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records
```

## Storage Patterns

### JSONL for Append-Only Logs
```python
# Best for: activity logs, audit trails, event streams
# Advantages: append is atomic, easy to stream, human-readable
# Disadvantages: no column pruning, no compression, slow for analytics

async def append_jsonl(path: str, record: dict) -> None:
    line = json.dumps(record, default=str) + "\n"
    async with aiofiles.open(path, "a") as f:
        await f.write(line)


async def read_jsonl(path: str) -> AsyncGenerator[dict, None]:
    async with aiofiles.open(path) as f:
        async for line in f:
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed JSONL line")
```

### Parquet for Analytics
```python
import pyarrow as pa
import pyarrow.parquet as pq

# Best for: historical data, analytics queries, large datasets
# Advantages: columnar (fast filters), compressed (10-100x smaller), typed
# Disadvantages: not appendable (must rewrite), binary format

def write_parquet(
    records: list[dict],
    path: str,
    partition_cols: list[str] | None = None,
) -> None:
    table = pa.Table.from_pylist(records)
    pq.write_to_dataset(
        table,
        root_path=path,
        partition_cols=partition_cols,
        compression="snappy",           # Fast compression
        use_dictionary=True,            # Compress repeated values
        write_statistics=True,          # Enable predicate pushdown
    )


# Partitioning strategy: date-based for time-series data
# data/trades/date=2024-01-15/part-0.parquet
# data/trades/date=2024-01-16/part-0.parquet
# Target file size: 128MB - 1GB for optimal read performance
```

### Atomic File Operations
```python
from pathlib import Path
from uuid import uuid4
import os


async def atomic_write(path: str, content: str) -> None:
    """Write to temp file, then rename (atomic on same filesystem)."""
    temp_path = f"{path}.tmp.{uuid4()}"
    async with aiofiles.open(temp_path, "w") as f:
        await f.write(content)
    os.rename(temp_path, path)


async def atomic_replace(src: str, dst: str) -> None:
    """Atomically replace a directory (for partition overwrites)."""
    if os.path.exists(dst):
        backup = f"{dst}.backup.{uuid4()}"
        os.rename(dst, backup)
        try:
            os.rename(src, dst)
            shutil.rmtree(backup)
        except Exception:
            os.rename(backup, dst)  # Rollback
            raise
    else:
        os.rename(src, dst)
```

## Time-Series Data

```python
from datetime import datetime, timedelta


def align_to_interval(
    timestamp: datetime,
    interval_seconds: int,
) -> datetime:
    """Align a timestamp to the start of its interval."""
    epoch = int(timestamp.timestamp())
    aligned = epoch - (epoch % interval_seconds)
    return datetime.utcfromtimestamp(aligned)


def build_ohlcv(
    trades: list[TradeRecord],
    interval_seconds: int = 60,
) -> list[dict]:
    """Aggregate trades into OHLCV candles."""
    buckets: dict[datetime, list[TradeRecord]] = {}

    for trade in trades:
        bucket = align_to_interval(trade.timestamp, interval_seconds)
        buckets.setdefault(bucket, []).append(trade)

    candles = []
    for timestamp, bucket_trades in sorted(buckets.items()):
        prices = [t.price for t in bucket_trades]
        volumes = [t.quantity for t in bucket_trades]
        candles.append({
            "timestamp": timestamp.isoformat(),
            "open": prices[0],
            "high": max(prices),
            "low": min(prices),
            "close": prices[-1],
            "volume": sum(volumes),
            "trade_count": len(bucket_trades),
        })

    return candles
```

## Backfill Patterns

```python
async def backfill(
    source: DataSource,
    sink: DataSink,
    start_date: str,
    end_date: str,
    concurrency: int = 3,
) -> None:
    """
    Backfill historical data. Rules:
    1. Start with a small test range before running full backfill
    2. Use partition-based idempotency (overwrite mode)
    3. Limit concurrency to avoid overwhelming the source
    4. Monitor resource usage throughout
    """
    dates = generate_date_range(start_date, end_date)
    semaphore = asyncio.Semaphore(concurrency)

    async def process_date(date: str) -> None:
        async with semaphore:
            logger.info(f"Backfilling {date}")
            await run_pipeline(source, sink, run_id=f"backfill-{date}", date_partition=date)

    # Process in batches — don't launch everything at once
    results = await asyncio.gather(
        *[process_date(d) for d in dates],
        return_exceptions=True,
    )

    failed = [(d, r) for d, r in zip(dates, results) if isinstance(r, Exception)]
    if failed:
        logger.error(f"Backfill failed for {len(failed)} dates: {[d for d, _ in failed]}")
```

## Quality Checklist

- [ ] Pipeline is idempotent — same input always produces same output
- [ ] All input data validated at ingestion (schema + quality checks)
- [ ] Failed records go to dead letter queue (not dropped)
- [ ] File writes are atomic (write-to-temp + rename)
- [ ] Partitioning strategy matches query patterns (date-based for time-series)
- [ ] Checkpointing enables resumable processing after failure
- [ ] Pipeline stats logged (extracted, valid, invalid, loaded counts)
- [ ] Backfill process tested with small range before full run
- [ ] No duplicate records after re-running pipeline
- [ ] Data quality checks run after every load
- [ ] Storage format matches use case (JSONL for logs, Parquet for analytics)
- [ ] Pipeline has monitoring and alerting on failure

## Anti-Patterns

- Append-only without deduplication (re-run creates duplicates)
- Validating data only at the end of the pipeline (garbage in, garbage out)
- Dropping invalid records silently (you'll never know data is missing)
- Using `readFile` for multi-GB files (stream them)
- No partition strategy — one giant file that grows forever
- Testing pipelines only with happy-path data (test with malformed, missing, duplicate)
- Backfilling without concurrency limits (overloads source systems)
- Mutable pipeline state (shared variables between runs)
- No checkpointing — every failure means starting over
- Mixing schema versions without migration logic
- Using CSV for anything beyond one-off data exchange (no types, no compression)
- Processing time-series data without timezone awareness
