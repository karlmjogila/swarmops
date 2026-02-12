/**
 * Chart Types - Multi-Timeframe Trading Chart
 */

// Re-export TradeMarker from trade-markers to avoid duplicate definitions
export type { TradeMarker } from './trade-markers'

export type Timeframe = '1m' | '5m' | '15m' | '30m' | '1h' | '4h' | '1d' | '1w'

export interface TimeframeConfig {
  value: Timeframe
  label: string
  seconds: number
  chartInterval: string
}

export interface CandleData {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

export interface MarketData {
  symbol: string
  timeframe: Timeframe
  candles: CandleData[]
  lastUpdate: number
}

export interface ChartSettings {
  theme: 'light' | 'dark'
  showVolume: boolean
  showGrid: boolean
  showCrosshair: boolean
  showWatermark: boolean
  autoScale: boolean
}

export interface PriceLineOptions {
  price: number
  color: string
  lineWidth: number
  lineStyle: number // 0: solid, 1: dotted, 2: dashed
  axisLabelVisible: boolean
  title?: string
}

export interface ChartIndicator {
  id: string
  type: 'sma' | 'ema' | 'bollinger' | 'rsi' | 'macd'
  visible: boolean
  parameters: Record<string, any>
}
