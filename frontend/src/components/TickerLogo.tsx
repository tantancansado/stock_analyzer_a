import { useMemo, useState } from 'react'
import { cn } from '@/lib/utils'
import { getLogoUrl, getClearbitUrl } from '@/lib/logos'

export type LogoSize = 'xs' | 'sm' | 'md' | 'lg'

const SIZE: Record<LogoSize, { px: number; text: string; rounded: string; pad: string }> = {
  xs: { px: 20, text: 'text-[0.48rem]', rounded: 'rounded',    pad: 'p-[1px]' },
  sm: { px: 26, text: 'text-[0.55rem]', rounded: 'rounded-md', pad: 'p-[1.5px]' },
  md: { px: 34, text: 'text-[0.62rem]', rounded: 'rounded-lg', pad: 'p-[2px]' },
  lg: { px: 46, text: 'text-[0.75rem]', rounded: 'rounded-xl', pad: 'p-[3px]' },
}

const PALETTE = [
  'bg-indigo-500/15 text-indigo-300 border-indigo-500/25',
  'bg-emerald-500/15 text-emerald-300 border-emerald-500/25',
  'bg-violet-500/15 text-violet-300 border-violet-500/25',
  'bg-sky-500/15 text-sky-300 border-sky-500/25',
  'bg-blue-500/15 text-blue-300 border-blue-500/25',
  'bg-teal-500/15 text-teal-300 border-teal-500/25',
]

function paletteColor(ticker: string): string {
  let h = 0
  for (let i = 0; i < ticker.length; i++) h = (h * 31 + (ticker.codePointAt(i) ?? 0)) & 0x7fffffff
  return PALETTE[h % PALETTE.length]
}

function makeInitials(ticker: string): string {
  return ticker.replaceAll(/\.[A-Z]{1,3}$/g, '').replaceAll(/[^A-Z0-9]/g, '').slice(0, 2)
}

/**
 * Build the ordered list of candidate URLs for a ticker.
 * Always tries Parqet first, Clearbit second (if a domain mapping exists).
 * The component renders initials when this list is exhausted.
 *
 * Both sources are always attempted: Parqet covers ~3000 symbols (US-heavy)
 * but misses many EU tickers. Clearbit only fires when we have a hand-curated
 * domain mapping but covers cases Parqet misses.
 */
function buildCandidates(ticker: string): string[] {
  const out: string[] = []
  if (!ticker) return out
  out.push(getLogoUrl(ticker))
  const cb = getClearbitUrl(ticker)
  if (cb && cb !== out[0]) out.push(cb)
  return out
}

// Module-level cache: ticker → candidate URL that successfully rendered
// in this session. Avoids hitting Parqet for tickers we already know are EU
// (saves a 404 round-trip, smoother re-mounts after navigation).
const _winnerByTicker = new Map<string, string>()
const _failedByTicker = new Set<string>()

interface Props {
  readonly ticker: string
  readonly size?: LogoSize
  readonly className?: string
}

export default function TickerLogo({ ticker, size = 'sm', className }: Props) {
  const safe = ticker ?? ''
  const { px, text, rounded, pad } = SIZE[size]
  const initials = makeInitials(safe)

  // Los candidatos se calculan DURANTE el render, no en un efecto.
  //
  // Antes vivían en un useRef que se llenaba dentro de un useEffect. Dos cosas
  // se juntaban para que no funcionara nunca: un ref no provoca re-render, y
  // el `setCandidateIdx(0)` que lo acompañaba no cambiaba el valor (ya era 0),
  // así que React salía por su bail-out. El primer render veía la lista vacía,
  // caía a las iniciales y no volvía a renderizar jamás.
  //
  // Efecto medido en producción: 114 fichas con iniciales y CERO peticiones de
  // logo — ni una fallida. El mecanismo entero estaba muerto.
  const candidates = useMemo(() => {
    const known = _winnerByTicker.get(safe)
    if (known) return [known]                    // ya validado en esta sesión
    if (_failedByTicker.has(safe)) return []     // ya se agotó, directo a iniciales
    return buildCandidates(safe)
  }, [safe])

  const [candidateIdx, setCandidateIdx] = useState(0)
  // Al cambiar de ticker hay que volver al primer candidato. Se compara contra
  // el ticker renderizado, que es el patrón de React para derivar estado sin
  // un efecto de por medio.
  const [tickerPintado, setTickerPintado] = useState(safe)
  if (tickerPintado !== safe) {
    setTickerPintado(safe)
    setCandidateIdx(0)
  }

  const base = cn(
    'flex-shrink-0 border inline-flex items-center justify-center overflow-hidden',
    rounded,
    className,
  )

  const exhausted = candidateIdx >= candidates.length

  // Initials fallback: no candidates, exhausted all, or empty ticker
  if (!safe || candidates.length === 0 || exhausted) {
    return (
      <span
        className={cn(base, paletteColor(safe))}
        style={{ width: px, height: px }}
        aria-hidden="true"
      >
        <span className={cn('font-mono font-bold leading-none select-none', text)}>
          {initials || '?'}
        </span>
      </span>
    )
  }

  const src = candidates[candidateIdx]

  // Un evento tardío de una imagen anterior no puede colarse: el <img> lleva
  // key={ticker}-{idx}, así que React lo desmonta al cambiar cualquiera de los
  // dos y sus handlers ya no se disparan.
  const advanceOrFail = () => {
    setCandidateIdx(idx => {
      const next = idx + 1
      if (next >= candidates.length) {
        _failedByTicker.add(safe)  // remember to skip both sources next time
      }
      return next
    })
  }

  const handleError = () => {
    advanceOrFail()
  }

  const handleLoad = (event: React.SyntheticEvent<HTMLImageElement>) => {
    const img = event.currentTarget
    // Detect 1x1 placeholders that some CDNs return with status 200 for
    // unknown tickers. Treat as a failed candidate.
    if (img.naturalWidth <= 1 || img.naturalHeight <= 1) {
      advanceOrFail()
      return
    }
    // Successful load — remember this URL for the rest of the session
    _winnerByTicker.set(safe, src)
  }

  return (
    <span
      className={cn(base, 'bg-white/90 border-border/30')}
      style={{ width: px, height: px }}
      aria-hidden="true"
    >
      <img
        // key forces a fresh <img> element on each candidate change so the
        // previous one doesn't fire late onLoad/onError after a setState.
        key={`${safe}-${candidateIdx}`}
        src={src}
        alt=""
        width={px}
        height={px}
        onError={handleError}
        onLoad={handleLoad}
        className={cn('w-full h-full object-contain', pad)}
        decoding="async"
      />
    </span>
  )
}
