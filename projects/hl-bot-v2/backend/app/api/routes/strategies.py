"""Strategy management API routes."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import StrategyRule as StrategyRuleModel


router = APIRouter(prefix="/api/v1", tags=["strategies"])


# ============================================================================
# Pydantic Models
# ============================================================================


class EntryCondition(BaseModel):
    type: str
    description: str
    options: Optional[List[str]] = None


class ExitRules(BaseModel):
    stop_loss: str
    take_profit_1: str
    take_profit_2: Optional[str] = None
    management: Optional[str] = None


class RiskParams(BaseModel):
    min_rr: float
    position_size_percent: float
    max_risk_percent: float


class StrategyRule(BaseModel):
    id: UUID
    name: str
    description: str
    timeframes: List[str]
    market_phase: Optional[str] = None
    entry_conditions: List[dict]
    exit_rules: dict
    risk_params: dict
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    effectiveness_score: float
    total_trades: int
    winning_trades: int
    is_active: bool

    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    strategies: List[StrategyRule]
    total: int


class StrategyUpdate(BaseModel):
    is_active: Optional[bool] = None
    effectiveness_score: Optional[float] = None


# ============================================================================
# Routes
# ============================================================================


@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies(
    enabled: Optional[bool] = None,
    market_phase: Optional[str] = None,
    min_effectiveness: Optional[float] = None,
    db: Session = Depends(get_db),
):
    """List all strategies with optional filters."""
    query = select(StrategyRuleModel)
    
    if enabled is not None:
        query = query.where(StrategyRuleModel.is_active == enabled)
    
    if market_phase is not None:
        query = query.where(StrategyRuleModel.market_phase == market_phase)
    
    if min_effectiveness is not None:
        query = query.where(StrategyRuleModel.effectiveness_score >= min_effectiveness)
    
    result = db.execute(query)
    strategies = result.scalars().all()
    
    return StrategyListResponse(
        strategies=[StrategyRule.model_validate(s) for s in strategies],
        total=len(strategies),
    )


@router.get("/strategies/{strategy_id}", response_model=StrategyRule)
async def get_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a single strategy by ID."""
    result = db.execute(
        select(StrategyRuleModel).where(StrategyRuleModel.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found"
        )
    
    return StrategyRule.model_validate(strategy)


@router.patch("/strategies/{strategy_id}", response_model=StrategyRule)
async def update_strategy(
    strategy_id: UUID,
    updates: StrategyUpdate,
    db: Session = Depends(get_db),
):
    """Update a strategy."""
    # Check if exists
    result = db.execute(
        select(StrategyRuleModel).where(StrategyRuleModel.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found"
        )
    
    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    if update_data:
        db.execute(
            update(StrategyRuleModel)
            .where(StrategyRuleModel.id == strategy_id)
            .values(**update_data)
        )
        db.commit()
        db.refresh(strategy)
    
    return StrategyRule.model_validate(strategy)


@router.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a strategy."""
    result = db.execute(
        select(StrategyRuleModel).where(StrategyRuleModel.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found"
        )
    
    db.delete(strategy)
    db.commit()
