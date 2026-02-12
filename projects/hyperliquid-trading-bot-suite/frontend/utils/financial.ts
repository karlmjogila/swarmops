/**
 * Financial Math Utilities using Decimal.js for precise calculations
 * 
 * CRITICAL: Never use JavaScript floats for financial calculations.
 * This module provides precision arithmetic for all trading operations.
 */

import Decimal from 'decimal.js'

// Configure Decimal for financial precision
Decimal.set({
  precision: 20,
  rounding: Decimal.ROUND_DOWN,
  toExpNeg: -9,
  toExpPos: 9,
})

/**
 * Convert a number, string, or Decimal to Decimal
 */
export function toDecimal(value: number | string | Decimal | null | undefined): Decimal {
  if (value === null || value === undefined || value === '') {
    return new Decimal(0)
  }
  if (value instanceof Decimal) {
    return value
  }
  return new Decimal(String(value))
}

/**
 * Calculate notional value (size × price)
 */
export function calculateNotional(
  size: number | string | Decimal,
  price: number | string | Decimal
): Decimal {
  return toDecimal(size).times(toDecimal(price))
}

/**
 * Calculate margin required (notional / leverage)
 */
export function calculateMargin(
  notional: number | string | Decimal,
  leverage: number | string | Decimal
): Decimal {
  const lev = toDecimal(leverage)
  if (lev.isZero()) return new Decimal(0)
  return toDecimal(notional).dividedBy(lev)
}

/**
 * Calculate liquidation price
 * For long: entryPrice × (1 - 1/leverage × maintenanceMargin)
 * For short: entryPrice × (1 + 1/leverage × maintenanceMargin)
 */
export function calculateLiquidationPrice(
  entryPrice: number | string | Decimal,
  leverage: number | string | Decimal,
  isLong: boolean,
  maintenanceMarginRate: number | string | Decimal = 0.05 // 5% default
): Decimal {
  const entry = toDecimal(entryPrice)
  const lev = toDecimal(leverage)
  const mmRate = toDecimal(maintenanceMarginRate)
  
  if (entry.isZero() || lev.isZero()) return new Decimal(0)
  
  // Distance to liquidation as percentage of entry
  const liqDistance = new Decimal(1).dividedBy(lev).times(new Decimal(1).minus(mmRate))
  
  if (isLong) {
    return entry.times(new Decimal(1).minus(liqDistance))
  } else {
    return entry.times(new Decimal(1).plus(liqDistance))
  }
}

/**
 * Calculate estimated fees
 */
export function calculateFees(
  notional: number | string | Decimal,
  feeRate: number | string | Decimal
): Decimal {
  return toDecimal(notional).times(toDecimal(feeRate))
}

/**
 * Calculate P&L for a trade
 */
export function calculatePnL(
  entryPrice: number | string | Decimal,
  currentPrice: number | string | Decimal,
  size: number | string | Decimal,
  isLong: boolean
): Decimal {
  const entry = toDecimal(entryPrice)
  const current = toDecimal(currentPrice)
  const qty = toDecimal(size)
  
  const priceDiff = current.minus(entry)
  const direction = isLong ? new Decimal(1) : new Decimal(-1)
  
  return priceDiff.times(qty).times(direction)
}

/**
 * Calculate P&L percentage
 */
export function calculatePnLPercent(
  entryPrice: number | string | Decimal,
  currentPrice: number | string | Decimal,
  leverage: number | string | Decimal,
  isLong: boolean
): Decimal {
  const entry = toDecimal(entryPrice)
  const current = toDecimal(currentPrice)
  const lev = toDecimal(leverage)
  
  if (entry.isZero()) return new Decimal(0)
  
  const priceChangePercent = current.minus(entry).dividedBy(entry).times(100)
  const direction = isLong ? new Decimal(1) : new Decimal(-1)
  
  return priceChangePercent.times(direction).times(lev)
}

/**
 * Calculate maximum position size based on available balance and leverage
 */
export function calculateMaxSize(
  availableBalance: number | string | Decimal,
  leverage: number | string | Decimal,
  price: number | string | Decimal
): Decimal {
  const balance = toDecimal(availableBalance)
  const lev = toDecimal(leverage)
  const p = toDecimal(price)
  
  if (p.isZero()) return new Decimal(0)
  
  return balance.times(lev).dividedBy(p)
}

/**
 * Format a Decimal for display
 */
export function formatDecimal(
  value: number | string | Decimal,
  decimals: number = 2
): string {
  return toDecimal(value).toFixed(decimals)
}

/**
 * Format as currency (without symbol)
 */
export function formatCurrency(
  value: number | string | Decimal,
  decimals: number = 2
): string {
  const d = toDecimal(value)
  const parts = d.toFixed(decimals).split('.')
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return parts.join('.')
}

/**
 * Format as price (with appropriate decimals based on magnitude)
 */
export function formatPrice(value: number | string | Decimal): string {
  const d = toDecimal(value)
  if (d.isZero()) return '—'
  
  // More decimals for smaller prices
  const abs = d.abs()
  let decimals = 2
  if (abs.lessThan(0.01)) decimals = 6
  else if (abs.lessThan(1)) decimals = 4
  else if (abs.greaterThan(1000)) decimals = 2
  
  const parts = d.toFixed(decimals).split('.')
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return parts.join('.')
}

/**
 * Check if value is within a percentage tolerance of target
 */
export function isWithinTolerance(
  value: number | string | Decimal,
  target: number | string | Decimal,
  tolerancePercent: number | string | Decimal
): boolean {
  const v = toDecimal(value)
  const t = toDecimal(target)
  const tol = toDecimal(tolerancePercent).dividedBy(100)
  
  if (t.isZero()) return v.isZero()
  
  const diff = v.minus(t).abs().dividedBy(t)
  return diff.lessThanOrEqualTo(tol)
}

/**
 * Round to tick size (common in trading)
 */
export function roundToTick(
  value: number | string | Decimal,
  tickSize: number | string | Decimal
): Decimal {
  const v = toDecimal(value)
  const tick = toDecimal(tickSize)
  
  if (tick.isZero()) return v
  
  return v.dividedBy(tick).floor().times(tick)
}

/**
 * Compare two Decimal values
 */
export function compareDecimals(
  a: number | string | Decimal,
  b: number | string | Decimal
): number {
  return toDecimal(a).comparedTo(toDecimal(b))
}

// Type exports for external use
export { Decimal }
