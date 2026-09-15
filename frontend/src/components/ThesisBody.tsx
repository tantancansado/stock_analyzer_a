import type { ReactNode } from 'react'
import { BarChart3, Users, Target, Zap, CheckCircle2, AlertTriangle, TrendingUp, Shield, Info, ChartColumn} from 'lucide-react'

// ── Section icon mapping ──────────────────────────────────────────────────────

const SECTION_ICONS: Array<[RegExp, ReactNode]> = [
  [/fundamentales/i,           <BarChart3 size={12} className="text-blue-400 shrink-0" />],
  [/insider/i,                 <Users size={12} className="text-violet-400 shrink-0" />],
  [/valorac|entrada|precio/i,  <Target size={12} className="text-emerald-400 shrink-0" />],
  [/cataliz/i,                 <Zap size={12} className="text-amber-400 shrink-0" />],
  [/conclus/i,                 <CheckCircle2 size={12} className="text-primary shrink-0" />],
  [/riesgo/i,                  <AlertTriangle size={12} className="text-red-400 shrink-0" />],
  [/momentum|técnico/i,        <TrendingUp size={12} className="text-cyan-400 shrink-0" />],
  [/salud|balance|financier/i, <Shield size={12} className="text-emerald-400 shrink-0" />],
]

function sectionIcon(header: string): ReactNode {
  for (const [re, icon] of SECTION_ICONS) {
    if (re.test(header)) return icon
  }
  return <Info size={12} className="text-muted-foreground shrink-0" />
}

// ── Value colorization ────────────────────────────────────────────────────────

/** Color a numeric value based on context keywords */
function valueColor(label: string, val: string): string {
  const lcLabel = label.toLowerCase()
  const lcVal = val.toLowerCase()

  // Explicit qualifiers
  if (lcVal.includes('excelente') || lcVal.includes('conservador') || lcVal.includes('fuerte'))
    return 'text-emerald-400'
  if (lcVal.includes('débil') || lcVal.includes('agresivo') || lcVal.includes('peligro'))
    return 'text-red-400'

  // Numeric extraction
  const numMatch = val.match(/[+-]?([\d,]+\.?\d*)/)
  if (!numMatch) return 'text-foreground/80'
  const num = parseFloat(numMatch[1].replace(',', ''))

  // ROE
  if (lcLabel.includes('roe'))
    return num >= 15 ? 'text-emerald-400' : num < 0 ? 'text-red-400' : 'text-foreground/80'
  // Margins
  if (lcLabel.includes('margen'))
    return num >= 20 ? 'text-emerald-400' : num < 5 ? 'text-red-400' : 'text-foreground/80'
  // Debt
  if (lcLabel.includes('deuda'))
    return num <= 0.5 ? 'text-emerald-400' : num > 1.5 ? 'text-red-400' : 'text-amber-400'
  // Growth (starts with + or -)
  if (lcLabel.includes('crecimiento') || val.startsWith('+'))
    return num > 0 ? 'text-emerald-400' : 'text-red-400'
  // Distance from 52w high
  if (lcLabel.includes('distancia') || lcLabel.includes('52'))
    return num >= -10 ? 'text-emerald-400' : num <= -25 ? 'text-red-400' : 'text-amber-400'
  // Short interest
  if (lcLabel.includes('short'))
    return num > 20 ? 'text-red-400' : num > 10 ? 'text-amber-400' : 'text-foreground/80'
  // Score
  if (lcLabel.includes('score'))
    return num >= 70 ? 'text-emerald-400' : num < 40 ? 'text-red-400' : 'text-foreground/80'
  // Upside/infravalorada
  if (lcVal.includes('infravalorada') || (val.startsWith('+') && num > 20))
    return 'text-emerald-400'

  return 'text-foreground/80'
}

// ── Bullet parsing helpers ────────────────────────────────────────────────────

interface KVPair { label: string; value: string }
interface InsiderTx { role: string; amount: string; date: string }

/** Try to parse "Label: Value (qualifier)" from a bullet line */
function parseKV(line: string): KVPair | null {
  // Skip insider transaction arrows
  if (line.trim().startsWith('→')) return null
  // "Label: Value" pattern
  const m = line.match(/^([^:]+):\s*(.+)$/)
  if (m) return { label: m[1].trim(), value: m[2].trim() }
  return null
}

/** Parse insider transaction "→ Role: $Amount (Date)" */
function parseInsiderTx(line: string): InsiderTx | null {
  const m = line.match(/→\s*([^:]+):\s*(\$[\d,.]+)\s*\(([^)]+)\)/)
  if (m) return { role: m[1].trim(), amount: m[2], date: m[3] }
  return null
}

/** Parse analyst target line "Consenso analistas (N analistas): $X (+Y%) — Rating" */
function parseAnalystLine(line: string): { analysts: string; target: string; upside: string; rating: string; range?: string } | null {
  const m = line.match(/Consenso analistas\s*\((\d+ analistas?)\):\s*(\$[\d,.]+)\s*\(([^)]+)\)\s*—\s*(.+)/)
  if (m) return { analysts: m[1], target: m[2], upside: m[3], rating: m[4].trim() }
  return null
}

// ── Section-specific renderers ────────────────────────────────────────────────

/** Render fundamentals as a metrics grid */
function FundamentalsGrid({ bullets }: { bullets: string[] }): ReactNode {
  const kvPairs: KVPair[] = []
  const otherLines: string[] = []

  for (const b of bullets) {
    const kv = parseKV(b)
    if (kv) kvPairs.push(kv)
    else otherLines.push(b)
  }

  if (kvPairs.length === 0) return null

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-1.5">
        {kvPairs.map((kv, i) => (
          <div key={i} className="flex items-baseline justify-between gap-2 px-2.5 py-1.5 rounded-lg bg-muted/20">
            <span className="text-mini text-muted-foreground truncate">{kv.label}</span>
            <span className={`text-apoyo font-semibold tabular-nums whitespace-nowrap ${valueColor(kv.label, kv.value)}`}>
              {kv.value}
            </span>
          </div>
        ))}
      </div>
      {otherLines.length > 0 && (
        <div className="text-apoyo space-y-1">
          {otherLines.map((l, i) => (
            <p key={i} className="text-muted-foreground">{l}</p>
          ))}
        </div>
      )}
    </div>
  )
}

/** Render insider section with transaction mini-table */
function InsiderSection({ preamble, bullets }: { preamble: string; bullets: string[] }): ReactNode {
  const kvPairs: KVPair[] = []
  const txs: InsiderTx[] = []
  const otherLines: string[] = []

  for (const b of bullets) {
    const tx = parseInsiderTx(b)
    if (tx) { txs.push(tx); continue }
    const kv = parseKV(b)
    if (kv) { kvPairs.push(kv); continue }
    otherLines.push(b)
  }

  return (
    <div className="space-y-2">
      {preamble && <p className="text-apoyo text-muted-foreground">{preamble}</p>}
      {kvPairs.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {kvPairs.map((kv, i) => (
            <span key={i} className="inline-flex items-baseline gap-1.5 px-2 py-1 rounded-md bg-violet-500/10 border border-violet-500/15 text-mini">
              <span className="text-muted-foreground">{kv.label}:</span>
              <span className="font-semibold text-violet-300">{kv.value}</span>
            </span>
          ))}
        </div>
      )}
      {txs.length > 0 && (
        <div className="rounded-lg border border-border/20 overflow-hidden">
          <table className="w-full text-mini">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-2 py-1 text-left font-medium text-muted-foreground">Rol</th>
                <th className="px-2 py-1 text-right font-medium text-muted-foreground">Monto</th>
                <th className="px-2 py-1 text-right font-medium text-muted-foreground">Fecha</th>
              </tr>
            </thead>
            <tbody>
              {txs.map((tx, i) => (
                <tr key={i} className="border-t border-border/10">
                  <td className="px-2 py-1 text-violet-300">{tx.role}</td>
                  <td className="px-2 py-1 text-right font-semibold tabular-nums text-foreground/70">{tx.amount}</td>
                  <td className="px-2 py-1 text-right tabular-nums text-muted-foreground">{tx.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {otherLines.length > 0 && (
        <div className="text-apoyo space-y-1">
          {otherLines.map((l, i) => <p key={i} className="text-muted-foreground">{l}</p>)}
        </div>
      )}
    </div>
  )
}

/** Render valuation section with visual target cards */
function ValuationSection({ bullets }: { bullets: string[] }): ReactNode {
  const items: ReactNode[] = []

  for (let i = 0; i < bullets.length; i++) {
    const b = bullets[i]
    // Analyst consensus
    const analyst = parseAnalystLine(b)
    if (analyst) {
      // Check if next line is range
      let range: string | undefined
      if (i + 1 < bullets.length && bullets[i + 1].includes('Rango:')) {
        range = bullets[i + 1].replace(/^Rango:\s*/, '').trim()
        i++
      }
      items.push(
        <div key={`a-${i}`} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-emerald-500/8 border border-emerald-500/15">
          <div className="flex-1">
            <div className="flex items-baseline gap-2">
              <span className="text-cuerpo font-bold text-emerald-400 tabular-nums">{analyst.target}</span>
              <span className="text-mini font-semibold text-emerald-400">{analyst.upside}</span>
              <span className="px-1.5 py-0.5 rounded text-micro font-bold uppercase bg-emerald-500/15 text-emerald-300">{analyst.rating}</span>
            </div>
            <div className="text-micro text-muted-foreground mt-0.5">
              Consenso {analyst.analysts}{range ? ` · Rango: ${range}` : ''}
            </div>
          </div>
        </div>
      )
      continue
    }

    // DCF / P/E valuation lines: "Valor intrínseco (DCF): $103.06 (+148.1% — infravalorada)"
    const valMatch = b.match(/^(Valor[^:]+):\s*(\$[\d,.]+)\s*\(([^)]+)\)/)
    if (valMatch) {
      const isPositive = valMatch[3].includes('+') || valMatch[3].includes('infravalorada')
      items.push(
        <div key={`v-${i}`} className="flex items-baseline justify-between px-3 py-1.5 rounded-lg bg-muted/20">
          <span className="text-mini text-muted-foreground">{valMatch[1]}</span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-apoyo font-bold tabular-nums text-foreground/80">{valMatch[2]}</span>
            <span className={`text-micro font-semibold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
              {valMatch[3]}
            </span>
          </div>
        </div>
      )
      continue
    }

    // Range line standalone
    if (b.startsWith('Rango:')) {
      items.push(
        <div key={`r-${i}`} className="text-mini text-muted-foreground px-3">
          <ChartColumn size={12} strokeWidth={2.25} className="inline -mt-px mr-1" />{b}
        </div>
      )
      continue
    }

    // Generic KV
    const kv = parseKV(b)
    if (kv) {
      items.push(
        <div key={`kv-${i}`} className="flex items-baseline justify-between px-3 py-1.5 rounded-lg bg-muted/20">
          <span className="text-mini text-muted-foreground">{kv.label}</span>
          <span className={`text-apoyo font-semibold tabular-nums ${valueColor(kv.label, kv.value)}`}>{kv.value}</span>
        </div>
      )
      continue
    }

    // Plain text
    items.push(<p key={`p-${i}`} className="text-apoyo text-muted-foreground px-1">{b}</p>)
  }

  return <div className="space-y-1.5">{items}</div>
}

/** Render conclusion as a styled callout */
function ConclusionBlock({ text }: { text: string }): ReactNode {
  return (
    <p className="text-apoyo text-foreground/70 leading-relaxed">{text}</p>
  )
}

// ── Bullet extraction ─────────────────────────────────────────────────────────

/** Split section body into individual bullet items */
function extractBullets(text: string): { preamble: string; bullets: string[] } {
  // Split on "• " at start or after newline
  const parts = text.split(/\n?•\s+/)
  const preamble = parts[0]?.trim() ?? ''
  const bullets = parts.slice(1).map(b => b.replace(/\n/g, ' ').trim()).filter(Boolean)
  return { preamble, bullets }
}

/** Detect section type for specialized rendering */
type SectionType = 'fundamentals' | 'insiders' | 'valuation' | 'conclusion' | 'catalysts' | 'risks' | 'generic'

function sectionType(header: string): SectionType {
  const lc = header.toLowerCase()
  if (/fundamentales|salud|balance/.test(lc)) return 'fundamentals'
  if (/insider/.test(lc)) return 'insiders'
  if (/valorac|entrada|precio/.test(lc)) return 'valuation'
  if (/conclus/.test(lc)) return 'conclusion'
  if (/cataliz/.test(lc)) return 'catalysts'
  if (/riesgo/.test(lc)) return 'risks'
  return 'generic'
}

/** Left accent color per section type */
function sectionAccent(type: SectionType): string {
  switch (type) {
    case 'fundamentals': return 'border-l-blue-500/50'
    case 'insiders':     return 'border-l-violet-500/50'
    case 'valuation':    return 'border-l-emerald-500/50'
    case 'conclusion':   return 'border-l-primary/50'
    case 'catalysts':    return 'border-l-amber-500/50'
    case 'risks':        return 'border-l-red-500/50'
    default:             return 'border-l-border/50'
  }
}

// ── Generic bullet renderer (catalysts, risks, etc.) ──────────────────────────

function GenericBullets({ preamble, bullets }: { preamble: string; bullets: string[] }): ReactNode {
  return (
    <div className="space-y-1.5">
      {preamble && <p className="text-apoyo text-muted-foreground">{preamble}</p>}
      {bullets.length > 0 && (
        <ul className="space-y-1">
          {bullets.map((b, i) => (
            <li key={i} className="flex gap-2 text-apoyo">
              <span className="text-primary select-none shrink-0 mt-0.5">▸</span>
              <span className="text-muted-foreground">{b}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

export default function ThesisBody({ text }: { text: string }) {
  // `typeof !== 'string'` además de `!text`: un objeto es truthy y pasaba el
  // guardia, y dos líneas más abajo `.replace()` reventaba la página entera
  // con "n.replace is not a function" al abrir una tesis. Pasaba porque las
  // páginas caían a `overview` cuando faltaba la narrativa, y overview es un
  // diccionario de métricas (ya corregido en fetchThesis). Un componente de
  // presentación no debe poder tumbar la pantalla por recibir algo raro.
  const isStatus = (
    typeof text !== 'string' ||
    !text ||
    text === 'Cargando tesis...' ||
    text === 'Sin tesis disponible' ||
    text === 'Error cargando tesis'
  )
  if (isStatus) {
    return (
      <p className="text-cuerpo text-muted-foreground italic">
        {typeof text === 'string' && text ? text : 'Sin tesis disponible'}
      </p>
    )
  }

  const processed = text
    .replace(/\s+(\*\*[A-ZÁÉÍÓÚÑ][^*]*:\*\*)/g, '\n\n$1')
    .replace(/\s+(\*\*[A-ZÁÉÍÓÚÑ][a-záéíóúñüä\s/-]+\*\*)(\s*[(:])/g, '\n\n$1$2')

  const paragraphs = processed.split('\n\n').map(p => p.trim()).filter(Boolean)

  return (
    <div className="text-cuerpo leading-relaxed text-muted-foreground space-y-2.5">
      {paragraphs.map((para, pi) => {
        if (pi === 0) {
          // Strip redundant ticker/sector (already in modal header)
          const clean = para.replace(/\*\*/g, '').replace(/^[A-Z0-9.]+\s*—\s*/, '')
          return (
            <p key={pi} className="text-apoyo text-muted-foreground leading-relaxed pb-1 border-b border-border/15 mb-1">
              {clean}
            </p>
          )
        }

        // Try to extract a bold section header at the start
        const m = para.match(/^\*\*([^*]+?):?\*\*([\s\S]*)$/)
        if (m) {
          const header = m[1].replace(/:$/, '').trim()
          const rest = m[2].trim()
          const type = sectionType(header)
          const { preamble, bullets } = extractBullets(rest)

          let content: ReactNode = null
          if (type === 'fundamentals' && bullets.length > 0) {
            content = <FundamentalsGrid bullets={bullets} />
          } else if (type === 'insiders') {
            content = <InsiderSection preamble={preamble} bullets={bullets} />
          } else if (type === 'valuation') {
            content = <ValuationSection bullets={bullets.length > 0 ? bullets : preamble ? [preamble] : []} />
          } else if (type === 'conclusion') {
            content = <ConclusionBlock text={rest.replace(/^•\s*/, '')} />
          } else if (bullets.length > 0) {
            content = <GenericBullets preamble={preamble} bullets={bullets} />
          } else if (rest) {
            content = <p className="text-apoyo text-muted-foreground">{rest}</p>
          }

          return (
            <div key={pi} className={`rounded-xl border border-border/30 border-l-2 ${sectionAccent(type)} overflow-hidden`}>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/30 border-b border-border/15">
                {sectionIcon(header)}
                <span className="text-micro font-bold tracking-widest uppercase text-muted-foreground">
                  {header}
                </span>
              </div>
              {content && (
                <div className="px-3 py-2">
                  {content}
                </div>
              )}
            </div>
          )
        }

        // Fallback: plain card block
        return (
          <div key={pi} className="rounded-xl bg-muted/20 border border-border/20 px-3 py-2.5 text-apoyo">
            <p className="text-muted-foreground">{para.replace(/\*\*/g, '')}</p>
          </div>
        )
      })}
    </div>
  )
}
