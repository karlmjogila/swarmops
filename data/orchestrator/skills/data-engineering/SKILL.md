---
name: data-engineering
description: >
  Build reliable, scalable data pipelines with proper validation, idempotent processing,
  error handling, and storage patterns. Covers ETL/ELT design, time-series data, stream
  processing (Kafka), distributed processing (Spark), orchestration (Airflow/dbt), data
  governance, data lake patterns (S3/Glue/Athena), data quality monitoring, and file-based
  data management. Tech stack: Python, AWS (S3, Glue, Athena), Kubernetes. Treats data
  stores and message queues as attached backing services (12-Factor IV). Trigger this skill
  for any task involving data pipelines, ETL, data processing, data validation, data storage,
  CSV/JSON/Parquet files, data transformation, Kafka, Spark, Airflow, dbt, data lake,
  data lineage, or data quality.
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
  - kafka
  - spark
  - flink
  - data governance
  - lineage
  - dbt
  - airflow
  - data lake
  - s3
---

# Data Engineering Excellence

Data pipelines are the plumbing of software — invisible when working, catastrophic when broken. Build pipelines that are idempotent, observable, and recoverable. Every record should be traceable from source to destination, and every failure should be retryable without data loss or duplication.

## Core Principles

1. **Idempotent by design** — Running the same pipeline twice with the same input produces the same output. No duplicates, no missing data.
2. **Schema is a contract** — Validate data shape at every boundary. Upstream changes should fail loudly at ingestion, not silently corrupt downstream.
3. **Fail fast, recover gracefully** — Bad records go to a dead letter queue. Good records keep flowing. Never let one bad row kill the entire pipeline.
4. **Backing services are attached resources** (12-Factor IV) — Databases, object stores (S3), message queues (Kafka), and warehouses are bound via configuration. Swapping local Kafka for managed MSK requires zero code changes — only a URL change in config.

```python
import os

PIPELINE_CONFIG = {
    "source_broker": os.environ["KAFKA_BROKER_URL"],       # local:9092 or MSK endpoint
    "sink_bucket": os.environ["DATA_LAKE_BUCKET"],          # s3://dev-lake or s3://prod-lake
    "warehouse_dsn": os.environ["WAREHOUSE_DSN"],           # local Postgres or Redshift
    "glue_catalog": os.environ.get("GLUE_CATALOG_ID", ""),  # AWS Glue catalog ID
    "dead_letter_queue": os.environ["DLQ_TOPIC"],           # Kafka DLQ topic or S3 prefix
}
```

## TDD: Data Quality Test-First

Write the quality assertion before the pipeline code. If the test does not exist, the pipeline must not ship.

```python
import pytest

def test_daily_trade_quality_rejects_duplicates():
    """Quality gate: duplicate trade IDs must be caught before load."""
    records = [
        {"trade_id": "T001", "symbol": "AAPL", "side": "buy", "price": 150.0,
         "quantity": 10, "timestamp": "2025-01-15T10:00:00Z", "exchange": "NYSE"},
        {"trade_id": "T001", "symbol": "AAPL", "side": "sell", "price": 151.0,
         "quantity": 5, "timestamp": "2025-01-15T10:01:00Z", "exchange": "NYSE"},
    ]
    valid, invalid = validate_batch(records)
    quality = check_data_quality(valid)
    uniqueness = next(c for c in quality if c.name == "unique_trade_ids")
    assert not uniqueness.passed, "Duplicate trade_id must fail quality check"

def test_daily_trade_quality_rejects_future_timestamps():
    """Quality gate: future timestamps indicate clock skew or bad data."""
    records = [
        {"trade_id": "T002", "symbol": "GOOG", "side": "buy", "price": 100.0,
         "quantity": 1, "timestamp": "2099-01-01T00:00:00Z", "exchange": "NASDAQ"},
    ]
    valid, invalid = validate_batch(records)
    assert len(invalid) == 1, "Future timestamp must fail schema validation"

# Step 2: THEN write the pipeline code that satisfies these tests (see below)
```

## Pipeline Architecture

```python
# Batch: latency tolerance > minutes, data arrives in dumps, need full reprocessing
# Stream: latency < seconds, continuous data source, event-driven
# Hybrid (most common): stream for real-time, batch for corrections and backfill

async def run_pipeline(
    source: DataSource, sink: DataSink, run_id: str, date_partition: str,
) -> PipelineResult:
    """Idempotent: running twice for the same date_partition produces identical output."""
    stats = PipelineStats(run_id=run_id)

    raw_records = await source.extract(date_partition)
    stats.extracted = len(raw_records)

    valid_records, invalid_records = validate_batch(raw_records)
    stats.valid, stats.invalid = len(valid_records), len(invalid_records)

    if invalid_records:
        await dead_letter_queue.write(invalid_records, run_id=run_id)

    transformed = [transform_record(r) for r in valid_records]
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

def validate_batch(records: list[dict]) -> tuple[list[TradeRecord], list[dict]]:
    """Never throw — sort into valid and invalid."""
    valid, invalid = [], []
    for raw in records:
        try:
            valid.append(TradeRecord.model_validate(raw))
        except Exception as e:
            invalid.append({"record": raw, "error": str(e), "timestamp": datetime.utcnow().isoformat()})
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
    checks = []
    checks.append(QualityCheck("record_count", len(records) > 0, f"Got {len(records)} records"))

    trade_ids = [r.trade_id for r in records]
    dupes = len(trade_ids) - len(set(trade_ids))
    checks.append(QualityCheck("unique_trade_ids", dupes == 0, f"Found {dupes} duplicates"))

    if records:
        latest = max(r.timestamp for r in records)
        age = (datetime.utcnow() - latest).total_seconds() / 60
        checks.append(QualityCheck("data_freshness", age < 60, f"Latest: {age:.0f}m old"))

        prices = [r.price for r in records]
        checks.append(QualityCheck("price_range", all(0.001 < p < 1_000_000 for p in prices),
                                   f"Range: {min(prices):.4f}-{max(prices):.4f}"))
    return checks
```

## Idempotent Processing

```python
async def load_daily_trades(trades: list[dict], date: str) -> None:
    """Idempotent: running twice for the same date overwrites, producing identical output."""
    partition_path = f"data/trades/date={date}"
    temp_path = f"{partition_path}.tmp.{uuid4()}"
    await write_parquet(trades, temp_path)
    await atomic_replace(temp_path, partition_path)

# For databases: UPSERT
async def upsert_trades(trades: list[TradeRecord], db) -> None:
    await db.execute("""
        INSERT INTO trades (trade_id, symbol, side, price, quantity, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (trade_id) DO UPDATE SET
            price = EXCLUDED.price, quantity = EXCLUDED.quantity, updated_at = now()
    """, [(t.trade_id, t.symbol, t.side, t.price, t.quantity, t.timestamp) for t in trades])
```

### Checkpointing
```python
class PipelineCheckpoint:
    def __init__(self, checkpoint_path: str):
        self._path = checkpoint_path

    async def get_last_processed(self) -> str | None:
        try:
            return json.loads(await aiofiles.read(self._path)).get("last_processed")
        except FileNotFoundError:
            return None

    async def save(self, last_processed: str) -> None:
        await atomic_write(self._path, json.dumps({
            "last_processed": last_processed,
            "updated_at": datetime.utcnow().isoformat(),
        }))
```

## Dead Letter Queue

```python
class DeadLetterQueue:
    """Store failed records for inspection and reprocessing. Never lose data."""

    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def write(self, records: list[dict], run_id: str) -> None:
        async with aiofiles.open(self._base_dir / f"dlq-{run_id}.jsonl", "a") as f:
            for record in records:
                await f.write(json.dumps(record) + "\n")

    async def reprocess(self, run_id: str) -> list[dict]:
        records = []
        async with aiofiles.open(self._base_dir / f"dlq-{run_id}.jsonl") as f:
            async for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records
```

## Storage Patterns

### JSONL for Append-Only Logs
```python
# Best for: audit trails, event streams. Append-atomic, human-readable. No column pruning.
async def append_jsonl(path: str, record: dict) -> None:
    async with aiofiles.open(path, "a") as f:
        await f.write(json.dumps(record, default=str) + "\n")
```

### Parquet for Analytics
```python
import pyarrow as pa, pyarrow.parquet as pq

# Best for: historical data, analytics. Columnar, compressed (10-100x), typed.
def write_parquet(records: list[dict], path: str, partition_cols: list[str] | None = None) -> None:
    table = pa.Table.from_pylist(records)
    pq.write_to_dataset(table, root_path=path, partition_cols=partition_cols,
                        compression="snappy", use_dictionary=True, write_statistics=True)

# Target file size: 128MB-1GB. Partition by date for time-series data.
# data/trades/date=2024-01-15/part-0.parquet
```

### Atomic File Operations
```python
async def atomic_write(path: str, content: str) -> None:
    temp_path = f"{path}.tmp.{uuid4()}"
    async with aiofiles.open(temp_path, "w") as f:
        await f.write(content)
    os.rename(temp_path, path)

async def atomic_replace(src: str, dst: str) -> None:
    if os.path.exists(dst):
        backup = f"{dst}.backup.{uuid4()}"
        os.rename(dst, backup)
        try:
            os.rename(src, dst)
            shutil.rmtree(backup)
        except Exception:
            os.rename(backup, dst)
            raise
    else:
        os.rename(src, dst)
```

## Time-Series Data

```python
def align_to_interval(timestamp: datetime, interval_seconds: int) -> datetime:
    epoch = int(timestamp.timestamp())
    return datetime.utcfromtimestamp(epoch - (epoch % interval_seconds))

def build_ohlcv(trades: list[TradeRecord], interval_seconds: int = 60) -> list[dict]:
    buckets: dict[datetime, list[TradeRecord]] = {}
    for trade in trades:
        bucket = align_to_interval(trade.timestamp, interval_seconds)
        buckets.setdefault(bucket, []).append(trade)

    return [
        {"timestamp": ts.isoformat(), "open": (p := [t.price for t in bt])[0],
         "high": max(p), "low": min(p), "close": p[-1],
         "volume": sum(t.quantity for t in bt), "trade_count": len(bt)}
        for ts, bt in sorted(buckets.items())
    ]
```

## Backfill Patterns

```python
async def backfill(source: DataSource, sink: DataSink,
                   start_date: str, end_date: str, concurrency: int = 3) -> None:
    """
    Rules: 1) Test with small range first  2) Partition-based idempotency (overwrite)
           3) Limit concurrency             4) Monitor resource usage
    """
    dates = generate_date_range(start_date, end_date)
    sem = asyncio.Semaphore(concurrency)

    async def process_date(date: str) -> None:
        async with sem:
            await run_pipeline(source, sink, run_id=f"backfill-{date}", date_partition=date)

    results = await asyncio.gather(*[process_date(d) for d in dates], return_exceptions=True)
    failed = [(d, r) for d, r in zip(dates, results) if isinstance(r, Exception)]
    if failed:
        logger.error(f"Backfill failed for {len(failed)} dates: {[d for d, _ in failed]}")
```

## Stream Processing (Kafka)

Kafka is the backbone for real-time pipelines. Every topic is a backing service (12-Factor IV) — broker URLs come from config.

### Producer/Consumer Patterns
```python
from confluent_kafka import Producer, Consumer, KafkaError

def create_producer() -> Producer:
    return Producer({
        "bootstrap.servers": os.environ["KAFKA_BROKER_URL"],
        "acks": "all",
        "enable.idempotence": True,
        "max.in.flight.requests.per.connection": 5,
        "linger.ms": 10,
    })

def produce_trade(producer: Producer, trade: TradeRecord) -> None:
    """Key by symbol — same symbol lands on same partition for ordering."""
    producer.produce(
        topic="trades.validated",
        key=trade.symbol.encode("utf-8"),
        value=json.dumps(trade.model_dump(), default=str).encode("utf-8"),
        callback=lambda err, msg: logger.error(f"Delivery failed: {err}") if err else None,
    )

def create_consumer(group_id: str) -> Consumer:
    return Consumer({
        "bootstrap.servers": os.environ["KAFKA_BROKER_URL"],
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,       # Manual commit after processing
    })

def consume_loop(consumer: Consumer, topics: list[str], handler) -> None:
    """At-least-once: commit AFTER successful processing."""
    consumer.subscribe(topics)
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise Exception(msg.error())
            handler(json.loads(msg.value().decode("utf-8")))
            consumer.commit(message=msg)
    finally:
        consumer.close()
```

### Avro Serialization with Schema Registry
```python
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer, AvroDeserializer

schema_registry = SchemaRegistryClient({"url": os.environ["SCHEMA_REGISTRY_URL"]})

TRADE_AVRO_SCHEMA = """{
    "type": "record", "name": "Trade", "namespace": "com.example.trades",
    "fields": [
        {"name": "trade_id", "type": "string"},
        {"name": "symbol",   "type": "string"},
        {"name": "side",     "type": {"type": "enum", "name": "Side", "symbols": ["buy","sell"]}},
        {"name": "price",    "type": "double"},
        {"name": "quantity", "type": "double"},
        {"name": "timestamp","type": {"type": "long", "logicalType": "timestamp-millis"}},
        {"name": "exchange", "type": "string"}
    ]
}"""

trade_serializer = AvroSerializer(schema_registry, TRADE_AVRO_SCHEMA)
trade_deserializer = AvroDeserializer(schema_registry, TRADE_AVRO_SCHEMA)
```

### Exactly-Once with Transactional Producer
```python
def create_transactional_producer() -> Producer:
    p = Producer({"bootstrap.servers": os.environ["KAFKA_BROKER_URL"],
                  "transactional.id": "trade-processor-001", "enable.idempotence": True})
    p.init_transactions()
    return p

def consume_transform_produce(consumer: Consumer, producer: Producer) -> None:
    """Exactly-once: read -> transform -> write in a single Kafka transaction."""
    consumer.subscribe(["trades.raw"])
    while True:
        msg = consumer.poll(1.0)
        if msg is None or msg.error():
            continue
        producer.begin_transaction()
        try:
            transformed = transform_record(json.loads(msg.value()))
            producer.produce("trades.enriched", value=json.dumps(transformed).encode())
            producer.send_offsets_to_transaction(
                consumer.position(consumer.assignment()), consumer.consumer_group_metadata())
            producer.commit_transaction()
        except Exception:
            producer.abort_transaction()
            raise
```

## Distributed Processing (Spark)

Use PySpark for datasets exceeding single-machine memory. Partition-aware processing is the most important optimization.

### PySpark Patterns
```python
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

def create_spark_session(app_name: str) -> SparkSession:
    return (SparkSession.builder.appName(app_name)
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.shuffle.partitions", "200")
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
            .getOrCreate())

TRADE_SCHEMA = StructType([
    StructField("trade_id", StringType(), False), StructField("symbol", StringType(), False),
    StructField("side", StringType(), False), StructField("price", DoubleType(), False),
    StructField("quantity", DoubleType(), False), StructField("timestamp", TimestampType(), False),
    StructField("exchange", StringType(), False),
])

def read_trades(spark: SparkSession, path: str, date: str) -> DataFrame:
    """Partition pruning — reads only one date directory from S3."""
    return spark.read.schema(TRADE_SCHEMA).parquet(path).filter(F.col("date") == date)
```

### Shuffle Optimization and Deduplication
```python
def compute_daily_volume(trades: DataFrame) -> DataFrame:
    """coalesce() reduces partitions without shuffle; repartition() only when needed."""
    return (trades.groupBy("symbol", "date")
            .agg(F.sum("quantity").alias("total_volume"), F.avg("price").alias("avg_price"),
                 F.count("*").alias("trade_count"))
            .coalesce(10))

def deduplicate_trades(trades: DataFrame) -> DataFrame:
    from pyspark.sql.window import Window
    w = Window.partitionBy("trade_id").orderBy(F.col("timestamp").desc())
    return trades.withColumn("rn", F.row_number().over(w)).filter(F.col("rn") == 1).drop("rn")
```

### Solving the Small File Problem
```python
def compact_small_files(spark: SparkSession, path: str, target_size_mb: int = 256) -> None:
    """Small files kill read performance. Run as scheduled maintenance, not inline."""
    df = spark.read.parquet(path)
    total_rows = df.count()
    if total_rows == 0:
        return
    # Estimate: ~100 bytes/row compressed Parquet
    num_files = max(1, (total_rows * 100) // (target_size_mb * 1024 * 1024))
    df.coalesce(num_files).write.mode("overwrite").parquet(path)
```

## Orchestration (Airflow / dbt)

### Airflow DAG Patterns
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from datetime import datetime, timedelta

default_args = {
    "owner": "data-engineering", "retries": 2,
    "retry_delay": timedelta(minutes=5), "execution_timeout": timedelta(hours=2),
}

with DAG("daily_trade_pipeline", default_args=default_args, schedule_interval="@daily",
         start_date=datetime(2025, 1, 1), catchup=False, max_active_runs=1) as dag:

    wait = S3KeySensor(task_id="wait_for_source",
        bucket_name="{{ var.value.data_lake_bucket }}",
        bucket_key="raw/trades/date={{ ds }}/", poke_interval=300, timeout=3600)

    validate = PythonOperator(task_id="validate_trades",
        python_callable=validate_and_dlq, op_kwargs={"date": "{{ ds }}"})

    transform = GlueJobOperator(task_id="transform_trades",
        job_name="trade_transformer", script_args={"--DATE": "{{ ds }}"})

    quality = PythonOperator(task_id="quality_gate",
        python_callable=run_quality_checks, op_kwargs={"date": "{{ ds }}"})

    wait >> validate >> transform >> quality
```

### dbt Models and Testing
```sql
-- models/staging/stg_trades.sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'trades') }}
    WHERE date = '{{ var("run_date") }}'
)
SELECT trade_id, UPPER(symbol) AS symbol, LOWER(side) AS side,
       CAST(price AS DECIMAL(18,8)) AS price, CAST(quantity AS DECIMAL(18,8)) AS quantity,
       CAST(timestamp AS TIMESTAMP) AS traded_at, exchange
FROM source
WHERE trade_id IS NOT NULL AND price > 0 AND quantity > 0
```

```yaml
# models/staging/stg_trades.yml — dbt tests as quality contracts
version: 2
models:
  - name: stg_trades
    columns:
      - name: trade_id
        tests: [unique, not_null]
      - name: price
        tests:
          - not_null
          - dbt_utils.accepted_range: {min_value: 0, inclusive: false}
      - name: side
        tests:
          - accepted_values: {values: ['buy', 'sell']}
```

```sql
-- models/marts/daily_volume.sql
SELECT symbol, date, COUNT(*) AS trade_count, SUM(quantity) AS total_volume,
       AVG(price) AS avg_price, MIN(price) AS low_price, MAX(price) AS high_price
FROM {{ ref('stg_trades') }}
GROUP BY symbol, date
```

## Data Governance

### Data Lineage and Classification
```python
from dataclasses import dataclass, field
from enum import Enum

class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    PII = "pii"

FIELD_CLASSIFICATIONS = {
    "email": DataClassification.PII, "phone": DataClassification.PII,
    "ip_address": DataClassification.SENSITIVE, "user_id": DataClassification.SENSITIVE,
    "trade_id": DataClassification.INTERNAL, "symbol": DataClassification.PUBLIC,
}

@dataclass
class LineageEvent:
    """Emitted by every pipeline run for auditable lineage."""
    run_id: str
    pipeline: str
    source_datasets: list[str]
    output_dataset: str
    record_count: int
    started_at: datetime
    completed_at: datetime
    status: str  # "success" | "failed" | "partial"

async def emit_lineage(event: LineageEvent) -> None:
    await append_jsonl(
        f"s3://{os.environ['DATA_LAKE_BUCKET']}/lineage/{event.pipeline}/{event.run_id}.jsonl",
        dataclasses.asdict(event))
```

### PII Masking and Retention Policies
```python
import hashlib

def mask_pii(record: dict) -> dict:
    """Hash PII fields before writing to analytics layer."""
    masked = record.copy()
    for name, value in masked.items():
        if FIELD_CLASSIFICATIONS.get(name) == DataClassification.PII and value:
            masked[name] = hashlib.sha256(str(value).encode()).hexdigest()[:16]
    return masked

RETENTION_POLICIES = {
    "raw/trades":     {"days": 90,   "action": "delete"},
    "staging/trades": {"days": 180,  "action": "archive_to_glacier"},
    "marts/":         {"days": 730,  "action": "archive_to_glacier"},
    "lineage/":       {"days": 2555, "action": "delete"},  # 7 years for audit
}

async def enforce_retention(bucket: str, policies: dict) -> None:
    """Delete or archive data past retention window. Run daily via Airflow."""
    s3 = boto3.client("s3")
    for prefix, policy in policies.items():
        cutoff = datetime.utcnow() - timedelta(days=policy["days"])
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                if obj["LastModified"].replace(tzinfo=None) < cutoff:
                    if policy["action"] == "delete":
                        s3.delete_object(Bucket=bucket, Key=obj["Key"])
                    elif policy["action"] == "archive_to_glacier":
                        s3.copy_object(Bucket=bucket, Key=obj["Key"],
                                       CopySource={"Bucket": bucket, "Key": obj["Key"]},
                                       StorageClass="GLACIER")
```

## Data Lake Patterns (S3)

### S3 Hive-Style Partitioning
```python
# s3://lake/raw/trades/exchange=NYSE/date=2025-01-15/part-000.parquet
# Rules: date first, limit 2-3 levels, NEVER high-cardinality keys, target 128MB-1GB/file

def build_s3_partition_path(bucket: str, table: str, partitions: dict[str, str]) -> str:
    parts = "/".join(f"{k}={v}" for k, v in partitions.items())
    return f"s3://{bucket}/{table}/{parts}"

async def write_partition_to_s3(records: list[dict], bucket: str, table: str,
                                 partitions: dict[str, str]) -> str:
    """Write partition via staging prefix — S3 has no atomic rename."""
    path = build_s3_partition_path(bucket, table, partitions)
    staging = path.replace(f"s3://{bucket}/", f"s3://{bucket}/_staging/")
    write_parquet(records, staging)
    # Copy from staging to final, then delete staging
    return path
```

### File Format Selection
```python
# | Format  | Columnar | ACID | Time Travel | Schema Evolution | Best For             |
# |---------|----------|------|-------------|------------------|----------------------|
# | Parquet | Yes      | No   | No          | Append-only      | Read-heavy analytics |
# | Delta   | Yes      | Yes  | Yes         | Full             | Lakehouse, CDC       |
# | Iceberg | Yes      | Yes  | Yes         | Full             | Multi-engine (Spark) |
# Default: Parquet. Upgrade to Iceberg when you need ACID or schema evolution.

def write_iceberg_table(spark: SparkSession, df: DataFrame, table: str) -> None:
    (df.writeTo(f"glue_catalog.analytics.{table}").using("iceberg")
       .tableProperty("write.format.default", "parquet")
       .tableProperty("write.parquet.compression-codec", "zstd")
       .partitionedBy("date").createOrReplace())
```

### AWS Glue Catalog Integration
```python
def register_table_in_glue(database: str, table_name: str, s3_location: str,
                            columns: list[dict], partition_keys: list[dict]) -> None:
    """Register Hive-partitioned table in Glue for Athena queries."""
    boto3.client("glue").create_table(DatabaseName=database, TableInput={
        "Name": table_name,
        "StorageDescriptor": {
            "Columns": columns,
            "Location": s3_location,
            "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
            "SerdeInfo": {"SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"},
        },
        "PartitionKeys": partition_keys,
        "TableType": "EXTERNAL_TABLE",
    })

def add_partition_to_glue(database: str, table_name: str,
                           values: list[str], s3_location: str) -> None:
    """Register new partition so Athena can query it immediately."""
    glue = boto3.client("glue")
    table = glue.get_table(DatabaseName=database, Name=table_name)["Table"]
    glue.create_partition(DatabaseName=database, TableName=table_name, PartitionInput={
        "Values": values,
        "StorageDescriptor": {**table["StorageDescriptor"], "Location": s3_location},
    })

# Athena: SELECT symbol, SUM(quantity) FROM analytics.trades WHERE date='2025-01-15' GROUP BY symbol
```

## Quality Checklist

- [ ] Pipeline is idempotent — same input always produces same output
- [ ] All input data validated at ingestion (schema + quality checks)
- [ ] Quality tests written BEFORE pipeline code (TDD)
- [ ] Failed records go to dead letter queue (not dropped)
- [ ] File writes are atomic (write-to-temp + rename)
- [ ] Partitioning strategy matches query patterns
- [ ] Checkpointing enables resumable processing after failure
- [ ] Pipeline stats logged (extracted, valid, invalid, loaded)
- [ ] Data stores and queues are attached backing services (12-Factor IV)
- [ ] Kafka consumers use manual offset commit for at-least-once delivery
- [ ] Spark jobs use partition pruning and avoid unnecessary shuffles
- [ ] Airflow DAGs have retry policies, timeouts, and quality gates
- [ ] dbt models have uniqueness and not-null tests on key columns
- [ ] PII fields are classified and masked before analytics layer
- [ ] Lineage events emitted for every pipeline run
- [ ] Glue catalog updated when new partitions land
- [ ] S3 files compacted to 128MB-1GB target size

## Anti-Patterns

- Append-only without deduplication (re-run creates duplicates)
- Validating data only at end of pipeline (garbage in, garbage out)
- Dropping invalid records silently (you will never know data is missing)
- No partition strategy — one giant file that grows forever
- Testing only happy-path data (test with malformed, missing, duplicate)
- Backfilling without concurrency limits (overloads source systems)
- Mutable pipeline state (shared variables between runs)
- No checkpointing — every failure means starting over
- Hard-coding broker URLs or bucket names instead of reading from config
- Auto-committing Kafka offsets before processing (data loss on crash)
- Using `repartition()` when `coalesce()` suffices (unnecessary shuffle)
- Partitioning S3 by high-cardinality keys (millions of tiny directories)
- Running Spark `collect()` on large datasets (OOM on driver)
- Airflow DAGs with no `max_active_runs` (overlapping runs corrupt data)
- Skipping schema registry — producers and consumers disagree on format
- No retention policy — storage costs grow unbounded
