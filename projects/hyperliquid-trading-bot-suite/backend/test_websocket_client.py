"""
WebSocket Client Test

Simple test client to verify WebSocket streaming functionality.
Connect to a backtest stream and display real-time updates.

Usage:
    python test_websocket_client.py [backtest_id]
    
Example:
    # Terminal 1: Start the API server
    uvicorn src.api.main:app --reload
    
    # Terminal 2: Start a backtest
    curl -X POST http://localhost:8000/api/backtesting/start \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Test Backtest",
        "symbol": "BTC-USD",
        "timeframes": ["4H", "1H"],
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "strategy_ids": ["strategy1"]
      }'
    
    # Terminal 3: Connect to WebSocket stream
    python test_websocket_client.py backtest_20240211_123456
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Any

try:
    import websockets
except ImportError:
    print("Error: websockets library not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


class BacktestStreamClient:
    """Simple WebSocket client for backtest streaming."""
    
    def __init__(self, backtest_id: str, host: str = "localhost", port: int = 8000):
        self.backtest_id = backtest_id
        self.url = f"ws://{host}:{port}/api/ws/stream/backtest/{backtest_id}"
        self.connected = False
        
    async def connect(self):
        """Connect to the WebSocket stream."""
        print(f"Connecting to: {self.url}")
        
        try:
            async with websockets.connect(self.url) as websocket:
                self.connected = True
                print(f"✓ Connected to backtest stream: {self.backtest_id}\n")
                
                # Receive messages
                async for message in websocket:
                    await self.handle_message(message)
                    
        except websockets.exceptions.WebSocketException as e:
            print(f"✗ WebSocket error: {e}")
        except KeyboardInterrupt:
            print("\n✓ Disconnected by user")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    async def handle_message(self, raw_message: str):
        """Handle incoming WebSocket message."""
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type", "unknown")
            timestamp = message.get("timestamp", "")
            data = message.get("data", {})
            
            # Format timestamp
            try:
                ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = ts.strftime("%H:%M:%S")
            except:
                time_str = timestamp
            
            # Display based on message type
            if msg_type == "connected":
                print(f"[{time_str}] 🟢 {data.get('message', 'Connected')}\n")
                
            elif msg_type == "progress":
                progress = data.get("progress", 0)
                metrics = data.get("metrics", {})
                
                print(f"[{time_str}] 📊 Progress: {progress:.1f}%")
                print(f"  Balance: ${metrics.get('balance', 0):,.2f}")
                print(f"  Open Positions: {metrics.get('open_positions', 0)}")
                print(f"  Total Trades: {metrics.get('total_trades', 0)}")
                print(f"  Win Rate: {metrics.get('win_rate', 0)*100:.1f}%")
                print()
                
            elif msg_type == "trade":
                event = data.get("event", "")
                trade_id = data.get("trade_id", "")
                symbol = data.get("symbol", "")
                
                if event == "entry":
                    direction = data.get("direction", "")
                    entry_price = data.get("entry_price", 0)
                    quantity = data.get("quantity", 0)
                    
                    print(f"[{time_str}] 🔵 Trade Entry")
                    print(f"  ID: {trade_id}")
                    print(f"  Symbol: {symbol}")
                    print(f"  Direction: {direction.upper()}")
                    print(f"  Price: ${entry_price:,.2f}")
                    print(f"  Quantity: {quantity}")
                    print()
                    
                elif event == "exit":
                    exit_price = data.get("exit_price", 0)
                    pnl = data.get("pnl", 0)
                    exit_reason = data.get("exit_reason", "")
                    
                    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                    
                    print(f"[{time_str}] {pnl_emoji} Trade Exit")
                    print(f"  ID: {trade_id}")
                    print(f"  Symbol: {symbol}")
                    print(f"  Exit Price: ${exit_price:,.2f}")
                    print(f"  P&L: ${pnl:,.2f}")
                    print(f"  Reason: {exit_reason}")
                    print()
                    
            elif msg_type == "equity":
                equity = data.get("equity", 0)
                balance = data.get("balance", 0)
                drawdown = data.get("drawdown", 0)
                
                print(f"[{time_str}] 💰 Equity Update")
                print(f"  Equity: ${equity:,.2f}")
                print(f"  Balance: ${balance:,.2f}")
                print(f"  Drawdown: {drawdown*100:.2f}%")
                print()
                
            elif msg_type == "metrics":
                print(f"[{time_str}] 📈 Performance Metrics")
                for key, value in data.items():
                    if key != "backtest_id":
                        if isinstance(value, float):
                            print(f"  {key}: {value:.2f}")
                        else:
                            print(f"  {key}: {value}")
                print()
                
            elif msg_type == "complete":
                print(f"[{time_str}] ✅ Backtest Complete!\n")
                print("=" * 50)
                print("FINAL RESULTS")
                print("=" * 50)
                
                metrics = data.get("metrics", {})
                for key, value in metrics.items():
                    label = key.replace("_", " ").title()
                    if isinstance(value, float):
                        print(f"{label:.<30} {value:.2f}")
                    else:
                        print(f"{label:.<30} {value}")
                
                print("=" * 50)
                print()
                
            elif msg_type == "error":
                error = data.get("error", "Unknown error")
                print(f"[{time_str}] ❌ Error: {error}\n")
                
            elif msg_type == "pong":
                # Heartbeat response
                pass
                
            else:
                print(f"[{time_str}] ❓ Unknown message type: {msg_type}")
                print(f"  Data: {data}\n")
                
        except json.JSONDecodeError:
            print(f"✗ Invalid JSON: {raw_message}")
        except Exception as e:
            print(f"✗ Error handling message: {e}")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_websocket_client.py <backtest_id>")
        print("\nExample:")
        print("  python test_websocket_client.py backtest_20240211_123456")
        sys.exit(1)
    
    backtest_id = sys.argv[1]
    
    print("=" * 60)
    print("WebSocket Backtest Stream Client")
    print("=" * 60)
    print(f"Backtest ID: {backtest_id}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    client = BacktestStreamClient(backtest_id)
    
    try:
        await client.connect()
    except KeyboardInterrupt:
        print("\n✓ Disconnected by user")


if __name__ == "__main__":
    asyncio.run(main())
