# Core Data Models and Types Summary

This document summarizes the comprehensive core data models and types defined for the Hyperliquid Trading Bot Suite.

## 📊 Core Type Definitions (`src/types/__init__.py`)

### Trading Enums
- **OrderSide**: `BUY`, `SELL`, `LONG`, `SHORT`
- **TradeDirection**: `LONG`, `SHORT` (alias for OrderSide)  
- **OrderType**: `MARKET`, `LIMIT`, `STOP`, `STOP_LIMIT`, `STOP_LOSS`, `TAKE_PROFIT`
- **OrderStatus**: `PENDING`, `FILLED`, `PARTIAL`, `CANCELLED`, `REJECTED`, `EXPIRED`
- **TradingMode**: `PAPER`, `LIVE`, `BACKTEST`
- **Timeframe**: `M1`, `M5`, `M15`, `M30`, `H1`, `H4`, `H12`, `D1`, `W1`

### Strategy Enums  
- **EntryType**: `LE`, `SMALL_WICK`, `STEEPER_WICK`, `CELERY`, `BREAKOUT`, `FAKEOUT`, `ONION`
- **PatternType**: `CANDLE`, `STRUCTURE`, `ZONE`, `CYCLE`, `CONFLUENCE`
- **MarketCycle**: `DRIVE`, `RANGE`, `LIQUIDITY`
- **ExitReason**: `TP1`, `TP2`, `TP3`, `STOP_LOSS`, `BREAKEVEN`, `MOMENTUM`, `TIME_STOP`, `MANUAL`
- **TradeOutcome**: `WIN`, `LOSS`, `BREAKEVEN`, `PENDING`
- **SourceType**: `PDF`, `VIDEO`, `MANUAL`, `SYSTEM`

## 🏗️ Core Data Classes

### Market Data
- **CandleData**: OHLCV data with timeframe, computed properties (body_size, wicks, etc.)
- **MarketData**: Real-time market data (bid/ask/last, volume, funding rates)
- **PriceActionSnapshot**: Multi-timeframe context with structure notes

### Strategy System
- **StrategyRule**: Complete strategy definition with conditions, confluence, risk params
- **PatternCondition**: Individual pattern detection conditions with parameters
- **TimeframeAlignment**: Multi-timeframe confluence requirements  
- **RiskParameters**: Risk management settings (risk%, TP levels, SL distance)

### Trading Execution
- **TradeRecord**: Complete trade execution record with P&L, reasoning, context
- **Position**: Current position tracking (size, PnL, risk management)
- **Order**: Order management with status tracking
- **Trade**: Individual trade execution details

### Learning System
- **LearningEntry**: Knowledge base insights from trade outcomes
- **PatternDetection**: Detected patterns with confidence scores
- **MarketStructure**: Structure analysis (HH, LL, support/resistance)

### Backtesting
- **BacktestConfig**: Backtest configuration (dates, assets, strategy rules)  
- **BacktestResult**: Complete backtest results with performance metrics

### Content Ingestion
- **IngestionSource**: Content source tracking (PDF/video processing)
- **VideoFrame**: Extracted video frames for analysis

## 🔗 Pydantic API Models (`src/types/pydantic_models.py`)

### API Validation Models
- **BaseAPIModel**: Common configuration for all Pydantic models
- **CandleDataModel**: Validated OHLCV data with price relationship checks
- **StrategyRuleModel**: API model for strategy rules with comprehensive validation
- **TradeRecordModel**: Complete trade record with validation
- **MarketDataModel**: Validated market data with spread checks

### Request/Response Models
- **StrategyRuleCreateModel**: Strategy creation requests
- **StrategyRuleUpdateModel**: Strategy update requests  
- **BacktestCreateModel**: Backtest creation requests
- **APIResponseModel**: Standard API responses
- **PaginatedResponseModel**: Paginated API responses

### Risk Management
- **RiskParametersModel**: Validated risk management parameters
- **TimeframeAlignmentModel**: Multi-timeframe validation
- **PatternConditionModel**: Pattern condition validation

## 💾 Database Models (`src/database/models.py`)

### SQLAlchemy ORM Models
- **StrategyRuleDB**: Strategy rules with performance tracking
- **TradeRecordDB**: Trade records with P&L and context
- **LearningEntryDB**: Learning insights with validation tracking
- **CandleDataDB**: Time series candle data with constraints
- **BacktestConfigDB** / **BacktestResultDB**: Backtesting data
- **IngestionTaskDB**: Content processing task tracking

### Database Features
- **TimestampMixin**: Automatic created_at/updated_at tracking
- **Comprehensive Constraints**: Price validation, date ranges, positive values
- **Performance Indexes**: Optimized queries for time series and performance data
- **Foreign Key Relationships**: Proper relational structure

## 🧠 Knowledge Base Models (`src/knowledge/models.py`)

### Specialized Knowledge Models
- **ContentSource**: Source tracking for strategy extraction
- **StrategyPerformance**: Performance metrics and statistics
- **LearningEntry**: AI-generated insights with validation
- **IngestPDFRequest** / **IngestVideoRequest**: Content processing requests

## ✅ Key Features Implemented

1. **Type Safety**: Comprehensive enum definitions for all trading concepts
2. **Data Validation**: Pydantic models with extensive validation rules
3. **Relationship Modeling**: Proper foreign key relationships and constraints  
4. **Performance Tracking**: Built-in metrics and performance monitoring
5. **Multi-Timeframe Support**: Native support for timeframe alignment and confluence
6. **Learning System**: Knowledge base for continuous improvement
7. **Risk Management**: Integrated risk parameters and validation
8. **Backtesting Support**: Complete backtesting configuration and results
9. **Content Ingestion**: PDF and video processing capabilities
10. **API Ready**: Request/response models for REST API integration

## 🔧 Fixed Issues

- ✅ Added missing `TradeDirection` enum (aliased to `OrderSide`)
- ✅ Resolved import inconsistencies across modules
- ✅ Verified all model files compile without syntax errors
- ✅ Ensured proper type exports in `__all__` lists

## 📝 Notes

The core data models provide a comprehensive foundation for:
- Strategy rule definition and management
- Real-time trading execution
- Performance tracking and analytics  
- Multi-timeframe pattern detection
- Risk management and position sizing
- Learning and adaptation capabilities
- Backtesting and historical analysis
- Content ingestion and knowledge extraction

All models are designed with proper validation, relationships, and extensibility for future enhancements.