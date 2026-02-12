/**
 * Trade Marker Types - Visual markers and overlays for trades on charts
 */

export type TradeMarkerType = 'entry' | 'exit' | 'partial-exit' | 'stop-loss' | 'take-profit'
export type TradeSide = 'buy' | 'sell'
export type TradeOutcome = 'win' | 'loss' | 'breakeven' | 'pending'

export interface TradeMarker {
  id: string
  time: number                    // Unix timestamp in seconds
  type: TradeMarkerType
  side: TradeSide
  price: number
  quantity: number
  
  // Optional metadata
  reason?: string                 // Entry/exit reason
  pnl?: number                    // P&L for exit markers
  pnlPercent?: number             // P&L percentage
  rMultiple?: number              // R-multiple (risk/reward)
  fees?: number                   // Trading fees
  
  // Associated trade info
  tradeId?: string
  strategyId?: string
  
  // Visual customization
  color?: string
  label?: string
  showTooltip?: boolean
}

export interface TradeOverlay {
  id: string
  tradeId: string
  
  // Entry/exit information
  entryTime: number
  entryPrice: number
  exitTime?: number
  exitPrice?: number
  
  // Trade details
  side: TradeSide
  quantity: number
  outcome: TradeOutcome
  
  // Performance metrics
  pnl: number
  pnlPercent: number
  rMultiple: number
  fees: number
  
  // Risk management levels
  stopLoss?: number
  takeProfitLevels?: number[]
  
  // Context
  reasoning?: string
  entryPattern?: string
  exitReason?: string
  
  // Visual state
  isActive: boolean
  isHighlighted: boolean
}

export interface TradeZone {
  id: string
  tradeId: string
  type: 'entry-zone' | 'target-zone' | 'stop-zone'
  
  // Zone boundaries
  topPrice: number
  bottomPrice: number
  startTime: number
  endTime?: number
  
  // Visual style
  color: string
  opacity: number
  borderColor?: string
  label?: string
}

export interface PriceLine {
  id: string
  price: number
  color: string
  width: number
  style: 'solid' | 'dotted' | 'dashed'
  label?: string
  showLabel?: boolean
  interactive?: boolean
}

export interface TradeStats {
  totalTrades: number
  winningTrades: number
  losingTrades: number
  breakevenTrades: number
  pendingTrades: number
  
  winRate: number
  averageWin: number
  averageLoss: number
  profitFactor: number
  averageRMultiple: number
  
  totalPnl: number
  totalFees: number
  netPnl: number
}

export interface MarkerStyle {
  size: number
  color: string
  borderColor?: string
  borderWidth?: number
  shape: 'circle' | 'triangle-up' | 'triangle-down' | 'square' | 'diamond'
  text?: string
  textColor?: string
  textSize?: number
}

export interface TooltipData {
  title: string
  items: Array<{
    label: string
    value: string | number
    color?: string
    suffix?: string
  }>
  timestamp?: number
  price?: number
}

/**
 * Configuration for trade marker display
 */
export interface TradeMarkerConfig {
  showEntryMarkers: boolean
  showExitMarkers: boolean
  showStopLoss: boolean
  showTakeProfit: boolean
  showPartialExits: boolean
  
  showTradeZones: boolean
  showPriceLines: boolean
  showTooltips: boolean
  showLabels: boolean
  
  highlightActiveTrades: boolean
  groupByTrade: boolean
  
  // Color scheme
  colors: {
    buyEntry: string
    sellEntry: string
    profitExit: string
    lossExit: string
    breakevenExit: string
    stopLoss: string
    takeProfit: string
    activeZone: string
  }
}

export const defaultMarkerConfig: TradeMarkerConfig = {
  showEntryMarkers: true,
  showExitMarkers: true,
  showStopLoss: true,
  showTakeProfit: true,
  showPartialExits: true,
  
  showTradeZones: true,
  showPriceLines: true,
  showTooltips: true,
  showLabels: true,
  
  highlightActiveTrades: true,
  groupByTrade: true,
  
  colors: {
    buyEntry: '#10b981',      // green-500
    sellEntry: '#ef4444',     // red-500
    profitExit: '#059669',    // green-600
    lossExit: '#dc2626',      // red-600
    breakevenExit: '#6b7280', // gray-500
    stopLoss: '#f59e0b',      // amber-500
    takeProfit: '#3b82f6',    // blue-500
    activeZone: '#8b5cf6',    // purple-500
  }
}
