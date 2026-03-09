import type { ReactNode } from 'react'

// ── helpers ───────────────────────────────────────────────────────────────────

/** Render a paragraph: inline **bold** + bullet splitting on ' • ' */
function Para({ text }: { text: string }): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  const items: ReactNode[] = []
  let bulletBuffer: ReactNode[] = []

  const flushBullets = (key: string) => {
    if (bulletBuffer.length === 0) return
    items.push(
      <ul key={key} className="mt-1 space-y-1">
        {bulletBuffer}
      </ul>
    )
    bulletBuffer = []
  }

  let inlineNodes: ReactNode[] = []
  let partIdx = 0

  const flushInline = () => {
    if (inlineNodes.length === 0) return
    items.push(<span key={`inline-${partIdx}`}>{inlineNodes}</span>)
    inlineNodes = []
  }

  parts.forEach((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      const content = part.slice(2, -2)
      inlineNodes.push(
        <strong key={`b-${i}`} className="text-foreground font-semibold">
          {content}
        </strong>
      )
      partIdx = i
    } else {
      // Split on ' • ' — first segment is inline, rest are bullet items
      const segs = part.split(' • ')
      segs.forEach((seg, j) => {
        const trimmed = seg.trim()
        if (!trimmed) return
        if (j === 0) {
          inlineNodes.push(<span key={`s-${i}-${j}`}>{trimmed}</span>)
        } else {
          // Flush any accumulated inline nodes as a line before starting bullets
          flushInline()
          bulletBuffer.push(
            <li key={`li-${i}-${j}`} className="flex gap-2">
              <span className="text-muted-foreground/50 select-none shrink-0">•</span>
              <span>{trimmed}</span>
            </li>
          )
        }
      })
      partIdx = i
    }
  })

  flushInline()
  flushBullets('final')

  return <>{items}</>
}

// ── main component ────────────────────────────────────────────────────────────

export default function ThesisBody({ text }: { text: string }) {
  const isStatus = (
    !text ||
    text === 'Cargando tesis...' ||
    text === 'Sin tesis disponible' ||
    text === 'Error cargando tesis'
  )
  if (isStatus) {
    return <p className="text-sm text-muted-foreground italic">{text || 'Sin tesis disponible'}</p>
  }

  // Pre-process: insert paragraph breaks before section headers so each section
  // renders in its own block.
  //
  // Pattern A — colon inside bold:  **Fundamentales:**  **Conclusión:**
  // Pattern B — colon/paren after:  **Actividad de insiders** (score ...)
  const processed = text
    // Pattern A: any **...:**, preceded by whitespace
    .replace(/\s+(\*\*[A-ZÁÉÍÓÚÑ][^*]*:\*\*)/g, '\n\n$1')
    // Pattern B: multi-word **Bold** immediately followed by ( or :
    .replace(/\s+(\*\*[A-ZÁÉÍÓÚÑ][a-záéíóúñüä\s\-\/]+\*\*)(\s*[\(:])/g, '\n\n$1$2')

  const paragraphs = processed.split('\n\n').map(p => p.trim()).filter(Boolean)

  return (
    <div className="text-sm leading-relaxed text-muted-foreground py-1 space-y-2.5">
      {paragraphs.map((para, pi) => {
        const isIntro = pi === 0
        return (
          <div
            key={pi}
            className={isIntro
              ? 'text-foreground/70 font-medium'
              : 'rounded-lg bg-muted/25 border border-border/25 px-3 py-2.5'}
          >
            <Para text={para} />
          </div>
        )
      })}
    </div>
  )
}
