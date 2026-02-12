<script lang="ts">
  import { 
    MultiTimeframeChart, 
    PlaybackControls, 
    TradeLog, 
    EquityCurve, 
    DecisionJournal,
    DataSourceSelector
  } from '$lib/components';
  import type { Candle, Trade, Signal, Timeframe, DataSource } from '$lib/types';
  import { createTradeId, createSignalId } from '$lib/types';
  import { backtestState, resetBacktest } from '$lib/stores/backtest';

  // ============================================================================
  // Demo Data - Will be replaced with WebSocket data in Phase 4
  // ============================================================================

  /**
   * Generate realistic demo candle data for testing
   */
  function generateDemoCandles(count: number, timeframe: Timeframe): Candle[] {
    const candles: Candle[] = [];
    let basePrice = 50000; // BTC starting price
    const now = Date.now();
    const tfMinutesMap: Record<Timeframe, number> = {
      '1m': 1,
      '5m': 5,
      '15m': 15,
      '30m': 30,
      '1h': 60,
      '4h': 240,
      '1d': 1440,
      '1w': 10080,
      '1M': 43200,
    };
    const tfMinutes = tfMinutesMap[timeframe];

    for (let i = 0; i < count; i++) {
      const timestamp = new Date(now - (count - i) * tfMinutes * 60 * 1000).toISOString();
      
      // Random walk with trend
      const trend = Math.sin(i / 20) * 100;
      const volatility = Math.random() * 200 - 100;
      basePrice += trend + volatility;
      
      const open = basePrice;
      const close = basePrice + (Math.random() * 300 - 150);
      const high = Math.max(open, close) + Math.random() * 100;
      const low = Math.min(open, close) - Math.random() * 100;
      const volume = Math.random() * 1000 + 500;

      candles.push({
        timestamp,
        open,
        high,
        low,
        close,
        volume,
        timeframe,
        symbol: 'BTCUSD',
      });
    }

    return candles;
  }

  /**
   * Generate demo trade data
   */
  function generateDemoTrades(): Trade[] {
    const candles = demoData['15m'];
    const trades: Trade[] = [];
    
    // Generate a few trades at random points
    for (let i = 10; i < candles.length - 10; i += 20) {
      const entryCandle = candles[i];
      const exitCandle = candles[i + 10];
      const isLong = Math.random() > 0.5;
      const pnl = (Math.random() - 0.4) * 1000; // Slightly profitable bias

      trades.push({
        id: createTradeId(`demo-${i}`),
        signal_id: createSignalId(`signal-${i}`),
        symbol: 'BTCUSD',
        side: isLong ? 'long' : 'short',
        entry_price: entryCandle.close,
        entry_time: entryCandle.timestamp,
        position_size: 0.1,
        stop_loss: isLong ? entryCandle.close - 500 : entryCandle.close + 500,
        take_profits: [
          isLong ? entryCandle.close + 500 : entryCandle.close - 500,
          isLong ? entryCandle.close + 1000 : entryCandle.close - 1000,
        ],
        status: 'closed',
        exit_price: exitCandle.close,
        exit_time: exitCandle.timestamp,
        pnl,
        pnl_percent: (pnl / (entryCandle.close * 0.1)) * 100,
        reasoning: `${isLong ? 'Long' : 'Short'} setup based on ${isLong ? 'support' : 'resistance'} confluence`,
        post_analysis: null,
        max_adverse_excursion: -200,
        max_favorable_excursion: 800,
      });
    }

    return trades;
  }

  /**
   * Generate demo signal data
   */
  function generateDemoSignals(): Signal[] {
    const candles = demoData['15m'];
    const signals: Signal[] = [];
    
    for (let i = 15; i < candles.length - 5; i += 25) {
      const candle = candles[i];
      const isLong = Math.random() > 0.5;

      signals.push({
        id: createSignalId(`signal-${i}`),
        timestamp: candle.timestamp,
        symbol: 'BTCUSD',
        signal_type: isLong ? 'long' : 'short',
        timeframe: '15m',
        entry_price: candle.close,
        stop_loss: isLong ? candle.close - 500 : candle.close + 500,
        take_profit_1: isLong ? candle.close + 500 : candle.close - 500,
        take_profit_2: isLong ? candle.close + 1000 : candle.close - 1000,
        take_profit_3: null,
        confluence_score: Math.floor(Math.random() * 40) + 60,
        patterns_detected: ['le_candle', 'small_wick'],
        setup_type: 'breakout',
        market_phase: 'drive',
        higher_tf_bias: isLong ? 'long' : 'short',
        reasoning: `High confluence ${isLong ? 'long' : 'short'} setup`,
      });
    }

    return signals;
  }

  // Generate demo data for all timeframes
  const demoData: Record<Timeframe, Candle[]> = {
    '1m': generateDemoCandles(300, '1m'),
    '5m': generateDemoCandles(200, '5m'),
    '15m': generateDemoCandles(150, '15m'),
    '30m': generateDemoCandles(100, '30m'),
    '1h': generateDemoCandles(100, '1h'),
    '4h': generateDemoCandles(80, '4h'),
    '1d': generateDemoCandles(60, '1d'),
    '1w': generateDemoCandles(52, '1w'),
    '1M': generateDemoCandles(24, '1M'),
  };

  const demoTrades = generateDemoTrades();
  const demoSignals = generateDemoSignals();

  // ============================================================================
  // State
  // ============================================================================

  let activeTimeframe = $state<Timeframe>('15m');
  let showTrades = $state(true);
  let showSignals = $state(false);
  let activeTab = $state<'chart' | 'trades' | 'journal' | 'equity'>('chart');
  let showSidebar = $state(true);
  
  // Backtest setup state
  let showSetupPanel = $state(true);
  let symbol = $state('BTC');
  let dataSource = $state<DataSource>('auto');
  let startDate = $state('2024-01-01');
  let endDate = $state('2024-12-31');
  let initialCapital = $state(10000);
  let isStarting = $state(false);
  let startError = $state<string | null>(null);

  // ============================================================================
  // Handlers
  // ============================================================================

  function handleTimeframeChange(tf: Timeframe) {
    activeTimeframe = tf;
  }

  function toggleSidebar() {
    showSidebar = !showSidebar;
  }
  
  function handleSymbolChange(newSymbol: string) {
    symbol = newSymbol;
  }
  
  function handleDataSourceChange(source: DataSource) {
    dataSource = source;
  }
  
  async function startBacktest() {
    if (isStarting) return;
    
    isStarting = true;
    startError = null;
    
    try {
      const response = await fetch('/api/backtest/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol,
          start_date: startDate,
          end_date: endDate,
          initial_capital: initialCapital,
          data_source: dataSource,
        }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to start backtest');
      }
      
      const result = await response.json();
      
      // Hide setup panel and reset backtest state
      showSetupPanel = false;
      resetBacktest();
      
      // Update backtest state with new session
      backtestState.update(state => ({
        ...state,
        session_id: result.session_id,
        is_running: true,
      }));
      
    } catch (e) {
      startError = e instanceof Error ? e.message : 'Failed to start backtest';
    } finally {
      isStarting = false;
    }
  }
  
  function showSetup() {
    showSetupPanel = true;
  }

  // ============================================================================
  // Stats
  // ============================================================================

  const stats = $derived(() => {
    const closedTrades = demoTrades.filter((t) => t.status === 'closed');
    const winningTrades = closedTrades.filter((t) => (t.pnl ?? 0) > 0);
    const totalPnl = closedTrades.reduce((sum, t) => sum + (t.pnl ?? 0), 0);

    return {
      totalTrades: closedTrades.length,
      winRate: closedTrades.length > 0 ? winningTrades.length / closedTrades.length : 0,
      totalPnl,
      avgPnl: closedTrades.length > 0 ? totalPnl / closedTrades.length : 0,
    };
  });
</script>

<svelte:head>
  <title>Backtest - HL-Bot V2</title>
</svelte:head>

<div class="h-screen flex flex-col bg-dark-900">
  <!-- Setup Panel Overlay -->
  {#if showSetupPanel}
    <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div class="bg-dark-800 rounded-xl border border-dark-600 w-full max-w-2xl mx-4 overflow-hidden">
        <!-- Panel Header -->
        <div class="px-6 py-4 border-b border-dark-700">
          <h2 class="text-xl font-bold text-white">Start New Backtest</h2>
          <p class="text-sm text-gray-400 mt-1">Configure your backtest parameters and data source</p>
        </div>
        
        <!-- Panel Content -->
        <div class="p-6 space-y-6">
          <!-- Data Source Selector -->
          <DataSourceSelector 
            bind:symbol={symbol}
            bind:timeframe={activeTimeframe}
            bind:dataSource={dataSource}
            onSymbolChange={handleSymbolChange}
            onDataSourceChange={handleDataSourceChange}
          />
          
          <!-- Date Range -->
          <div class="grid grid-cols-2 gap-4">
            <div class="flex flex-col gap-1">
              <label for="start-date" class="text-xs font-medium text-gray-400 uppercase tracking-wide">Start Date</label>
              <input
                type="date"
                id="start-date"
                bind:value={startDate}
                class="px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:outline-none focus:border-primary-500"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label for="end-date" class="text-xs font-medium text-gray-400 uppercase tracking-wide">End Date</label>
              <input
                type="date"
                id="end-date"
                bind:value={endDate}
                class="px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:outline-none focus:border-primary-500"
              />
            </div>
          </div>
          
          <!-- Initial Capital -->
          <div class="flex flex-col gap-1">
            <label for="capital" class="text-xs font-medium text-gray-400 uppercase tracking-wide">Initial Capital ($)</label>
            <input
              type="number"
              id="capital"
              bind:value={initialCapital}
              min="100"
              max="10000000"
              class="px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-white focus:outline-none focus:border-primary-500"
            />
          </div>
          
          <!-- Error Message -->
          {#if startError}
            <div class="p-3 bg-red-900/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
              ⚠️ {startError}
            </div>
          {/if}
        </div>
        
        <!-- Panel Footer -->
        <div class="px-6 py-4 border-t border-dark-700 flex justify-end gap-3">
          <button
            type="button"
            onclick={() => { console.log('Cancel clicked'); showSetupPanel = false; }}
            class="px-4 py-2 rounded-lg bg-dark-700 hover:bg-dark-600 text-gray-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onclick={startBacktest}
            disabled={isStarting}
            class="px-6 py-2 rounded-lg bg-primary-600 hover:bg-primary-500 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {#if isStarting}
              <span class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              Starting...
            {:else}
              🚀 Start Backtest
            {/if}
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Header Bar -->
  <div class="bg-dark-800 border-b border-dark-700 px-6 py-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <h1 class="text-2xl font-bold text-white">Backtest Replay</h1>
        <div class="h-6 w-px bg-dark-600"></div>
        <p class="text-gray-400 text-sm">Visual candle-by-candle backtesting</p>
        {#if $backtestState.session_id}
          <div class="px-2 py-1 bg-green-900/30 border border-green-500/30 rounded text-green-400 text-xs font-medium">
            {symbol} • {dataSource}
          </div>
        {/if}
      </div>
      <div class="flex items-center gap-2">
        {#if !showSetupPanel}
          <button
            onclick={showSetup}
            class="px-3 py-2 rounded-lg bg-primary-600 hover:bg-primary-500 text-white transition-colors flex items-center gap-2"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            <span class="text-sm font-medium">New Backtest</span>
          </button>
        {/if}
        <button
          onclick={toggleSidebar}
          class="px-3 py-2 rounded-lg bg-dark-700 hover:bg-dark-600 text-gray-300 hover:text-white transition-colors flex items-center gap-2"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
          <span class="text-sm font-medium">{showSidebar ? 'Hide' : 'Show'} Sidebar</span>
        </button>
      </div>
    </div>
  </div>

  <!-- Main Content Area -->
  <div class="flex-1 flex overflow-hidden">
    <!-- Chart and Controls Section (Left) -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Stats Bar -->
      <div class="bg-dark-800 border-b border-dark-700 px-6 py-3">
        <div class="grid grid-cols-4 gap-6">
          <div class="flex items-center gap-3">
            <span class="text-2xl">📊</span>
            <div>
              <div class="text-xs text-gray-500 uppercase tracking-wide">Total Trades</div>
              <div class="text-lg font-bold text-white">{stats().totalTrades}</div>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-2xl">🎯</span>
            <div>
              <div class="text-xs text-gray-500 uppercase tracking-wide">Win Rate</div>
              <div class="text-lg font-bold text-white">
                {(stats().winRate * 100).toFixed(1)}%
              </div>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-2xl">{stats().totalPnl >= 0 ? '💰' : '📉'}</span>
            <div>
              <div class="text-xs text-gray-500 uppercase tracking-wide">Total P&L</div>
              <div 
                class="text-lg font-bold"
                class:text-green-400={stats().totalPnl > 0}
                class:text-red-400={stats().totalPnl < 0}
                class:text-gray-400={stats().totalPnl === 0}
              >
                ${stats().totalPnl.toFixed(2)}
              </div>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-2xl">📈</span>
            <div>
              <div class="text-xs text-gray-500 uppercase tracking-wide">Avg P&L</div>
              <div 
                class="text-lg font-bold"
                class:text-green-400={stats().avgPnl > 0}
                class:text-red-400={stats().avgPnl < 0}
                class:text-gray-400={stats().avgPnl === 0}
              >
                ${stats().avgPnl.toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Playback Controls -->
      <div class="bg-dark-800 border-b border-dark-700 px-6 py-3">
        <PlaybackControls sessionId={$backtestState.session_id} />
      </div>

      <!-- Chart Display Options -->
      <div class="bg-dark-800 border-b border-dark-700 px-6 py-2">
        <div class="flex items-center gap-6">
          <label class="flex items-center gap-2 text-gray-300 cursor-pointer hover:text-white transition-colors">
            <input type="checkbox" bind:checked={showTrades} class="checkbox" />
            <span class="text-sm font-medium">Show Trades</span>
          </label>
          <label class="flex items-center gap-2 text-gray-300 cursor-pointer hover:text-white transition-colors">
            <input type="checkbox" bind:checked={showSignals} class="checkbox" />
            <span class="text-sm font-medium">Show Signals</span>
          </label>
        </div>
      </div>

      <!-- Chart Area -->
      <div class="flex-1 bg-dark-900 p-4 overflow-auto">
        <div class="h-full card">
          <MultiTimeframeChart
            candleData={demoData}
            trades={demoTrades}
            signals={demoSignals}
            showTrades={showTrades}
            showSignals={showSignals}
            bind:activeTimeframe={activeTimeframe}
            onTimeframeChange={handleTimeframeChange}
            displayMode="grid"
          />
        </div>
      </div>
    </div>

    <!-- Right Sidebar with Tabs -->
    {#if showSidebar}
      <div class="w-96 bg-dark-800 border-l border-dark-700 flex flex-col">
        <!-- Tab Navigation -->
        <div class="border-b border-dark-700 bg-dark-800">
          <div class="flex">
            <button
              class="flex-1 px-4 py-3 text-sm font-medium transition-colors border-b-2"
              class:border-primary-500={activeTab === 'trades'}
              class:text-primary-400={activeTab === 'trades'}
              class:border-transparent={activeTab !== 'trades'}
              class:text-gray-400={activeTab !== 'trades'}
              class:hover:text-gray-300={activeTab !== 'trades'}
              onclick={() => activeTab = 'trades'}
            >
              💹 Trades
            </button>
            <button
              class="flex-1 px-4 py-3 text-sm font-medium transition-colors border-b-2"
              class:border-primary-500={activeTab === 'journal'}
              class:text-primary-400={activeTab === 'journal'}
              class:border-transparent={activeTab !== 'journal'}
              class:text-gray-400={activeTab !== 'journal'}
              class:hover:text-gray-300={activeTab !== 'journal'}
              onclick={() => activeTab = 'journal'}
            >
              📝 Journal
            </button>
            <button
              class="flex-1 px-4 py-3 text-sm font-medium transition-colors border-b-2"
              class:border-primary-500={activeTab === 'equity'}
              class:text-primary-400={activeTab === 'equity'}
              class:border-transparent={activeTab !== 'equity'}
              class:text-gray-400={activeTab !== 'equity'}
              class:hover:text-gray-300={activeTab !== 'equity'}
              onclick={() => activeTab = 'equity'}
            >
              📊 Equity
            </button>
          </div>
        </div>

        <!-- Tab Content -->
        <div class="flex-1 overflow-hidden">
          {#if activeTab === 'trades'}
            <div class="h-full overflow-auto p-4">
              <TradeLog trades={demoTrades} />
            </div>
          {:else if activeTab === 'journal'}
            <div class="h-full overflow-auto p-4">
              <DecisionJournal />
            </div>
          {:else if activeTab === 'equity'}
            <div class="h-full overflow-auto p-4">
              <EquityCurve trades={demoTrades} />
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Info Banner (Bottom) -->
  <div class="bg-blue-900/20 border-t border-blue-500/30 px-6 py-3">
    <div class="flex items-center gap-3">
      <div class="text-xl">ℹ️</div>
      <div class="flex-1">
        {#if $backtestState.session_id}
          <span class="text-blue-200 text-sm font-medium">Running:</span>
          <span class="text-blue-300/80 text-sm ml-2">
            {symbol} backtest using {dataSource === 'auto' ? 'auto-selected' : dataSource} data • {startDate} to {endDate}
          </span>
        {:else}
          <span class="text-blue-200 text-sm font-medium">Data Sources:</span>
          <span class="text-blue-300/80 text-sm ml-2">
            Choose between Hyperliquid API data, imported CSV data, or let the system auto-select the best available source.
          </span>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .card {
    background: #1f1f1f;
    border-radius: 8px;
    border: 1px solid #2a2a2a;
  }

  .checkbox {
    width: 18px;
    height: 18px;
    accent-color: #2196f3;
  }
</style>
