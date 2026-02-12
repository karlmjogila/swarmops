/**
 * Composable for managing trade markers and overlays on charts
 * 
 * Includes rate limiting to prevent exceeding API limits.
 */

import type { 
  TradeMarker, 
  TradeOverlay, 
  TradeZone,
  PriceLine,
  TradeMarkerConfig,
  TradeStats,
} from '~/types/trade-markers'
import { defaultMarkerConfig } from '~/types/trade-markers'
import { RateLimiter, debounce } from '~/utils/rate-limiter'

// Rate limiter for API calls - 60 requests per minute with 80% headroom
const apiRateLimiter = new RateLimiter({
  maxRequests: 60,
  windowMs: 60000,
  headroom: 0.8,
  retryAfterMs: 2000,
})

export const useTradeMarkers = () => {
  // State
  const markers = ref<Map<string, TradeMarker>>(new Map())
  const overlays = ref<Map<string, TradeOverlay>>(new Map())
  const zones = ref<Map<string, TradeZone>>(new Map())
  const priceLines = ref<Map<string, PriceLine>>(new Map())
  const config = ref<TradeMarkerConfig>({ ...defaultMarkerConfig })
  
  const selectedTradeId = ref<string | null>(null)
  const hoveredMarkerId = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const allMarkers = computed(() => Array.from(markers.value.values()))
  const allOverlays = computed(() => Array.from(overlays.value.values()))
  const allZones = computed(() => Array.from(zones.value.values()))
  const allPriceLines = computed(() => Array.from(priceLines.value.values()))
  
  const activeOverlays = computed(() => 
    allOverlays.value.filter(o => o.isActive)
  )
  
  const highlightedOverlays = computed(() => 
    allOverlays.value.filter(o => o.isHighlighted)
  )

  const stats = computed((): TradeStats => {
    const overlayList = allOverlays.value
    
    const totalTrades = overlayList.length
    const winningTrades = overlayList.filter(o => o.outcome === 'win').length
    const losingTrades = overlayList.filter(o => o.outcome === 'loss').length
    const breakevenTrades = overlayList.filter(o => o.outcome === 'breakeven').length
    const pendingTrades = overlayList.filter(o => o.outcome === 'pending').length
    
    const winRate = totalTrades > 0 ? (winningTrades / (totalTrades - pendingTrades)) * 100 : 0
    
    const wins = overlayList.filter(o => o.outcome === 'win')
    const losses = overlayList.filter(o => o.outcome === 'loss')
    
    const averageWin = wins.length > 0
      ? wins.reduce((sum, o) => sum + o.pnl, 0) / wins.length
      : 0
    
    const averageLoss = losses.length > 0
      ? Math.abs(losses.reduce((sum, o) => sum + o.pnl, 0) / losses.length)
      : 0
    
    const totalPnl = overlayList.reduce((sum, o) => sum + o.pnl, 0)
    const totalFees = overlayList.reduce((sum, o) => sum + o.fees, 0)
    
    const profitFactor = averageLoss > 0 ? averageWin / averageLoss : 0
    
    const completedTrades = overlayList.filter(o => o.rMultiple !== undefined)
    const averageRMultiple = completedTrades.length > 0
      ? completedTrades.reduce((sum, o) => sum + o.rMultiple, 0) / completedTrades.length
      : 0
    
    return {
      totalTrades,
      winningTrades,
      losingTrades,
      breakevenTrades,
      pendingTrades,
      winRate,
      averageWin,
      averageLoss,
      profitFactor,
      averageRMultiple,
      totalPnl,
      totalFees,
      netPnl: totalPnl - totalFees,
    }
  })

  // Methods
  const addMarker = (marker: TradeMarker) => {
    markers.value.set(marker.id, marker)
  }

  const removeMarker = (markerId: string) => {
    markers.value.delete(markerId)
  }

  const updateMarker = (markerId: string, updates: Partial<TradeMarker>) => {
    const marker = markers.value.get(markerId)
    if (marker) {
      markers.value.set(markerId, { ...marker, ...updates })
    }
  }

  const addOverlay = (overlay: TradeOverlay) => {
    overlays.value.set(overlay.id, overlay)
  }

  const removeOverlay = (overlayId: string) => {
    overlays.value.delete(overlayId)
  }

  const updateOverlay = (overlayId: string, updates: Partial<TradeOverlay>) => {
    const overlay = overlays.value.get(overlayId)
    if (overlay) {
      overlays.value.set(overlayId, { ...overlay, ...updates })
    }
  }

  const addZone = (zone: TradeZone) => {
    zones.value.set(zone.id, zone)
  }

  const removeZone = (zoneId: string) => {
    zones.value.delete(zoneId)
  }

  const addPriceLine = (line: PriceLine) => {
    priceLines.value.set(line.id, line)
  }

  const removePriceLine = (lineId: string) => {
    priceLines.value.delete(lineId)
  }

  const getMarkersByTrade = (tradeId: string): TradeMarker[] => {
    return allMarkers.value.filter(m => m.tradeId === tradeId)
  }

  const getOverlayByTrade = (tradeId: string): TradeOverlay | undefined => {
    return allOverlays.value.find(o => o.tradeId === tradeId)
  }

  const getZonesByTrade = (tradeId: string): TradeZone[] => {
    return allZones.value.filter(z => z.tradeId === tradeId)
  }

  const selectTrade = (tradeId: string | null) => {
    selectedTradeId.value = tradeId
    
    // Highlight selected trade overlay
    allOverlays.value.forEach(overlay => {
      updateOverlay(overlay.id, {
        isHighlighted: overlay.tradeId === tradeId
      })
    })
  }

  const hoverMarker = (markerId: string | null) => {
    hoveredMarkerId.value = markerId
  }

  const clearAll = () => {
    markers.value.clear()
    overlays.value.clear()
    zones.value.clear()
    priceLines.value.clear()
    selectedTradeId.value = null
    hoveredMarkerId.value = null
  }

  const clearByTrade = (tradeId: string) => {
    // Remove all markers for this trade
    allMarkers.value
      .filter(m => m.tradeId === tradeId)
      .forEach(m => removeMarker(m.id))
    
    // Remove overlay
    const overlay = getOverlayByTrade(tradeId)
    if (overlay) {
      removeOverlay(overlay.id)
    }
    
    // Remove zones
    getZonesByTrade(tradeId).forEach(z => removeZone(z.id))
  }

  /**
   * Load trade markers from API for a specific symbol and timeframe
   * Includes rate limiting to prevent exceeding API limits.
   */
  const loadTrades = async (symbol: string, timeframe: string, startTime?: number, endTime?: number) => {
    // Check rate limit before making request
    if (!apiRateLimiter.canRequest()) {
      const waitTime = apiRateLimiter.getWaitTime()
      error.value = `Rate limited. Please wait ${Math.ceil(waitTime / 1000)}s.`
      console.warn(`Rate limited: waiting ${waitTime}ms before next request`)
      
      // Wait and retry
      await apiRateLimiter.waitForSlot()
    }
    
    loading.value = true
    error.value = null
    
    try {
      // Record this request
      apiRateLimiter.recordRequest()
      
      const config = useRuntimeConfig()
      const apiBaseUrl = config.public.apiBaseUrl || 'http://localhost:8000'
      
      const response = await $fetch<{ trades: any[] }>(
        `${apiBaseUrl}/api/trades`,
        {
          query: {
            symbol: symbol.replace('/', ''),
            timeframe,
            start_time: startTime,
            end_time: endTime,
          },
          timeout: 10000, // 10 second timeout
        }
      )
      
      // Convert API trades to markers and overlays
      response.trades.forEach(trade => {
        createTradeMarkers(trade)
      })
      
    } catch (err: any) {
      // Check for rate limit response (429)
      if (err.statusCode === 429) {
        const retryAfter = parseInt(err.headers?.['retry-after'] || '60', 10) * 1000
        apiRateLimiter.markLimited(retryAfter)
        error.value = `Rate limited by server. Retry after ${Math.ceil(retryAfter / 1000)}s.`
      } else {
        error.value = err.message || 'Failed to load trades'
      }
      console.error('Error loading trades:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Debounced version of loadTrades for use with reactive inputs
   * Prevents excessive API calls when parameters change rapidly
   */
  const loadTradesDebounced = debounce(
    (symbol: string, timeframe: string, startTime?: number, endTime?: number) => {
      loadTrades(symbol, timeframe, startTime, endTime)
    },
    500 // 500ms debounce
  )

  /**
   * Create markers and overlay from a trade record
   */
  const createTradeMarkers = (trade: any) => {
    const tradeId = trade.id
    
    // Create entry marker
    const entryMarker: TradeMarker = {
      id: `${tradeId}-entry`,
      time: Math.floor(new Date(trade.entry_time).getTime() / 1000),
      type: 'entry',
      side: trade.direction.toLowerCase() as 'buy' | 'sell',
      price: trade.entry_price,
      quantity: trade.quantity,
      reason: trade.reasoning,
      tradeId,
      strategyId: trade.strategy_rule_id,
      showTooltip: true,
    }
    addMarker(entryMarker)
    
    // Create exit marker if trade is closed
    if (trade.exit_time && trade.exit_price) {
      const exitMarker: TradeMarker = {
        id: `${tradeId}-exit`,
        time: Math.floor(new Date(trade.exit_time).getTime() / 1000),
        type: 'exit',
        side: trade.direction.toLowerCase() === 'buy' ? 'sell' : 'buy',
        price: trade.exit_price,
        quantity: trade.quantity,
        reason: trade.exit_reason,
        pnl: trade.pnl_absolute,
        pnlPercent: trade.pnl_absolute / (trade.entry_price * trade.quantity) * 100,
        rMultiple: trade.pnl_r_multiple,
        fees: trade.fees_paid,
        tradeId,
        showTooltip: true,
      }
      addMarker(exitMarker)
    }
    
    // Create partial exit markers
    if (trade.partial_exits) {
      trade.partial_exits.forEach((exit: any, index: number) => {
        const partialMarker: TradeMarker = {
          id: `${tradeId}-partial-${index}`,
          time: Math.floor(new Date(exit.time).getTime() / 1000),
          type: 'partial-exit',
          side: trade.direction.toLowerCase() === 'buy' ? 'sell' : 'buy',
          price: exit.price,
          quantity: exit.quantity,
          pnl: exit.pnl,
          tradeId,
          showTooltip: true,
        }
        addMarker(partialMarker)
      })
    }
    
    // Determine trade outcome
    let outcome: 'win' | 'loss' | 'breakeven' | 'pending' = 'pending'
    if (trade.outcome) {
      outcome = trade.outcome.toLowerCase()
    } else if (trade.pnl_absolute > 0) {
      outcome = 'win'
    } else if (trade.pnl_absolute < 0) {
      outcome = 'loss'
    } else if (trade.exit_time) {
      outcome = 'breakeven'
    }
    
    // Create overlay
    const overlay: TradeOverlay = {
      id: `overlay-${tradeId}`,
      tradeId,
      entryTime: Math.floor(new Date(trade.entry_time).getTime() / 1000),
      entryPrice: trade.entry_price,
      exitTime: trade.exit_time ? Math.floor(new Date(trade.exit_time).getTime() / 1000) : undefined,
      exitPrice: trade.exit_price,
      side: trade.direction.toLowerCase() as 'buy' | 'sell',
      quantity: trade.quantity,
      outcome,
      pnl: trade.pnl_absolute || 0,
      pnlPercent: trade.pnl_absolute ? (trade.pnl_absolute / (trade.entry_price * trade.quantity) * 100) : 0,
      rMultiple: trade.pnl_r_multiple || 0,
      fees: trade.fees_paid || 0,
      stopLoss: trade.current_stop_loss || trade.initial_stop_loss,
      takeProfitLevels: trade.take_profit_levels || [],
      reasoning: trade.reasoning,
      entryPattern: trade.price_action_context?.entry_type,
      exitReason: trade.exit_reason,
      isActive: !trade.exit_time,
      isHighlighted: false,
    }
    addOverlay(overlay)
    
    // Create zones if enabled
    if (config.value.showTradeZones) {
      const zoneOpacity = 0.1
      
      // Entry zone (small range around entry)
      const entryZone: TradeZone = {
        id: `${tradeId}-entry-zone`,
        tradeId,
        type: 'entry-zone',
        topPrice: trade.entry_price * 1.002,
        bottomPrice: trade.entry_price * 0.998,
        startTime: entryMarker.time,
        endTime: overlay.exitTime,
        color: trade.direction === 'buy' ? config.value.colors.buyEntry : config.value.colors.sellEntry,
        opacity: zoneOpacity,
        label: 'Entry',
      }
      addZone(entryZone)
      
      // Stop loss zone
      if (overlay.stopLoss) {
        const stopZone: TradeZone = {
          id: `${tradeId}-stop-zone`,
          tradeId,
          type: 'stop-zone',
          topPrice: Math.max(overlay.stopLoss, trade.entry_price),
          bottomPrice: Math.min(overlay.stopLoss, trade.entry_price),
          startTime: entryMarker.time,
          endTime: overlay.exitTime,
          color: config.value.colors.stopLoss,
          opacity: zoneOpacity,
          label: 'Stop Loss',
        }
        addZone(stopZone)
      }
      
      // Take profit zones
      if (overlay.takeProfitLevels) {
        overlay.takeProfitLevels.forEach((tp, index) => {
          const tpZone: TradeZone = {
            id: `${tradeId}-tp-zone-${index}`,
            tradeId,
            type: 'target-zone',
            topPrice: Math.max(tp, trade.entry_price),
            bottomPrice: Math.min(tp, trade.entry_price),
            startTime: entryMarker.time,
            endTime: overlay.exitTime,
            color: config.value.colors.takeProfit,
            opacity: zoneOpacity,
            label: `TP${index + 1}`,
          }
          addZone(tpZone)
        })
      }
    }
    
    // Create price lines for active trades
    if (overlay.isActive && config.value.showPriceLines) {
      if (overlay.stopLoss) {
        addPriceLine({
          id: `${tradeId}-sl-line`,
          price: overlay.stopLoss,
          color: config.value.colors.stopLoss,
          width: 2,
          style: 'dashed',
          label: 'SL',
          showLabel: true,
          interactive: false,
        })
      }
      
      if (overlay.takeProfitLevels) {
        overlay.takeProfitLevels.forEach((tp, index) => {
          addPriceLine({
            id: `${tradeId}-tp-line-${index}`,
            price: tp,
            color: config.value.colors.takeProfit,
            width: 2,
            style: 'dashed',
            label: `TP${index + 1}`,
            showLabel: true,
            interactive: false,
          })
        })
      }
    }
  }

  /**
   * Update configuration
   */
  const updateConfig = (updates: Partial<TradeMarkerConfig>) => {
    config.value = { ...config.value, ...updates }
  }

  return {
    // State
    markers,
    overlays,
    zones,
    priceLines,
    config,
    selectedTradeId,
    hoveredMarkerId,
    loading,
    error,
    
    // Computed
    allMarkers,
    allOverlays,
    allZones,
    allPriceLines,
    activeOverlays,
    highlightedOverlays,
    stats,
    
    // Methods
    addMarker,
    removeMarker,
    updateMarker,
    addOverlay,
    removeOverlay,
    updateOverlay,
    addZone,
    removeZone,
    addPriceLine,
    removePriceLine,
    getMarkersByTrade,
    getOverlayByTrade,
    getZonesByTrade,
    selectTrade,
    hoverMarker,
    clearAll,
    clearByTrade,
    loadTrades,
    loadTradesDebounced,
    createTradeMarkers,
    updateConfig,
  }
}
