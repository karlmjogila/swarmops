<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { backtests, strategies } from '$lib/stores';
  import { api } from '$lib/api';
  import { MTFGrid, TradingChart } from '$lib/components/charts';
  import { BacktestReplayControls } from '$lib/components/trading';
  import {
    Button,
    Card,
    CardHeader,
    CardBody,
    CardFooter,
    Badge,
    Modal,
    ModalBody,
    ModalFooter,
    Tabs,
    TabList,
    Tab,
    TabPanel,
    Input,
  } from '$lib/components/ui';
  import { LoadingState, EmptyState } from '$lib/components/layout';
  import type {
    BacktestResult,
    BacktestConfig,
    BacktestTrade,
    BacktestMetrics,
    EquityPoint,
    OHLCV,
    Timeframe,
    Strategy,
    ReplayAction,
  } from '@hl-bot/shared';
  import { createPrice, TIMEFRAMES, TIMEFRAME_MINUTES } from '@hl-bot/shared';

  // Local Backtest type for list items (matches API response)
  interface BacktestItem {
    id: string;
    strategyId: string;
    symbol: string;
    startDate: Date;
    endDate: Date;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
    metrics?: BacktestMetrics;
    error?: string;
    createdAt: Date;
    updatedAt: Date;
  }

  // State
  let loading = $state(true);
  let error = $state<string | null>(null);
  let selectedBacktest = $state<BacktestItem | null>(null);
  let backtestResult = $state<BacktestResult | null>(null);
  let activeTab = $state<string>('list');

  // Configuration form state
  let configModalOpen = $state(false);
  let formStrategyId = $state('');
  let formSymbol = $state('BTC-USD');
  let formStartDate = $state('');
  let formEndDate = $state('');
  let formInitialCapital = $state(10000);
  let formMode = $state<'stf' | 'mtf'>('mtf');
  let formTimeframes = $state<Timeframe[]>(['15m', '1h', '4h', '1d']);
  let formStreamReplay = $state(true);
  let formReplaySpeed = $state(1);
  let formCommission = $state(0.001);
  let formSlippage = $state(0.0005);
  let isSubmitting = $state(false);

  // Replay state
  let isPlaying = $state(false);
  let speed = $state(1);
  let currentTime = $state(new Date());
  let chartData = $state<OHLCV[]>([]);
  let allChartData = $state<OHLCV[]>([]);
  let mtfData = $state<Map<Timeframe, OHLCV[]>>(new Map());
  let replayInterval: number | null = null;
  let currentReplayIndex = $state(0);

  // Computed
  let backtestItems = $derived($backtests.items as BacktestItem[]);
  let strategyItems = $derived($strategies.items);
  let pendingBacktests = $derived(backtestItems.filter(b => b.status === 'pending' || b.status === 'running'));
  let completedBacktests = $derived(backtestItems.filter(b => b.status === 'completed'));
  let failedBacktests = $derived(backtestItems.filter(b => b.status === 'failed'));

  // Initialize default dates
  $effect(() => {
    if (!formStartDate) {
      const now = new Date();
      const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      formStartDate = thirtyDaysAgo.toISOString().split('T')[0];
      formEndDate = now.toISOString().split('T')[0];
    }
  });

  // Handle tab changes via Tabs value
  function handleTabChange(value: string) {
    activeTab = value;
  }

  // Load data on mount
  onMount(async () => {
    try {
      loading = true;
      await Promise.all([
        backtests.load(),
        strategies.load({ status: 'approved' }),
      ]);
    } catch (err) {
      console.error('Failed to load data:', err);
      error = err instanceof Error ? err.message : 'Failed to load backtests';
    } finally {
      loading = false;
    }
  });

  // Cleanup on destroy
  onDestroy(() => {
    if (replayInterval) {
      clearInterval(replayInterval);
    }
  });

  // Actions
  async function createBacktest() {
    if (!formStrategyId) {
      alert('Please select a strategy');
      return;
    }

    isSubmitting = true;
    try {
      const input = {
        strategyId: formStrategyId,
        symbol: formSymbol,
        startDate: new Date(formStartDate),
        endDate: new Date(formEndDate),
        initialCapital: formInitialCapital,
        mode: formMode,
        timeframes: formTimeframes,
        streamReplay: formStreamReplay,
        replaySpeed: formReplaySpeed,
        commission: formCommission,
        slippage: formSlippage,
      };

      const newBacktest = await backtests.create(input as any);
      configModalOpen = false;
      resetForm();
      
      // Select the new backtest
      await viewBacktest(newBacktest as BacktestItem);
    } catch (err) {
      console.error('Failed to create backtest:', err);
      alert('Failed to create backtest');
    } finally {
      isSubmitting = false;
    }
  }

  function resetForm() {
    formStrategyId = '';
    formSymbol = 'BTC-USD';
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    formStartDate = thirtyDaysAgo.toISOString().split('T')[0];
    formEndDate = now.toISOString().split('T')[0];
    formInitialCapital = 10000;
    formMode = 'mtf';
    formTimeframes = ['15m', '1h', '4h', '1d'];
    formStreamReplay = true;
    formReplaySpeed = 1;
    formCommission = 0.001;
    formSlippage = 0.0005;
  }

  async function viewBacktest(backtest: BacktestItem) {
    selectedBacktest = backtest;
    activeTab = 'results';
    
    if (backtest.status === 'completed') {
      try {
        await backtests.loadResults(backtest.id);
        backtestResult = $backtests.currentResult;
        
        // Generate chart data from the backtest result
        if (backtestResult) {
          generateChartDataFromResult(backtestResult);
        }
      } catch (err) {
        console.error('Failed to load backtest results:', err);
      }
    }
  }

  function generateChartDataFromResult(result: BacktestResult) {
    // Generate synthetic chart data based on equity curve
    // In a real implementation, this would come from the API
    const equity = result.equityCurve;
    if (equity.length === 0) return;

    const startTime = new Date(result.config.startDate);
    const endTime = new Date(result.config.endDate);
    currentTime = startTime;

    // Reset replay state
    stopReplay();
    currentReplayIndex = 0;

    // Generate mock OHLCV data based on trades
    allChartData = generateMockOHLCV(result.trades, startTime, endTime);
    chartData = allChartData.slice(0, Math.min(100, allChartData.length));

    // Generate MTF data
    mtfData = new Map();
    for (const tf of result.config.timeframes) {
      mtfData.set(tf, aggregateToTimeframe(allChartData, tf));
    }
  }

  function generateMockOHLCV(trades: readonly BacktestTrade[], start: Date, end: Date): OHLCV[] {
    const data: OHLCV[] = [];
    const interval = 60000; // 1 minute
    let price = trades.length > 0 ? trades[0].entryPrice : 50000;

    const totalMs = end.getTime() - start.getTime();
    const totalCandles = Math.min(Math.floor(totalMs / interval), 2000);

    for (let i = 0; i < totalCandles; i++) {
      const timestamp = new Date(start.getTime() + i * interval);
      
      // Check if any trade is active at this time
      const activeTrade = trades.find(t => 
        timestamp >= new Date(t.entryTime) && timestamp <= new Date(t.exitTime)
      );

      // Price movement influenced by trades
      const change = (Math.random() - 0.48) * 50;
      price += change;

      if (activeTrade) {
        // Trend towards exit price during active trade
        const progress = (timestamp.getTime() - new Date(activeTrade.entryTime).getTime()) / 
                        (new Date(activeTrade.exitTime).getTime() - new Date(activeTrade.entryTime).getTime());
        price = activeTrade.entryPrice + (activeTrade.exitPrice - activeTrade.entryPrice) * progress * 0.3 + (Math.random() - 0.5) * 20;
      }

      const open = price;
      const close = price + (Math.random() - 0.5) * 30;
      const high = Math.max(open, close) + Math.random() * 20;
      const low = Math.min(open, close) - Math.random() * 20;
      const volume = 1000 + Math.random() * 5000;

      data.push({
        timestamp,
        symbol: 'BTC-USD',
        timeframe: '1m' as Timeframe,
        open: createPrice(Math.max(open, 1)),
        high: createPrice(Math.max(high, 1)),
        low: createPrice(Math.max(low, 1)),
        close: createPrice(Math.max(close, 1)),
        volume,
      });

      price = close;
    }

    return data;
  }

  function aggregateToTimeframe(data: OHLCV[], timeframe: Timeframe): OHLCV[] {
    const period = TIMEFRAME_MINUTES[timeframe] || 60;
    const result: OHLCV[] = [];

    for (let i = 0; i < data.length; i += period) {
      const slice = data.slice(i, Math.min(i + period, data.length));
      if (slice.length === 0) continue;

      result.push({
        timestamp: slice[0].timestamp,
        symbol: slice[0].symbol,
        timeframe,
        open: slice[0].open,
        high: createPrice(Math.max(...slice.map(c => c.high))),
        low: createPrice(Math.min(...slice.map(c => c.low))),
        close: slice[slice.length - 1].close,
        volume: slice.reduce((sum, c) => sum + c.volume, 0),
      });
    }

    return result;
  }

  // Replay controls
  function handleReplayAction(action: ReplayAction, params?: { timestamp?: Date; speed?: number }) {
    switch (action) {
      case 'play':
        startReplay();
        break;
      case 'pause':
        pauseReplay();
        break;
      case 'stop':
        stopReplay();
        break;
      case 'seek':
        if (params?.timestamp) {
          seekToTime(params.timestamp);
        }
        break;
      case 'speed':
        if (params?.speed) {
          speed = params.speed;
          if (isPlaying) {
            pauseReplay();
            startReplay();
          }
        }
        break;
    }
  }

  function startReplay() {
    if (replayInterval || allChartData.length === 0) return;
    isPlaying = true;
    
    const interval = 100 / speed;
    
    replayInterval = window.setInterval(() => {
      if (currentReplayIndex >= allChartData.length) {
        stopReplay();
        return;
      }

      chartData = allChartData.slice(
        Math.max(0, currentReplayIndex - 199),
        currentReplayIndex + 1
      );
      currentTime = allChartData[currentReplayIndex].timestamp;
      currentReplayIndex++;
    }, interval);
  }

  function pauseReplay() {
    if (replayInterval) {
      clearInterval(replayInterval);
      replayInterval = null;
    }
    isPlaying = false;
  }

  function stopReplay() {
    pauseReplay();
    currentReplayIndex = Math.min(100, allChartData.length);
    chartData = allChartData.slice(0, currentReplayIndex);
    if (allChartData.length > 0) {
      currentTime = allChartData[currentReplayIndex - 1]?.timestamp || new Date();
    }
    isPlaying = false;
  }

  function seekToTime(timestamp: Date) {
    pauseReplay();
    
    const targetTime = timestamp.getTime();
    let closestIndex = 0;
    let closestDiff = Math.abs(allChartData[0]?.timestamp.getTime() - targetTime);

    for (let i = 1; i < allChartData.length; i++) {
      const diff = Math.abs(allChartData[i].timestamp.getTime() - targetTime);
      if (diff < closestDiff) {
        closestDiff = diff;
        closestIndex = i;
      }
    }

    currentReplayIndex = closestIndex + 1;
    chartData = allChartData.slice(
      Math.max(0, closestIndex - 199),
      closestIndex + 1
    );
    currentTime = allChartData[closestIndex].timestamp;
  }

  async function cancelBacktest(id: string) {
    try {
      await backtests.cancel(id);
    } catch (err) {
      console.error('Failed to cancel backtest:', err);
      alert('Failed to cancel backtest');
    }
  }

  // Formatting helpers
  function formatDate(date: Date | string): string {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function formatCurrency(value: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  }

  function formatPercent(value: number): string {
    return `${(value * 100).toFixed(2)}%`;
  }

  function formatDuration(minutes: number): string {
    if (minutes < 60) return `${minutes.toFixed(0)}m`;
    if (minutes < 1440) return `${(minutes / 60).toFixed(1)}h`;
    return `${(minutes / 1440).toFixed(1)}d`;
  }

  function getStatusBadgeVariant(status: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'info';
      case 'pending': return 'warning';
      case 'failed': return 'error';
      case 'cancelled': return 'default';
      default: return 'default';
    }
  }

  function getStrategyName(id: string): string {
    const strategy = strategyItems.find(s => s.id === id);
    return strategy?.name || 'Unknown Strategy';
  }

  function toggleTimeframe(tf: Timeframe) {
    if (formTimeframes.includes(tf)) {
      formTimeframes = formTimeframes.filter(t => t !== tf);
    } else {
      formTimeframes = [...formTimeframes, tf];
    }
  }

  // Get mutable copy of timeframes for MTFGrid
  function getMutableTimeframes(tfs: readonly Timeframe[]): Timeframe[] {
    return [...tfs];
  }
</script>

<div class="min-h-screen bg-bg-primary p-6">
  <div class="max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-text-primary">Backtesting</h1>
        <p class="text-text-secondary mt-1">Test your strategies against historical data</p>
      </div>
      <div class="flex gap-3">
        <a href="/strategies" class="inline-flex items-center justify-center gap-2 font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-bg-primary h-10 px-4 text-base rounded-md bg-transparent border-2 border-accent-primary text-accent-primary hover:bg-accent-primary hover:text-white">
          Strategies
        </a>
        <Button variant="primary" onclick={() => configModalOpen = true}>
          New Backtest
        </Button>
      </div>
    </div>

    <!-- Tabs -->
    <Tabs value={activeTab}>
      <TabList>
        <Tab value="list">
          Backtests
          {#if backtestItems.length > 0}
            <Badge variant="info" class="ml-2">{backtestItems.length}</Badge>
          {/if}
        </Tab>
        <Tab value="results" disabled={!selectedBacktest}>
          Results
        </Tab>
      </TabList>

      <!-- Backtest List Tab -->
      <TabPanel value="list">
        {#if loading}
          <LoadingState type="spinner" />
        {:else if error}
          <Card>
            <CardBody>
              <div class="text-center py-8">
                <p class="text-error text-lg mb-4">Error loading backtests</p>
                <p class="text-text-secondary mb-4">{error}</p>
                <Button variant="primary" onclick={() => backtests.load()}>Try Again</Button>
              </div>
            </CardBody>
          </Card>
        {:else if backtestItems.length === 0}
          <Card>
            <CardBody>
              <EmptyState
                title="No backtests yet"
                description="Create your first backtest to test your trading strategies"
                action={{
                  label: 'Create Backtest',
                  onClick: () => configModalOpen = true,
                }}
              />
            </CardBody>
          </Card>
        {:else}
          <div class="space-y-4">
            <!-- Running/Pending Backtests -->
            {#if pendingBacktests.length > 0}
              <Card>
                <CardHeader>
                  <h2 class="text-lg font-semibold text-text-primary flex items-center gap-2">
                    Active Backtests
                    <Badge variant="info">{pendingBacktests.length}</Badge>
                  </h2>
                </CardHeader>
                <CardBody>
                  <div class="space-y-3">
                    {#each pendingBacktests as backtest (backtest.id)}
                      <div class="flex items-center justify-between p-4 bg-bg-tertiary rounded-lg">
                        <div class="flex-1">
                          <div class="flex items-center gap-2 mb-1">
                            <span class="font-semibold text-text-primary">
                              {getStrategyName(backtest.strategyId)}
                            </span>
                            <Badge variant={getStatusBadgeVariant(backtest.status)}>
                              {backtest.status}
                            </Badge>
                          </div>
                          <p class="text-sm text-text-secondary">
                            {backtest.symbol} • {formatDate(backtest.startDate)} - {formatDate(backtest.endDate)}
                          </p>
                        </div>
                        <div class="flex items-center gap-2">
                          {#if backtest.status === 'running'}
                            <div class="w-32 h-2 bg-bg-secondary rounded-full overflow-hidden">
                              <div class="h-full bg-info animate-pulse" style="width: 60%"></div>
                            </div>
                          {/if}
                          <Button
                            variant="danger"
                            size="sm"
                            onclick={() => cancelBacktest(backtest.id)}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    {/each}
                  </div>
                </CardBody>
              </Card>
            {/if}

            <!-- Completed Backtests -->
            <Card>
              <CardHeader>
                <h2 class="text-lg font-semibold text-text-primary flex items-center gap-2">
                  Completed Backtests
                  <Badge variant="success">{completedBacktests.length}</Badge>
                </h2>
              </CardHeader>
              <CardBody>
                {#if completedBacktests.length === 0}
                  <p class="text-text-secondary text-center py-6">
                    No completed backtests yet
                  </p>
                {:else}
                  <div class="overflow-x-auto">
                    <table class="w-full">
                      <thead>
                        <tr class="text-left text-text-secondary text-sm border-b border-border">
                          <th class="pb-3 font-medium">Strategy</th>
                          <th class="pb-3 font-medium">Symbol</th>
                          <th class="pb-3 font-medium">Period</th>
                          <th class="pb-3 font-medium">P&L</th>
                          <th class="pb-3 font-medium">Win Rate</th>
                          <th class="pb-3 font-medium">Trades</th>
                          <th class="pb-3 font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each completedBacktests as backtest (backtest.id)}
                          <tr class="border-b border-border-subtle hover:bg-bg-hover cursor-pointer"
                              onclick={() => viewBacktest(backtest)}>
                            <td class="py-3">
                              <span class="font-medium text-text-primary">
                                {getStrategyName(backtest.strategyId)}
                              </span>
                            </td>
                            <td class="py-3 text-text-secondary">{backtest.symbol}</td>
                            <td class="py-3 text-text-secondary text-sm">
                              {formatDate(backtest.startDate)} - {formatDate(backtest.endDate)}
                            </td>
                            <td class="py-3">
                              {#if backtest.metrics}
                                <span class={backtest.metrics.totalPnL >= 0 ? 'text-long-green' : 'text-short-red'}>
                                  {formatCurrency(backtest.metrics.totalPnL)}
                                </span>
                              {:else}
                                <span class="text-text-tertiary">-</span>
                              {/if}
                            </td>
                            <td class="py-3">
                              {#if backtest.metrics}
                                <span class={backtest.metrics.winRate >= 0.5 ? 'text-long-green' : 'text-short-red'}>
                                  {formatPercent(backtest.metrics.winRate)}
                                </span>
                              {:else}
                                <span class="text-text-tertiary">-</span>
                              {/if}
                            </td>
                            <td class="py-3 text-text-secondary">
                              {backtest.metrics?.totalTrades || '-'}
                            </td>
                            <td class="py-3">
                              <Button variant="outline" size="sm" onclick={() => viewBacktest(backtest)}>
                                View
                              </Button>
                            </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/if}
              </CardBody>
            </Card>

            <!-- Failed Backtests -->
            {#if failedBacktests.length > 0}
              <Card>
                <CardHeader>
                  <h2 class="text-lg font-semibold text-text-primary flex items-center gap-2">
                    Failed Backtests
                    <Badge variant="error">{failedBacktests.length}</Badge>
                  </h2>
                </CardHeader>
                <CardBody>
                  <div class="space-y-3">
                    {#each failedBacktests as backtest (backtest.id)}
                      <div class="flex items-center justify-between p-4 bg-bg-tertiary rounded-lg">
                        <div>
                          <div class="flex items-center gap-2 mb-1">
                            <span class="font-medium text-text-primary">
                              {getStrategyName(backtest.strategyId)}
                            </span>
                            <Badge variant="error">Failed</Badge>
                          </div>
                          <p class="text-sm text-text-secondary">
                            {backtest.error || 'Unknown error'}
                          </p>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onclick={() => {
                            formStrategyId = backtest.strategyId;
                            formSymbol = backtest.symbol;
                            configModalOpen = true;
                          }}
                        >
                          Retry
                        </Button>
                      </div>
                    {/each}
                  </div>
                </CardBody>
              </Card>
            {/if}
          </div>
        {/if}
      </TabPanel>

      <!-- Results Tab -->
      <TabPanel value="results">
        {#if !selectedBacktest}
          <Card>
            <CardBody>
              <EmptyState
                title="No backtest selected"
                description="Select a backtest from the list to view its results"
              />
            </CardBody>
          </Card>
        {:else if selectedBacktest.status !== 'completed'}
          <Card>
            <CardBody>
              <div class="text-center py-12">
                <LoadingState type="spinner" size="lg" />
                <p class="text-text-secondary mt-4">
                  Backtest is {selectedBacktest.status}...
                </p>
              </div>
            </CardBody>
          </Card>
        {:else if !backtestResult}
          <Card>
            <CardBody>
              <LoadingState type="spinner" />
            </CardBody>
          </Card>
        {:else}
          <div class="space-y-6">
            <!-- Backtest Header -->
            <Card>
              <CardBody>
                <div class="flex items-center justify-between">
                  <div>
                    <h2 class="text-xl font-bold text-text-primary">
                      {getStrategyName(backtestResult.strategyId)}
                    </h2>
                    <p class="text-text-secondary">
                      {backtestResult.config.symbol} •
                      {formatDate(backtestResult.config.startDate)} - {formatDate(backtestResult.config.endDate)}
                    </p>
                  </div>
                  <Button variant="outline" onclick={() => activeTab = 'list'}>
                    ← Back to List
                  </Button>
                </div>
              </CardBody>
            </Card>

            <!-- Key Metrics -->
            <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              <Card>
                <CardBody>
                  <div class="text-sm text-text-secondary">Total P&L</div>
                  <div class={`text-2xl font-bold ${backtestResult.metrics.totalPnL >= 0 ? 'text-long-green' : 'text-short-red'}`}>
                    {formatCurrency(backtestResult.metrics.totalPnL)}
                  </div>
                  <div class="text-xs text-text-tertiary">
                    {formatPercent(backtestResult.metrics.totalPnLPercent / 100)}
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardBody>
                  <div class="text-sm text-text-secondary">Win Rate</div>
                  <div class={`text-2xl font-bold ${backtestResult.metrics.winRate >= 0.5 ? 'text-long-green' : 'text-short-red'}`}>
                    {formatPercent(backtestResult.metrics.winRate)}
                  </div>
                  <div class="text-xs text-text-tertiary">
                    {backtestResult.metrics.winningTrades}W / {backtestResult.metrics.losingTrades}L
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardBody>
                  <div class="text-sm text-text-secondary">Profit Factor</div>
                  <div class={`text-2xl font-bold ${backtestResult.metrics.profitFactor >= 1.5 ? 'text-long-green' : backtestResult.metrics.profitFactor >= 1 ? 'text-warning' : 'text-short-red'}`}>
                    {backtestResult.metrics.profitFactor.toFixed(2)}
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardBody>
                  <div class="text-sm text-text-secondary">Sharpe Ratio</div>
                  <div class={`text-2xl font-bold ${backtestResult.metrics.sharpeRatio >= 1 ? 'text-long-green' : 'text-warning'}`}>
                    {backtestResult.metrics.sharpeRatio.toFixed(2)}
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardBody>
                  <div class="text-sm text-text-secondary">Max Drawdown</div>
                  <div class="text-2xl font-bold text-short-red">
                    {formatPercent(backtestResult.metrics.maxDrawdownPercent / 100)}
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardBody>
                  <div class="text-sm text-text-secondary">Total Trades</div>
                  <div class="text-2xl font-bold text-text-primary">
                    {backtestResult.metrics.totalTrades}
                  </div>
                  <div class="text-xs text-text-tertiary">
                    Avg: {formatDuration(backtestResult.metrics.averageHoldTime)}
                  </div>
                </CardBody>
              </Card>
            </div>

            <!-- Chart with Replay Controls -->
            {#if allChartData.length > 0}
              <Card>
                <CardHeader>
                  <h3 class="text-lg font-semibold text-text-primary">Price Chart</h3>
                </CardHeader>
                <CardBody>
                  <TradingChart
                    data={chartData}
                    symbol={backtestResult.config.symbol}
                    timeframe="1m"
                    height={400}
                    showLegend={true}
                  />
                </CardBody>
                <CardFooter>
                  <BacktestReplayControls
                    bind:isPlaying
                    bind:speed
                    bind:currentTime
                    startTime={new Date(backtestResult.config.startDate)}
                    endTime={new Date(backtestResult.config.endDate)}
                    onAction={handleReplayAction}
                  />
                </CardFooter>
              </Card>
            {/if}

            <!-- Multi-Timeframe Grid -->
            {#if mtfData.size > 0}
              <Card>
                <CardHeader>
                  <h3 class="text-lg font-semibold text-text-primary">Multi-Timeframe Analysis</h3>
                </CardHeader>
                <CardBody>
                  <MTFGrid
                    symbol={backtestResult.config.symbol}
                    timeframes={getMutableTimeframes(backtestResult.config.timeframes)}
                    dataByTimeframe={mtfData}
                    columns={2}
                    chartHeight={250}
                  />
                </CardBody>
              </Card>
            {/if}

            <!-- Additional Metrics -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <!-- Detailed Metrics -->
              <Card>
                <CardHeader>
                  <h3 class="text-lg font-semibold text-text-primary">Performance Metrics</h3>
                </CardHeader>
                <CardBody>
                  <div class="space-y-3">
                    <div class="flex justify-between py-2 border-b border-border-subtle">
                      <span class="text-text-secondary">Expectancy</span>
                      <span class="font-medium text-text-primary">{formatCurrency(backtestResult.metrics.expectancy)}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-border-subtle">
                      <span class="text-text-secondary">Recovery Factor</span>
                      <span class="font-medium text-text-primary">{backtestResult.metrics.recoveryFactor.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-border-subtle">
                      <span class="text-text-secondary">Calmar Ratio</span>
                      <span class="font-medium text-text-primary">{backtestResult.metrics.calmarRatio.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-border-subtle">
                      <span class="text-text-secondary">Sortino Ratio</span>
                      <span class="font-medium text-text-primary">{backtestResult.metrics.sortinoRatio.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-border-subtle">
                      <span class="text-text-secondary">Average Win</span>
                      <span class="font-medium text-long-green">{formatCurrency(backtestResult.metrics.averageWin)}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-border-subtle">
                      <span class="text-text-secondary">Average Loss</span>
                      <span class="font-medium text-short-red">{formatCurrency(backtestResult.metrics.averageLoss)}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-border-subtle">
                      <span class="text-text-secondary">Largest Win</span>
                      <span class="font-medium text-long-green">{formatCurrency(backtestResult.metrics.largestWin)}</span>
                    </div>
                    <div class="flex justify-between py-2">
                      <span class="text-text-secondary">Largest Loss</span>
                      <span class="font-medium text-short-red">{formatCurrency(backtestResult.metrics.largestLoss)}</span>
                    </div>
                  </div>
                </CardBody>
              </Card>

              <!-- Configuration -->
              <Card>
                <CardHeader>
                  <h3 class="text-lg font-semibold text-text-primary">Configuration</h3>
                </CardHeader>
                <CardBody>
                  <div class="space-y-3">
                    <div class="flex justify-between py-2 border-b border-border-subtle">
                      <span class="text-text-secondary">Initial Capital</span>
                      <span class="font-medium text-text-primary">{formatCurrency(backtestResult.config.initialCapital)}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-border-subtle">
                      <span class="text-text-secondary">Commission</span>
                      <span class="font-medium text-text-primary">{formatPercent(backtestResult.config.commission || 0)}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-border-subtle">
                      <span class="text-text-secondary">Slippage</span>
                      <span class="font-medium text-text-primary">{formatPercent(backtestResult.config.slippage || 0)}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-border-subtle">
                      <span class="text-text-secondary">Mode</span>
                      <span class="font-medium text-text-primary">{backtestResult.config.mode.toUpperCase()}</span>
                    </div>
                    <div class="flex justify-between py-2">
                      <span class="text-text-secondary">Timeframes</span>
                      <span class="font-medium text-text-primary">{backtestResult.config.timeframes.join(', ')}</span>
                    </div>
                  </div>
                </CardBody>
              </Card>
            </div>

            <!-- Trades List -->
            <Card>
              <CardHeader>
                <h3 class="text-lg font-semibold text-text-primary flex items-center gap-2">
                  Trade History
                  <Badge variant="info">{backtestResult.trades.length}</Badge>
                </h3>
              </CardHeader>
              <CardBody>
                {#if backtestResult.trades.length === 0}
                  <p class="text-text-secondary text-center py-6">No trades executed</p>
                {:else}
                  <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                      <thead>
                        <tr class="text-left text-text-secondary border-b border-border">
                          <th class="pb-3 font-medium">#</th>
                          <th class="pb-3 font-medium">Direction</th>
                          <th class="pb-3 font-medium">Entry</th>
                          <th class="pb-3 font-medium">Exit</th>
                          <th class="pb-3 font-medium">Size</th>
                          <th class="pb-3 font-medium">P&L</th>
                          <th class="pb-3 font-medium">P&L %</th>
                          <th class="pb-3 font-medium">Duration</th>
                          <th class="pb-3 font-medium">Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each backtestResult.trades as trade, idx (idx)}
                          <tr class="border-b border-border-subtle">
                            <td class="py-3 text-text-tertiary">{idx + 1}</td>
                            <td class="py-3">
                              <Badge variant={trade.direction === 'long' ? 'success' : 'error'}>
                                {trade.direction.toUpperCase()}
                              </Badge>
                            </td>
                            <td class="py-3">
                              <div class="text-text-primary">{formatCurrency(trade.entryPrice)}</div>
                              <div class="text-xs text-text-tertiary">{formatDate(trade.entryTime)}</div>
                            </td>
                            <td class="py-3">
                              <div class="text-text-primary">{formatCurrency(trade.exitPrice)}</div>
                              <div class="text-xs text-text-tertiary">{formatDate(trade.exitTime)}</div>
                            </td>
                            <td class="py-3 text-text-secondary">{trade.size.toFixed(4)}</td>
                            <td class="py-3">
                              <span class={trade.pnl >= 0 ? 'text-long-green' : 'text-short-red'}>
                                {formatCurrency(trade.pnl)}
                              </span>
                            </td>
                            <td class="py-3">
                              <span class={trade.pnlPercent >= 0 ? 'text-long-green' : 'text-short-red'}>
                                {formatPercent(trade.pnlPercent / 100)}
                              </span>
                            </td>
                            <td class="py-3 text-text-secondary">
                              {formatDuration((new Date(trade.exitTime).getTime() - new Date(trade.entryTime).getTime()) / 60000)}
                            </td>
                            <td class="py-3 text-text-secondary text-xs max-w-[200px] truncate">
                              {trade.reason}
                            </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/if}
              </CardBody>
            </Card>
          </div>
        {/if}
      </TabPanel>
    </Tabs>
  </div>
</div>

<!-- New Backtest Configuration Modal -->
<Modal bind:open={configModalOpen} title="New Backtest" size="lg">
  <ModalBody>
    <div class="space-y-4">
      <!-- Strategy Selection -->
      <div>
        <label for="strategy" class="block text-sm font-medium text-text-primary mb-1">
          Strategy *
        </label>
        <select
          id="strategy"
          bind:value={formStrategyId}
          class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">Select a strategy...</option>
          {#each strategyItems as strategy (strategy.id)}
            <option value={strategy.id}>{strategy.name}</option>
          {/each}
        </select>
      </div>

      <!-- Symbol -->
      <div>
        <label for="symbol" class="block text-sm font-medium text-text-primary mb-1">
          Symbol *
        </label>
        <input
          id="symbol"
          type="text"
          bind:value={formSymbol}
          placeholder="BTC-USD"
          class="w-full px-3 py-2 border border-border rounded-md bg-bg-secondary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      <!-- Date Range -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label for="startDate" class="block text-sm font-medium text-text-primary mb-1">
            Start Date *
          </label>
          <input
            id="startDate"
            type="date"
            bind:value={formStartDate}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-secondary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <div>
          <label for="endDate" class="block text-sm font-medium text-text-primary mb-1">
            End Date *
          </label>
          <input
            id="endDate"
            type="date"
            bind:value={formEndDate}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-secondary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>

      <!-- Initial Capital -->
      <div>
        <label for="capital" class="block text-sm font-medium text-text-primary mb-1">
          Initial Capital (USD) *
        </label>
        <input
          id="capital"
          type="number"
          bind:value={formInitialCapital}
          min={100}
          step={100}
          class="w-full px-3 py-2 border border-border rounded-md bg-bg-secondary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      <!-- Mode -->
      <fieldset>
        <legend class="block text-sm font-medium text-text-primary mb-1">Mode</legend>
        <div class="flex gap-4">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="mode"
              bind:group={formMode}
              value="mtf"
              class="text-primary"
            />
            <span class="text-text-primary">Multi-Timeframe</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="mode"
              bind:group={formMode}
              value="stf"
              class="text-primary"
            />
            <span class="text-text-primary">Single-Timeframe</span>
          </label>
        </div>
      </fieldset>

      <!-- Timeframes -->
      <fieldset>
        <legend class="block text-sm font-medium text-text-primary mb-1">Timeframes</legend>
        <div class="flex flex-wrap gap-2">
          {#each TIMEFRAMES as tf}
            <button
              type="button"
              class="px-3 py-1 rounded border text-sm transition-colors"
              class:bg-primary={formTimeframes.includes(tf)}
              class:text-white={formTimeframes.includes(tf)}
              class:border-primary={formTimeframes.includes(tf)}
              class:bg-bg-secondary={!formTimeframes.includes(tf)}
              class:text-text-secondary={!formTimeframes.includes(tf)}
              class:border-border={!formTimeframes.includes(tf)}
              onclick={() => toggleTimeframe(tf)}
            >
              {tf}
            </button>
          {/each}
        </div>
      </fieldset>

      <!-- Advanced Settings -->
      <details class="border border-border rounded-lg p-4">
        <summary class="cursor-pointer text-sm font-medium text-text-primary">
          Advanced Settings
        </summary>
        <div class="mt-4 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="commission" class="block text-sm font-medium text-text-primary mb-1">
                Commission (%)
              </label>
              <input
                id="commission"
                type="number"
                bind:value={formCommission}
                min={0}
                max={1}
                step={0.0001}
                class="w-full px-3 py-2 border border-border rounded-md bg-bg-secondary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label for="slippage" class="block text-sm font-medium text-text-primary mb-1">
                Slippage (%)
              </label>
              <input
                id="slippage"
                type="number"
                bind:value={formSlippage}
                min={0}
                max={1}
                step={0.0001}
                class="w-full px-3 py-2 border border-border rounded-md bg-bg-secondary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          <div class="flex items-center gap-2">
            <input
              type="checkbox"
              id="streamReplay"
              bind:checked={formStreamReplay}
              class="rounded text-primary"
            />
            <label for="streamReplay" class="text-sm text-text-primary">
              Enable replay streaming
            </label>
          </div>

          {#if formStreamReplay}
            <div>
              <label for="replaySpeed" class="block text-sm font-medium text-text-primary mb-1">
                Default Replay Speed
              </label>
              <select
                id="replaySpeed"
                bind:value={formReplaySpeed}
                class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value={0.5}>0.5x</option>
                <option value={1}>1x</option>
                <option value={2}>2x</option>
                <option value={5}>5x</option>
                <option value={10}>10x</option>
              </select>
            </div>
          {/if}
        </div>
      </details>
    </div>
  </ModalBody>
  <ModalFooter>
    <Button variant="secondary" onclick={() => configModalOpen = false} disabled={isSubmitting}>
      Cancel
    </Button>
    <Button variant="primary" onclick={createBacktest} disabled={isSubmitting || !formStrategyId}>
      {isSubmitting ? 'Creating...' : 'Start Backtest'}
    </Button>
  </ModalFooter>
</Modal>

<style>
  details summary::-webkit-details-marker {
    display: none;
  }
  
  details summary::before {
    content: '▶';
    display: inline-block;
    margin-right: 8px;
    font-size: 10px;
    transition: transform 0.2s;
  }
  
  details[open] summary::before {
    transform: rotate(90deg);
  }
</style>
