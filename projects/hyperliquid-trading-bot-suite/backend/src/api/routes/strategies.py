"""Strategy management endpoints."""

from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
import structlog

from ...database import get_db
from ...database.models import StrategyRuleDB, TradeRecordDB
from ...types import SourceType, EntryType

router = APIRouter()
logger = structlog.get_logger()


class StrategyRule(BaseModel):
    """Strategy rule model for API responses."""
    id: str
    name: str
    description: Optional[str] = None
    entry_type: str
    conditions: List[Dict[str, Any]]
    confluence_required: List[Dict[str, Any]]
    risk_params: Dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    source_type: str
    source_ref: str
    created_at: str
    last_used: Optional[str] = None
    win_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    total_trades: int = Field(ge=0, default=0)
    enabled: bool = True
    tags: List[str] = []
    
    class Config:
        from_attributes = True


class StrategyPerformance(BaseModel):
    """Strategy performance metrics."""
    strategy_id: str
    total_trades: int = Field(ge=0)
    winning_trades: int = Field(ge=0)
    losing_trades: int = Field(ge=0)
    win_rate: float = Field(ge=0.0, le=1.0)
    profit_factor: float = Field(ge=0.0)
    avg_win_r: float
    avg_loss_r: float
    max_consecutive_losses: int = Field(ge=0)
    avg_r_multiple: float
    total_pnl_r: float


class StrategyCreateRequest(BaseModel):
    """Request model for creating a strategy."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    entry_type: str
    conditions: List[Dict[str, Any]]
    confluence_required: List[Dict[str, Any]] = []
    risk_params: Dict[str, Any]
    source_type: str
    source_ref: str
    tags: List[str] = []
    
    @validator('entry_type')
    def validate_entry_type(cls, v):
        valid_types = [e.value for e in EntryType]
        if v not in valid_types:
            raise ValueError(f"Invalid entry_type. Must be one of: {', '.join(valid_types)}")
        return v
    
    @validator('source_type')
    def validate_source_type(cls, v):
        valid_types = [e.value for e in SourceType]
        if v not in valid_types:
            raise ValueError(f"Invalid source_type. Must be one of: {', '.join(valid_types)}")
        return v


def _serialize_strategy(strategy_db: StrategyRuleDB) -> StrategyRule:
    """Convert database model to API model."""
    return StrategyRule(
        id=strategy_db.id,
        name=strategy_db.name,
        description=strategy_db.description,
        entry_type=strategy_db.entry_type,
        conditions=strategy_db.conditions,
        confluence_required=strategy_db.confluence_required,
        risk_params=strategy_db.risk_params,
        confidence=strategy_db.confidence,
        source_type=strategy_db.source_type,
        source_ref=strategy_db.source_ref,
        created_at=strategy_db.created_at.isoformat(),
        last_used=strategy_db.last_used.isoformat() if strategy_db.last_used else None,
        win_rate=strategy_db.win_rate,
        total_trades=strategy_db.trade_count,
        enabled=True,  # TODO: Add enabled field to database
        tags=strategy_db.tags or []
    )


@router.get("/", summary="List all strategies")
async def list_strategies(
    enabled_only: bool = Query(False, description="Only return enabled strategies"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    source_type: Optional[str] = Query(None, description="Filter by source type (pdf, video)"),
    entry_type: Optional[str] = Query(None, description="Filter by entry type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of strategies to return"),
    offset: int = Query(0, ge=0, description="Number of strategies to skip"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all strategy rules in the knowledge base.
    
    Supports filtering by:
    - Enabled status
    - Minimum confidence score
    - Source type (PDF or video)
    - Entry type
    
    Returns paginated results with metadata.
    """
    # Validate source_type if provided
    if source_type:
        valid_types = [e.value for e in SourceType]
        if source_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source_type. Must be one of: {', '.join(valid_types)}"
            )
    
    # Validate entry_type if provided
    if entry_type:
        valid_types = [e.value for e in EntryType]
        if entry_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entry_type. Must be one of: {', '.join(valid_types)}"
            )
    
    try:
        # Build query
        query = db.query(StrategyRuleDB)
        
        # Apply filters
        if min_confidence > 0:
            query = query.filter(StrategyRuleDB.confidence >= min_confidence)
        
        if source_type:
            query = query.filter(StrategyRuleDB.source_type == source_type)
        
        if entry_type:
            query = query.filter(StrategyRuleDB.entry_type == entry_type)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and order by confidence (highest first)
        strategies_db = query.order_by(
            StrategyRuleDB.confidence.desc()
        ).offset(offset).limit(limit).all()
        
        # Serialize strategies
        strategies = [_serialize_strategy(s) for s in strategies_db]
        
        logger.info(
            "Strategy list requested",
            count=len(strategies),
            total=total,
            filters={
                "min_confidence": min_confidence,
                "source_type": source_type,
                "entry_type": entry_type
            }
        )
        
        return {
            "data": strategies,
            "meta": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            }
        }
        
    except Exception as e:
        logger.error("Failed to list strategies", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve strategies")


@router.post("/", summary="Create new strategy", status_code=201)
async def create_strategy(
    request: StrategyCreateRequest,
    db: Session = Depends(get_db)
) -> StrategyRule:
    """Create a new strategy rule manually."""
    try:
        # Create strategy in database
        strategy_db = StrategyRuleDB(
            name=request.name,
            description=request.description,
            entry_type=request.entry_type,
            conditions=request.conditions,
            confluence_required=request.confluence_required,
            risk_params=request.risk_params,
            source_type=request.source_type,
            source_ref=request.source_ref,
            tags=request.tags,
            confidence=0.5  # Default confidence for new strategies
        )
        
        db.add(strategy_db)
        db.commit()
        db.refresh(strategy_db)
        
        logger.info("Strategy created", strategy_id=strategy_db.id, name=strategy_db.name)
        
        return _serialize_strategy(strategy_db)
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to create strategy", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create strategy")


@router.get("/{strategy_id}", summary="Get strategy details")
async def get_strategy(
    strategy_id: str,
    db: Session = Depends(get_db)
) -> StrategyRule:
    """Get detailed information about a specific strategy."""
    try:
        strategy_db = db.query(StrategyRuleDB).filter(
            StrategyRuleDB.id == strategy_id
        ).first()
        
        if not strategy_db:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_id}' not found"
            )
        
        logger.info("Strategy details requested", strategy_id=strategy_id)
        
        return _serialize_strategy(strategy_db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get strategy", strategy_id=strategy_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve strategy")


@router.put("/{strategy_id}", summary="Update strategy")
async def update_strategy(
    strategy_id: str,
    request: StrategyCreateRequest,
    db: Session = Depends(get_db)
) -> StrategyRule:
    """Update an existing strategy."""
    try:
        strategy_db = db.query(StrategyRuleDB).filter(
            StrategyRuleDB.id == strategy_id
        ).first()
        
        if not strategy_db:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_id}' not found"
            )
        
        # Update fields
        strategy_db.name = request.name
        strategy_db.description = request.description
        strategy_db.entry_type = request.entry_type
        strategy_db.conditions = request.conditions
        strategy_db.confluence_required = request.confluence_required
        strategy_db.risk_params = request.risk_params
        strategy_db.tags = request.tags
        
        db.commit()
        db.refresh(strategy_db)
        
        logger.info("Strategy updated", strategy_id=strategy_id)
        
        return _serialize_strategy(strategy_db)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to update strategy", strategy_id=strategy_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update strategy")


@router.get("/{strategy_id}/performance", summary="Get strategy performance")
async def get_strategy_performance(
    strategy_id: str,
    db: Session = Depends(get_db)
) -> StrategyPerformance:
    """Get detailed performance metrics for a strategy."""
    try:
        # Check if strategy exists
        strategy_db = db.query(StrategyRuleDB).filter(
            StrategyRuleDB.id == strategy_id
        ).first()
        
        if not strategy_db:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_id}' not found"
            )
        
        # Get all trades for this strategy
        trades = db.query(TradeRecordDB).filter(
            TradeRecordDB.strategy_rule_id == strategy_id
        ).all()
        
        if not trades:
            # No trades yet
            return StrategyPerformance(
                strategy_id=strategy_id,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                avg_win_r=0.0,
                avg_loss_r=0.0,
                max_consecutive_losses=0,
                avg_r_multiple=0.0,
                total_pnl_r=0.0
            )
        
        # Calculate metrics
        winning_trades = [t for t in trades if t.pnl_r > 0]
        losing_trades = [t for t in trades if t.pnl_r < 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        total_count = len(trades)
        
        win_rate = win_count / total_count if total_count > 0 else 0.0
        
        avg_win_r = sum(t.pnl_r for t in winning_trades) / win_count if win_count > 0 else 0.0
        avg_loss_r = sum(t.pnl_r for t in losing_trades) / loss_count if loss_count > 0 else 0.0
        
        total_wins_r = sum(t.pnl_r for t in winning_trades)
        total_losses_r = abs(sum(t.pnl_r for t in losing_trades))
        
        profit_factor = total_wins_r / total_losses_r if total_losses_r > 0 else float('inf')
        
        # Calculate max consecutive losses
        max_consecutive = 0
        current_consecutive = 0
        for trade in trades:
            if trade.pnl_r < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        total_pnl_r = sum(t.pnl_r for t in trades)
        avg_r_multiple = total_pnl_r / total_count if total_count > 0 else 0.0
        
        logger.info("Strategy performance requested", strategy_id=strategy_id, total_trades=total_count)
        
        return StrategyPerformance(
            strategy_id=strategy_id,
            total_trades=total_count,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win_r=avg_win_r,
            avg_loss_r=avg_loss_r,
            max_consecutive_losses=max_consecutive,
            avg_r_multiple=avg_r_multiple,
            total_pnl_r=total_pnl_r
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get strategy performance", strategy_id=strategy_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve strategy performance")


@router.delete("/{strategy_id}", summary="Delete strategy")
async def delete_strategy(
    strategy_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete a strategy from the knowledge base."""
    try:
        strategy_db = db.query(StrategyRuleDB).filter(
            StrategyRuleDB.id == strategy_id
        ).first()
        
        if not strategy_db:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_id}' not found"
            )
        
        # Check if strategy has associated trades
        trade_count = db.query(TradeRecordDB).filter(
            TradeRecordDB.strategy_rule_id == strategy_id
        ).count()
        
        if trade_count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete strategy with {trade_count} associated trades. Archive it instead."
            )
        
        db.delete(strategy_db)
        db.commit()
        
        logger.info("Strategy deleted", strategy_id=strategy_id)
        
        return {"message": "Strategy deleted successfully", "strategy_id": strategy_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to delete strategy", strategy_id=strategy_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete strategy")
