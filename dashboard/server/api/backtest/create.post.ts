/**
 * Create a new backtest session
 * 
 * POST /api/backtest/create
 * 
 * Body:
 * {
 *   symbol: string,
 *   startDate: string,
 *   endDate: string,
 *   initialCapital: number,
 *   positionSizePercent: number,
 *   maxOpenTrades: number,
 *   useStopOrders: boolean,
 *   useTakeProfits: boolean
 * }
 * 
 * Returns:
 * {
 *   sessionId: string
 * }
 */

import { requireAuth } from '../../utils/security'
import { backtestManager, type BacktestConfig } from '../../utils/backtest-manager'

// Validation patterns
const SYMBOL_PATTERN = /^[A-Z0-9]{2,10}(-[A-Z0-9]{2,10})?$/  // e.g., BTC-USD, ETH, BTCUSD
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/  // YYYY-MM-DD

// Session limit to prevent resource exhaustion
const MAX_CONCURRENT_SESSIONS = 10

/**
 * Validate date string format and check it's a valid date
 */
function isValidDate(dateStr: string): boolean {
  if (!DATE_PATTERN.test(dateStr)) return false
  const date = new Date(dateStr)
  return !isNaN(date.getTime())
}

export default defineEventHandler(async (event) => {
  // Require authentication
  requireAuth(event)

  const body = await readBody<BacktestConfig>(event)

  // Validate required fields
  if (!body.symbol || !body.startDate || !body.endDate) {
    throw createError({
      statusCode: 400,
      message: 'Missing required fields: symbol, startDate, endDate',
    })
  }

  // Validate symbol format
  const symbol = body.symbol.toUpperCase().trim()
  if (!SYMBOL_PATTERN.test(symbol)) {
    throw createError({
      statusCode: 400,
      message: 'Invalid symbol format. Expected format: BTC-USD, ETH, or BTCUSD',
    })
  }

  // Validate date formats
  if (!isValidDate(body.startDate)) {
    throw createError({
      statusCode: 400,
      message: 'Invalid startDate format. Expected YYYY-MM-DD',
    })
  }

  if (!isValidDate(body.endDate)) {
    throw createError({
      statusCode: 400,
      message: 'Invalid endDate format. Expected YYYY-MM-DD',
    })
  }

  // Validate date range
  const startDate = new Date(body.startDate)
  const endDate = new Date(body.endDate)
  if (startDate >= endDate) {
    throw createError({
      statusCode: 400,
      message: 'startDate must be before endDate',
    })
  }

  // Validate numeric parameters
  const initialCapital = body.initialCapital ?? 10000
  if (typeof initialCapital !== 'number' || initialCapital <= 0 || initialCapital > 1e12) {
    throw createError({
      statusCode: 400,
      message: 'initialCapital must be a positive number (max 1 trillion)',
    })
  }

  const positionSizePercent = body.positionSizePercent ?? 0.02
  if (typeof positionSizePercent !== 'number' || positionSizePercent <= 0 || positionSizePercent > 1) {
    throw createError({
      statusCode: 400,
      message: 'positionSizePercent must be between 0 and 1 (exclusive)',
    })
  }

  const maxOpenTrades = body.maxOpenTrades ?? 3
  if (!Number.isInteger(maxOpenTrades) || maxOpenTrades < 1 || maxOpenTrades > 100) {
    throw createError({
      statusCode: 400,
      message: 'maxOpenTrades must be an integer between 1 and 100',
    })
  }

  // Check session limit
  const currentSessions = backtestManager.getAllSessions()
  const activeSessions = currentSessions.filter(s => 
    s.state.status === 'running' || s.state.status === 'paused' || s.state.status === 'idle'
  )
  
  if (activeSessions.length >= MAX_CONCURRENT_SESSIONS) {
    throw createError({
      statusCode: 429,
      message: `Maximum concurrent sessions (${MAX_CONCURRENT_SESSIONS}) reached. Please stop or delete existing sessions.`,
    })
  }

  // Set defaults with validated values
  const config: BacktestConfig = {
    symbol,
    startDate: body.startDate,
    endDate: body.endDate,
    initialCapital,
    positionSizePercent,
    maxOpenTrades,
    useStopOrders: body.useStopOrders !== false,
    useTakeProfits: body.useTakeProfits !== false,
  }

  const sessionId = backtestManager.createSession(config)

  return {
    sessionId,
    config,
  }
})
