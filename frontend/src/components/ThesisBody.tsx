import type { ReactNode } from 'react'
import { BarChart3, Users, Target, Zap, CheckCircle2, AlertTriangle, TrendingUp, Shield, Info } from 'lucide-react'

// ── Section icon mapping ──────────────────────────────────────────────────────

const SECTION_ICONS: Array<[RegExp, ReactNode]> = [
  [/fundamentales/i,           <BarChart3 size={11} className="text-blue-400 shrink-0" />],
  [/insider/i,                 <Users size={11} className="text-violet-400 shrink-0" />],
  [/valorac|entrada|precio/i,  <Target size={11} className="text-emerald-400 shrink-0" />],
  [/cataliz/i,                 <Zap size={11} className="text-amber-400 shrink-0" />],
  [/conclus/i,                 <CheckCircle2 size={11} className="text-primary shrink-0" />],
  [/riesgo/i,                  <AlertTriangle size={11} className="text-red-400 shrink-0" />],
  [/momentum|técnico/i,        <TrendingUp size={11} className="text-cyan-400 shrink-0" />],
  [/salud|balance|financier/i, <Shield size={11} className="text-emerald-400 shrink-0" />],
]

function sectionIcon(header: string): ReactNode {
  for (const [re, icon] of SECTION_ICONS) {
    if (re.test(header)) return icon
  }
  return <Info size={11} className="text-muted-foreground/40 shrink-0" />
}

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
      const segs = part.split(' • ')
      segs.forEach((seg, j) => {
        const trimmed = seg.trim()
        if (!trimmed) return
        if (j === 0) {
          inlineNodes.push(<span key={`s-${i}-${j}`}>{trimmed}</span>)
        } else {
          flushInline()
          bulletBuffer.push(
            <li key={`li-${i}-${j}`} className="flex gap-2">
              <span className="text-muted-foreground/40 select-none shrink-0 mt-0.5">▸</span>
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

  const processed = text
    .replace(/\s+(\*\*[A-ZÁÉÍÓÚÑ][^*]*:\*\*)/g, '\n\n$1')
    .replace(/\s+(\*\*[A-ZÁÉÍÓÚÑ][a-záéíóúñüä\s\-\/]+\*\*)(\s*[\(:])/g, '\n\n$1$2')

  const paragraphs = processed.split('\n\n').map(p => p.trim()).filter(Boolean)

  return (
    <div className="text-sm leading-relaxed text-muted-foreground space-y-2">
      {paragraphs.map((para, pi) => {
        if (pi === 0) {
          // Intro line — lead summary
          return (
            <p key={pi} className="text-[0.82rem] text-foreground/65 leading-relaxed pb-1">
              {para}
            </p>
          )
        }

        // Try to extract a bold section header at the start
        const m = para.match(/^\*\*([^*]+?):?\*\*([\s\S]*)$/)
        if (m) {
          const header = m[1].replace(/:$/, '').trim()
          const rest = m[2].trim()
          return (
            <div key={pi} className="rounded-xl border border-border/30 overflow-hidden">
              {/* Section header row */}
              <div className="flex items-center gap-2 px-3 py-2 bg-muted/40 border-b border-border/20">
                {sectionIcon(header)}
                <span className="text-[0.65rem] font-bold tracking-widest uppercase text-foreground/55">
                  {header}
                </span>
              </div>
              {/* Content */}
              {rest && (
                <div className="px-3 py-2.5 text-[0.8rem]">
                  <Para text={rest} />
                </div>
              )}
            </div>
          )
        }

        // Fallback: plain card block
        return (
          <div key={pi} className="rounded-xl bg-muted/20 border border-border/20 px-3 py-2.5 text-[0.8rem]">
            <Para text={para} />
          </div>
        )
      })}
    </div>
  )
}
