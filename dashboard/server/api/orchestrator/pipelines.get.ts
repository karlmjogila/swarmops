import { readFile } from 'fs/promises'
import { join } from 'path'

const DATA_DIR = '/home/siim/swarmops/data/orchestrator'

export default defineEventHandler(async () => {
  try {
    const data = await readFile(join(DATA_DIR, 'pipelines.json'), 'utf-8')
    return JSON.parse(data)
  } catch {
    return []
  }
})
