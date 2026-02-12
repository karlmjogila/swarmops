#!/usr/bin/env python3
"""
Backtest runner with WebSocket streaming.

Runs a backtest and streams state updates to stdout as JSON.
Listens for control commands (pause/resume/stop) on stdin.

Usage:
    python run_backtest_stream.py \
        --session-id <id> \
        --symbol <symbol> \
        --start-date <YYYY-MM-DD> \
        --end-date <YYYY-MM-DD> \
        --initial-capital <float> \
        --position-size-percent <float> \
        --max-open-trades <int> \
        --use-stop-orders <bool> \
        --use-take-profits <bool> \
        --emit-interval <int>
"""

import argparse
import asyncio
import json
import sys
import signal
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.hl_bot.trading.backtest import (
    BacktestEngine,
    BacktestConfig,
    BacktestState,
)
from app.db.session import SessionLocal
from app.db.repositories.ohlcv import OHLCVRepository
from app.core.market.data import Candle


class BacktestStreamRunner:
    """Backtest runner with state streaming."""

    def __init__(
        self,
        session_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
        config: BacktestConfig,
        emit_interval: int = 10,
        data_source: str = 'auto',
    ):
        self.session_id = session_id
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.config = config
        self.emit_interval = emit_interval
        self.data_source = data_source  # 'hyperliquid', 'csv', or 'auto'

        self.engine: Optional[BacktestEngine] = None
        self.running = True
        self.paused = False

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        self.log("Received shutdown signal")
        self.running = False
        if self.engine:
            self.engine.stop()

    def emit_state(self, state: BacktestState):
        """Emit state update to stdout."""
        try:
            # Convert Pydantic model to dict
            state_dict = state.model_dump()

            # Convert datetime objects to ISO strings
            if state_dict.get('currentTime'):
                state_dict['currentTime'] = state_dict['currentTime'].isoformat()

            message = {
                'type': 'state_update',
                'sessionId': self.session_id,
                'state': state_dict,
            }

            # Write to stdout as JSON line
            print(json.dumps(message), flush=True)
        except Exception as e:
            self.error(f"Failed to emit state: {e}")

    def log(self, message: str):
        """Log message to stdout."""
        print(json.dumps({
            'type': 'log',
            'sessionId': self.session_id,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }), flush=True)

    def error(self, message: str):
        """Emit error to stdout."""
        print(json.dumps({
            'type': 'error',
            'sessionId': self.session_id,
            'error': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }), flush=True)

    async def load_candles(self) -> list[Candle]:
        """Load candles for the backtest period based on data source."""
        try:
            self.log(f"Loading candles for {self.symbol} from {self.start_date} to {self.end_date} (source: {self.data_source})")

            # Parse dates
            start_dt = datetime.strptime(self.start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")

            # Initialize database session and repository
            db = SessionLocal()
            try:
                repo = OHLCVRepository(db)

                # Load candles from database with source filtering
                db_candles = repo.get_candles(
                    symbol=self.symbol,
                    timeframe="1h",  # Default to 1h for now
                    start_time=start_dt,
                    end_time=end_dt,
                    source=self.data_source,
                )

                if not db_candles:
                    source_msg = f" from source '{self.data_source}'" if self.data_source != 'auto' else ""
                    raise ValueError(f"No candles found for {self.symbol} between {self.start_date} and {self.end_date}{source_msg}")

                # Log which source was actually used
                actual_source = db_candles[0].source if hasattr(db_candles[0], 'source') else 'unknown'
                self.log(f"Loaded {len(db_candles)} candles from source: {actual_source}")
                
                # Convert OHLCVData models to Candle objects
                candles = [
                    Candle(
                        timestamp=c.timestamp,
                        open=c.open,
                        high=c.high,
                        low=c.low,
                        close=c.close,
                        volume=c.volume,
                    )
                    for c in db_candles
                ]
                return candles
            finally:
                db.close()

        except Exception as e:
            self.error(f"Failed to load candles: {e}")
            raise

    def listen_for_commands(self):
        """Listen for control commands on stdin (non-blocking)."""
        def read_stdin():
            for line in sys.stdin:
                try:
                    command = json.loads(line.strip())
                    cmd_type = command.get('command')

                    if cmd_type == 'pause':
                        self.log("Pausing backtest")
                        self.paused = True
                        if self.engine:
                            self.engine.pause()
                    elif cmd_type == 'resume':
                        self.log("Resuming backtest")
                        self.paused = False
                        if self.engine:
                            self.engine.resume()
                    elif cmd_type == 'stop':
                        self.log("Stopping backtest")
                        self.running = False
                        if self.engine:
                            self.engine.stop()
                    elif cmd_type == 'step':
                        self.log("Stepping one candle")
                        if self.engine:
                            self.engine.step()
                    elif cmd_type == 'speed':
                        speed = command.get('speed', 1.0)
                        self.log(f"Setting playback speed to {speed}x")
                        if self.engine:
                            self.engine.set_speed(speed)
                    elif cmd_type == 'seek':
                        candle_index = command.get('index', 0)
                        self.log(f"Seeking to candle index {candle_index}")
                        if self.engine:
                            self.engine.seek(candle_index)
                except json.JSONDecodeError:
                    pass  # Ignore invalid JSON
                except Exception as e:
                    self.error(f"Command error: {e}")

        # Run stdin listener in background thread
        thread = threading.Thread(target=read_stdin, daemon=True)
        thread.start()

    async def run(self):
        """Run the backtest with streaming."""
        try:
            # Start listening for commands
            self.listen_for_commands()

            # Load candles
            candles = await self.load_candles()

            # Create backtest engine
            self.engine = BacktestEngine(
                config=self.config,
                signal_generator=None,  # TODO: Add signal generator
            )

            # Add state callback to emit updates
            self.engine.add_state_callback(self.emit_state)

            self.log("Starting backtest")

            # Run backtest
            async for state in self.engine.run(candles, emit_interval=self.emit_interval):
                # State is automatically emitted via callback
                pass

            self.log("Backtest completed")

        except Exception as e:
            self.error(f"Backtest failed: {e}")
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run backtest with WebSocket streaming")

    parser.add_argument("--session-id", required=True, help="Backtest session ID")
    parser.add_argument("--symbol", required=True, help="Trading symbol")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--initial-capital", type=float, default=10000.0, help="Initial capital")
    parser.add_argument("--position-size-percent", type=float, default=0.02, help="Position size as % of capital")
    parser.add_argument("--max-open-trades", type=int, default=3, help="Max open trades")
    parser.add_argument("--use-stop-orders", type=str, default="true", help="Use stop orders (true/false)")
    parser.add_argument("--use-take-profits", type=str, default="true", help="Use take profits (true/false)")
    parser.add_argument("--emit-interval", type=int, default=10, help="Emit state every N candles")
    parser.add_argument("--data-source", type=str, default="auto", 
                       choices=["hyperliquid", "csv", "auto"],
                       help="Data source: 'hyperliquid', 'csv', or 'auto' (default)")

    args = parser.parse_args()

    # Parse boolean flags
    use_stop_orders = args.use_stop_orders.lower() == "true"
    use_take_profits = args.use_take_profits.lower() == "true"

    # Create backtest config
    config = BacktestConfig(
        initial_capital=args.initial_capital,
        position_size_percent=args.position_size_percent,
        max_open_trades=args.max_open_trades,
        use_stop_orders=use_stop_orders,
        use_take_profits=use_take_profits,
    )

    # Create runner
    runner = BacktestStreamRunner(
        session_id=args.session_id,
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        config=config,
        emit_interval=args.emit_interval,
        data_source=args.data_source,
    )

    # Run backtest
    try:
        asyncio.run(runner.run())
        sys.exit(0)
    except Exception as e:
        runner.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
