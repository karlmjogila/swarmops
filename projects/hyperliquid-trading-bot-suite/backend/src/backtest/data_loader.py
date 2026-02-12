"""
Data loader for backtesting engine.

This module provides efficient loading and processing of historical market data
for backtesting purposes. It supports multiple assets and timeframes with
optimized data access patterns.
"""

from typing import Dict, List, Optional, Tuple, Iterator, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
import logging

from ..types import CandleData, Timeframe, BacktestConfig
from ..database.models import CandleDataDB, Base
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class DataRange:
    """Represents a data range request."""
    asset: str
    timeframe: Timeframe
    start_date: datetime
    end_date: datetime


class DataLoader:
    """
    Efficient data loader for backtesting engine.
    
    Features:
    - Multi-asset, multi-timeframe support
    - Memory-efficient data streaming
    - Data validation and gap detection
    - Caching for performance optimization
    - Support for missing data handling
    """
    
    def __init__(self, session: Session, cache_size: int = 10000):
        """
        Initialize data loader.
        
        Args:
            session: Database session
            cache_size: Maximum number of candles to cache per asset/timeframe
        """
        self.session = session
        self.cache_size = cache_size
        self._data_cache: Dict[str, List[CandleData]] = {}
        self._cache_metadata: Dict[str, Dict[str, datetime]] = {}
        
    def _cache_key(self, asset: str, timeframe: Timeframe) -> str:
        """Generate cache key for asset/timeframe combination."""
        return f"{asset}_{timeframe.value}"
    
    def load_data_for_backtest(self, config: BacktestConfig) -> Dict[str, Dict[Timeframe, List[CandleData]]]:
        """
        Load all data needed for a backtest configuration.
        
        Args:
            config: Backtest configuration specifying assets, timeframes, and date range
            
        Returns:
            Dictionary with structure: {asset: {timeframe: [CandleData]}}
            
        Raises:
            ValueError: If data is missing or invalid
        """
        logger.info(f"Loading backtest data for {len(config.assets)} assets, {len(config.timeframes)} timeframes")
        logger.info(f"Date range: {config.start_date} to {config.end_date}")
        
        result = {}
        data_ranges = []
        
        # Create data range requests
        for asset in config.assets:
            result[asset] = {}
            for timeframe in config.timeframes:
                data_ranges.append(DataRange(
                    asset=asset,
                    timeframe=timeframe,
                    start_date=config.start_date,
                    end_date=config.end_date
                ))
        
        # Load data for each range
        for data_range in data_ranges:
            candles = self.load_candles(
                asset=data_range.asset,
                timeframe=data_range.timeframe,
                start_date=data_range.start_date,
                end_date=data_range.end_date
            )
            
            if not candles:
                logger.warning(f"No data found for {data_range.asset} {data_range.timeframe.value}")
                candles = []
            
            result[data_range.asset][data_range.timeframe] = candles
            logger.info(f"Loaded {len(candles)} candles for {data_range.asset} {data_range.timeframe.value}")
        
        # Validate data coverage
        self._validate_data_coverage(result, config)
        
        return result
    
    def load_candles(
        self,
        asset: str,
        timeframe: Timeframe,
        start_date: datetime,
        end_date: datetime,
        use_cache: bool = True
    ) -> List[CandleData]:
        """
        Load candle data for a specific asset and timeframe.
        
        Args:
            asset: Trading asset (e.g., 'BTC-USD')
            timeframe: Timeframe (e.g., Timeframe.M15)
            start_date: Start date for data
            end_date: End date for data
            use_cache: Whether to use cached data
            
        Returns:
            List of CandleData objects sorted by timestamp
        """
        cache_key = self._cache_key(asset, timeframe)
        
        # Check cache first
        if use_cache and self._is_data_cached(cache_key, start_date, end_date):
            logger.debug(f"Using cached data for {asset} {timeframe.value}")
            return self._get_cached_data(cache_key, start_date, end_date)
        
        # Query database
        logger.debug(f"Querying database for {asset} {timeframe.value} from {start_date} to {end_date}")
        
        query = self.session.query(CandleDataDB).filter(
            and_(
                CandleDataDB.asset == asset,
                CandleDataDB.timeframe == timeframe.value,
                CandleDataDB.timestamp >= start_date,
                CandleDataDB.timestamp <= end_date
            )
        ).order_by(asc(CandleDataDB.timestamp))
        
        candle_records = query.all()
        
        # Convert to CandleData objects
        candles = []
        for record in candle_records:
            candle = CandleData(
                timestamp=record.timestamp,
                open=record.open,
                high=record.high,
                low=record.low,
                close=record.close,
                volume=record.volume,
                timeframe=timeframe
            )
            candles.append(candle)
        
        # Cache the results
        if use_cache and candles:
            self._cache_data(cache_key, candles, start_date, end_date)
        
        return candles
    
    def load_candles_streaming(
        self,
        asset: str,
        timeframe: Timeframe,
        start_date: datetime,
        end_date: datetime,
        batch_size: int = 1000
    ) -> Iterator[List[CandleData]]:
        """
        Stream candle data in batches for memory-efficient processing.
        
        Args:
            asset: Trading asset
            timeframe: Timeframe
            start_date: Start date
            end_date: End date
            batch_size: Number of candles per batch
            
        Yields:
            Batches of CandleData objects
        """
        logger.debug(f"Streaming data for {asset} {timeframe.value} in batches of {batch_size}")
        
        offset = 0
        while True:
            query = self.session.query(CandleDataDB).filter(
                and_(
                    CandleDataDB.asset == asset,
                    CandleDataDB.timeframe == timeframe.value,
                    CandleDataDB.timestamp >= start_date,
                    CandleDataDB.timestamp <= end_date
                )
            ).order_by(asc(CandleDataDB.timestamp)).offset(offset).limit(batch_size)
            
            candle_records = query.all()
            
            if not candle_records:
                break
            
            # Convert to CandleData objects
            candles = []
            for record in candle_records:
                candle = CandleData(
                    timestamp=record.timestamp,
                    open=record.open,
                    high=record.high,
                    low=record.low,
                    close=record.close,
                    volume=record.volume,
                    timeframe=timeframe
                )
                candles.append(candle)
            
            yield candles
            
            if len(candle_records) < batch_size:
                break
            
            offset += batch_size
    
    def get_latest_candle(self, asset: str, timeframe: Timeframe) -> Optional[CandleData]:
        """
        Get the most recent candle for an asset/timeframe.
        
        Args:
            asset: Trading asset
            timeframe: Timeframe
            
        Returns:
            Latest CandleData or None if no data exists
        """
        query = self.session.query(CandleDataDB).filter(
            and_(
                CandleDataDB.asset == asset,
                CandleDataDB.timeframe == timeframe.value
            )
        ).order_by(desc(CandleDataDB.timestamp)).limit(1)
        
        record = query.first()
        if not record:
            return None
        
        return CandleData(
            timestamp=record.timestamp,
            open=record.open,
            high=record.high,
            low=record.low,
            close=record.close,
            volume=record.volume,
            timeframe=timeframe
        )
    
    def get_data_availability(self, asset: str, timeframe: Timeframe) -> Optional[Tuple[datetime, datetime]]:
        """
        Get the available date range for an asset/timeframe.
        
        Args:
            asset: Trading asset
            timeframe: Timeframe
            
        Returns:
            Tuple of (earliest_date, latest_date) or None if no data
        """
        query = self.session.query(
            CandleDataDB.timestamp
        ).filter(
            and_(
                CandleDataDB.asset == asset,
                CandleDataDB.timeframe == timeframe.value
            )
        )
        
        earliest = query.order_by(asc(CandleDataDB.timestamp)).first()
        latest = query.order_by(desc(CandleDataDB.timestamp)).first()
        
        if not earliest or not latest:
            return None
        
        return (earliest.timestamp, latest.timestamp)
    
    def detect_data_gaps(
        self,
        asset: str,
        timeframe: Timeframe,
        start_date: datetime,
        end_date: datetime
    ) -> List[Tuple[datetime, datetime]]:
        """
        Detect gaps in data coverage.
        
        Args:
            asset: Trading asset
            timeframe: Timeframe
            start_date: Start date to check
            end_date: End date to check
            
        Returns:
            List of (gap_start, gap_end) tuples
        """
        candles = self.load_candles(asset, timeframe, start_date, end_date, use_cache=False)
        
        if not candles:
            return [(start_date, end_date)]
        
        gaps = []
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        expected_interval = timedelta(minutes=timeframe_minutes)
        
        for i in range(1, len(candles)):
            prev_candle = candles[i - 1]
            current_candle = candles[i]
            
            expected_next_time = prev_candle.timestamp + expected_interval
            actual_time = current_candle.timestamp
            
            if actual_time > expected_next_time:
                gaps.append((expected_next_time, actual_time - expected_interval))
        
        return gaps
    
    def validate_data_quality(
        self,
        asset: str,
        timeframe: Timeframe,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, any]:
        """
        Validate data quality and return metrics.
        
        Args:
            asset: Trading asset
            timeframe: Timeframe
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with quality metrics
        """
        candles = self.load_candles(asset, timeframe, start_date, end_date, use_cache=False)
        
        if not candles:
            return {
                'total_candles': 0,
                'data_completeness': 0.0,
                'gaps': [],
                'invalid_candles': 0,
                'quality_score': 0.0
            }
        
        # Check for invalid candles
        invalid_candles = 0
        for candle in candles:
            if (candle.high < candle.low or 
                candle.high < candle.open or 
                candle.high < candle.close or
                candle.low > candle.open or 
                candle.low > candle.close or
                candle.volume < 0):
                invalid_candles += 1
        
        # Detect gaps
        gaps = self.detect_data_gaps(asset, timeframe, start_date, end_date)
        
        # Calculate expected number of candles
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        total_minutes = (end_date - start_date).total_seconds() / 60
        expected_candles = int(total_minutes / timeframe_minutes)
        
        # Data completeness
        data_completeness = len(candles) / expected_candles if expected_candles > 0 else 0.0
        
        # Overall quality score (0.0 to 1.0)
        quality_score = data_completeness * (1 - min(invalid_candles / len(candles), 1.0))
        
        return {
            'total_candles': len(candles),
            'expected_candles': expected_candles,
            'data_completeness': data_completeness,
            'gaps': gaps,
            'gap_count': len(gaps),
            'invalid_candles': invalid_candles,
            'quality_score': quality_score
        }
    
    def _validate_data_coverage(self, data: Dict[str, Dict[Timeframe, List[CandleData]]], config: BacktestConfig):
        """Validate that loaded data meets minimum requirements."""
        for asset in config.assets:
            for timeframe in config.timeframes:
                candles = data.get(asset, {}).get(timeframe, [])
                
                if not candles:
                    logger.warning(f"No data available for {asset} {timeframe.value}")
                    continue
                
                # Check date coverage
                first_candle = candles[0]
                last_candle = candles[-1]
                
                if first_candle.timestamp > config.start_date + timedelta(days=1):
                    logger.warning(f"Data starts late for {asset} {timeframe.value}: {first_candle.timestamp}")
                
                if last_candle.timestamp < config.end_date - timedelta(days=1):
                    logger.warning(f"Data ends early for {asset} {timeframe.value}: {last_candle.timestamp}")
    
    def _is_data_cached(self, cache_key: str, start_date: datetime, end_date: datetime) -> bool:
        """Check if data is available in cache for the requested range."""
        if cache_key not in self._cache_metadata:
            return False
        
        metadata = self._cache_metadata[cache_key]
        cached_start = metadata.get('start_date')
        cached_end = metadata.get('end_date')
        
        return (cached_start and cached_end and 
                cached_start <= start_date and 
                cached_end >= end_date)
    
    def _get_cached_data(self, cache_key: str, start_date: datetime, end_date: datetime) -> List[CandleData]:
        """Get data from cache for the specified range."""
        cached_candles = self._data_cache.get(cache_key, [])
        
        # Filter to the requested range
        filtered_candles = [
            candle for candle in cached_candles
            if start_date <= candle.timestamp <= end_date
        ]
        
        return filtered_candles
    
    def _cache_data(self, cache_key: str, candles: List[CandleData], start_date: datetime, end_date: datetime):
        """Cache candle data."""
        # Limit cache size
        if len(candles) > self.cache_size:
            candles = candles[-self.cache_size:]  # Keep most recent
        
        self._data_cache[cache_key] = candles
        self._cache_metadata[cache_key] = {
            'start_date': start_date,
            'end_date': end_date,
            'cached_at': datetime.utcnow()
        }
    
    def _get_timeframe_minutes(self, timeframe: Timeframe) -> int:
        """Get timeframe duration in minutes."""
        timeframe_map = {
            Timeframe.M1: 1,
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.M30: 30,
            Timeframe.H1: 60,
            Timeframe.H4: 240,
            Timeframe.H12: 720,
            Timeframe.D1: 1440,
            Timeframe.W1: 10080
        }
        return timeframe_map.get(timeframe, 15)  # Default to 15 minutes
    
    def clear_cache(self):
        """Clear all cached data."""
        self._data_cache.clear()
        self._cache_metadata.clear()
        logger.debug("Data cache cleared")
    
    def get_cache_info(self) -> Dict[str, any]:
        """Get information about cached data."""
        total_candles = sum(len(candles) for candles in self._data_cache.values())
        
        return {
            'cached_series': len(self._data_cache),
            'total_cached_candles': total_candles,
            'cache_keys': list(self._data_cache.keys()),
            'cache_metadata': self._cache_metadata
        }


class BacktestDataManager:
    """
    High-level data manager for backtesting.
    
    Provides convenient methods for managing data during backtesting,
    including data validation, preprocessing, and efficient access patterns.
    """
    
    def __init__(self, session: Session):
        """
        Initialize backtest data manager.
        
        Args:
            session: Database session
        """
        self.session = session
        self.data_loader = DataLoader(session)
        self._loaded_data: Optional[Dict[str, Dict[Timeframe, List[CandleData]]]] = None
        self._current_config: Optional[BacktestConfig] = None
    
    def prepare_backtest_data(self, config: BacktestConfig) -> Dict[str, any]:
        """
        Prepare and validate data for backtesting.
        
        Args:
            config: Backtest configuration
            
        Returns:
            Data preparation report
        """
        logger.info("Preparing backtest data...")
        
        self._current_config = config
        
        # Validate data availability
        availability_report = self._check_data_availability(config)
        
        # Load data
        self._loaded_data = self.data_loader.load_data_for_backtest(config)
        
        # Generate quality report
        quality_report = self._generate_quality_report(config)
        
        return {
            'config': config,
            'availability': availability_report,
            'quality': quality_report,
            'data_loaded': True
        }
    
    def get_candles_at_time(
        self,
        asset: str,
        timeframe: Timeframe,
        timestamp: datetime,
        lookback_count: int = 100
    ) -> List[CandleData]:
        """
        Get candles for an asset/timeframe at a specific time.
        
        Args:
            asset: Trading asset
            timeframe: Timeframe
            timestamp: Reference timestamp
            lookback_count: Number of previous candles to include
            
        Returns:
            List of CandleData objects up to the timestamp
        """
        if not self._loaded_data or asset not in self._loaded_data:
            raise ValueError(f"Data not loaded for asset: {asset}")
        
        if timeframe not in self._loaded_data[asset]:
            raise ValueError(f"Data not loaded for timeframe: {timeframe.value}")
        
        candles = self._loaded_data[asset][timeframe]
        
        # Find candles up to the timestamp
        valid_candles = [c for c in candles if c.timestamp <= timestamp]
        
        # Return the most recent lookback_count candles
        return valid_candles[-lookback_count:] if valid_candles else []
    
    def get_available_assets(self) -> List[str]:
        """Get list of assets with loaded data."""
        return list(self._loaded_data.keys()) if self._loaded_data else []
    
    def get_available_timeframes(self, asset: str) -> List[Timeframe]:
        """Get list of timeframes available for an asset."""
        if not self._loaded_data or asset not in self._loaded_data:
            return []
        return list(self._loaded_data[asset].keys())
    
    def _check_data_availability(self, config: BacktestConfig) -> Dict[str, any]:
        """Check data availability for backtest configuration."""
        availability = {}
        
        for asset in config.assets:
            availability[asset] = {}
            for timeframe in config.timeframes:
                range_info = self.data_loader.get_data_availability(asset, timeframe)
                
                if range_info:
                    earliest, latest = range_info
                    available = (earliest <= config.start_date and 
                               latest >= config.end_date)
                else:
                    earliest = latest = None
                    available = False
                
                availability[asset][timeframe.value] = {
                    'available': available,
                    'earliest_date': earliest,
                    'latest_date': latest
                }
        
        return availability
    
    def _generate_quality_report(self, config: BacktestConfig) -> Dict[str, any]:
        """Generate data quality report."""
        quality_report = {}
        
        for asset in config.assets:
            quality_report[asset] = {}
            for timeframe in config.timeframes:
                quality_metrics = self.data_loader.validate_data_quality(
                    asset, timeframe, config.start_date, config.end_date
                )
                quality_report[asset][timeframe.value] = quality_metrics
        
        return quality_report


# Export main classes
__all__ = [
    "DataLoader",
    "BacktestDataManager", 
    "DataRange"
]