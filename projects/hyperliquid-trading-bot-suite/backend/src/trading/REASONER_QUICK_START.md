# Trade Reasoner - Quick Start Guide

## 🚀 Quick Start

### Installation
```bash
pip install anthropic  # For LLM mode
```

### Basic Usage

```python
from src.trading.trade_reasoner import TradeReasoner, explain_trade
from src.detection.confluence_scorer import ConfluenceScorer

# Initialize
reasoner = TradeReasoner(
    use_llm=True,  # Use Claude API
    min_confluence_score=0.50
)

# Get a signal from confluence scorer
scorer = ConfluenceScorer()
signal = scorer.analyze_confluence(
    asset="BTC-USD",
    multi_timeframe_data=mtf_data
)

# Generate reasoning
reasoning = reasoner.analyze_setup(
    signal=signal,
    timeframe_candles=candle_data
)

# Check result
if reasoning.should_enter:
    print(f"✅ ENTER {reasoning.entry_bias.value.upper()}")
    print(f"Confidence: {reasoning.confidence:.1%}")
    print(f"\nExplanation:\n{reasoning.explanation}")
    print(f"\nStop: ${reasoning.suggested_stop_loss:,.2f}")
    print(f"Targets: {reasoning.suggested_targets}")
else:
    print(f"❌ NO ENTRY: {reasoning.explanation}")
```

### One-Liner
```python
from src.trading.trade_reasoner import explain_trade

reasoning = explain_trade(signal, candle_data, use_llm=True)
```

## 🎯 Key Features

| Feature | Description |
|---------|-------------|
| **LLM Reasoning** | Uses Claude Sonnet 4 for natural language explanations |
| **Rule-Based Fallback** | Template-based reasoning when no API key |
| **Confidence Scoring** | 0.0-1.0 confidence with boost/penalty logic |
| **Risk Management** | Auto-calculates stop loss and targets |
| **Context Analysis** | HTF/LTF analysis, confluences, risks |

## 📊 Output Structure

```python
TradeReasoning:
  should_enter: bool          # Enter this trade?
  confidence: float           # 0.0 to 1.0
  explanation: str            # Human-readable narrative
  
  entry_bias: OrderSide       # LONG or SHORT
  setup_type: str            # E.g., "Strong long LE setup"
  
  suggested_stop_loss: float
  suggested_targets: List[float]
  risk_reward_ratio: float
  
  key_confluences: List[str]
  risks: List[str]
  invalidation_points: List[str]
  
  higher_tf_context: str
  entry_tf_context: str
  expected_behavior: str
```

## 🔧 Configuration

```python
reasoner = TradeReasoner(
    anthropic_api_key="sk-...",        # Or use ANTHROPIC_API_KEY env var
    model="claude-sonnet-4-20250514",  # Claude model
    use_llm=True,                      # Enable LLM mode
    min_confidence_for_entry=0.55,     # Entry threshold
    min_confluence_score=0.50          # Min confluence required
)
```

## 💰 Cost

- **LLM mode**: ~$0.003 per trade analysis
- **Monthly** (100 trades/day): ~$9
- **Rule-based mode**: Free

## 📚 Documentation

- Full documentation: `TRADE_REASONER_README.md`
- Completion summary: `TRADE_REASONER_COMPLETE.md`
- Examples: `reasoner_example.py`

## 🔗 Integration Points

| Component | Integration |
|-----------|-------------|
| Confluence Scorer | Analyzes signals from scorer |
| Position Manager | Provides risk levels for execution |
| Backtest Engine | Historical signal analysis |
| Frontend Dashboard | Display reasoning to users |

## ⚡ Performance

| Metric | LLM Mode | Rule-Based Mode |
|--------|----------|-----------------|
| Latency | 1-2 seconds | <100ms |
| Cost | $0.003/trade | Free |
| Quality | Excellent | Good |
| API Required | Yes (Anthropic) | No |

## 🎓 Examples

See `reasoner_example.py` for complete examples including:
- Basic reasoning
- SHORT signals
- Error handling
- Formatted display output

---

**Status**: ✅ Production Ready  
**Author**: Hyperliquid Trading Bot Suite  
**Last Updated**: February 11, 2025
