import { useMemo, useState } from 'react'
import { cn } from '@/lib/utils'
import { getLogoUrl, getClearbitUrl } from '@/lib/logos'

export type LogoSize = 'xs' | 'sm' | 'md' | 'lg'

const SIZE: Record<LogoSize, { px: number; text: string; rounded: string; pad: string }> = {
  xs: { px: 20, text: 'text-micro', rounded: 'rounded',    pad: 'p-[1px]' },
  sm: { px: 26, text: 'text-micro', rounded: 'rounded-md', pad: 'p-[1.5px]' },
  md: { px: 34, text: 'text-micro', rounded: 'rounded-lg', pad: 'p-[2px]' },
  lg: { px: 46, text: 'text-mini', rounded: 'rounded-xl', pad: 'p-[3px]' },
}

/* Cuando no hay logo se pintan las iniciales, y el color lo elige un hash del
   ticker para que dos empresas seguidas no salgan iguales.
   Los tonos -300 sobre un fondo al 15% están calculados para tarjeta casi
   negra; sobre la blanca del modo claro las iniciales desaparecían y la ficha
   se veía como un círculo vacío — así salía CBOE, que no tiene logo en
   ninguna de las dos fuentes. En claro van los tonos -700, que es la banda que
   alcanza contraste sobre blanco. */
const PALETTE = [
  'bg-indigo-500/10  text-indigo-700  border-indigo-500/20  dark:bg-indigo-500/15  dark:text-indigo-300  dark:border-indigo-500/25',
  'bg-emerald-500/10 text-emerald-700 border-emerald-500/20 dark:bg-emerald-500/15 dark:text-emerald-300 dark:border-emerald-500/25',
  'bg-violet-500/10  text-violet-700  border-violet-500/20  dark:bg-violet-500/15  dark:text-violet-300  dark:border-violet-500/25',
  'bg-sky-500/10     text-sky-700     border-sky-500/20     dark:bg-sky-500/15     dark:text-sky-300     dark:border-sky-500/25',
  'bg-blue-500/10    text-blue-700    border-blue-500/20    dark:bg-blue-500/15    dark:text-blue-300    dark:border-blue-500/25',
  'bg-teal-500/10    text-teal-700    border-teal-500/20    dark:bg-teal-500/15    dark:text-teal-300    dark:border-teal-500/25',
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

// Tickers cuyo logo es casi blanco. Medido, no mantenido a mano.
//
// El 21% de los logos de la lista principal (8 de 38: V, RACE, CTAS, CBOE,
// EQIX, TW, NDSN, FHN) son glifos blancos sobre transparente, pensados para
// fondo oscuro. La ficha los pinta sobre `bg-white/90`, así que salían como un
// círculo vacío — no un logo roto, uno invisible, que es peor porque no hay
// nada que delate el fallo. CBOE tiene 249/255 de luminancia media y 1,05 de
// contraste contra blanco.
//
// La fuente sirve las imágenes con `access-control-allow-origin: *`, así que
// se pueden leer en un canvas y decidirlo mirando los píxeles. Una lista fija
// se quedaría desfasada la primera vez que una empresa cambie de logo.
const _logoClaroPorTicker = new Map<string, boolean>()

/** Media de luminancia de los píxeles NO transparentes. null si no se puede leer. */
function medirClaridad(src: string): Promise<boolean | null> {
  return new Promise(resolve => {
    const lienzo = document.createElement('canvas')
    const ctx = lienzo.getContext?.('2d')
    if (!ctx) { resolve(null); return }          // jsdom y navegadores sin canvas
    const sonda = new Image()
    sonda.crossOrigin = 'anonymous'              // sin esto, el canvas queda manchado
    sonda.onerror = () => resolve(null)
    sonda.onload = () => {
      try {
        // 16x16 basta para una media y evita leer 62.500 píxeles por logo.
        lienzo.width = lienzo.height = 16
        ctx.drawImage(sonda, 0, 0, 16, 16)
        const { data } = ctx.getImageData(0, 0, 16, 16)
        let suma = 0, n = 0
        for (let i = 0; i < data.length; i += 4) {
          if (data[i + 3] <= 30) continue        // transparente: no es el logo
          suma += 0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2]
          n++
        }
        // Por debajo de ~200 el logo ya contrasta de sobra con el blanco; el
        // corte deja fuera los ocho medidos (231-255) y no toca a los demás.
        resolve(n > 0 ? suma / n > 200 : null)
      } catch { resolve(null) }                  // canvas manchado pese al CORS
    }
    sonda.src = src
  })
}

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
  // Se re-renderiza cuando la medida termina. Arranca con lo ya cacheado para
  // que un ticker medido en esta sesión pinte bien al primer render.
  const [logoClaro, setLogoClaro] = useState(() => _logoClaroPorTicker.get(safe) ?? false)
  const [tickerPintado, setTickerPintado] = useState(safe)
  if (tickerPintado !== safe) {
    setTickerPintado(safe)
    setCandidateIdx(0)
    setLogoClaro(_logoClaroPorTicker.get(safe) ?? false)
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

    // Y, una sola vez por ticker, mirar si el logo es casi blanco para darle
    // una ficha oscura. Va aquí y no en un efecto porque es la reacción a un
    // evento, y el resultado se guarda a nivel de módulo: el segundo render de
    // la misma empresa ya no mide nada.
    if (!_logoClaroPorTicker.has(safe)) {
      void medirClaridad(src).then(claro => {
        if (claro == null) return                // no se pudo leer: ficha blanca
        _logoClaroPorTicker.set(safe, claro)
        if (claro) setLogoClaro(true)
      })
    }
  }

  return (
    <span
      className={cn(base, logoClaro ? 'ficha-logo-claro' : 'bg-white/90 border-border/30')}
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
