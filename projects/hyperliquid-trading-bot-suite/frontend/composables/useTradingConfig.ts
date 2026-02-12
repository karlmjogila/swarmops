/**
 * Trading Configuration Composable
 * 
 * Provides configurable fee rates, position limits, and validation settings.
 * Values can be loaded from the backend API or configured via environment.
 */

import { toDecimal, type Decimal } from '~/utils/financial'

export interface FeeConfig {
  takerFeeRate: string     // As string for Decimal precision
  makerFeeRate: string
  fundingRateInterval: number  // In hours
}

export interface PositionLimits {
  maxPositionValue: string         // Maximum position value in USD
  maxLeverage: number              // Maximum allowed leverage
  maxDailyLoss: string             // Maximum daily loss in USD
  maxDailyLossPercent: string      // Maximum daily loss as percentage of equity
  maxOpenPositions: number         // Maximum number of open positions
  maxPositionPercentOfEquity: string // Max position size as % of equity
}

export interface PriceValidation {
  maxSlippagePercent: string       // Maximum allowed slippage from market price
  maxPriceDeviationPercent: string // Max deviation of limit price from market
  minNotionalValue: string         // Minimum order notional value
}

export interface TradingConfig {
  fees: FeeConfig
  positionLimits: PositionLimits
  priceValidation: PriceValidation
  isTestnet: boolean
  paperTradingMode: boolean
}

// Default configuration (can be overridden by API)
const defaultConfig: TradingConfig = {
  fees: {
    takerFeeRate: '0.0005',   // 0.05%
    makerFeeRate: '0.0002',   // 0.02%
    fundingRateInterval: 8,
  },
  positionLimits: {
    maxPositionValue: '100000',     // $100k max position
    maxLeverage: 50,
    maxDailyLoss: '5000',           // $5k max daily loss
    maxDailyLossPercent: '5',       // 5% of equity
    maxOpenPositions: 10,
    maxPositionPercentOfEquity: '25', // 25% of equity per position
  },
  priceValidation: {
    maxSlippagePercent: '1',        // 1% max slippage
    maxPriceDeviationPercent: '5',  // 5% max deviation for limit orders
    minNotionalValue: '10',         // $10 minimum order
  },
  isTestnet: true,
  paperTradingMode: true,
}

export const useTradingConfig = () => {
  const config = useState<TradingConfig>('trading-config', () => ({ ...defaultConfig }))
  const loading = useState<boolean>('trading-config-loading', () => false)
  const error = useState<string | null>('trading-config-error', () => null)
  const lastFetched = useState<number>('trading-config-last-fetched', () => 0)
  
  const runtimeConfig = useRuntimeConfig()
  
  /**
   * Load configuration from backend API
   */
  const loadConfig = async (): Promise<void> => {
    // Don't reload if we fetched recently (within 5 minutes)
    const now = Date.now()
    if (lastFetched.value && (now - lastFetched.value) < 300000) {
      return
    }
    
    loading.value = true
    error.value = null
    
    try {
      const apiBaseUrl = runtimeConfig.public.apiBaseUrl || 'http://localhost:8000'
      
      const response = await $fetch<{ config: Partial<TradingConfig> }>(
        `${apiBaseUrl}/api/config/trading`,
        {
          timeout: 5000,
        }
      )
      
      // Merge with defaults
      if (response.config) {
        config.value = {
          ...defaultConfig,
          ...response.config,
          fees: { ...defaultConfig.fees, ...response.config.fees },
          positionLimits: { ...defaultConfig.positionLimits, ...response.config.positionLimits },
          priceValidation: { ...defaultConfig.priceValidation, ...response.config.priceValidation },
        }
      }
      
      lastFetched.value = now
    } catch (err: any) {
      // Use defaults if API unavailable
      console.warn('Failed to load trading config, using defaults:', err.message)
      error.value = err.message
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Update configuration locally
   */
  const updateConfig = (updates: Partial<TradingConfig>): void => {
    config.value = {
      ...config.value,
      ...updates,
    }
  }
  
  /**
   * Get fee rate for order type
   */
  const getFeeRate = (orderType: 'market' | 'limit' | 'stop'): Decimal => {
    if (orderType === 'limit') {
      return toDecimal(config.value.fees.makerFeeRate)
    }
    return toDecimal(config.value.fees.takerFeeRate)
  }
  
  /**
   * Check if leverage is within limits
   */
  const isLeverageAllowed = (leverage: number): boolean => {
    return leverage >= 1 && leverage <= config.value.positionLimits.maxLeverage
  }
  
  /**
   * Check if position value is within limits
   */
  const isPositionValueAllowed = (value: number | string | Decimal): boolean => {
    const v = toDecimal(value)
    const max = toDecimal(config.value.positionLimits.maxPositionValue)
    return v.lessThanOrEqualTo(max)
  }
  
  /**
   * Check if notional value meets minimum
   */
  const meetsMinimumNotional = (notional: number | string | Decimal): boolean => {
    const n = toDecimal(notional)
    const min = toDecimal(config.value.priceValidation.minNotionalValue)
    return n.greaterThanOrEqualTo(min)
  }
  
  /**
   * Check if price is within acceptable deviation from market
   */
  const isPriceWithinDeviation = (
    limitPrice: number | string | Decimal,
    marketPrice: number | string | Decimal
  ): boolean => {
    const limit = toDecimal(limitPrice)
    const market = toDecimal(marketPrice)
    const maxDeviation = toDecimal(config.value.priceValidation.maxPriceDeviationPercent).dividedBy(100)
    
    if (market.isZero()) return false
    
    const deviation = limit.minus(market).abs().dividedBy(market)
    return deviation.lessThanOrEqualTo(maxDeviation)
  }
  
  /**
   * Reset to defaults
   */
  const resetToDefaults = (): void => {
    config.value = { ...defaultConfig }
    lastFetched.value = 0
  }
  
  return {
    // State
    config: readonly(config),
    loading: readonly(loading),
    error: readonly(error),
    
    // Methods
    loadConfig,
    updateConfig,
    resetToDefaults,
    
    // Fee helpers
    getFeeRate,
    
    // Validation helpers
    isLeverageAllowed,
    isPositionValueAllowed,
    meetsMinimumNotional,
    isPriceWithinDeviation,
  }
}
