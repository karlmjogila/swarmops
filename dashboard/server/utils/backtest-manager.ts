/**
 * Backtest Session Manager
 * 
 * Manages active backtest sessions with WebSocket streaming.
 * Handles communication with Python backtest engine via child process.
 */

import { spawn, type ChildProcess } from 'child_process'
import { EventEmitter } from 'events'
import { join } from 'path'
import { broadcast } from '../plugins/websocket'

export interface BacktestConfig {
  symbol: string
  startDate: string
  endDate: string
  initialCapital: number
  positionSizePercent: number
  maxOpenTrades: number
  useStopOrders: boolean
  useTakeProfits: boolean
}

export interface BacktestState {
  sessionId: string
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed'
  currentTime: string | null
  currentCandleIndex: number
  totalCandles: number
  progressPercent: number
  currentCapital: number
  peakCapital: number
  drawdown: number
  openTrades: any[]
  recentSignals: any[]
  recentTrades: any[]
  metrics: {
    totalTrades: number
    winningTrades: number
    losingTrades: number
    winRate: number
    totalPnl: number
    totalPnlPercent: number
    averageWin: number
    averageLoss: number
    largestWin: number
    largestLoss: number
    profitFactor: number
    expectancy: number
    maxDrawdown: number
    maxDrawdownPercent: number
    sharpeRatio: number
    totalCommission: number
    totalSlippage: number
    equityCurve: Array<{
      timestamp: string
      equity: number
      drawdown: number
    }>
  }
  currentPrices: Record<string, number>
}

export interface BacktestSession {
  id: string
  config: BacktestConfig
  state: BacktestState
  process: ChildProcess | null
  emitter: EventEmitter
  createdAt: Date
}

class BacktestManager {
  private sessions: Map<string, BacktestSession> = new Map()
  private projectRoot: string

  constructor() {
    // Find project root (assumes dashboard is at /opt/swarmops/dashboard)
    this.projectRoot = join(process.cwd(), '..')
  }

  /**
   * Create a new backtest session
   */
  createSession(config: BacktestConfig): string {
    const sessionId = `backtest-${Date.now()}-${Math.random().toString(36).substring(7)}`
    
    const session: BacktestSession = {
      id: sessionId,
      config,
      state: {
        sessionId,
        status: 'idle',
        currentTime: null,
        currentCandleIndex: 0,
        totalCandles: 0,
        progressPercent: 0,
        currentCapital: config.initialCapital,
        peakCapital: config.initialCapital,
        drawdown: 0,
        openTrades: [],
        recentSignals: [],
        recentTrades: [],
        metrics: {
          totalTrades: 0,
          winningTrades: 0,
          losingTrades: 0,
          winRate: 0,
          totalPnl: 0,
          totalPnlPercent: 0,
          averageWin: 0,
          averageLoss: 0,
          largestWin: 0,
          largestLoss: 0,
          profitFactor: 0,
          expectancy: 0,
          maxDrawdown: 0,
          maxDrawdownPercent: 0,
          sharpeRatio: 0,
          totalCommission: 0,
          totalSlippage: 0,
          equityCurve: [],
        },
        currentPrices: {},
      },
      process: null,
      emitter: new EventEmitter(),
      createdAt: new Date(),
    }

    this.sessions.set(sessionId, session)
    console.log(`[backtest] Created session: ${sessionId}`)

    return sessionId
  }

  /**
   * Start a backtest session
   */
  async start(sessionId: string): Promise<void> {
    const session = this.sessions.get(sessionId)
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`)
    }

    if (session.process) {
      throw new Error('Backtest already running')
    }

    // Path to Python backtest runner script
    const pythonScript = join(
      this.projectRoot,
      'projects/hl-bot-v2/backend/scripts/run_backtest_stream.py'
    )

    // Spawn Python process
    const process = spawn('python3', [
      pythonScript,
      '--session-id', sessionId,
      '--symbol', session.config.symbol,
      '--start-date', session.config.startDate,
      '--end-date', session.config.endDate,
      '--initial-capital', session.config.initialCapital.toString(),
      '--position-size-percent', session.config.positionSizePercent.toString(),
      '--max-open-trades', session.config.maxOpenTrades.toString(),
      '--use-stop-orders', session.config.useStopOrders ? 'true' : 'false',
      '--use-take-profits', session.config.useTakeProfits ? 'true' : 'false',
      '--emit-interval', '10', // Emit state every 10 candles
    ], {
      cwd: join(this.projectRoot, 'projects/hl-bot-v2/backend'),
      env: {
        ...process.env,
        PYTHONPATH: join(this.projectRoot, 'projects/hl-bot-v2/backend'),
      },
    })

    session.process = process
    session.state.status = 'running'

    // Handle stdout (backtest state updates)
    process.stdout?.on('data', (data) => {
      const lines = data.toString().split('\n')
      for (const line of lines) {
        if (!line.trim()) continue
        
        try {
          const message = JSON.parse(line)
          this.handleBacktestMessage(sessionId, message)
        } catch (err) {
          console.error('[backtest] Failed to parse stdout:', line)
        }
      }
    })

    // Handle stderr (errors and logs)
    process.stderr?.on('data', (data) => {
      console.error(`[backtest] ${sessionId}:`, data.toString())
    })

    // Handle process exit
    process.on('close', (code) => {
      console.log(`[backtest] Session ${sessionId} exited with code ${code}`)
      
      if (code === 0) {
        session.state.status = 'completed'
      } else {
        session.state.status = 'failed'
      }

      session.process = null
      
      // Broadcast final state
      this.broadcastState(sessionId, session.state)
    })

    // Handle process errors
    process.on('error', (err) => {
      console.error(`[backtest] Process error for ${sessionId}:`, err)
      session.state.status = 'failed'
      session.process = null
      this.broadcastState(sessionId, session.state)
    })

    console.log(`[backtest] Started session: ${sessionId}`)
  }

  /**
   * Pause a backtest session
   */
  async pause(sessionId: string): Promise<void> {
    const session = this.sessions.get(sessionId)
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`)
    }

    if (!session.process) {
      throw new Error('No active backtest to pause')
    }

    // Send pause signal to Python process (via stdin)
    session.process.stdin?.write(JSON.stringify({ command: 'pause' }) + '\n')
    session.state.status = 'paused'
    
    this.broadcastState(sessionId, session.state)
    console.log(`[backtest] Paused session: ${sessionId}`)
  }

  /**
   * Resume a paused backtest session
   */
  async resume(sessionId: string): Promise<void> {
    const session = this.sessions.get(sessionId)
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`)
    }

    if (!session.process) {
      throw new Error('No active backtest to resume')
    }

    // Send resume signal to Python process (via stdin)
    session.process.stdin?.write(JSON.stringify({ command: 'resume' }) + '\n')
    session.state.status = 'running'
    
    this.broadcastState(sessionId, session.state)
    console.log(`[backtest] Resumed session: ${sessionId}`)
  }

  /**
   * Stop a backtest session
   */
  async stop(sessionId: string): Promise<void> {
    const session = this.sessions.get(sessionId)
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`)
    }

    if (!session.process) {
      throw new Error('No active backtest to stop')
    }

    // Send stop signal
    session.process.stdin?.write(JSON.stringify({ command: 'stop' }) + '\n')
    
    // Give it 2 seconds to exit gracefully, then kill
    setTimeout(() => {
      if (session.process && !session.process.killed) {
        session.process.kill('SIGTERM')
      }
    }, 2000)

    console.log(`[backtest] Stopped session: ${sessionId}`)
  }

  /**
   * Get session by ID
   */
  getSession(sessionId: string): BacktestSession | undefined {
    return this.sessions.get(sessionId)
  }

  /**
   * Get all sessions
   */
  getAllSessions(): BacktestSession[] {
    return Array.from(this.sessions.values())
  }

  /**
   * Delete a session
   */
  deleteSession(sessionId: string): boolean {
    const session = this.sessions.get(sessionId)
    if (!session) {
      return false
    }

    // Kill process if running
    if (session.process && !session.process.killed) {
      session.process.kill('SIGTERM')
    }

    this.sessions.delete(sessionId)
    console.log(`[backtest] Deleted session: ${sessionId}`)
    
    return true
  }

  /**
   * Handle backtest message from Python process
   */
  private handleBacktestMessage(sessionId: string, message: any): void {
    const session = this.sessions.get(sessionId)
    if (!session) return

    if (message.type === 'state_update') {
      // Update session state
      session.state = {
        ...session.state,
        ...message.state,
      }

      // Broadcast to WebSocket clients
      this.broadcastState(sessionId, session.state)
      
      // Emit event for local listeners
      session.emitter.emit('state_update', session.state)
    } else if (message.type === 'error') {
      console.error(`[backtest] Error in session ${sessionId}:`, message.error)
      session.state.status = 'failed'
      this.broadcastState(sessionId, session.state)
    } else if (message.type === 'log') {
      console.log(`[backtest] ${sessionId}:`, message.message)
    }
  }

  /**
   * Broadcast state update via WebSocket
   */
  private broadcastState(sessionId: string, state: BacktestState): void {
    broadcast({
      type: 'backtest_state_update',
      sessionId,
      state,
    })
  }

  /**
   * Clean up old sessions (older than 1 hour and not running)
   */
  cleanup(): void {
    const now = Date.now()
    const oneHour = 60 * 60 * 1000

    for (const [sessionId, session] of this.sessions.entries()) {
      const age = now - session.createdAt.getTime()
      
      if (age > oneHour && session.state.status !== 'running') {
        console.log(`[backtest] Cleaning up old session: ${sessionId}`)
        this.deleteSession(sessionId)
      }
    }
  }
}

// Singleton instance
export const backtestManager = new BacktestManager()

// Clean up old sessions every 30 minutes
setInterval(() => {
  backtestManager.cleanup()
}, 30 * 60 * 1000)
