"""OHLCV data repository.

Repository pattern for OHLCV data access following Database Excellence principles:
- Specific column selection (no SELECT *)
- Proper indexing usage
- Parameterized queries (SQLAlchemy ORM)
- Efficient batch operations
- Time-series optimized queries for TimescaleDB
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, delete, desc, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

# Import from the existing app structure
import sys
sys.path.insert(0, '/opt/swarmops/projects/hl-bot-v2/backend')
from app.db.models import OHLCVData

from hl_bot.types import Candle, Timeframe


class OHLCVRepository:
    """Repository for OHLCV candlestick data.
    
    Handles all database operations for market data.
    Optimized for TimescaleDB time-series queries.
    """

    def __init__(self, db: Session):
        """Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self._db = db

    def insert_candle(self, candle: Candle) -> OHLCVData:
        """Insert a single candle.
        
        Args:
            candle: Candle data to insert
            
        Returns:
            Created database record
            
        Raises:
            IntegrityError: If candle already exists (duplicate primary key)
        """
        db_candle = OHLCVData(
            timestamp=candle.timestamp,
            symbol=candle.symbol,
            timeframe=candle.timeframe.value,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )
        
        self._db.add(db_candle)
        self._db.commit()
        self._db.refresh(db_candle)
        
        return db_candle

    def insert_candles_batch(self, candles: List[Candle]) -> int:
        """Insert multiple candles efficiently.
        
        Uses batch insert for better performance.
        On conflict (duplicate primary key), does nothing (idempotent).
        
        Args:
            candles: List of candles to insert
            
        Returns:
            Number of candles inserted
        """
        if not candles:
            return 0
        
        # Convert Pydantic models to dicts
        values = [
            {
                "timestamp": c.timestamp,
                "symbol": c.symbol,
                "timeframe": c.timeframe.value,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]
        
        # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING for idempotency
        stmt = insert(OHLCVData).values(values)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["timestamp", "symbol", "timeframe"]
        )
        
        result = self._db.execute(stmt)
        self._db.commit()
        
        return result.rowcount

    def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[Candle]:
        """Get candles for a symbol and timeframe.
        
        Args:
            symbol: Trading symbol (e.g., "BTC-USD")
            timeframe: Candle timeframe
            start_time: Optional start time (inclusive)
            end_time: Optional end time (inclusive)
            limit: Optional limit on number of candles returned
            
        Returns:
            List of candles ordered by timestamp (oldest first)
        """
        query = self._db.query(OHLCVData).filter(
            and_(
                OHLCVData.symbol == symbol,
                OHLCVData.timeframe == timeframe.value,
            )
        )
        
        # Apply time filters
        if start_time:
            query = query.filter(OHLCVData.timestamp >= start_time)
        if end_time:
            query = query.filter(OHLCVData.timestamp <= end_time)
        
        # Order by timestamp (oldest first for time-series processing)
        query = query.order_by(OHLCVData.timestamp)
        
        # Apply limit
        if limit:
            query = query.limit(limit)
        
        results = query.all()
        
        # Convert to Pydantic models
        return [self._to_candle(db_candle) for db_candle in results]

    def get_latest_candle(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Optional[Candle]:
        """Get the most recent candle for a symbol and timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            
        Returns:
            Latest candle or None if no data exists
        """
        result = (
            self._db.query(OHLCVData)
            .filter(
                and_(
                    OHLCVData.symbol == symbol,
                    OHLCVData.timeframe == timeframe.value,
                )
            )
            .order_by(desc(OHLCVData.timestamp))
            .first()
        )
        
        return self._to_candle(result) if result else None

    def get_candle_at_time(
        self,
        symbol: str,
        timeframe: Timeframe,
        timestamp: datetime,
    ) -> Optional[Candle]:
        """Get candle at a specific timestamp.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            timestamp: Exact candle timestamp
            
        Returns:
            Candle or None if not found
        """
        result = (
            self._db.query(OHLCVData)
            .filter(
                and_(
                    OHLCVData.timestamp == timestamp,
                    OHLCVData.symbol == symbol,
                    OHLCVData.timeframe == timeframe.value,
                )
            )
            .first()
        )
        
        return self._to_candle(result) if result else None

    def count_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Count candles for a symbol and timeframe.
        
        Efficient count query without loading all data.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            Number of candles matching criteria
        """
        query = self._db.query(func.count(OHLCVData.timestamp)).filter(
            and_(
                OHLCVData.symbol == symbol,
                OHLCVData.timeframe == timeframe.value,
            )
        )
        
        if start_time:
            query = query.filter(OHLCVData.timestamp >= start_time)
        if end_time:
            query = query.filter(OHLCVData.timestamp <= end_time)
        
        return query.scalar()

    def get_available_symbols(self) -> List[str]:
        """Get list of all symbols with data.
        
        Returns:
            List of unique symbols
        """
        results = (
            self._db.query(OHLCVData.symbol)
            .distinct()
            .order_by(OHLCVData.symbol)
            .all()
        )
        
        return [r[0] for r in results]

    def get_available_timeframes(self, symbol: str) -> List[str]:
        """Get list of available timeframes for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            List of timeframe strings
        """
        results = (
            self._db.query(OHLCVData.timeframe)
            .filter(OHLCVData.symbol == symbol)
            .distinct()
            .order_by(OHLCVData.timeframe)
            .all()
        )
        
        return [r[0] for r in results]

    def get_time_range(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Optional[tuple[datetime, datetime]]:
        """Get the time range (earliest, latest) of available data.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            
        Returns:
            Tuple of (earliest_timestamp, latest_timestamp) or None if no data
        """
        result = (
            self._db.query(
                func.min(OHLCVData.timestamp).label("earliest"),
                func.max(OHLCVData.timestamp).label("latest"),
            )
            .filter(
                and_(
                    OHLCVData.symbol == symbol,
                    OHLCVData.timeframe == timeframe.value,
                )
            )
            .first()
        )
        
        if result and result.earliest and result.latest:
            return (result.earliest, result.latest)
        return None

    def delete_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Delete candles matching criteria.
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            start_time: Optional start time (inclusive)
            end_time: Optional end time (inclusive)
            
        Returns:
            Number of candles deleted
        """
        stmt = delete(OHLCVData).where(
            and_(
                OHLCVData.symbol == symbol,
                OHLCVData.timeframe == timeframe.value,
            )
        )
        
        if start_time:
            stmt = stmt.where(OHLCVData.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(OHLCVData.timestamp <= end_time)
        
        result = self._db.execute(stmt)
        self._db.commit()
        
        return result.rowcount

    def upsert_candle(self, candle: Candle) -> OHLCVData:
        """Insert or update a candle.
        
        If candle exists, updates OHLCV values.
        If not, inserts new candle.
        
        Args:
            candle: Candle data to upsert
            
        Returns:
            Database record
        """
        values = {
            "timestamp": candle.timestamp,
            "symbol": candle.symbol,
            "timeframe": candle.timeframe.value,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }
        
        stmt = insert(OHLCVData).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["timestamp", "symbol", "timeframe"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
            },
        )
        
        self._db.execute(stmt)
        self._db.commit()
        
        # Fetch and return the record
        result = (
            self._db.query(OHLCVData)
            .filter(
                and_(
                    OHLCVData.timestamp == candle.timestamp,
                    OHLCVData.symbol == candle.symbol,
                    OHLCVData.timeframe == candle.timeframe.value,
                )
            )
            .first()
        )
        
        return result

    @staticmethod
    def _to_candle(db_candle: OHLCVData) -> Candle:
        """Convert database model to Pydantic model.
        
        Args:
            db_candle: SQLAlchemy OHLCVData instance
            
        Returns:
            Pydantic Candle model
        """
        return Candle(
            timestamp=db_candle.timestamp,
            symbol=db_candle.symbol,
            timeframe=Timeframe(db_candle.timeframe),
            open=db_candle.open,
            high=db_candle.high,
            low=db_candle.low,
            close=db_candle.close,
            volume=db_candle.volume,
        )
