export interface MarkdownSection {
  title: string
  content: string
  summary: string
  variant: 'default' | 'success' | 'warning' | 'error' | 'info'
  icon: string
  taskStats?: { done: number; total: number }
}

export function useMarkdownParser() {
  function parseProgressMarkdown(markdown: string): MarkdownSection[] {
    if (!markdown) return []
    
    const sections: MarkdownSection[] = []
    const lines = markdown.split('\n')
    
    let currentSection: MarkdownSection | null = null
    let contentLines: string[] = []
    
    for (const line of lines) {
      // Match ## headers
      const headerMatch = line.match(/^##\s+(.+)/)
      
      if (headerMatch) {
        // Save previous section
        if (currentSection) {
          currentSection.content = contentLines.join('\n').trim()
          currentSection.summary = generateSummary(currentSection)
          sections.push(currentSection)
        }
        
        const title = headerMatch[1].trim()
        currentSection = {
          title,
          content: '',
          summary: '',
          variant: getVariantForSection(title),
          icon: getIconForSection(title),
        }
        contentLines = []
      } else if (currentSection) {
        contentLines.push(line)
      }
    }
    
    // Save last section
    if (currentSection) {
      currentSection.content = contentLines.join('\n').trim()
      currentSection.summary = generateSummary(currentSection)
      sections.push(currentSection)
    }
    
    return sections
  }
  
  function getVariantForSection(title: string): MarkdownSection['variant'] {
    const lower = title.toLowerCase()
    if (lower.includes('status')) return 'info'
    if (lower.includes('complete') || lower.includes('done') || lower.includes('delivered')) return 'success'
    if (lower.includes('blocker') || lower.includes('error') || lower.includes('issue')) return 'error'
    if (lower.includes('warning') || lower.includes('pending') || lower.includes('todo')) return 'warning'
    return 'default'
  }
  
  function getIconForSection(title: string): string {
    const lower = title.toLowerCase()
    if (lower.includes('status')) return 'i-heroicons-signal'
    if (lower.includes('task') || lower.includes('todo')) return 'i-heroicons-clipboard-document-check'
    if (lower.includes('complete') || lower.includes('done')) return 'i-heroicons-check-circle'
    if (lower.includes('file')) return 'i-heroicons-document-text'
    if (lower.includes('blocker') || lower.includes('issue')) return 'i-heroicons-exclamation-triangle'
    if (lower.includes('feature') || lower.includes('deliver')) return 'i-heroicons-sparkles'
    if (lower.includes('tech') || lower.includes('stack')) return 'i-heroicons-cpu-chip'
    if (lower.includes('config') || lower.includes('deploy')) return 'i-heroicons-cog-6-tooth'
    if (lower.includes('summary')) return 'i-heroicons-document-magnifying-glass'
    return 'i-heroicons-document-text'
  }
  
  function generateSummary(section: MarkdownSection): string {
    const content = section.content
    const lines = content.split('\n').filter(l => l.trim())
    
    // Count tasks
    const taskLines = lines.filter(l => l.match(/^-\s*\[[ x]\]/i))
    if (taskLines.length > 0) {
      const done = taskLines.filter(l => l.match(/^-\s*\[x\]/i)).length
      section.taskStats = { done, total: taskLines.length }
      return `${done}/${taskLines.length} tasks complete`
    }
    
    // Check for status indicators
    if (content.includes('✅') || content.toLowerCase().includes('complete')) {
      return 'Complete'
    }
    if (content.includes('⚠️') || content.toLowerCase().includes('pending')) {
      return 'Pending'
    }
    if (content.includes('❌') || content.toLowerCase().includes('blocked')) {
      return 'Blocked'
    }
    
    // First meaningful line as summary
    const firstLine = lines[0] || ''
    // Clean up markdown
    const cleaned = firstLine
      .replace(/^\*\*(.+)\*\*$/, '$1')
      .replace(/^#+\s*/, '')
      .replace(/^\s*[-*]\s*/, '')
      .trim()
    
    return cleaned.length > 60 ? cleaned.substring(0, 57) + '...' : cleaned
  }
  
  function renderMarkdownContent(content: string): string {
    // Handle code blocks first - preserve them as <pre>
    const codeBlocks: string[] = []
    let processed = content.replace(/```[\s\S]*?```/g, (match) => {
      const code = match.replace(/```\w*\n?/, '').replace(/\n?```$/, '')
      const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`
      codeBlocks.push(`<pre class="code-block">${escapeHtml(code)}</pre>`)
      return placeholder
    })
    
    // Basic markdown to HTML conversion
    processed = processed
      .replace(/^### (.+)$/gm, '<h4 class="subsection-title">$1</h4>')
      .replace(/^\*\*(.+)\*\*$/gm, '<strong>$1</strong>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/^- \[x\] (.+)$/gim, '<li class="task done">✓ $1</li>')
      .replace(/^- \[ \] (.+)$/gim, '<li class="task pending">○ $1</li>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/^\d+\.\s+(.+)$/gm, '<li class="numbered">$1</li>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>')
    
    // Restore code blocks
    codeBlocks.forEach((block, i) => {
      processed = processed.replace(`__CODE_BLOCK_${i}__`, block)
    })
    
    return processed
  }
  
  function escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
  }
  
  return {
    parseProgressMarkdown,
    renderMarkdownContent,
  }
}
