import { spawn } from 'child_process'

export default defineEventHandler(async (event) => {
  return new Promise((resolve, reject) => {
    const child = spawn('openclaw', ['sessions', 'list', '--json'], {
      stdio: 'pipe'
    })
    
    let stdout = ''
    let stderr = ''
    
    child.stdout?.on('data', (data) => {
      stdout += data.toString()
    })
    
    child.stderr?.on('data', (data) => {
      stderr += data.toString()
    })
    
    child.on('close', (code) => {
      if (code !== 0) {
        resolve({ sessions: [], error: stderr || 'Failed to list sessions' })
        return
      }
      
      try {
        const result = JSON.parse(stdout)
        // Filter to show recent/relevant sessions (subagents, exclude main/cron/discord unless labeled appropriately)
        const sessions = (result.sessions || [])
          .filter((s: any) => 
            s.label?.startsWith('swarm:') || 
            s.label?.startsWith('builder:') ||
            (s.type === 'subagent' && s.label?.includes('builder')) ||
            (s.type === 'subagent' && s.label?.includes('swarm'))
          )
          .map((s: any) => ({
            key: s.key,
            label: s.label,
            status: s.status || 'active',
            model: s.model,
            updatedAt: s.updatedAt,
            tokens: s.tokens?.total || 0,
            type: s.type
          }))
        resolve({ sessions })
      } catch {
        resolve({ sessions: [], raw: stdout })
      }
    })
    
    child.on('error', (error) => {
      resolve({ sessions: [], error: error.message })
    })
    
    setTimeout(() => {
      child.kill()
      resolve({ sessions: [], error: 'Timeout' })
    }, 10000)
  })
})