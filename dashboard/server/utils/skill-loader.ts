/**
 * Dynamic Skill Loader
 *
 * Auto-discovers skills from the skills directory and matches them to tasks
 * based on trigger keywords defined in each skill's YAML frontmatter.
 */

import { readFile, readdir } from 'fs/promises'
import { join } from 'path'
import { SKILLS_DIR } from './paths'

export interface SkillDefinition {
  name: string
  description: string
  triggers: string[]
  content: string  // Markdown content (without frontmatter)
}

// Cache loaded skills (reload on first use per process)
let _skillsCache: SkillDefinition[] | null = null
let _skillsLoadedAt = 0
const CACHE_TTL_MS = 60 * 1000  // Reload skills every 60 seconds

/**
 * Parse YAML frontmatter from a SKILL.md file
 */
function parseFrontmatter(content: string): { meta: Record<string, any>; body: string } {
  const match = content.match(/^---\n([\s\S]*?)\n---\n*([\s\S]*)$/)
  if (!match) {
    return { meta: {}, body: content }
  }

  const yamlText = match[1]
  const body = match[2]

  // Simple YAML parser for our known fields
  const meta: Record<string, any> = {}
  let currentKey = ''
  let currentList: string[] | null = null

  for (const line of yamlText.split('\n')) {
    // List item
    if (line.match(/^\s+-\s+/)) {
      const value = line.replace(/^\s+-\s+/, '').trim()
      if (currentList) {
        currentList.push(value)
      }
      continue
    }

    // Key-value pair
    const kvMatch = line.match(/^(\w+):\s*(.*)$/)
    if (kvMatch) {
      // Save previous list if any
      if (currentList && currentKey) {
        meta[currentKey] = currentList
      }

      currentKey = kvMatch[1]
      const value = kvMatch[2].trim()

      if (value === '' || value === '>') {
        // Start of a list or multiline value
        currentList = []
      } else {
        currentList = null
        meta[currentKey] = value
      }
    }
  }

  // Save last list
  if (currentList && currentKey) {
    meta[currentKey] = currentList
  }

  return { meta, body }
}

/**
 * Load all skills from the skills directory
 */
export async function loadAllSkills(): Promise<SkillDefinition[]> {
  const now = Date.now()
  if (_skillsCache && (now - _skillsLoadedAt) < CACHE_TTL_MS) {
    return _skillsCache
  }

  const skills: SkillDefinition[] = []

  try {
    const entries = await readdir(SKILLS_DIR, { withFileTypes: true })

    for (const entry of entries) {
      if (!entry.isDirectory()) continue
      if (entry.name.startsWith('.')) continue

      const skillPath = join(SKILLS_DIR, entry.name, 'SKILL.md')

      try {
        const content = await readFile(skillPath, 'utf-8')
        const { meta, body } = parseFrontmatter(content)

        // Extract triggers from frontmatter
        let triggers: string[] = []
        if (Array.isArray(meta.triggers)) {
          triggers = meta.triggers.map((t: string) => t.toLowerCase().trim())
        }

        skills.push({
          name: meta.name || entry.name,
          description: Array.isArray(meta.description)
            ? meta.description.join(' ')
            : (meta.description || ''),
          triggers,
          content: body.trim(),
        })
      } catch {
        // Skip skills with missing or invalid SKILL.md
      }
    }
  } catch (err) {
    console.error('[skill-loader] Failed to read skills directory:', err)
  }

  _skillsCache = skills
  _skillsLoadedAt = now
  console.log(`[skill-loader] Loaded ${skills.length} skills: ${skills.map(s => s.name).join(', ')}`)
  return skills
}

/**
 * Find matching skills for a task based on trigger keywords
 */
export async function findMatchingSkills(
  taskTitle: string,
  taskId: string,
  projectName: string
): Promise<SkillDefinition[]> {
  const skills = await loadAllSkills()
  const searchText = `${taskTitle} ${taskId} ${projectName}`.toLowerCase()

  return skills.filter(skill =>
    skill.triggers.some(trigger => searchText.includes(trigger))
  )
}

/**
 * Build the skill injection block for a worker prompt
 */
export async function buildSkillBlock(
  taskTitle: string,
  taskId: string,
  projectName: string
): Promise<string> {
  const matched = await findMatchingSkills(taskTitle, taskId, projectName)

  if (matched.length === 0) return ''

  const blocks = matched.map(skill => {
    const emoji = getSkillEmoji(skill.name)
    return `## ${emoji} ${formatSkillName(skill.name)} Skill

${skill.content}

---`
  })

  console.log(`[skill-loader] Matched ${matched.length} skills for task "${taskId}": ${matched.map(s => s.name).join(', ')}`)

  return '\n' + blocks.join('\n\n') + '\n'
}

function getSkillEmoji(name: string): string {
  const emojis: Record<string, string> = {
    'web-visuals': '🎨',
    'api-design': '🔌',
    'vue-nuxt': '💚',
    'testing': '🧪',
    'security-hardening': '🔒',
    'database': '🗄️',
    'typescript-patterns': '📐',
    'devops-infra': '⚙️',
    'accessibility': '♿',
    'node-backend': '🟢',
    'python-backend': '🐍',
    'trading-systems': '📈',
    'data-engineering': '🔄',
    'llm-integration': '🤖',
  }
  return emojis[name] || '📋'
}

function formatSkillName(name: string): string {
  return name
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
