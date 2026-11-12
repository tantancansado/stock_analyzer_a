import { useState, useEffect, useRef, useMemo, useCallback, useDeferredValue } from 'react'
import { AnimatePresence } from 'motion/react'
import { TriangleAlert, Gem, Landmark } from 'lucide-react'
import { precio } from '../lib/moneda'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchValueOpportunities, fetchMarketRegime, fetchThesis, fetchMacroRadar, type ValueOpportunity } from '../api/client'
import StaleDataBanner from '../components/StaleDataBanner'
import { usePersonalPortfolio } from '../context/PersonalPortfolioContext'
import { useApi } from '../hooks/useApi'
import ScoreBar from '../components/ScoreBar'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import CsvDownload from '../components/CsvDownload'
import PaginationBar from '../components/PaginationBar'
import InfoTooltip from '../components/InfoTooltip'
import ThesisModal from '../components/ThesisModal'
import TickerLogo from '../components/TickerLogo'
import OwnedBadge from '../components/OwnedBadge'
import ValuationBar from '../components/ValuationBar'
import OeAiBadge from '../components/OeAiBadge'
import PageHeader from '../components/PageHeader'
import AvisoDatosViejos from '@/components/AvisoDatosViejos'
import RendimientoReal from '../components/RendimientoReal'
import { LogoCandleBull } from '../components/BrandLogos'
import { useValueExperienceMode } from '../hooks/useValueExperienceMode'
import { ValueClarityPanel, ValueDecisionBadge, ValueModeToggle } from '../components/ValueDecision'
import { getValueDecision } from '@/lib/valueDecision'
import PageShell from '@/components/PageShell'
import { nlRegimen, nlRegimenTono } from '@/lib/nl'
import CifrasClave from '../components/CifrasClave'

/** Nuestro potencial: la valoración triangulada (DCF y P/E propios con el
 *  consenso), que es lo que decide la lista. El objetivo de los analistas solo,
 *  donde no hay otro. Era el del analista: INTU salía a +19 % con nuestros
 *  modelos viéndole +150 %. */
function potencial(d: ValueOpportunity): number | null {
  return d.upside_triangulated_pct ?? d.analyst_upside_pct ?? null
}

// Value US decide con UNA regla (value_bands.nota_value) y cada fila dice su grupo y
// por qué. El 12-nov la vista completa enseñaba, al lado de tres de Prioridad,
// ESPERA, EXIT, TRAP, un grado D, «HARD REJECT», un R:R con stop del 8 % y un P(win)
// que ya no se publica: reglas anteriores que la lista no usa y que decían lo
// contrario. Esas señales viven en la ficha como datos, no en la fila como veredicto.
const GRUPO_FILTROS: { clave: string; etiqueta: string }[] = [
  { clave: 'ALL',       etiqueta: 'Todas' },
  { clave: 'PRIORIDAD', etiqueta: 'Prioridad' },
  { clave: 'OBSERVAR',  etiqueta: 'Observar' },
]

type SortKey = keyof ValueOpportunity
type SortDir = 'asc' | 'desc'

export default function ValueUS() {
  const { data, loading, error } = useApi(() => fetchValueOpportunities(), [])
  const { data: regime } = useApi(() => fetchMarketRegime(), [])
  const { data: macroRaw } = useApi(() => fetchMacroRadar(), [])
  const [sortKey, setSortKey] = useState<SortKey>('value_score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [expandedRow, setExpandedRow] = useState<ValueOpportunity | null>(null)
  const [thesisText, setThesisText] = useState<string>('')
  const { clearMode, setClearMode } = useValueExperienceMode()

  // URL-synced filters
  const [searchParams, setSearchParams] = useSearchParams()

  const filterGrupo = searchParams.get('grupo') ?? 'ALL'
  const filterSector = searchParams.get('sector') ?? 'ALL'
  const minFcf = searchParams.get('fcf') ?? ''

  function setFilterGrupo(v: string) {
    setSearchParams(p => {
      const next = new URLSearchParams(p)
      if (v === 'ALL') next.delete('grupo')
      else next.set('grupo', v)
      return next
    }, { replace: true })
  }
  function setFilterSector(v: string) {
    setSearchParams(p => {
      const next = new URLSearchParams(p)
      if (v === 'ALL') next.delete('sector')
      else next.set('sector', v)
      return next
    }, { replace: true })
  }
  function setMinFcf(v: string) {
    setSearchParams(p => {
      const next = new URLSearchParams(p)
      if (v === '') next.delete('fcf')
      else next.set('fcf', v)
      return next
    }, { replace: true })
  }

  const [hideEarnings, setHideEarnings] = useState(false)
  const [onlyOwned, setOnlyOwned] = useState(false)
  const [onlyHf, setOnlyHf] = useState(false)
  const [compact, setCompact] = useState(() => typeof window !== 'undefined' && window.innerWidth < 1280)
  const { isOwned, positions: myPos } = usePersonalPortfolio()
  const [page, setPage] = useState(1)
  const [focusedIdx, setFocusedIdx] = useState(-1)
  const PAGE_SIZE = 50

  // useDeferredValue: los filtros de texto/número no bloquean el UI mientras se recalcula
  const deferredMinFcf = useDeferredValue(minFcf)

  const currentThesisTicker = useRef<string | null>(null)
  // pagedRef must be declared before early returns (React Rules of Hooks)
  const pagedRef = useRef<ValueOpportunity[]>([])

  const toggleThesis = useCallback(async (ticker: string, row: ValueOpportunity) => {
    currentThesisTicker.current = ticker
    setExpandedRow(row)
    setThesisText('Cargando tesis...')
    const fallback = () => {
      const parts: string[] = []
      if (row.ai_reasoning) parts.push(row.ai_reasoning)
      if (row.conviction_reasons) parts.push(row.conviction_reasons.split(/\s*\|\|?\s*/).slice(0, 3).map(r => `• ${r}`).join('\n'))
      return parts.length > 0
        ? `${parts.join('\n\n')}\n\n_Tesis narrativa aún no generada. Mostrando el razonamiento de la IA._`
        : 'Sin tesis disponible'
    }
    try {
      const res = await fetchThesis(ticker)
      if (currentThesisTicker.current !== ticker) return
      const t = res.data.thesis
      const text = t ?? fallback()
      setThesisText(text)
    } catch { if (currentThesisTicker.current === ticker) setThesisText(fallback()) }
  }, [])

  // Reset page + scroll to top when any filter changes
  useEffect(() => { setPage(1); setFocusedIdx(-1) }, [filterGrupo, filterSector, minFcf, hideEarnings, onlyOwned, onlyHf])
  // Scroll to top when page changes
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'smooth' }) }, [page])

  // Keyboard navigation — j/k/Enter/Escape
  // useRef para evitar stale closures (paged se recalcula cada render)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (document.activeElement as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return
      if (e.key === 'Escape') { setFocusedIdx(-1); return }
      if (e.key === 'j' || e.key === 'ArrowDown') {
        e.preventDefault()
        setFocusedIdx(i => {
          const next = Math.min(i + 1, pagedRef.current.length - 1)
          setTimeout(() => document.querySelector(`[data-row-idx="${next}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 0)
          return next
        })
      } else if (e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault()
        setFocusedIdx(i => {
          const prev = Math.max(i - 1, 0)
          setTimeout(() => document.querySelector(`[data-row-idx="${prev}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 0)
          return prev
        })
      } else if (e.key === 'Enter') {
        setFocusedIdx(i => {
          if (i >= 0 && pagedRef.current[i]) toggleThesis(pagedRef.current[i].ticker, pagedRef.current[i])
          return i
        })
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [toggleThesis])

  // ─── Derived data — computed before early returns (Rules of Hooks) ───────────
  const rows = data?.data ?? []

  const sectors = useMemo(
    () => ['ALL', ...Array.from(new Set(rows.map(r => r.sector).filter(Boolean) as string[])).sort()],
    [rows]
  )


  const filtered = useMemo(() => rows.filter(r => {
    if (filterGrupo !== 'ALL' && r.value_grupo !== filterGrupo) return false
    if (filterSector !== 'ALL' && r.sector !== filterSector) return false
    if (deferredMinFcf !== '' && (r.fcf_yield_pct == null || r.fcf_yield_pct < Number(deferredMinFcf))) return false
    if (hideEarnings && r.earnings_warning) return false
    if (onlyOwned && !isOwned(r.ticker)) return false
    if (onlyHf && (r.hedge_fund_count ?? 0) < 1) return false
    return true
  }), [rows, filterGrupo, filterSector, deferredMinFcf, hideEarnings, onlyOwned, onlyHf, isOwned])

  // Por defecto manda la nota: PRIORIDAD arriba y, dentro de cada grupo, lo barata.
  const sorted = useMemo(() => [...filtered].sort((a, b) => {
    const av = a[sortKey] ?? 0
    const bv = b[sortKey] ?? 0
    if (av < bv) return sortDir === 'asc' ? -1 : 1
    if (av > bv) return sortDir === 'asc' ? 1 : -1
    return 0
  }), [filtered, sortKey, sortDir])


  // Concentración DE VERDAD: un sector que se lleve al menos un cuarto de la
  // lista. El umbral era "3 o más empresas", que con 57 ideas es el 5% y lo
  // cumplían siete sectores a la vez — o sea, el reparto normal. El aviso
  // salía siempre y en ámbar de alarma, avisando de nada.
  const concentrated = useMemo(() => {
    const counts: Record<string, number> = {}
    sorted.forEach(d => { const s = d.sector || 'Unknown'; counts[s] = (counts[s] || 0) + 1 })
    const minimo = Math.max(3, Math.ceil(sorted.length * 0.25))
    return Object.entries(counts).filter(([, c]) => c >= minimo).sort((a, b) => b[1] - a[1])
  }, [sorted])

  // Cabecera también mientras carga o si la API falla: si no, la pantalla
  // de error no dice en qué sección estás. Ver PageShell.
  if (loading || error) return <PageShell title="VALUE US" loading={loading} error={error} />

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const paged = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  pagedRef.current = paged

  const onSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const thCls = (key: SortKey) =>
    `cursor-pointer select-none whitespace-nowrap transition-colors hover:text-foreground ${sortKey === key ? 'text-primary' : ''}`

  const usRegime = regime?.us as Record<string, string> | undefined
  // "UNKNOWN" no es un régimen, es la ausencia de dato. Pintarlo como badge
  // al lado del título es decirle al usuario "el mercado está: desconocido",
  // que no informa de nada y ocupa el mismo sitio que un aviso de verdad.
  const regimeCrudo = usRegime?.regime || usRegime?.market_regime || ''
  const regimeLabel = nlRegimen(regimeCrudo)
  const regimeRec = usRegime?.recommendation || ''

  const hasActiveFilters = filterGrupo !== 'ALL' || filterSector !== 'ALL' || minFcf !== '' || hideEarnings || onlyOwned || onlyHf
  const resetFilters = () => {
    setSearchParams({}, { replace: true })
    setMinFcf(''); setHideEarnings(false); setOnlyOwned(false); setOnlyHf(false)
  }
  // Solo el grupo decide (Cerebro y el veredicto de entrada no entran: medidos, no
  // separan, y cargarlos solo servía para avisar de que no habían cargado).
  const decisionFor = (row: ValueOpportunity) => getValueDecision({ row })

  const fmtFcf = (v?: number) => {
    if (v == null) return <span className="text-muted-foreground">—</span>
    const cls = v >= 5 ? 'text-emerald-400' : v >= 3 ? 'text-amber-400' : v < 0 ? 'text-red-400' : ''
    return <span className={cls}>{v.toFixed(1)}%</span>
  }
  const fmtPotencial = (d: ValueOpportunity) => {
    const v = potencial(d)
    if (v == null) return <span className="text-muted-foreground">—</span>
    return <span className={v >= 0 ? 'text-emerald-400' : 'text-red-400'}>{v >= 0 ? '+' : ''}{v.toFixed(0)}%</span>
  }
  const fmtDivBB = (d: ValueOpportunity) => {
    const parts: string[] = []
    if (d.dividend_yield_pct != null && d.dividend_yield_pct > 0) parts.push(`${d.dividend_yield_pct.toFixed(1)}%`)
    if (d.buyback_active) parts.push('BB')
    return parts.length
      ? <span className="text-emerald-400">{parts.join('+')}</span>
      : <span className="text-muted-foreground">—</span>
  }
  // Sin semáforo: en rojo, unos resultados a 7 días decían «no entres» al lado de
  // una de Prioridad, y la casa no frena por eso (se dice como hecho).
  const fmtEarn = (d: ValueOpportunity) => {
    if (d.days_to_earnings == null || d.days_to_earnings < 0) return <span className="text-muted-foreground">—</span>
    return <span className="text-muted-foreground">{d.days_to_earnings}d</span>
  }

  return (
    <>
      <StaleDataBanner module="value_us" />
      {/* El título SE VE. Estuvo oculto porque la pestaña de arriba ya decía
          "VALUE US" y repetirlo era decir lo mismo dos veces — cierto, pero el
          remedio dejó la página sin ningún punto de entrada: se empezaba a
          leer por un aviso, unas pestañas y cuatro tarjetas, todo del mismo
          tamaño. Una pantalla necesita UNA cosa que se lea primero. Se queda
          el título y la pestaña es lo que se calla, que es lo que hace iOS. */}
      <PageHeader
        title="Value US"
        subtitle={<>
          {regimeLabel && (
            <Badge variant={nlRegimenTono(regimeCrudo)} className="mr-2 align-middle text-mini">
              {regimeLabel}
            </Badge>
          )}
          Primero las de prioridad: baratas frente a su propia historia y creciendo.
          {regimeRec && <> · <strong className="text-foreground">{regimeRec}</strong></>}
        </>}
      >
        <ValueModeToggle clearMode={clearMode} onChange={setClearMode} />
        <CsvDownload dataset="value-us" label="CSV" />
        <CsvDownload dataset="value-us-full" label="CSV Full" />
        <LogoCandleBull size={44} className="ml-1 opacity-80 hidden sm:block" />
      </PageHeader>

      <AvisoDatosViejos clave="value" />

      {/* Lo primero tras la cabecera: si esta lista bate al índice o no. Estaba
          solo en la página de Cartera, o sea en cualquier sitio menos donde se
          decide la compra. */}
      <RendimientoReal fuente="alpha_us" />

      {/* Macro Risk Overlay */}
      {(() => {
        const macro = macroRaw as { regime?: { name: string; color: string; description: string }; composite_score?: number; max_score?: number } | null
        const rname = macro?.regime?.name
        if (!rname || !['STRESS', 'ALERT', 'CRISIS'].includes(rname)) return null
        const cfg = {
          STRESS: { bg: 'border-yellow-500/30 bg-yellow-500/8', text: 'text-yellow-400', msg: 'Estrés moderado detectado. Reduce tamaño de posición y prioriza picks con mayor margen de seguridad.' },
          ALERT:  { bg: 'border-orange-500/30 bg-orange-500/8', text: 'text-orange-400', msg: 'Alerta macro elevada. Considera posiciones más pequeñas, stop loss más ajustados y diversificación.' },
          CRISIS: { bg: 'border-red-500/40 bg-red-500/10',     text: 'text-red-400',    msg: 'Régimen de crisis potencial. Capital preservation mode — evitar nuevas entradas agresivas.' },
        }[rname]!
        return (
          <div className={`mb-5 flex items-start gap-3 px-4 py-3 rounded-lg border ${cfg.bg}`}>
            <TriangleAlert size={16} strokeWidth={2} className={`shrink-0 mt-0.5 ${cfg.text}`} />
            <div>
              <span className={`etiqueta-seccion ${cfg.text}`}>
                Macro Radar: {rname} ({macro.composite_score?.toFixed(1)}/{macro.max_score})
              </span>
              <p className="text-mini text-muted-foreground mt-0.5">{cfg.msg}</p>
            </div>
            <Link to="/macro-radar" className={`ml-auto shrink-0 text-micro font-semibold ${cfg.text} hover:underline`}>
              Ver detalle →
            </Link>
          </div>
        )
      })()}

      {clearMode && (
        <ValueClarityPanel
          rows={sorted}
          totalPublicadas={rows.length}
          onResetFilters={resetFilters}
          getDecision={decisionFor}
        />
      )}

      <CifrasClave cifras={rows.some(r => r.value_grupo) ? [
        { etiqueta: 'Prioridad', valor: rows.filter(r => r.value_grupo === 'PRIORIDAD').length,
          sub: 'barata frente a su historia y creciendo', tono: 'favor' },
        { etiqueta: 'Observar', valor: rows.filter(r => r.value_grupo === 'OBSERVAR').length,
          sub: 'pasan la puerta, les falta algo' },
      ] : [
        { etiqueta: 'Publicadas', valor: rows.length, sub: 'con los datos verificados' },
      ]} />

      {/* Una nota, no una caja. Era una tarjeta a todo el ancho con borde
          ámbar para UNA línea de texto: el contenedor pesaba más que lo que
          contenía y competía con las tarjetas de arriba sin decir nada más
          importante que ellas. */}
      {concentrated.length > 0 && (
        <p className="mb-5 flex items-center gap-2 text-apoyo text-warn">
          <TriangleAlert size={12} strokeWidth={2.25} className="shrink-0" />
          Concentración sectorial: {concentrated.map(([s, c]) => `${s} (${c})`).join(', ')}
        </p>
      )}

      {/* Una tira, no un panel. La vista recomendada era `liquid-glass` —la
          piel reservada a modales y tarjetas líder— para explicar un modo de
          vista: pesaba más que la lista que introduce. */}
      {clearMode ? (
        <div className="mb-3 flex flex-wrap items-center gap-3 border-b border-border/60 pb-3">
          {/* basis-full en móvil: con solo min-w-0 flex-1, el texto competía por la
              línea con los controles de al lado y se quedaba en 53px. */}
          <p className="min-w-0 basis-full text-mini text-muted-foreground sm:flex-1 sm:basis-auto">
            Dentro de cada grupo, las más baratas primero. No se oculta nada: los avisos van en cada empresa.
          </p>
          {hasActiveFilters && (
            <button type="button" onClick={resetFilters} className="filter-btn active">
              Restaurar criterio
            </button>
          )}
          <button type="button" onClick={() => setClearMode(false)} className="filter-btn">
            Ver filtros
          </button>
          <span className="filter-label !normal-case !tracking-normal">
            {filtered.length !== rows.length ? `${filtered.length} / ${rows.length}` : `${rows.length} ideas`}
          </span>
        </div>
      ) : (
      // Toolbar estilo Apple: la barra de filtros es la superficie "hero" de la
      // página (liquid-glass); tabla y stat cards quedan en .glass plano — un
      // foco, resto quieto. NO sticky: chocaría con el thead sticky de la tabla.
      <Card className="liquid-glass px-4 py-3 mb-3 animate-fade-in-up rounded-xl">
        <div className="flex flex-wrap gap-x-4 gap-y-2 items-center">

          {/* El grupo: lo que decide la lista */}
          <div className="flex items-center gap-1 flex-wrap">
            <span className="filter-label mr-0.5">Grupo</span>
            {GRUPO_FILTROS.map(({ clave, etiqueta }) => (
              <button
                key={clave}
                onClick={() => setFilterGrupo(clave)}
                className={`filter-btn ${filterGrupo === clave ? 'active' : ''}`}
              >{etiqueta}</button>
            ))}
          </div>

          {/* Sector */}
          {sectors.length > 2 && (
            <>
              <div className="w-px h-4 bg-border/40 self-center" />
              <div className="flex items-center gap-1 flex-wrap max-w-[400px]">
                <span className="filter-label mr-0.5">Sector</span>
                {sectors.slice(0, 7).map(s => (
                  <button key={s} onClick={() => setFilterSector(s)} className={`filter-btn ${filterSector === s ? 'active' : ''}`}>
                    {s === 'ALL' ? 'Todos' : s}
                  </button>
                ))}
              </div>
            </>
          )}

          <div className="w-px h-4 bg-border/40 self-center" />

          {/* FCF% min */}
          <div className="flex items-center gap-1.5">
            <span className="filter-label">FCF%≥</span>
            <input type="number" value={minFcf} onChange={e => setMinFcf(e.target.value)} placeholder="0" className="filter-input" />
          </div>

          <div className="w-px h-4 bg-border/40 self-center" />

          <button onClick={() => setHideEarnings(v => !v)} className={`filter-btn ${hideEarnings ? 'active-amber' : ''}`}>
            Earn &lt;7d
          </button>

          {myPos.length > 0 && (
            <button onClick={() => setOnlyOwned(v => !v)} className={`filter-btn ${onlyOwned ? 'active' : ''}`}>
              En cartera
            </button>
          )}
          <button onClick={() => setOnlyHf(v => !v)} className={`filter-btn ${onlyHf ? 'active' : ''}`}
            title="Mostrar solo tickers en cartera de Buffett, Ackman o Tepper">
            <Landmark size={12} strokeWidth={2.25} />HF Watch
          </button>

          {/* Compact toggle */}
          <button onClick={() => setCompact(v => !v)} className={`filter-btn ${compact ? 'active' : ''}`}
            title="Alternar entre vista compacta y completa">
            {compact ? '⊟ Compacta' : '⊞ Completa'}
          </button>

          {/* Reset + count — pushed to the right */}
          <div className="flex items-center gap-3 ml-auto">
            {hasActiveFilters && (
              <button onClick={resetFilters} className="text-mini text-muted-foreground hover:text-foreground underline underline-offset-2 transition-colors">
                Limpiar
              </button>
            )}
            <span className="filter-label !normal-case !tracking-normal">
              {filtered.length !== rows.length ? `${filtered.length} / ${rows.length}` : `${rows.length} picks`}
            </span>
          </div>
        </div>
      </Card>
      )}

      {/* Mobile card view */}
      {/* En el móvil, siempre la tarjeta clara: la «avanzada» era la misma con
          LISTO al lado de TRAP/EXIT, grado, ML y entrada/stop/objetivo, que la
          regla de Value US no usa. */}
      <div className="sm:hidden space-y-2.5 mb-2">
        {paged.map((d, i) => {
          const decision = decisionFor(d)
          const pot = potencial(d)
          return (
              <div
                key={d.ticker}
                data-fila-value={d.ticker}
                onClick={() => { setFocusedIdx(i); toggleThesis(d.ticker, d) }}
                className={`glass rounded-2xl p-4 cursor-pointer active:scale-[0.98] transition-transform border entra-escalonada ${decision.panelClass}`}
                style={{ '--i': Math.min(i, 12) } as React.CSSProperties}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <TickerLogo ticker={d.ticker} size="md" className="mt-0.5 shrink-0" />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono font-extrabold text-titulo leading-tight">{d.ticker}</span>
                        <ValueDecisionBadge decision={decision} />
                        <OwnedBadge ticker={d.ticker} />
                      </div>
                      <span className="text-mini text-muted-foreground truncate max-w-[210px] block mt-0.5">{d.company_name}</span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    {/* Nuestra valoración: es lo que decide la lista. El analista va en la barra de abajo. */}
                    {pot != null && (
                      <div className={`text-cuerpo font-bold ${pot >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {pot >= 0 ? '+' : ''}{pot.toFixed(0)}%
                      </div>
                    )}
                    <div className="text-micro text-muted-foreground mt-0.5">{precio(d.current_price, d.ticker)}</div>
                  </div>
                </div>
                {/* `decision.detail` es texto fijo por categoría, no por
                    empresa: cuatro tarjetas seguidas repetían palabra por
                    palabra "Interesante, pero falta confirmación / Espera
                    mejor punto de entrada", ocupando el 60% de cada una para
                    decir lo que el badge ya dice. En una lista de 65 ideas eso
                    es scroll puro. Se queda el titular (una línea) y el sitio
                    lo ocupa lo que SÍ cambia entre empresas: dónde está el
                    precio en su rango del año y hacia dónde apuntan los tres
                    objetivos. El detalle completo sigue en el modal de tesis,
                    a un toque, donde no se repite. */}
                <p className="mt-3 text-apoyo font-semibold text-foreground">{decision.headline}</p>
                <ValuationBar
                  className="mt-2.5"
                  precio={d.current_price}
                  pctDesdeMax={d.pct_from_52w_high}
                  pctDesdeMin={d.pct_from_52w_low}
                  objetivoAnalista={d.target_price_analyst}
                  objetivoDcf={d.target_price_dcf}
                  objetivoPe={d.target_price_pe}
                />
              </div>
          )
        })}
      </div>

      {/* Desktop table */}
      {clearMode ? (
        <div className="hidden sm:block">
          <Card className="glass animate-fade-in-up overflow-clip">
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead>Idea</TableHead>
                  <TableHead>Decisión</TableHead>
                  <TableHead>Lectura simple</TableHead>
                  <TableHead>Potencial</TableHead>
                  <TableHead>Precio</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paged.map((d, i) => {
                  const decision = decisionFor(d)
                  return (
                    <TableRow
                      key={d.ticker}
                      data-row-idx={i}
                      data-fila-value={d.ticker}
                      style={{ '--i': Math.min(i, 12) } as React.CSSProperties}
                      className={`entra-escalonada cursor-pointer transition-colors ${i === focusedIdx ? 'ring-1 ring-inset ring-primary/40 bg-primary/5' : ''}`}
                      onClick={() => { setFocusedIdx(i); toggleThesis(d.ticker, d) }}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <TickerLogo ticker={d.ticker} size="sm" />
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono font-bold text-primary text-cuerpo">{d.ticker}</span>
                              <OwnedBadge ticker={d.ticker} />
                            </div>
                            <div className="max-w-[180px] truncate text-mini text-muted-foreground">{d.company_name}</div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell><ValueDecisionBadge decision={decision} /></TableCell>
                      <TableCell className="max-w-[520px] whitespace-normal">
                        <div className="text-apoyo font-semibold text-foreground">{decision.headline}</div>
                        <div className="mt-0.5 text-mini leading-relaxed text-muted-foreground">{decision.detail}</div>
                      </TableCell>
                      <TableCell className="tabular-nums">{fmtPotencial(d)}</TableCell>
                      <TableCell className="tabular-nums">{precio(d.current_price, d.ticker)}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
            {sorted.length === 0 && (
              <CardContent className="py-16 text-center">
                <p className="font-medium text-muted-foreground">
                  {rows.length === 0 ? 'No hay ideas VALUE ahora mismo' : 'No hay ideas con los filtros actuales'}
                </p>
              </CardContent>
            )}
          </Card>
        </div>
      ) : (
      <div className="hidden sm:block">
      <Card className="glass animate-fade-in-up">
        <Table>
          <TableHeader>
            <TableRow className="border-border/50 hover:bg-transparent">
              <TableHead className={thCls('ticker')} onClick={() => onSort('ticker')}>Ticker</TableHead>
              <TableHead className={compact ? 'hidden' : `hidden sm:table-cell ${thCls('company_name')}`} onClick={() => onSort('company_name')}>Empresa</TableHead>
              <TableHead className={compact ? 'hidden' : `hidden sm:table-cell ${thCls('current_price')}`} onClick={() => onSort('current_price')}>Precio</TableHead>
              <TableHead className={thCls('value_score')} onClick={() => onSort('value_score')}>
                Score
                <InfoTooltip
                  text="Nota de Value US. PRIORIDAD (80-100): ventas del último año al 10 % o más y PER a más de 1σ bajo su media de 10 años, la única combinación con ventaja medida. OBSERVAR (40-60): pasa la puerta pero le falta algo. Dentro de cada grupo ordena lo barata que está: su PER contra su historia y su FCF yield."
                  align="left"
                />
              </TableHead>
              <TableHead className={compact ? 'hidden' : `hidden md:table-cell ${thCls('sector')}`} onClick={() => onSort('sector')}>Sector</TableHead>
              <TableHead className={thCls('upside_triangulated_pct')} onClick={() => onSort('upside_triangulated_pct')}>
                Potencial
                <InfoTooltip text="Lo que le ven nuestras valoraciones (DCF y P/E propios) junto al consenso de analistas. Es lo que decide la lista; el objetivo de los analistas solo está en la ficha." />
              </TableHead>
              <TableHead className={`hidden sm:table-cell ${thCls('fcf_yield_pct')}`} onClick={() => onSort('fcf_yield_pct')}>
                FCF%
                <InfoTooltip text="FCF Yield = Free Cash Flow / Market Cap. ≥5% excelente (verde), 3-5% bueno (ámbar), <0% negativo (rojo). Indica cuánto cash genera la empresa respecto a su valor de mercado." />
              </TableHead>
              <TableHead className={compact ? 'hidden' : 'hidden sm:table-cell'}>
                Div/BB
                <InfoTooltip text="Dividend yield del ticker. 'BB' indica que la empresa está recomprando acciones propias activamente (buyback), lo que también retorna capital al accionista." />
              </TableHead>
              <TableHead className={thCls('days_to_earnings')} onClick={() => onSort('days_to_earnings')}>
                Earn
                <InfoTooltip
                  text="Días hasta los próximos resultados. Es un dato: no frena una de Prioridad."
                  align="right"
                />
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paged.map((d, i) => {
            const decision = decisionFor(d)
            return (
              <TableRow
                key={d.ticker}
                data-row-idx={i}
                data-fila-value={d.ticker}
                style={{ '--i': Math.min(i, 12) } as React.CSSProperties}
                className={`entra-escalonada cursor-pointer transition-colors ${i === focusedIdx ? 'ring-1 ring-inset ring-primary/40 bg-primary/5' : ''}`}
                onClick={() => { setFocusedIdx(i); toggleThesis(d.ticker, d) }}
              >
                  <TableCell className="font-mono font-bold text-primary text-apoyo tracking-wide">
                    <div className="flex items-center gap-2">
                      <TickerLogo ticker={d.ticker} size="sm" />
                      <div className="flex flex-col gap-0.5">
                      {/* La fila dice UNA cosa: su grupo y por qué. Timing, Cerebro,
                          grado, Magic Formula y fondos son datos de la ficha. */}
                      <div className="flex items-center gap-1.5">
                        {d.ticker}
                        <ValueDecisionBadge decision={decision} />
                        <OwnedBadge ticker={d.ticker} />
                        {d.oe_ai_verdict?.toUpperCase().startsWith('UNRELIABLE') && (
                          <OeAiBadge verdict={d.oe_ai_verdict} adjustment={d.oe_ai_adjustment} />
                        )}
                      </div>
                      <span className="text-micro text-muted-foreground font-normal font-sans leading-snug max-w-[420px] line-clamp-2 whitespace-normal">
                        {decision.headline}
                      </span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden sm:table-cell max-w-[160px] truncate text-muted-foreground text-mini'}>{d.company_name}</TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden sm:table-cell tabular-nums'}>{precio(d.current_price, d.ticker)}</TableCell>
                  <TableCell><ScoreBar score={d.value_score} /></TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden md:table-cell max-w-[120px] truncate text-muted-foreground text-mini'}>{d.sector}</TableCell>
                  <TableCell className="tabular-nums">
                    {fmtPotencial(d)}
                    {/* Dos avisos distintos, y el orden importa: si tus propios
                        modelos se contradicen ENTRE ELLOS, no hay con qué
                        contrastar el target del analista, así que ese aviso
                        manda sobre el de divergencia. */}
                    {d.modelos_acuerdo === 'CONTRADICEN' ? (
                      <span
                        className="ml-1 text-micro font-bold text-red-400"
                        title={`Tus dos modelos se contradicen: el DCF dice ${(d.target_price_dcf_upside_pct ?? 0) > 0 ? 'barata' : 'cara'} (${d.target_price_dcf_upside_pct?.toFixed(0) ?? '?'}%) y el P/E lo contrario (${d.target_price_pe_upside_pct?.toFixed(0) ?? '?'}%). No hay valoración propia que respalde ni desmienta el target del analista — por eso no se publica un upside triangulado.`}
                      >
                        ⇅
                      </span>
                    ) : (d.upside_divergence === 'ALTA' || d.upside_divergence === 'MEDIA') && (
                      <span
                        className={`ml-1 inline-flex align-middle ${d.upside_divergence === 'ALTA' ? 'text-red-400' : 'text-amber-400'}`}
                        title={`Los modelos propios (DCF/P-E) no respaldan el target de analistas — se separan ${d.upside_divergence_pts?.toFixed(0) ?? '?'}pts. Upside triangulado (mediana de las 3 estimaciones): ${d.upside_triangulated_pct != null ? `${d.upside_triangulated_pct > 0 ? '+' : ''}${d.upside_triangulated_pct.toFixed(0)}%` : 'n/d'}`}
                      >
                        <TriangleAlert size={12} aria-label="los modelos propios no respaldan el target" />
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="hidden sm:table-cell">{fmtFcf(d.fcf_yield_pct)}</TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden sm:table-cell'}>{fmtDivBB(d)}</TableCell>
                  <TableCell>{fmtEarn(d)}</TableCell>
              </TableRow>
            )
          })}
          </TableBody>
        </Table>
        {sorted.length === 0 && (
          <CardContent className="py-16 text-center">
            <Gem size={32} strokeWidth={1.5} className="mx-auto mb-4 opacity-20" />
            {/* Vacío por el gate NO es lo mismo que vacío por los filtros de la
                pantalla, y confundirlos deja al usuario pensando que la app
                está rota. Antes, cuando el gate no verificaba nada, la página
                caía al fichero SIN filtrar y enseñaba el universo entero como
                si estuviera verificado — peor que no enseñar nada. */}
            <p className="font-medium text-muted-foreground">
              {rows.length === 0
                ? 'Hoy no hay ninguna idea verificada'
                : 'Sin resultados con los filtros aplicados'}
            </p>
            {rows.length === 0 && (
              <p className="mt-2 text-mini text-muted-foreground max-w-md mx-auto leading-relaxed">
                El filtro de calidad no dio por buena ninguna: o los candidatos de hoy
                no pasaron la revisión de datos, o no pudo ejecutarse. Antes se
                enseñaban igualmente las ideas sin verificar, y eso es justo lo que
                no quieres ver.
              </p>
            )}
          </CardContent>
        )}
        {sorted.length > 0 && (
          <div className="hidden sm:block text-micro text-muted-foreground text-right px-3 py-1.5 border-t border-border/10">
            j / k navegar · Enter ver tesis · Esc cerrar
          </div>
        )}
      </Card>
      </div>
      )}

      <PaginationBar page={page} totalPages={totalPages} onPage={setPage} />

      {/* AnimatePresence aquí, no dentro del modal: el modal se DESMONTA al
          cerrarse, y una animación de salida necesita que alguien retrase ese
          desmontaje. Sin esto el panel entra con muelle y se va de golpe. */}
      <AnimatePresence>
        {expandedRow && (
          <ThesisModal
            row={expandedRow}
            thesisText={thesisText}
            onClose={() => setExpandedRow(null)}
          />
        )}
      </AnimatePresence>
    </>
  )
}
