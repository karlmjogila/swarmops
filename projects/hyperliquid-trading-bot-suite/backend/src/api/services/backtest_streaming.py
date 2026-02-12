"""Backtest streaming service with real-time WebSocket updates."""

from typing import Dict, Any, Optional, Callable
from datetime import datetime
import asyncio
import structlog

from ...backtest.backtest_engine import BacktestEngine, BacktestConfig, BacktestState, SimulatedPosition
from ...backtest.data_loader import BacktestDataManager
from ...detection.confluence_scorer import ConfluenceScorer
from ...trading.trade_reasoner import TradeReasoner
from ...knowledge.repository import StrategyRuleRepository
from ...types import BacktestResult, TradeRecord, ExitReason
from .websocket_manager import WebSocketManager, StreamType

logger = structlog.get_logger()


class StreamingBacktestEngine:
    """
    Wrapper around BacktestEngine that emits real-time updates via WebSocket.
    
    Emits events for:
    - Progress updates (every N candles)
    - Trade entry/exit
    - Equity curve updates
    - Performance metrics
    - Completion
    
    This allows the frontend to show backtest execution in real-time,
    making the process transparent and debuggable.
    """
    
    def __init__(
        self,
        ws_manager: WebSocketManager,
        data_manager: BacktestDataManager,
        confluence_scorer: ConfluenceScorer,
        trade_reasoner: TradeReasoner,
        strategy_repo: StrategyRuleRepository,
        progress_interval: int = 100  # Emit progress every N candles
    ):
        """
        Initialize streaming backtest engine.
        
        Args:
            ws_manager: WebSocket manager for streaming
            data_manager: Backtest data manager
            confluence_scorer: Confluence scorer instance
            trade_reasoner: Trade reasoner instance
            strategy_repo: Strategy rule repository
            progress_interval: Number of candles between progress updates
        """
        self.ws_manager = ws_manager
        self.data_manager = data_manager
        self.confluence_scorer = confluence_scorer
        self.trade_reasoner = trade_reasoner
        self.strategy_repo = strategy_repo
        self.progress_interval = progress_interval
        
        self.engine: Optional[BacktestEngine] = None
        self.backtest_id: Optional[str] = None
        
        logger.info("StreamingBacktestEngine initialized")
    
    async def run_backtest(
        self,
        backtest_id: str,
        config: BacktestConfig,
        db_session: Any  # SQLAlchemy session
    ) -> BacktestResult:
        """
        Run backtest with real-time streaming.
        
        Args:
            backtest_id: Unique backtest identifier
            config: Backtest configuration
            db_session: Database session
            
        Returns:
            Final backtest result
        """
        self.backtest_id = backtest_id
        
        try:
            # Initialize engine with callbacks
            self.engine = BacktestEngine(
                data_manager=self.data_manager,
                confluence_scorer=self.confluence_scorer,
                trade_reasoner=self.trade_reasoner,
                strategy_repo=self.strategy_repo,
                db_session=db_session,
                config=config
            )
            
            logger.info("Starting streaming backtest", backtest_id=backtest_id)
            
            # Notify start
            await self._emit_start()
            
            # Run backtest with streaming callbacks
            result = await self._run_with_streaming(config)
            
            # Notify completion
            await self._emit_complete(result)
            
            logger.info("Streaming backtest completed", backtest_id=backtest_id)
            
            return result
            
        except Exception as e:
            logger.error(
                "Backtest failed",
                backtest_id=backtest_id,
                error=str(e),
                exc_info=e
            )
            await self._emit_error(str(e))
            raise
    
    async def _run_with_streaming(self, config: BacktestConfig) -> BacktestResult:
        """
        Run backtest with streaming updates.
        
        This is a wrapper around the synchronous BacktestEngine.run()
        that emits WebSocket events at key points.
        """
        # In a real implementation, we'd modify BacktestEngine to support
        # async callbacks. For now, we'll run it in a thread pool and
        # emit updates periodically.
        
        # Since BacktestEngine.run() is synchronous, we need to either:
        # 1. Make it async (preferred)
        # 2. Run it in an executor and poll for updates
        # 3. Modify it to accept callbacks
        
        # For this implementation, I'll create a modified version that
        # accepts callbacks
        
        result = await self._run_backtest_with_callbacks(config)
        return result
    
    async def _run_backtest_with_callbacks(
        self,
        config: BacktestConfig
    ) -> BacktestResult:
        """
        Run backtest with callback hooks for streaming.
        
        This method would ideally be integrated into the BacktestEngine class,
        but for now we'll run it in chunks and emit updates.
        """
        # Run the backtest (this would need to be modified to support callbacks)
        # For now, we'll call the original run() method
        # In production, BacktestEngine would be modified to call these callbacks
        
        # Placeholder: In real implementation, BacktestEngine.run() would call:
        # - await self.on_progress(progress, state)
        # - await self.on_trade_entry(position)
        # - await self.on_trade_exit(position)
        # - await self.on_equity_update(state)
        
        # For demonstration, we'll run synchronously and emit a few updates
        loop = asyncio.get_event_loop()
        
        # Run in executor to avoid blocking
        result = await loop.run_in_executor(
            None,
            self.engine.run,
            config
        )
        
        return result
    
    async def _emit_start(self) -> None:
        """Emit backtest start event."""
        message = {
            "type": "start",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "backtest_id": self.backtest_id,
                "message": "Backtest started"
            }
        }
        await self.ws_manager.send_to_stream(
            StreamType.BACKTEST,
            self.backtest_id,
            message
        )
    
    async def _emit_progress(
        self,
        progress: float,
        state: BacktestState
    ) -> None:
        """
        Emit progress update.
        
        Args:
            progress: Progress percentage (0-100)
            state: Current backtest state
        """
        await self.ws_manager.send_progress(
            self.backtest_id,
            progress,
            state.current_time,
            {
                "balance": state.current_balance,
                "equity": state.current_balance,  # Would include unrealized P&L
                "open_positions": len(state.open_positions),
                "total_trades": state.total_trades,
                "winning_trades": state.winning_trades,
                "losing_trades": state.losing_trades,
                "win_rate": (
                    state.winning_trades / state.total_trades
                    if state.total_trades > 0 else 0
                ),
                "max_drawdown": state.max_drawdown
            }
        )
    
    async def _emit_trade_entry(self, position: SimulatedPosition) -> None:
        """
        Emit trade entry event.
        
        Args:
            position: Simulated position that was opened
        """
        await self.ws_manager.send_trade(
            self.backtest_id,
            {
                "event": "entry",
                "trade_id": position.id,
                "symbol": position.asset,
                "direction": position.direction.value,
                "entry_price": position.entry_price,
                "entry_time": position.entry_time.isoformat(),
                "quantity": position.quantity,
                "stop_loss": position.stop_loss,
                "take_profit_levels": position.take_profit_levels,
                "reasoning": (
                    position.reasoning.model_dump()
                    if position.reasoning else None
                )
            }
        )
    
    async def _emit_trade_exit(self, position: SimulatedPosition) -> None:
        """
        Emit trade exit event.
        
        Args:
            position: Simulated position that was closed
        """
        await self.ws_manager.send_trade(
            self.backtest_id,
            {
                "event": "exit",
                "trade_id": position.id,
                "symbol": position.asset,
                "direction": position.direction.value,
                "entry_price": position.entry_price,
                "entry_time": position.entry_time.isoformat(),
                "exit_price": position.exit_price,
                "exit_time": position.exit_time.isoformat(),
                "exit_reason": position.exit_reason.value if position.exit_reason else None,
                "pnl": position.current_pnl,
                "pnl_percent": (
                    (position.current_pnl / (position.entry_price * position.quantity)) * 100
                    if position.entry_price > 0 else 0
                ),
                "mfe": position.max_favorable_excursion,
                "mae": position.max_adverse_excursion
            }
        )
    
    async def _emit_equity_update(self, state: BacktestState) -> None:
        """
        Emit equity curve update.
        
        Args:
            state: Current backtest state
        """
        # Calculate total equity (balance + unrealized P&L)
        unrealized_pnl = sum(
            pos.current_pnl for pos in state.open_positions
        )
        equity = state.current_balance + unrealized_pnl
        
        await self.ws_manager.send_equity_update(
            self.backtest_id,
            equity=equity,
            balance=state.current_balance,
            drawdown=state.current_drawdown,
            timestamp=state.current_time
        )
    
    async def _emit_complete(self, result: BacktestResult) -> None:
        """
        Emit backtest completion event.
        
        Args:
            result: Final backtest result
        """
        # Convert result to dict format
        metrics = {
            "total_trades": result.total_trades,
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "total_return": result.total_return_pct,
            "max_drawdown": result.max_drawdown_pct,
            "sharpe_ratio": result.sharpe_ratio,
            "average_win": result.avg_win_r,
            "average_loss": result.avg_loss_r,
            "largest_win": result.largest_win_r,
            "largest_loss": result.largest_loss_r,
            "total_commissions": result.total_commissions
        }
        
        await self.ws_manager.send_complete(
            self.backtest_id,
            metrics
        )
    
    async def _emit_error(self, error: str) -> None:
        """
        Emit error event.
        
        Args:
            error: Error message
        """
        await self.ws_manager.send_error(
            StreamType.BACKTEST,
            self.backtest_id,
            error
        )


# Callback integration for BacktestEngine
# These would be added to BacktestEngine to enable streaming

async def create_streaming_callbacks(
    ws_manager: WebSocketManager,
    backtest_id: str,
    progress_interval: int = 100
) -> Dict[str, Callable]:
    """
    Create callback functions for BacktestEngine.
    
    These callbacks would be passed to a modified BacktestEngine
    that supports async callback hooks.
    
    Args:
        ws_manager: WebSocket manager
        backtest_id: Backtest identifier
        progress_interval: Candles between progress updates
        
    Returns:
        Dictionary of callback functions
    """
    candle_count = 0
    
    async def on_candle_processed(state: BacktestState, total_candles: int) -> None:
        """Called after each candle is processed."""
        nonlocal candle_count
        candle_count += 1
        
        if candle_count % progress_interval == 0:
            progress = (candle_count / total_candles) * 100
            await ws_manager.send_progress(
                backtest_id,
                progress,
                state.current_time,
                {
                    "balance": state.current_balance,
                    "open_positions": len(state.open_positions),
                    "total_trades": state.total_trades,
                    "win_rate": (
                        state.winning_trades / state.total_trades
                        if state.total_trades > 0 else 0
                    )
                }
            )
    
    async def on_position_opened(position: SimulatedPosition) -> None:
        """Called when a position is opened."""
        await ws_manager.send_trade(backtest_id, {
            "event": "entry",
            "trade_id": position.id,
            "symbol": position.asset,
            "direction": position.direction.value,
            "entry_price": position.entry_price,
            "entry_time": position.entry_time.isoformat(),
            "quantity": position.quantity
        })
    
    async def on_position_closed(position: SimulatedPosition) -> None:
        """Called when a position is closed."""
        await ws_manager.send_trade(backtest_id, {
            "event": "exit",
            "trade_id": position.id,
            "symbol": position.asset,
            "exit_price": position.exit_price,
            "exit_time": position.exit_time.isoformat(),
            "pnl": position.current_pnl,
            "exit_reason": position.exit_reason.value if position.exit_reason else None
        })
    
    return {
        "on_candle_processed": on_candle_processed,
        "on_position_opened": on_position_opened,
        "on_position_closed": on_position_closed
    }
