/**
 * Order Validation Composable
 * 
 * CRITICAL: Comprehensive pre-trade risk checks before order submission.
 * Validates position limits, price sanity, leverage, and daily loss limits.
 */

import Decimal from 'decimal.js'
import {
  toDecimal,
  calculateNotional,
  calculateMargin,
  formatCurrency,
} from '~/utils/financial'

export interface OrderParams {
  pair: string
  side: 'long' | 'short'
  orderType: 'market' | 'limit' | 'stop'
  size: string | number
  price?: string | number          // Entry price (limit price or market price)
  leverage: number
  stopLoss?: string | number
  takeProfit?: string | number
}

export interface AccountState {
  availableBalance: string | number
  equity: string | number
  currentDailyPnL: string | number
  openPositions: number
  existingPositionValue?: string | number  // Existing position in same pair
}

export interface MarketState {
  currentPrice: string | number
  bid?: string | number
  ask?: string | number
  dailyVolume?: string | number
}

export interface ValidationResult {
  isValid: boolean
  errors: ValidationError[]
  warnings: ValidationWarning[]
}

export interface ValidationError {
  code: string
  message: string
  field?: string
}

export interface ValidationWarning {
  code: string
  message: string
}

export const useOrderValidation = () => {
  const { config } = useTradingConfig()
  
  /**
   * Validate an order before submission
   */
  const validateOrder = (
    order: OrderParams,
    account: AccountState,
    market: MarketState
  ): ValidationResult => {
    const errors: ValidationError[] = []
    const warnings: ValidationWarning[] = []
    
    // Convert values to Decimal for precision
    const size = toDecimal(order.size)
    const price = toDecimal(order.price || market.currentPrice)
    const currentPrice = toDecimal(market.currentPrice)
    const availableBalance = toDecimal(account.availableBalance)
    const equity = toDecimal(account.equity)
    const currentDailyPnL = toDecimal(account.currentDailyPnL)
    const limits = config.value.positionLimits
    const priceValidation = config.value.priceValidation
    
    // ===== BASIC VALIDATION =====
    
    // Size must be positive
    if (size.lessThanOrEqualTo(0)) {
      errors.push({
        code: 'INVALID_SIZE',
        message: 'Order size must be greater than zero',
        field: 'size',
      })
    }
    
    // Price must be positive
    if (price.lessThanOrEqualTo(0)) {
      errors.push({
        code: 'INVALID_PRICE',
        message: 'Price must be greater than zero',
        field: 'price',
      })
    }
    
    // ===== NOTIONAL VALUE CHECKS =====
    
    const notional = calculateNotional(size, price)
    
    // Minimum notional check
    const minNotional = toDecimal(priceValidation.minNotionalValue)
    if (notional.lessThan(minNotional)) {
      errors.push({
        code: 'BELOW_MIN_NOTIONAL',
        message: `Order value ($${formatCurrency(notional)}) is below minimum ($${formatCurrency(minNotional)})`,
        field: 'size',
      })
    }
    
    // Maximum position value check
    const maxPositionValue = toDecimal(limits.maxPositionValue)
    if (notional.greaterThan(maxPositionValue)) {
      errors.push({
        code: 'EXCEEDS_MAX_POSITION',
        message: `Order value ($${formatCurrency(notional)}) exceeds maximum ($${formatCurrency(maxPositionValue)})`,
        field: 'size',
      })
    }
    
    // ===== MARGIN & BALANCE CHECKS =====
    
    const margin = calculateMargin(notional, order.leverage)
    
    // Sufficient balance check
    if (margin.greaterThan(availableBalance)) {
      errors.push({
        code: 'INSUFFICIENT_BALANCE',
        message: `Required margin ($${formatCurrency(margin)}) exceeds available balance ($${formatCurrency(availableBalance)})`,
        field: 'size',
      })
    }
    
    // Position size as percentage of equity
    const maxPositionPercent = toDecimal(limits.maxPositionPercentOfEquity).dividedBy(100)
    const positionPercent = notional.dividedBy(equity)
    if (!equity.isZero() && positionPercent.greaterThan(maxPositionPercent)) {
      errors.push({
        code: 'EXCEEDS_EQUITY_PERCENT',
        message: `Position is ${positionPercent.times(100).toFixed(1)}% of equity (max: ${maxPositionPercent.times(100).toFixed(0)}%)`,
        field: 'size',
      })
    }
    
    // ===== LEVERAGE CHECKS =====
    
    if (order.leverage < 1) {
      errors.push({
        code: 'INVALID_LEVERAGE',
        message: 'Leverage must be at least 1x',
        field: 'leverage',
      })
    }
    
    if (order.leverage > limits.maxLeverage) {
      errors.push({
        code: 'EXCEEDS_MAX_LEVERAGE',
        message: `Leverage ${order.leverage}x exceeds maximum ${limits.maxLeverage}x`,
        field: 'leverage',
      })
    }
    
    // High leverage warning
    if (order.leverage > 20) {
      warnings.push({
        code: 'HIGH_LEVERAGE',
        message: `High leverage (${order.leverage}x) significantly increases liquidation risk`,
      })
    }
    
    // ===== PRICE SANITY CHECKS =====
    
    if (order.orderType === 'limit' && order.price) {
      const limitPrice = toDecimal(order.price)
      const maxDeviation = toDecimal(priceValidation.maxPriceDeviationPercent).dividedBy(100)
      const deviation = limitPrice.minus(currentPrice).abs().dividedBy(currentPrice)
      
      if (deviation.greaterThan(maxDeviation)) {
        errors.push({
          code: 'PRICE_DEVIATION_EXCEEDED',
          message: `Limit price deviates ${deviation.times(100).toFixed(1)}% from market (max: ${maxDeviation.times(100).toFixed(0)}%)`,
          field: 'price',
        })
      }
      
      // Check if limit price makes sense for the side
      if (order.side === 'long' && limitPrice.greaterThan(currentPrice.times(1.01))) {
        warnings.push({
          code: 'UNFAVORABLE_LIMIT_LONG',
          message: 'Limit buy price is above current market price',
        })
      }
      if (order.side === 'short' && limitPrice.lessThan(currentPrice.times(0.99))) {
        warnings.push({
          code: 'UNFAVORABLE_LIMIT_SHORT',
          message: 'Limit sell price is below current market price',
        })
      }
    }
    
    // ===== DAILY LOSS LIMIT CHECKS =====
    
    const maxDailyLoss = toDecimal(limits.maxDailyLoss)
    const maxDailyLossPercent = toDecimal(limits.maxDailyLossPercent).dividedBy(100)
    const maxDailyLossFromPercent = equity.times(maxDailyLossPercent)
    const effectiveMaxLoss = Decimal.min(maxDailyLoss, maxDailyLossFromPercent)
    
    // Check if already at daily loss limit
    if (currentDailyPnL.isNegative() && currentDailyPnL.abs().greaterThanOrEqualTo(effectiveMaxLoss)) {
      errors.push({
        code: 'DAILY_LOSS_LIMIT_REACHED',
        message: `Daily loss limit reached. Current loss: $${formatCurrency(currentDailyPnL.abs())}`,
      })
    }
    
    // Warn if close to daily loss limit
    if (currentDailyPnL.isNegative()) {
      const lossPercent = currentDailyPnL.abs().dividedBy(effectiveMaxLoss).times(100)
      if (lossPercent.greaterThan(70)) {
        warnings.push({
          code: 'NEAR_DAILY_LOSS_LIMIT',
          message: `${lossPercent.toFixed(0)}% of daily loss limit used`,
        })
      }
    }
    
    // ===== POSITION COUNT CHECK =====
    
    if (account.openPositions >= limits.maxOpenPositions) {
      errors.push({
        code: 'MAX_POSITIONS_REACHED',
        message: `Maximum open positions (${limits.maxOpenPositions}) reached`,
      })
    }
    
    // ===== STOP LOSS VALIDATION =====
    
    if (order.stopLoss) {
      const stopLoss = toDecimal(order.stopLoss)
      
      if (order.side === 'long' && stopLoss.greaterThanOrEqualTo(price)) {
        errors.push({
          code: 'INVALID_STOP_LOSS_LONG',
          message: 'Stop loss must be below entry price for long positions',
          field: 'stopLoss',
        })
      }
      
      if (order.side === 'short' && stopLoss.lessThanOrEqualTo(price)) {
        errors.push({
          code: 'INVALID_STOP_LOSS_SHORT',
          message: 'Stop loss must be above entry price for short positions',
          field: 'stopLoss',
        })
      }
      
      // Check stop loss distance
      const stopDistance = stopLoss.minus(price).abs().dividedBy(price).times(100)
      if (stopDistance.greaterThan(50)) {
        warnings.push({
          code: 'WIDE_STOP_LOSS',
          message: `Stop loss is ${stopDistance.toFixed(1)}% from entry`,
        })
      }
    } else {
      // Warn about missing stop loss
      warnings.push({
        code: 'NO_STOP_LOSS',
        message: 'Consider setting a stop loss to manage risk',
      })
    }
    
    // ===== TAKE PROFIT VALIDATION =====
    
    if (order.takeProfit) {
      const takeProfit = toDecimal(order.takeProfit)
      
      if (order.side === 'long' && takeProfit.lessThanOrEqualTo(price)) {
        errors.push({
          code: 'INVALID_TAKE_PROFIT_LONG',
          message: 'Take profit must be above entry price for long positions',
          field: 'takeProfit',
        })
      }
      
      if (order.side === 'short' && takeProfit.greaterThanOrEqualTo(price)) {
        errors.push({
          code: 'INVALID_TAKE_PROFIT_SHORT',
          message: 'Take profit must be below entry price for short positions',
          field: 'takeProfit',
        })
      }
    }
    
    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    }
  }
  
  /**
   * Quick check if order can be submitted (used for button state)
   */
  const canSubmitOrder = (
    order: Partial<OrderParams>,
    account: Partial<AccountState>
  ): boolean => {
    // Basic checks only for button enablement
    if (!order.size || toDecimal(order.size).lessThanOrEqualTo(0)) return false
    if (!order.leverage || order.leverage < 1) return false
    if (order.orderType === 'limit' && (!order.price || toDecimal(order.price).lessThanOrEqualTo(0))) return false
    
    // Check margin
    if (order.price && account.availableBalance) {
      const notional = calculateNotional(order.size, order.price)
      const margin = calculateMargin(notional, order.leverage)
      if (margin.greaterThan(toDecimal(account.availableBalance))) return false
    }
    
    return true
  }
  
  return {
    validateOrder,
    canSubmitOrder,
  }
}
