"""OHLCV data repository.

Provides clean data access for OHLCV candlestick data.
All queries are optimized for TimescaleDB hypertables.
"""
from datetime import datetime, timezone
from typing import Optional, List, Literal
from sqlalchemy import desc, asc, and_, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import OHLCVData


# Valid data sources
DataSource = Literal['hyperliquid', 'csv', 'auto']


class OHLCVRepository:
    """Repository for OHLCV data access.
    
    Follows repository pattern to keep database logic separate from business logic.
    All methods use parameterized queries (no SQL injection risk).
    """
    
    def __init__(self, db: Session):
        """Initialize repository with database session.
        
        Args:
            db: SQLAlchemy session from dependency injection
        """
        self._db = db
    
    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        limit: Optional[int] = None,
        source: Optional[DataSource] = None,
    ) -> List[OHLCVData]:
        """Get OHLCV candles for a symbol and timeframe within time range.
        
        Args:
            symbol: Trading pair (e.g., "BTC-USD")
            timeframe: Candle timeframe (e.g., "5m", "15m", "1h")
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            limit: Optional maximum number of candles to return
            source: Data source filter ('hyperliquid', 'csv', 'auto', or None for all)
                    'auto' prefers hyperliquid, falls back to csv
            
        Returns:
            List of OHLCV candles ordered by timestamp ascending
            
        Example:
            >>> candles = repo.get_candles(
            ...     "BTC-USD", "15m",
            ...     datetime(2024, 1, 1),
            ...     datetime(2024, 1, 2),
            ...     source='hyperliquid'
            ... )
        """
        base_filters = [
            OHLCVData.symbol == symbol,
            OHLCVData.timeframe == timeframe,
            OHLCVData.timestamp >= start_time,
            OHLCVData.timestamp <= end_time,
        ]
        
        if source == 'auto':
            # Try hyperliquid first
            hl_query = (
                self._db.query(OHLCVData)
                .filter(and_(*base_filters, OHLCVData.source == 'hyperliquid'))
                .order_by(asc(OHLCVData.timestamp))
            )
            if limit:
                hl_query = hl_query.limit(limit)
            candles = hl_query.all()
            
            # Fall back to csv if no hyperliquid data
            if not candles:
                csv_query = (
                    self._db.query(OHLCVData)
                    .filter(and_(*base_filters, OHLCVData.source == 'csv'))
                    .order_by(asc(OHLCVData.timestamp))
                )
                if limit:
                    csv_query = csv_query.limit(limit)
                candles = csv_query.all()
            
            return candles
        
        elif source and source != 'auto':
            base_filters.append(OHLCVData.source == source)
        
        query = (
            self._db.query(OHLCVData)
            .filter(and_(*base_filters))
            .order_by(asc(OHLCVData.timestamp))
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_latest_candle(
        self,
        symbol: str,
        timeframe: str,
        source: Optional[str] = None,
    ) -> Optional[OHLCVData]:
        """Get the most recent candle for a symbol and timeframe.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            source: Optional data source filter
            
        Returns:
            Latest OHLCV candle or None if no data exists
        """
        filters = [
            OHLCVData.symbol == symbol,
            OHLCVData.timeframe == timeframe,
        ]
        if source:
            filters.append(OHLCVData.source == source)
            
        return (
            self._db.query(OHLCVData)
            .filter(and_(*filters))
            .order_by(desc(OHLCVData.timestamp))
            .first()
        )
    
    def get_candles_since(
        self,
        symbol: str,
        timeframe: str,
        since: datetime,
    ) -> List[OHLCVData]:
        """Get all candles after a specific timestamp.
        
        Useful for incremental updates.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            since: Get candles after this timestamp
            
        Returns:
            List of OHLCV candles ordered by timestamp ascending
        """
        return (
            self._db.query(OHLCVData)
            .filter(
                and_(
                    OHLCVData.symbol == symbol,
                    OHLCVData.timeframe == timeframe,
                    OHLCVData.timestamp > since,
                )
            )
            .order_by(asc(OHLCVData.timestamp))
            .all()
        )
    
    def get_last_n_candles(
        self,
        symbol: str,
        timeframe: str,
        n: int,
    ) -> List[OHLCVData]:
        """Get the last N candles for a symbol and timeframe.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            n: Number of candles to return
            
        Returns:
            List of OHLCV candles ordered by timestamp ascending
        """
        # Query in descending order, then reverse to get ascending
        candles = (
            self._db.query(OHLCVData)
            .filter(
                and_(
                    OHLCVData.symbol == symbol,
                    OHLCVData.timeframe == timeframe,
                )
            )
            .order_by(desc(OHLCVData.timestamp))
            .limit(n)
            .all()
        )
        
        # Reverse to get chronological order
        return list(reversed(candles))
    
    def insert_candle(
        self,
        symbol: str,
        timeframe: str,
        timestamp: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float = 0.0,
        source: str = 'csv',
    ) -> Optional[OHLCVData]:
        """Insert a single OHLCV candle.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            timestamp: Candle timestamp
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Trade volume (default: 0.0)
            source: Data source ('hyperliquid' or 'csv', default: 'csv')
            
        Returns:
            Created OHLCV candle or None if duplicate
            
        Note:
            Silently ignores duplicates (same symbol + timeframe + timestamp + source).
            Database constraints validate price relationships (high >= low, etc.).
        """
        candle = OHLCVData(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            source=source,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            created_at=datetime.now(timezone.utc),
        )
        
        try:
            self._db.add(candle)
            self._db.flush()  # Flush to catch constraint violations
            return candle
        except IntegrityError:
            # Duplicate key - candle already exists
            self._db.rollback()
            return None
    
    def bulk_insert_candles(
        self,
        candles: List[dict],
        source: str = 'csv',
    ) -> int:
        """Bulk insert multiple candles efficiently.
        
        Uses batch insert for better performance on large datasets.
        Silently skips duplicates.
        
        Args:
            candles: List of dicts with keys:
                - symbol: str
                - timeframe: str
                - timestamp: datetime
                - open: float
                - high: float
                - low: float
                - close: float
                - volume: float (optional, default 0.0)
            source: Data source for all candles ('hyperliquid' or 'csv')
                
        Returns:
            Number of candles successfully inserted
            
        Example:
            >>> candles = [
            ...     {
            ...         "symbol": "BTC-USD",
            ...         "timeframe": "5m",
            ...         "timestamp": datetime(2024, 1, 1, 0, 0),
            ...         "open": 50000.0,
            ...         "high": 50100.0,
            ...         "low": 49900.0,
            ...         "close": 50050.0,
            ...         "volume": 100.0,
            ...     },
            ...     # ... more candles
            ... ]
            >>> count = repo.bulk_insert_candles(candles, source='csv')
        """
        if not candles:
            return 0
        
        inserted_count = 0
        now = datetime.now(timezone.utc)
        
        # Process in batches to avoid memory issues with huge imports
        batch_size = 1000
        for i in range(0, len(candles), batch_size):
            batch = candles[i:i + batch_size]
            
            # Prepare objects for bulk insert
            candle_objects = [
                OHLCVData(
                    symbol=c["symbol"],
                    timeframe=c["timeframe"],
                    timestamp=c["timestamp"],
                    source=source,
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                    volume=c.get("volume", 0.0),
                    created_at=now,
                )
                for c in batch
            ]
            
            try:
                self._db.bulk_save_objects(candle_objects)
                self._db.flush()
                inserted_count += len(batch)
            except IntegrityError:
                # Some duplicates in batch - fall back to individual inserts
                self._db.rollback()
                for candle_dict in batch:
                    # Convert 'open' to 'open_price' for insert_candle signature
                    insert_args = {
                        "symbol": candle_dict["symbol"],
                        "timeframe": candle_dict["timeframe"],
                        "timestamp": candle_dict["timestamp"],
                        "open_price": candle_dict["open"],
                        "high": candle_dict["high"],
                        "low": candle_dict["low"],
                        "close": candle_dict["close"],
                        "volume": candle_dict.get("volume", 0.0),
                        "source": source,
                    }
                    result = self.insert_candle(**insert_args)
                    if result:
                        inserted_count += 1
        
        return inserted_count
    
    def delete_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Delete candles within a time range.
        
        Useful for data cleanup or re-importing corrected data.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            start_time: Optional start of time range
            end_time: Optional end of time range
            
        Returns:
            Number of candles deleted
            
        Warning:
            If both start_time and end_time are None, deletes ALL candles
            for the symbol and timeframe.
        """
        query = self._db.query(OHLCVData).filter(
            and_(
                OHLCVData.symbol == symbol,
                OHLCVData.timeframe == timeframe,
            )
        )
        
        if start_time:
            query = query.filter(OHLCVData.timestamp >= start_time)
        if end_time:
            query = query.filter(OHLCVData.timestamp <= end_time)
        
        count = query.count()
        query.delete(synchronize_session=False)
        return count
    
    def get_available_symbols(self, timeframe: Optional[str] = None) -> List[str]:
        """Get list of all symbols with data.
        
        Args:
            timeframe: Optional filter by timeframe
            
        Returns:
            List of unique symbols
        """
        query = self._db.query(OHLCVData.symbol).distinct()
        
        if timeframe:
            query = query.filter(OHLCVData.timeframe == timeframe)
        
        return [row[0] for row in query.all()]
    
    def get_available_timeframes(self, symbol: Optional[str] = None) -> List[str]:
        """Get list of all timeframes with data.
        
        Args:
            symbol: Optional filter by symbol
            
        Returns:
            List of unique timeframes
        """
        query = self._db.query(OHLCVData.timeframe).distinct()
        
        if symbol:
            query = query.filter(OHLCVData.symbol == symbol)
        
        return [row[0] for row in query.all()]
    
    def get_time_range(
        self,
        symbol: str,
        timeframe: str,
    ) -> Optional[tuple[datetime, datetime]]:
        """Get the earliest and latest timestamp for a symbol and timeframe.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            
        Returns:
            Tuple of (earliest_timestamp, latest_timestamp) or None if no data
        """
        result = (
            self._db.query(
                func.min(OHLCVData.timestamp),
                func.max(OHLCVData.timestamp),
            )
            .filter(
                and_(
                    OHLCVData.symbol == symbol,
                    OHLCVData.timeframe == timeframe,
                )
            )
            .first()
        )
        
        if result and result[0] and result[1]:
            return (result[0], result[1])
        return None
    
    def count_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Count candles for a symbol and timeframe.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            start_time: Optional start of time range
            end_time: Optional end of time range
            
        Returns:
            Number of candles
        """
        query = self._db.query(func.count(OHLCVData.timestamp)).filter(
            and_(
                OHLCVData.symbol == symbol,
                OHLCVData.timeframe == timeframe,
            )
        )
        
        if start_time:
            query = query.filter(OHLCVData.timestamp >= start_time)
        if end_time:
            query = query.filter(OHLCVData.timestamp <= end_time)
        
        return query.scalar()
    
    def get_ohlc_aggregates(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[dict]:
        """Get aggregate statistics for a time range.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Dict with keys: min_low, max_high, total_volume, candle_count
            or None if no data
        """
        result = (
            self._db.query(
                func.min(OHLCVData.low),
                func.max(OHLCVData.high),
                func.sum(OHLCVData.volume),
                func.count(OHLCVData.timestamp),
            )
            .filter(
                and_(
                    OHLCVData.symbol == symbol,
                    OHLCVData.timeframe == timeframe,
                    OHLCVData.timestamp >= start_time,
                    OHLCVData.timestamp <= end_time,
                )
            )
            .first()
        )
        
        if result and result[3] > 0:  # Check candle_count
            return {
                "min_low": result[0],
                "max_high": result[1],
                "total_volume": result[2] or 0.0,
                "candle_count": result[3],
            }
        return None
    
    def get_data_availability_by_source(
        self,
        symbol: str,
        timeframe: str,
    ) -> dict:
        """Get data availability information for each source.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            
        Returns:
            Dict with source as key and availability info as value:
            {
                'hyperliquid': {
                    'available': True,
                    'earliest': '2024-01-01T00:00:00Z',
                    'latest': '2024-12-31T23:59:00Z',
                    'candle_count': 10000
                },
                'csv': {
                    'available': False,
                    'earliest': None,
                    'latest': None,
                    'candle_count': 0
                }
            }
        """
        result = {}
        
        for source in ['hyperliquid', 'csv']:
            # Get time range and count for this source
            range_result = (
                self._db.query(
                    func.min(OHLCVData.timestamp),
                    func.max(OHLCVData.timestamp),
                    func.count(OHLCVData.timestamp),
                )
                .filter(
                    and_(
                        OHLCVData.symbol == symbol,
                        OHLCVData.timeframe == timeframe,
                        OHLCVData.source == source,
                    )
                )
                .first()
            )
            
            if range_result and range_result[2] > 0:
                result[source] = {
                    'available': True,
                    'earliest': range_result[0].isoformat() if range_result[0] else None,
                    'latest': range_result[1].isoformat() if range_result[1] else None,
                    'candle_count': range_result[2],
                }
            else:
                result[source] = {
                    'available': False,
                    'earliest': None,
                    'latest': None,
                    'candle_count': 0,
                }
        
        return result
    
    def get_available_sources(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> List[str]:
        """Get list of all sources with data.
        
        Args:
            symbol: Optional filter by symbol
            timeframe: Optional filter by timeframe
            
        Returns:
            List of unique sources
        """
        query = self._db.query(OHLCVData.source).distinct()
        
        if symbol:
            query = query.filter(OHLCVData.symbol == symbol)
        if timeframe:
            query = query.filter(OHLCVData.timeframe == timeframe)
        
        return [row[0] for row in query.all()]
