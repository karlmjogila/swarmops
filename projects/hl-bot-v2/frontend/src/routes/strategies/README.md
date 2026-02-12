# Strategy Manager UI

## Overview

Comprehensive strategy management interface for viewing, filtering, enabling/disabling, and monitoring trading strategies.

## Components

### Main Page (`+page.svelte`)
- Strategy list with cards
- Search and filtering (by phase, status, search query)
- Sorting (by name, effectiveness, trades, win rate)
- Summary statistics dashboard
- Create strategy modal (placeholder for future implementation)

### StrategyCard Component
- Compact strategy overview
- Toggle switch for enable/disable
- Key metrics display (effectiveness, win rate, trades)
- Risk parameters preview
- Source badges (YouTube, PDF, manual)
- Phase and timeframe badges
- Click to view details

### StrategyDetails Component
- Full-screen sidebar panel
- Complete strategy information
- Entry conditions list
- Exit rules breakdown
- Risk management parameters with progress bars
- Performance statistics
- Source information with confidence score
- Action buttons (enable/disable, delete)

## Features

### Filtering & Search
- **Search**: Filter by strategy name or description
- **Market Phase**: Filter by drive/range/liquidity
- **Status**: Show all/enabled/disabled strategies
- **Sorting**: By effectiveness, name, total trades, or win rate

### Statistics Dashboard
- Total strategies count
- Enabled strategies count
- Average effectiveness score
- Overall win rate across all strategies

### Strategy Details
- **Entry Conditions**: Numbered list with descriptions and formatted expressions
- **Exit Rules**: TP1/TP2/TP3 levels, breakeven trigger, trailing stop configuration
- **Risk Parameters**: Visual progress bars for risk percentages, position limits, correlation limits
- **Performance Metrics**: Effectiveness score, win rate, total trades, wins/losses
- **Source Tracking**: Where the strategy came from (YouTube, PDF, manual), extraction confidence

### Actions
- **Toggle Strategy**: Enable/disable individual strategies
- **View Details**: Open full detail sidebar
- **Delete Strategy**: Remove strategy (with confirmation)

## API Integration

### Backend Endpoints
- `GET /api/v1/strategies` - List all strategies with optional filters
- `GET /api/v1/strategies/{id}` - Get single strategy details
- `PATCH /api/v1/strategies/{id}` - Update strategy (enable/disable)
- `DELETE /api/v1/strategies/{id}` - Delete strategy

### Mock Data
Currently using mock data with 4 example strategies:
1. **Breakout + Higher TF Bias** - Drive phase, 78% effective, 45 trades
2. **Range Fade** - Range phase, 65% effective, 67 trades
3. **Liquidity Grab Reversal** - Liquidity phase, 82% effective, 38 trades
4. **Failed Strategy Example** - Disabled, 35% effective, 52 trades

## Safety Features

Following trading systems excellence principles:

### Risk Management Display
- Clear visualization of risk parameters
- Max daily loss limits prominently displayed
- Position limits shown
- Correlation limits visible

### Validation Indicators
- Effectiveness score color-coded:
  - Green (≥70%): High performance
  - Yellow (50-70%): Moderate performance
  - Red (<50%): Low performance
- Win rate color coding
- Source confidence levels

### Defensive Design
- Confirmation dialogs for destructive actions (delete)
- Error handling with user-friendly messages
- Loading states for async operations
- Empty states when no results

## Trading Systems Principles Applied

1. **Safety over speed**: Strategies can be disabled instantly, preventing bad trades
2. **Audit everything**: Source tracking, confidence scores, timestamps for created/updated
3. **Fail closed**: Strategies default to disabled when performance is poor
4. **Clear risk limits**: All risk parameters visible and enforced at strategy level
5. **No ambiguity**: Entry conditions and exit rules explicitly defined and displayed
6. **Performance tracking**: Win rate, effectiveness score, trade count prominently shown

## Future Enhancements

- [ ] Create strategy via manual entry form
- [ ] Edit strategy conditions and parameters
- [ ] Strategy versioning and history
- [ ] Backtest strategy directly from UI
- [ ] Clone/duplicate strategies
- [ ] Export/import strategy definitions
- [ ] Strategy performance charts (equity curve per strategy)
- [ ] Real-time strategy monitoring during live trading
- [ ] Strategy correlation matrix
- [ ] Automated strategy optimization suggestions

## Integration Points

- **Content Ingestion**: Strategies extracted from YouTube/PDFs appear here
- **Backtesting**: Strategies can be selected for backtest runs
- **Live Trading**: Enabled strategies are used by the trading engine
- **Learning Loop**: Strategy effectiveness scores updated based on performance

## Color Scheme

- **Primary**: Blue (#0284c7) - Actions, highlights
- **Success**: Green - Enabled, profitable, positive metrics
- **Warning**: Yellow - Moderate performance, range phase
- **Danger**: Red - Disabled, poor performance, risk limits
- **Dark Theme**: Gray-900 background, consistent with app theme

## Responsive Design

- Mobile: Single column layout, full-width cards
- Tablet: 2-column grid
- Desktop: 3-column grid for strategy cards
- Detail sidebar: Full-width on mobile, 50-66% on desktop
