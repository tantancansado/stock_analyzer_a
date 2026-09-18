import { useState, useEffect, useRef, useMemo, useCallback, useDeferredValue } from 'react'
import { TriangleAlert, LogOut, Gem, Flame, CalendarClock, CircleCheck, Landmark } from 'lucide-react'
import SignalBadge from '../components/SignalBadge'
import { precio } from '../lib/moneda'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchValueOpportunities, fetchMarketRegime, fetchThesis, fetchMacroRadar, fetchMlWinProbability, type ValueOpportunity, type MlWinPrediction } from '../api/client'
import StaleDataBanner from '../components/StaleDataBanner'
import { usePersonalPortfolio } from '../context/PersonalPortfolioContext'
import { useApi } from '../hooks/useApi'
import ScoreBar from '../components/ScoreBar'
import ScoreRing from '../components/ScoreRing'
import GradeBadge from '../components/GradeBadge'
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
import { useTechnicalSummaryMap } from '../hooks/useTechnicalSummaryMap'
import { useCerebroSignals } from '../hooks/useCerebroSignals'
import { useChartSignals } from '../hooks/useChartSignals'
import CerebroBadges from '../components/CerebroBadges'
import OeAiBadge from '../components/OeAiBadge'
import AnalystRevisionBadge from '../components/AnalystRevisionBadge'
import EntryVerdictBadge from '../components/EntryVerdictBadge'
import { useEntryVerdicts } from '../hooks/useEntryVerdicts'
import type { TechnicalSummary } from '../api/client'
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

function TechBiasCell({ t }: { t?: TechnicalSummary }) {
  if (!t) return <span className="text-muted-foreground text-mini">—</span>
  const cls = t.bias === 'BULLISH'
    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
    : t.bias === 'BEARISH'
    ? 'bg-red-500/15 text-red-400 border-red-500/30'
    : 'bg-muted/20 text-muted-foreground border-border/20'
  const icon = t.bias === 'BULLISH' ? '▲' : t.bias === 'BEARISH' ? '▼' : '—'
  return (
    <span className={`text-mini font-bold px-1.5 py-0.5 rounded-full border ${cls}`}
      title={`+${t.bullish_count} alcistas / -${t.bearish_count} bajistas`}>
      {icon}
    </span>
  )
}

function MlWinBadge({ pred }: { pred?: MlWinPrediction }) {
  if (!pred) return <span className="text-muted-foreground text-mini">—</span>
  const cls =
    pred.label === 'ALTA'  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' :
    pred.label === 'MEDIA' ? 'bg-amber-500/15 text-amber-400 border-amber-500/30' :
                             'bg-muted/20 text-muted-foreground border-border/30'
  return (
    <span
      className={`text-micro font-bold px-1.5 py-0.5 rounded border tracking-wide ${cls}`}
      title={`XGBoost win probability: ${(pred.probability * 100).toFixed(0)}% (P${pred.percentile})`}
    >
      {(pred.probability * 100).toFixed(0)}%
    </span>
  )
}

/** Cuántos días vale una lectura de gráfico antes de dejar de ser el "ahora". */
const CADUCIDAD_CHART_DIAS = 7

/**
 * Calidad de entrada leída del gráfico por un modelo de visión.
 *
 * Dos filtros que antes no había:
 *
 *  1. **Caducidad.** El análisis salió del pipeline diario el 14-sep-2026 —
 *     costaba 15 de los 90 minutos del job y era lo primero que moría en cada
 *     timeout, así que su salida llevaba días congelada. Ahora se pide bajo
 *     demanda, y una lectura de hace dos semanas no describe el gráfico de hoy.
 *
 *  2. **Confianza.** 73 de 103 lecturas salían con confidence "low". Marcarlas
 *     con un "?" no bastaba: en una tabla se leen igual que las buenas. Si el
 *     modelo dice que no está seguro, no hay dato.
 */
function EntryQualityBadge({ quality, confidence, analyzedAt }: {
  quality?: string
  confidence?: string
  analyzedAt?: string
}) {
  const sinDato = <span className="text-muted-foreground text-mini">—</span>
  if (!quality || quality === 'wait' || confidence === 'low') return sinDato
  if (analyzedAt) {
    const dias = (Date.now() - new Date(analyzedAt).getTime()) / 86_400_000
    if (!Number.isFinite(dias) || dias > CADUCIDAD_CHART_DIAS) return sinDato
  }
  const cfg: Record<string, { cls: string; label: string }> = {
    ideal:      { cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', label: 'IDEAL' },
    acceptable: { cls: 'bg-amber-500/15 text-amber-400 border-amber-500/30',      label: 'OK' },
    avoid:      { cls: 'bg-red-500/15 text-red-400 border-red-500/30',             label: 'EVITAR' },
  }
  const { cls, label } = cfg[quality] ?? { cls: 'bg-muted/20 text-muted-foreground border-border/20', label: quality }
  const confSuffix = confidence === 'low' ? '?' : ''
  return (
    <span className={`text-micro font-bold px-1.5 py-0.5 rounded border tracking-wide ${cls}`}
      title={`Entrada: ${quality} · Confianza: ${confidence ?? '?'}`}>
      {label}{confSuffix}
    </span>
  )
}

type SortKey = keyof ValueOpportunity
type SortDir = 'asc' | 'desc'

export default function ValueUS() {
  const { data, loading, error } = useApi(() => fetchValueOpportunities(), [])
  const { data: regime } = useApi(() => fetchMarketRegime(), [])
  const { data: macroRaw } = useApi(() => fetchMacroRadar(), [])
  const { data: mlData } = useApi(() => fetchMlWinProbability().then(d => ({ data: d })), [])
  const mlMap = useMemo(() => mlData?.predictions ?? {}, [mlData])
  const techMap = useTechnicalSummaryMap()
  const cerebro = useCerebroSignals()
  const chartSignals = useChartSignals()
  const verdicts = useEntryVerdicts()
  const [sortKey, setSortKey] = useState<SortKey>('value_score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [expandedRow, setExpandedRow] = useState<ValueOpportunity | null>(null)
  const [thesisText, setThesisText] = useState<string>('')
  const { clearMode, setClearMode } = useValueExperienceMode()

  // URL-synced filters
  const [searchParams, setSearchParams] = useSearchParams()

  const filterGrade = searchParams.get('grade') ?? 'ALL'
  const filterSector = searchParams.get('sector') ?? 'ALL'
  // Sin suelo por defecto. Lo que llega a este CSV YA pasó el gate de Claude
  // y el conviction filter: poner encima un mínimo de score en la UI es
  // filtrar dos veces y esconder justo lo que el backend acaba de verificar.
  // El 9-sep-2026 el default de '55' dejaba la pantalla principal en "No hay
  // ideas visibles" con 4 picks publicados (45,8 / 39,9 / 38,1 / 31,1) —
  // parecía que el pipeline no había sacado nada. El score sigue estando en
  // los filtros para quien lo quiera; simplemente no se aplica solo.
  const minScore = searchParams.get('score') ?? ''
  const minFcf = searchParams.get('fcf') ?? ''
  const minRr = searchParams.get('rr') ?? ''

  function setFilterGrade(v: string) {
    setSearchParams(p => {
      const next = new URLSearchParams(p)
      if (v === 'ALL') next.delete('grade')
      else next.set('grade', v)
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
  function setMinScore(v: string) {
    setSearchParams(p => {
      const next = new URLSearchParams(p)
      if (v === '') next.delete('score')
      else next.set('score', v)
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
  function setMinRr(v: string) {
    setSearchParams(p => {
      const next = new URLSearchParams(p)
      if (v === '') next.delete('rr')
      else next.set('rr', v)
      return next
    }, { replace: true })
  }

  const [hideEarnings, setHideEarnings] = useState(false)
  const [hideTraps, setHideTraps] = useState(true)
  const [hideExits, setHideExits] = useState(true)
  const [onlyOwned, setOnlyOwned] = useState(false)
  const [onlyHf, setOnlyHf] = useState(false)
  const [compact, setCompact] = useState(() => typeof window !== 'undefined' && window.innerWidth < 1280)
  const { isOwned, positions: myPos } = usePersonalPortfolio()
  const [page, setPage] = useState(1)
  const [focusedIdx, setFocusedIdx] = useState(-1)
  const PAGE_SIZE = 50

  // useDeferredValue: los filtros de texto/número no bloquean el UI mientras se recalcula
  const deferredMinFcf = useDeferredValue(minFcf)
  const deferredMinRr = useDeferredValue(minRr)
  const deferredMinScore = useDeferredValue(minScore)

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
      if (row.conviction_reasons) parts.push(row.conviction_reasons.split(' | ').slice(0, 3).map(r => `• ${r}`).join('\n'))
      return parts.length > 0
        ? `${parts.join('\n\n')}\n\n_Tesis narrativa no generada (solo top-50 por super_score_5d). Mostrando razonamiento IA + conviction._`
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
  useEffect(() => { setPage(1); setFocusedIdx(-1) }, [filterGrade, filterSector, minScore, minFcf, minRr, hideEarnings, hideTraps, hideExits, onlyOwned, onlyHf])
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
    if (filterGrade !== 'ALL' && r.conviction_grade !== filterGrade) return false
    if (filterSector !== 'ALL' && r.sector !== filterSector) return false
    // El umbral de score mira value_score (métrica rápida), pero conviction_grade
    // sale de un análisis más profundo (ROE, deuda, DCF, R:R) que puede discrepar
    // — un A/B de alta convicción no debe desaparecer solo porque el value_score
    // simple cae un par de puntos por debajo del mínimo (caso real: CBOE,
    // value_score 52.6 bajo el corte de 55 pero grade A con 8 positivos/0 red flags).
    // El filtro de score filtra siempre — ver la nota en ValueEU: los grados A
    // y B se lo saltaban y la lista mostraba tickers por debajo del umbral
    // elegido sin decirlo. Para alta convicción está el filtro de GRADO.
    if (deferredMinScore !== '' && (r.value_score == null || r.value_score < Number(deferredMinScore))) return false
    if (deferredMinFcf !== '' && (r.fcf_yield_pct == null || r.fcf_yield_pct < Number(deferredMinFcf))) return false
    if (deferredMinRr !== '' && (r.risk_reward_ratio == null || r.risk_reward_ratio < Number(deferredMinRr))) return false
    if (hideEarnings && r.earnings_warning) return false
    if (hideTraps && cerebro.trapMap[r.ticker]?.severity === 'HIGH') return false
    if (hideExits && (cerebro.exitMap[r.ticker] || r.cerebro_signal === 'EXIT')) return false
    if (onlyOwned && !isOwned(r.ticker)) return false
    if (onlyHf && (r.hedge_fund_count ?? 0) < 1) return false
    return true
  }), [rows, filterGrade, filterSector, deferredMinScore, deferredMinFcf, deferredMinRr, hideEarnings, hideTraps, hideExits, onlyOwned, onlyHf, cerebro.trapMap, cerebro.exitMap, isOwned])

  const sorted = useMemo(() => [...filtered].sort((a, b) => {
    const av = a[sortKey] ?? 0
    const bv = b[sortKey] ?? 0
    if (av < bv) return sortDir === 'asc' ? -1 : 1
    if (av > bv) return sortDir === 'asc' ? 1 : -1
    return 0
  }), [filtered, sortKey, sortDir])

  const stats = useMemo(() => ({
    avgScore:   filtered.length ? filtered.reduce((s, r) => s + (r.value_score || 0), 0) / filtered.length : 0,
    gradeA:     filtered.filter(r => r.conviction_grade === 'A').length,
    gradeB:     filtered.filter(r => r.conviction_grade === 'B').length,
    bestUpside: Math.max(...filtered.map(r => r.analyst_upside_pct || 0), 0),
  }), [filtered])

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

  const hiddenByTraps = hideTraps ? Object.values(cerebro.trapMap).filter(t => t.severity === 'HIGH').length : 0
  const hiddenByExits = hideExits ? rows.filter(r => cerebro.exitMap[r.ticker] || r.cerebro_signal === 'EXIT').length : 0
  const hasActiveFilters = filterGrade !== 'ALL' || filterSector !== 'ALL' || minScore !== '' || minFcf !== '' || minRr !== '' || hideEarnings || hideTraps || hideExits || onlyOwned || onlyHf
  const resetFilters = () => {
    setSearchParams({}, { replace: true })
    setMinFcf(''); setMinRr(''); setHideEarnings(false); setHideTraps(false); setHideExits(false); setOnlyOwned(false); setOnlyHf(false)
  }
  const applyRecommendedView = () => {
    setSearchParams({}, { replace: true })
    setMinFcf('')
    setMinRr('')
    setHideEarnings(false)
    setHideTraps(true)
    setHideExits(true)
    setOnlyOwned(false)
  }
  const decisionFor = (row: ValueOpportunity) => getValueDecision({
    row,
    hasTrap: !!cerebro.trapMap[row.ticker],
    hasExit: !!(cerebro.exitMap[row.ticker] || row.cerebro_signal === 'EXIT'),
    hasEntry: !!cerebro.entryMap[row.ticker],
    hasSmartMoney: !!cerebro.smMap[row.ticker],
    hasSqueeze: !!cerebro.squeezeMap[row.ticker],
  })

  const fmtFcf = (v?: number) => {
    if (v == null) return <span className="text-muted-foreground">—</span>
    const cls = v >= 5 ? 'text-emerald-400' : v >= 3 ? 'text-amber-400' : v < 0 ? 'text-red-400' : ''
    return <span className={cls}>{v.toFixed(1)}%</span>
  }
  const fmtRR = (v?: number | null) => {
    if (v == null) return <span className="text-muted-foreground">—</span>
    const cls = v >= 2 ? 'text-emerald-400' : v >= 1 ? 'text-amber-400' : 'text-red-400'
    return <span className={cls}>{v.toFixed(1)}</span>
  }
  const fmtDivBB = (d: ValueOpportunity) => {
    const parts: string[] = []
    if (d.dividend_yield_pct != null && d.dividend_yield_pct > 0) parts.push(`${d.dividend_yield_pct.toFixed(1)}%`)
    if (d.buyback_active) parts.push('BB')
    return parts.length
      ? <span className="text-emerald-400">{parts.join('+')}</span>
      : <span className="text-muted-foreground">—</span>
  }
  const fmtEarn = (d: ValueOpportunity) => {
    if (d.days_to_earnings == null) return <span className="text-muted-foreground">—</span>
    const cls = d.days_to_earnings <= 7 ? 'text-red-400' : d.days_to_earnings <= 21 ? 'text-amber-400' : 'text-emerald-400'
    return <span className={cls}>{d.days_to_earnings}d</span>
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
          Ideas ordenadas por oportunidad. La vista clara traduce los modelos a decisiones.
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

      <CifrasClave cifras={[
        { etiqueta: 'Oportunidades', valor: rows.length, sub: 'tickers analizados' },
        { etiqueta: 'Score medio',   valor: stats.avgScore.toFixed(1), unidad: '/100',
          tono: stats.avgScore >= 50 ? 'favor' : 'aviso' },
        { etiqueta: 'Grado A+B',     valor: stats.gradeA + stats.gradeB,
          sub: `${stats.gradeA} A, ${stats.gradeB} B`, tono: 'favor' },
        { etiqueta: 'Mejor upside',  valor: `+${stats.bestUpside.toFixed(0)}`, unidad: '%',
          sub: 'potencial analistas', tono: 'favor' },
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
          <div className="flex flex-wrap items-center gap-3 w-full">
            {/* basis-full en móvil: con solo min-w-0 flex-1, el texto competía
                por la línea con los tres controles de al lado y se quedaba en
                53px — 13 líneas de 8 caracteres, ilegible. Ocupando la línea
                entera, los botones bajan solos. */}
            <div className="min-w-0 basis-full sm:flex-1 sm:basis-auto">
              <p className="text-cuerpo font-semibold text-foreground">Vista recomendada activa</p>
              <p className="text-mini text-muted-foreground">
                Ocultamos alertas de riesgo graves y ordenamos por oportunidad. Los filtros técnicos siguen disponibles.
              </p>
            </div>
            <button type="button" onClick={applyRecommendedView} className="filter-btn active">
              Restaurar criterio
            </button>
            <button type="button" onClick={() => setClearMode(false)} className="filter-btn">
              Ver filtros
            </button>
            <span className="filter-label !normal-case !tracking-normal">
              {filtered.length !== rows.length ? `${filtered.length} / ${rows.length}` : `${rows.length} ideas`}
            </span>
          </div>
        </div>
      ) : (
      // Toolbar estilo Apple: la barra de filtros es la superficie "hero" de la
      // página (liquid-glass); tabla y stat cards quedan en .glass plano — un
      // foco, resto quieto. NO sticky: chocaría con el thead sticky de la tabla.
      <Card className="liquid-glass px-4 py-3 mb-3 animate-fade-in-up rounded-xl">
        <div className="flex flex-wrap gap-x-4 gap-y-2 items-center">

          {/* Min Score */}
          <div className="flex items-center gap-1">
            <span className="filter-label mr-0.5">Score≥</span>
            {[['ALL', ''], ['50+', '50'], ['55+', '55'], ['60+', '60'], ['65+', '65']].map(([label, val]) => (
              <button key={val} onClick={() => setMinScore(val)} className={`filter-btn ${minScore === val ? 'active' : ''}`}>{label}</button>
            ))}
          </div>

          <div className="w-px h-4 bg-border/40 self-center" />

          {/* Grade */}
          <div className="flex items-center gap-1">
            <span className="filter-label mr-0.5">Grado</span>
            {['ALL', 'A', 'B', 'C'].map(g => (
              <button key={g} onClick={() => setFilterGrade(g)} className={`filter-btn ${filterGrade === g ? 'active' : ''}`}>{g}</button>
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

          {/* R:R min */}
          <div className="flex items-center gap-1.5">
            <span className="filter-label">R:R≥</span>
            <input type="number" value={minRr} onChange={e => setMinRr(e.target.value)} placeholder="0" className="filter-input" />
          </div>

          <div className="w-px h-4 bg-border/40 self-center" />

          {/* Cerebro IA filters */}
          <button onClick={() => setHideTraps(v => !v)} className={`filter-btn ${hideTraps ? 'active-red' : ''}`}
            title="Ocultar tickers marcados como value trap HIGH por Cerebro IA">
            <TriangleAlert size={12} strokeWidth={2.25} />{hiddenByTraps > 0 && hideTraps ? `TRAP (${hiddenByTraps})` : 'TRAP'}
          </button>
          <button onClick={() => setHideExits(v => !v)} className={`filter-btn ${hideExits ? 'active-red' : ''}`}
            title="Ocultar tickers con señal de salida HIGH por Cerebro IA">
            <LogOut size={12} strokeWidth={2.25} />{hiddenByExits > 0 && hideExits ? `EXIT (${hiddenByExits})` : 'EXIT'}
          </button>
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
      <div className="sm:hidden space-y-2.5 mb-2">
        {paged.map((d, i) => {
          const isReady =
            (d.value_score ?? 0) >= 65 &&
            ['A', 'B', 'EXCELLENT', 'STRONG'].includes((d.conviction_grade ?? '').toUpperCase()) &&
            !d.earnings_warning &&
            (d.days_to_earnings == null || d.days_to_earnings > 7) &&
            d.cerebro_signal !== 'EXIT' &&
            d.cerebro_signal !== 'TRAP'
          const hasTrap   = !!cerebro.trapMap[d.ticker]
          const hasExit   = !!(cerebro.exitMap[d.ticker] || d.cerebro_signal === 'EXIT')
          const hasSM     = !!cerebro.smMap[d.ticker]
          const hasSqueeze = !!cerebro.squeezeMap[d.ticker]
          const decision = decisionFor(d)
          if (clearMode) {
            return (
              <div
                key={d.ticker}
                onClick={() => { setFocusedIdx(i); toggleThesis(d.ticker, d) }}
                className={`glass rounded-2xl p-4 cursor-pointer active:scale-[0.98] transition-transform border ${decision.panelClass}`}
                style={{ animationDelay: `${i * 40}ms` }}
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
                    {d.analyst_upside_pct != null && (
                      <div className={`text-cuerpo font-bold ${d.analyst_upside_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {d.analyst_upside_pct >= 0 ? '+' : ''}{d.analyst_upside_pct.toFixed(0)}%
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
          }
          return (
            <div
              key={d.ticker}
              onClick={() => { setFocusedIdx(i); toggleThesis(d.ticker, d) }}
              className={`glass rounded-2xl p-4 cursor-pointer active:scale-[0.98] transition-transform border ${hasTrap ? 'border-red-500/30' : hasExit ? 'border-amber-500/30' : 'border-foreground/5'}`}
              style={{ animationDelay: `${i * 40}ms` }}
            >
              {/* Fila 1: logo + puntuación + ticker + grado + upside.
                  El logo faltaba: el anillo de puntuación ocupaba su sitio, así
                  que al apagar la vista clara —que es lo que pasa al filtrar—
                  la tarjeta perdía lo único que identifica la empresa de un
                  vistazo y se quedaba con un número. El comentario de esta
                  misma línea ya decía «logo». */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <TickerLogo ticker={d.ticker} size="sm" />
                  <ScoreRing score={d.value_score} size="sm" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono font-extrabold text-titulo leading-tight">{d.ticker}</span>
                      {isReady && (
                        <SignalBadge icon={CircleCheck} tono="favor" texto="LISTO" />
                      )}
                      <OwnedBadge ticker={d.ticker} />
                    </div>
                    <span className="text-mini text-muted-foreground truncate max-w-[160px] block mt-0.5">{d.company_name}</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <GradeBadge grade={d.conviction_grade} score={d.conviction_score} />
                  {d.ml_score != null && d.ml_score !== 50 && (
                    <div className={`text-micro font-bold px-1.5 py-0.5 rounded-full border mt-1 inline-block ${
                      d.ml_score >= 70 ? 'bg-violet-500/15 text-violet-400 border-violet-500/30' :
                      d.ml_score >= 55 ? 'bg-blue-500/15 text-blue-400 border-blue-500/30' :
                      'bg-muted/20 text-muted-foreground border-border/30'
                    }`}>ML {d.ml_score.toFixed(0)}</div>
                  )}
                  {d.analyst_upside_pct != null && (
                    <div className={`text-cuerpo font-bold mt-1 ${d.analyst_upside_pct > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {d.analyst_upside_pct > 0 ? '+' : ''}{d.analyst_upside_pct.toFixed(0)}%
                    </div>
                  )}
                  <div className="text-micro text-muted-foreground mt-0.5">{precio(d.current_price, d.ticker)}</div>
                </div>
              </div>

              {/* Row 2: Cerebro signals */}
              {(hasTrap || hasExit || hasSM || hasSqueeze || d.earnings_warning) && (
                <div className="flex flex-wrap gap-1.5 mt-2.5">
                  {hasTrap && <SignalBadge icon={TriangleAlert} tono="alarma" texto="TRAP" />}
                  {hasExit && <SignalBadge icon={LogOut} tono="aviso" texto="EXIT" />}
                  {hasSM && <SignalBadge icon={Gem} tono="favor" texto="SMART MONEY" />}
                  {hasSqueeze && <SignalBadge icon={Flame} tono="info" texto="SQUEEZE" />}
                  {d.earnings_warning && <SignalBadge icon={CalendarClock} tono="aviso" texto="EARNINGS" />}
                </div>
              )}

              {/* Row 3: Entry / Stop / Target */}
              {(d.entry_price || d.stop_loss || d.target_price) && (
                <div className="flex gap-3 mt-2.5 text-mini font-mono">
                  {d.entry_price && <span className="text-cyan-400">E ${d.entry_price.toFixed(2)}</span>}
                  {d.stop_loss && <span className="text-red-400">SL ${d.stop_loss.toFixed(2)}</span>}
                  {d.target_price && <span className="text-emerald-400">TP ${d.target_price.toFixed(2)}</span>}
                </div>
              )}

              {/* Row 4: FCF / R:R / Sector */}
              <div className="flex gap-3 mt-2 text-mini text-muted-foreground">
                {d.fcf_yield_pct != null && <span>FCF {d.fcf_yield_pct.toFixed(1)}%</span>}
                {d.rr_operativo != null && <span>R:R {d.rr_operativo.toFixed(1)}x</span>}
                {d.sector && <span className="truncate">{d.sector}</span>}
              </div>
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
                      className={`cursor-pointer transition-colors ${i === focusedIdx ? 'ring-1 ring-inset ring-primary/40 bg-primary/5' : ''}`}
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
                      <TableCell className="tabular-nums">
                        {d.analyst_upside_pct != null ? (
                          <span className={d.analyst_upside_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                            {d.analyst_upside_pct >= 0 ? '+' : ''}{d.analyst_upside_pct.toFixed(0)}%
                          </span>
                        ) : <span className="text-muted-foreground">—</span>}
                      </TableCell>
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
                  text="Score VALUE propio (0-100): fundamentales 40pts, insiders 15pts, institucionales 15pts, opciones 10pts, ML 5pts, sector/reversion 20pts. Bonificaciones por FCF, dividendo, recompras y R:R."
                  align="left"
                />
              </TableHead>
              <TableHead>
                Grade
                <InfoTooltip
                  text={
                    <span>
                      Grado de convicción del filtro IA:<br />
                      <span className="text-emerald-400">A</span> — alta convicción (pocas alertas, múltiples positivos)<br />
                      <span className="text-blue-400">B</span> — convicción moderada<br />
                      <span className="text-amber-400">C</span> — baja convicción (revisar antes de entrar)
                    </span>
                  }
                />
              </TableHead>
              <TableHead className={compact ? 'hidden' : `hidden md:table-cell ${thCls('sector')}`} onClick={() => onSort('sector')}>Sector</TableHead>
              <TableHead className={thCls('analyst_upside_pct')} onClick={() => onSort('analyst_upside_pct')}>
                Objetivo
                <InfoTooltip text="Upside según precio objetivo de analistas = (precio objetivo − precio actual) / precio actual. Negativo = analistas ven el valor sobrevalorado." />
              </TableHead>
              <TableHead className={`hidden sm:table-cell ${thCls('fcf_yield_pct')}`} onClick={() => onSort('fcf_yield_pct')}>
                FCF%
                <InfoTooltip text="FCF Yield = Free Cash Flow / Market Cap. ≥5% excelente (verde), 3-5% bueno (ámbar), <0% negativo (rojo). Indica cuánto cash genera la empresa respecto a su valor de mercado." />
              </TableHead>
              <TableHead className={compact ? 'hidden' : thCls('risk_reward_ratio')} onClick={() => onSort('risk_reward_ratio')}>
                R:R
                <InfoTooltip text="Risk:Reward = upside analista / 8% stop loss estándar. ≥3 excelente (verde), ≥2 bueno, <1 desfavorable (rojo). Mide si el potencial de ganancia justifica el riesgo." />
              </TableHead>
              <TableHead className={compact ? 'hidden' : 'hidden sm:table-cell'}>
                OE AI
                <InfoTooltip text="Validación IA del modelo Owner Earnings (FCF-based). Evalúa calidad del dato subyacente y corrección de la tesis. Verde=RELIABLE/BUY · Rojo=RELIABLE/AVOID · Gris=UNRELIABLE (dato no fiable). Ajusta ±8pts el value_score (−10 si UNRELIABLE)." align="right" />
              </TableHead>
              <TableHead className={compact ? 'hidden' : 'hidden sm:table-cell'}>
                Div/BB
                <InfoTooltip text="Dividend yield del ticker. 'BB' indica que la empresa está recomprando acciones propias activamente (buyback), lo que también retorna capital al accionista." />
              </TableHead>
              <TableHead className={thCls('days_to_earnings')} onClick={() => onSort('days_to_earnings')}>
                Earn
                <InfoTooltip
                  text="Días hasta próximos resultados trimestrales. Rojo ≤7d — entrada muy arriesgada (gap post-earnings). Ámbar ≤21d — precaución. Verde >21d — zona segura."
                  align="right"
                />
              </TableHead>
              <TableHead className={compact ? 'hidden' : 'hidden sm:table-cell'}>
                Téc
                <InfoTooltip text="Sesgo técnico detectado automáticamente: indicadores de tendencia, RSI, MACD, Bollinger y velas. ▲ Alcista · ▼ Bajista · — Neutro." align="right" />
              </TableHead>
              <TableHead className={compact ? 'hidden' : 'hidden sm:table-cell'}>
                Entry
                <InfoTooltip text="Calidad de entrada según análisis de gráfico por IA (Groq Vision): IDEAL=en pivote/base, OK=extensión leve, EVITAR=extendido/distribución. '?' = baja confianza." align="right" />
              </TableHead>
              <TableHead className={compact ? 'hidden' : 'hidden sm:table-cell'}>
                P(win)
                <InfoTooltip text="Probabilidad de ganar en 14 días según modelo XGBoost entrenado con 1.300+ señales históricas VALUE. Verde ≥45%, ámbar 30-45%, gris <30%. Basado en value_score, FCF, R:R, sector y régimen de mercado." align="right" />
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paged.map((d, i) => {
            const isReady =
              (d.value_score ?? 0) >= 65 &&
              ['A', 'B', 'EXCELLENT', 'STRONG'].includes((d.conviction_grade ?? '').toUpperCase()) &&
              !d.earnings_warning &&
              (d.days_to_earnings == null || d.days_to_earnings > 7) &&
              d.cerebro_signal !== 'EXIT' &&
              d.cerebro_signal !== 'TRAP' &&
              // Overlay value+timing: barata NO significa "cómprala hoy" — si
              // sigue en caída (stage 4), no está lista por buena que sea la
              // tesis (tracker real: comprar el día del screen = alpha -12% 30d)
              d.entry_readiness !== 'ESPERAR' &&
              d.upside_divergence !== 'ALTA'
            return (
              <TableRow
                key={d.ticker}
                data-row-idx={i}
                className={`cursor-pointer transition-colors ${i === focusedIdx ? 'ring-1 ring-inset ring-primary/40 bg-primary/5' : ''}`}
                onClick={() => { setFocusedIdx(i); toggleThesis(d.ticker, d) }}
              >
                  <TableCell className="font-mono font-bold text-primary text-apoyo tracking-wide">
                    <div className="flex items-center gap-2">
                      <TickerLogo ticker={d.ticker} size="sm" />
                      <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-1.5">
                        {d.ticker}
                        {isReady && (
                          <span
                            title="Todos los filtros pasan — setup listo para operar"
                            className="inline-flex items-center gap-0.5 text-micro font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 tracking-wide"
                          >
                            LISTO
                          </span>
                        )}
                        <OwnedBadge ticker={d.ticker} />
                        {d.magic_formula_rank != null && d.magic_formula_rank <= 50 && (
                          <span
                            className="text-micro font-bold px-1 py-0.5 rounded bg-violet-500/15 text-violet-400 border border-violet-500/25"
                            title={`Magic Formula (Greenblatt) rank #${d.magic_formula_rank} — EBIT/EV yield ${d.ebit_ev_yield != null ? d.ebit_ev_yield.toFixed(1) + '%' : '—'} · ROIC ${d.roic_greenblatt != null ? d.roic_greenblatt.toFixed(1) + '%' : '—'}`}
                          >
                            MF #{d.magic_formula_rank}
                          </span>
                        )}
                        {d.proximity_to_52w_high != null && d.proximity_to_52w_high > -5 && (
                          <span className="text-micro font-bold px-1 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/25" title={`A ${Math.abs(d.proximity_to_52w_high).toFixed(1)}% del máximo 52 semanas — posible entrada en techo`}>
                            TECHO
                          </span>
                        )}
                        {d.entry_readiness === 'ESPERAR' && (
                          <span
                            className="text-micro font-bold px-1 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/25"
                            title={d.entry_readiness_reason || 'Aún en caída — espera a que haga suelo antes de entrar'}
                          >
                            ESPERA
                          </span>
                        )}
                        {d.entry_readiness === 'ENTRADA' && !isReady && (
                          <span
                            className="text-micro font-bold px-1 py-0.5 rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/25"
                            title={d.entry_readiness_reason || 'Suelo técnico confirmado (stage 2)'}
                          >
                            SUELO OK
                          </span>
                        )}
                        <AnalystRevisionBadge
                          targetChange7dPct={d.target_change_7d_pct}
                          upgradeDays14d={d.upgrade_days_14d}
                          downgradeDays14d={d.downgrade_days_14d}
                          compact
                        />
                        <EntryVerdictBadge verdict={verdicts[d.ticker?.toUpperCase() ?? '']} compact />
                        {(d.hedge_fund_count ?? 0) >= 1 && (
                          <span
                            className={`text-micro font-bold px-1 py-0.5 rounded border ${(d.hedge_fund_count ?? 0) >= 2 ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25' : 'bg-muted/20 text-muted-foreground border-border/30'}`}
                            title={d.hedge_fund_names || `${d.hedge_fund_count} hedge fund(s) en posición`}
                          >
                            {d.hedge_fund_count ?? 1} {(d.hedge_fund_count ?? 1) === 1 ? 'FONDO' : 'FONDOS'}
                          </span>
                        )}
                      </div>
                      {/* NL reason preview — first conviction reason or AI reasoning */}
                      {(() => {
                        const reason = d.ai_reasoning
                          ?? (d.conviction_reasons ? d.conviction_reasons.split(' | ')[0] : null)
                        return reason ? (
                          <span
                            className="text-micro text-muted-foreground font-normal font-sans leading-snug max-w-[360px] line-clamp-2 hidden lg:block"
                            title={reason}
                          >
                            {reason}
                          </span>
                        ) : null
                      })()}
                      <CerebroBadges
                        entryInfo={cerebro.entryMap[d.ticker]}
                        trapInfo={cerebro.trapMap[d.ticker]}
                        smInfo={cerebro.smMap[d.ticker]}
                        exitInfo={cerebro.exitMap[d.ticker]}
                        divInfo={cerebro.divMap[d.ticker]}
                        piotrInfo={cerebro.piotrMap[d.ticker]}
                        squeezeInfo={cerebro.squeezeMap[d.ticker]}
                        decayInfo={cerebro.decayMap[d.ticker]}
                        sectorInfo={cerebro.sectorMap[d.ticker]}
                      />
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden sm:table-cell max-w-[160px] truncate text-muted-foreground text-mini'}>{d.company_name}</TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden sm:table-cell tabular-nums'}>{precio(d.current_price, d.ticker)}</TableCell>
                  <TableCell><ScoreBar score={d.value_score} /></TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <GradeBadge grade={d.conviction_grade} score={d.conviction_score} />
                      {d.ml_score != null && d.ml_score !== 50 && (
                        <span className={`text-micro font-bold px-1.5 py-0.5 rounded-full border ${
                          d.ml_score >= 70 ? 'bg-violet-500/15 text-violet-400 border-violet-500/30' :
                          d.ml_score >= 55 ? 'bg-blue-500/15 text-blue-400 border-blue-500/30' :
                          'bg-muted/20 text-muted-foreground border-border/30'
                        }`}>ML {d.ml_score.toFixed(0)}</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden md:table-cell max-w-[120px] truncate text-muted-foreground text-mini'}>{d.sector}</TableCell>
                  <TableCell className="tabular-nums">
                    {d.target_price_analyst ? `$${d.target_price_analyst.toFixed(0)}` : '—'}
                    {d.analyst_upside_pct != null && (
                      <span className={`ml-1.5 text-mini font-semibold ${d.analyst_upside_pct > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {d.analyst_upside_pct > 0 ? '+' : ''}{d.analyst_upside_pct.toFixed(0)}%
                      </span>
                    )}
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
                        className={`ml-1 text-micro font-bold ${d.upside_divergence === 'ALTA' ? 'text-red-400' : 'text-amber-400'}`}
                        title={`Los modelos propios (DCF/P-E) no respaldan el target de analistas — se separan ${d.upside_divergence_pts?.toFixed(0) ?? '?'}pts. Upside triangulado (mediana de las 3 estimaciones): ${d.upside_triangulated_pct != null ? `${d.upside_triangulated_pct > 0 ? '+' : ''}${d.upside_triangulated_pct.toFixed(0)}%` : 'n/d'}`}
                      >
                        
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="hidden sm:table-cell">{fmtFcf(d.fcf_yield_pct)}</TableCell>
                  <TableCell className={compact ? 'hidden' : ''}>{fmtRR(d.rr_operativo)}</TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden sm:table-cell'}>
                    <OeAiBadge verdict={d.oe_ai_verdict} adjustment={d.oe_ai_adjustment} />
                  </TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden sm:table-cell'}>{fmtDivBB(d)}</TableCell>
                  <TableCell>{fmtEarn(d)}</TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden sm:table-cell'}>
                    <TechBiasCell t={techMap[d.ticker]} />
                  </TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden sm:table-cell'}>
                    <EntryQualityBadge
                      quality={chartSignals[d.ticker]?.entry_quality}
                      confidence={chartSignals[d.ticker]?.confidence}
                      analyzedAt={chartSignals[d.ticker]?.analyzed_at}
                    />
                  </TableCell>
                  <TableCell className={compact ? 'hidden' : 'hidden sm:table-cell'}>
                    <MlWinBadge pred={mlMap[d.ticker?.toUpperCase() ?? '']} />
                  </TableCell>
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

      {expandedRow && (
        <ThesisModal
          row={expandedRow}
          thesisText={thesisText}
          onClose={() => setExpandedRow(null)}
        />
      )}
    </>
  )
}
