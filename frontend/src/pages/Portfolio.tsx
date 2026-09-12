import { useState, lazy, Suspense } from 'react'
import api, { fetchPortfolioTracker, fetchCorrelationMatrix, fetchPortfolioInsight, fetchCalibration, type PortfolioSummary, type CorrelationData, type CalibrationData } from '../api/client'
import { useApi } from '../hooks/useApi'
import AiNarrativeCard from '../components/AiNarrativeCard'
import TickerLogo from '../components/TickerLogo'
import Loading, { ErrorState } from '../components/Loading'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, LineChart, Line,
} from 'recharts'
import PageHeader from '@/components/PageHeader'

const mkFmtPct = (horizonte: string) =>
  (v: unknown) => [`${Number(v).toFixed(1)}%`, `Win rate ${horizonte}`] as [string, string]
const winColor = (wr: number) => wr >= 55 ? '#10b981' : wr >= 45 ? '#f59e0b' : '#ef4444'

/** El tracker marca de qué población sale cada cifra. Traducirlo importa: no
 *  es lo mismo "lo que el sistema emite hoy" que "todo lo que emitió nunca",
 *  y hasta ahora la pantalla enseñaba las dos con la misma cara. */
const BASIS_LABEL: Record<string, string> = {
  clean_period: 'solo señales que el filtro de hoy sí emitiría',
  eu_full_hist: 'todo el histórico, incluida la política ya retirada',
}
const PortfolioStatsPlayer = lazy(() =>
  import('../components/PortfolioStatsVideo').then(m => ({ default: m.PortfolioStatsPlayer }))
)

interface SignalRow {
  ticker: string
  strategy?: string
  signal_date?: string
  signal_price?: number
  value_score?: number
  fcf_yield_pct?: number
  risk_reward_ratio?: number
  analyst_upside_pct?: number
  sector?: string
  market_regime?: string
  return_7d?: number
  return_14d?: number
  return_30d?: number
  max_drawdown_30d?: number
  win_7d?: boolean
  win_14d?: boolean
  alpha_7d?: number | null
  alpha_30d?: number | null
  status?: string
}

interface SignalsResponse {
  data: SignalRow[]
  count: number
}

type Performer = {
  ticker: unknown
  company_name?: unknown
  strategy?: unknown
  signal_date: unknown
  signal_price?: unknown
  /** Retorno al horizonte que indique `performers_horizon` (90d en la
   *  práctica). Antes era return_14d fijo: dos semanas no dicen nada de una
   *  tesis value y premiaban al pick más volátil, no al mejor. */
  return_pct: unknown
}

type RecentSignal = {
  ticker: unknown
  company_name?: unknown
  strategy?: unknown
  signal_date: unknown
  signal_price?: unknown
  sector?: unknown
  value_score?: unknown
  days_active?: unknown
  first_result_date?: unknown
}

const stratVariant = (s?: unknown): 'blue' | 'green' | 'gray' =>
  s === 'VALUE' || s === 'EU_VALUE' ? 'blue' : s === 'MOMENTUM' ? 'green' : 'gray'

const stratLabel = (s?: unknown): string =>
  s === 'EU_VALUE' ? 'EU' : s === 'VALUE' ? 'US' : s === 'MOMENTUM' ? 'MOM' : String(s ?? '')

type SortKey = keyof SignalRow
type SortDir = 'asc' | 'desc'

function retColor(v?: number) {
  if (v == null) return 'text-muted-foreground'
  if (v > 0) return 'text-emerald-400'
  if (v < 0) return 'text-red-400'
  return 'text-muted-foreground'
}

export default function Portfolio() {
  const { data, loading, error } = useApi(() => fetchPortfolioTracker(), [])
  const { data: corrData } = useApi<CorrelationData>(() => fetchCorrelationMatrix(), [])
  const { data: insightRaw } = useApi(() => fetchPortfolioInsight(), [])
  const { data: calibData } = useApi<CalibrationData>(() => fetchCalibration(), [])
  const { data: signalsData } = useApi<SignalsResponse>(
    () => api.get<SignalsResponse>('/api/portfolio-tracker/signals'),
    []
  )
  const [sigSortKey, setSigSortKey] = useState<SortKey>('signal_date')
  const [sigSortDir, setSigSortDir] = useState<SortDir>('desc')
  const [sigFilter, setSigFilter] = useState<'ALL' | 'ACTIVE' | 'COMPLETED'>('ALL')
  const [sigPage, setSigPage] = useState(1)
  const SIG_PAGE_SIZE = 30

  if (loading) return <Loading />
  if (error) return <ErrorState message={error} />

  const pf = (data as PortfolioSummary) || {}

  if (pf.total_signals == null) {
    return (
      <>
        <PageHeader
        title="Portfolio Tracker"
        subtitle="Seguimiento de rendimiento de recomendaciones"
      />
        <Card className="glass">
          <CardContent className="py-16 text-center">
            <div className="text-4xl mb-4 opacity-20">📋</div>
            <p className="font-medium text-muted-foreground">Sin datos de portfolio disponibles</p>
          </CardContent>
        </Card>
      </>
    )
  }

  // Lidera con el horizonte value (90d+); 30d se mantiene como contraste del
  // ruido de corto plazo, pero 7d/14d fuera — no dicen nada útil para value.
  // 180d manda: una tesis value tarda trimestres en resolverse y a 90d aún es
  // ruido. 90d queda como referencia provisional hasta que la muestra de 180d
  // tenga tamaño (la señal más antigua es de feb-2026).
  const periods = ['180d', '90d', '365d', '30d'] as const
  // TITULAR = US, no la mezcla. `overall` promedia VALUE US con EU_VALUE, y
  // el usuario compra casi solo acciones americanas: a 90d eso convierte un
  // alpha de +4,54% (US, n=103) en -2,12% arrastrado por 727 señales
  // europeas que nunca va a operar. Europa sigue publicada, en su propia
  // columna del panel US vs EU y con su etiqueta de población.
  const overall = (pf.value_strategy ?? pf.overall ?? {}) as Record<string, { count: number; win_rate: number; avg_return: number; ci_low?: number; ci_high?: number }>

  // El tracker dice a qué horizonte ordenó los rankings. Si no lo dice (JSON
  // viejo, antes del cambio del 9-sep-2026), se etiqueta como 14d, que es lo
  // que ese JSON contiene de verdad — mejor un rótulo honesto y anticuado que
  // uno bonito y falso.
  const horizonteLabel = (pf.performers_horizon as string | undefined) ?? '14d'
  const calibHorizonte = calibData?.horizon ?? '14d'
  const fmtPct = mkFmtPct(calibHorizonte)

  // ¿US y EU salen de la misma población a 90d? Si no, la comparación directa
  // no vale y no se corona ganador.
  const basisUs = pf.value_strategy?.['90d']?.basis
  const basisEu = pf.eu_value_strategy?.['90d']?.basis
  const basesDistintas = !!basisUs && !!basisEu && basisUs !== basisEu

  const bestPeriod = periods.reduce((best, p) => {
    const d = (overall as Record<string, { count: number; win_rate: number; avg_return: number }>)[p]
    const bD = (overall as Record<string, { count: number; win_rate: number; avg_return: number }>)[best]
    if (!d) return best
    if (!bD) return p
    return d.win_rate > bD.win_rate ? p : best
  }, periods[0] as string)

  const recentSignals = (pf as Record<string, unknown>).recent_signals as RecentSignal[] | undefined
  const hasReturns = (pf.overall as Record<string, { count: number }>)?.['7d']?.count > 0
  const activeCount = pf.active_signals ?? 0

  // Days until first result across all active signals
  const daysToFirst = recentSignals && recentSignals.length > 0
    ? Math.max(0, 7 - Number(recentSignals[0]?.days_active ?? 7))
    : null

  return (
    <>
      <PageHeader
        title="Portfolio Tracker"
        subtitle={<>Rendimiento de <strong className="text-foreground">VALUE US</strong> — {pf.value_strategy?.count ?? pf.total_signals} señales
          {pf.date_range && <span className="ml-1 opacity-60">({pf.date_range})</span>}
          <span className="mt-1 block text-xs text-muted-foreground/70">
            Europa va aparte, más abajo: mezclarla en el titular hundía el número con señales que no operas.
          </span></>}
      />

      {insightRaw?.narrative && (
        <AiNarrativeCard narrative={insightRaw.narrative} label="Análisis de Rendimiento" className="mb-5" />
      )}

      {/* Win Rate Animation */}
      {hasReturns && (() => {
        const statsData = {
          periods: (['30d', '90d', '180d', '365d'] as const)
            .map(p => {
              const d = (overall as Record<string, { count: number; win_rate: number; avg_return: number }>)[p]
              if (!d || d.count === 0) return null
              return { label: p, win_rate: d.win_rate, avg_return: d.avg_return, count: d.count }
            })
            .filter(Boolean) as Array<{ label: string; win_rate: number; avg_return: number; count: number }>,
          score_correlation: pf.score_correlation ?? undefined,
          best_period: bestPeriod,
        }
        if (statsData.periods.length === 0) return null
        return (
          <div className="mb-5">
            <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground/50 mb-3 px-1">Resumen animado</div>
            <Suspense fallback={<div className="glass border border-border/40 rounded-xl h-20 flex items-center justify-center text-sm text-muted-foreground">Cargando…</div>}>
              <PortfolioStatsPlayer data={statsData} />
            </Suspense>
          </div>
        )
      })()}

      {/* Win Rate Cards — shown once returns exist */}
      {hasReturns && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
          {periods.map((p, idx) => {
            const d = (overall as Record<string, { count: number; win_rate: number; avg_return: number }>)[p]
            if (!d || d.count === 0) return null
            return (
              <Card key={p} className={`glass p-5 stagger-${idx + 1}`}>
                <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1">
                  Win Rate {p}
                  {p === bestPeriod && <Badge variant="green" className="text-[0.5rem] px-1 py-0 leading-4">BEST</Badge>}
                </div>
                <div className={`text-3xl font-extrabold tracking-tight tabular-nums leading-none mb-2 ${d.win_rate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {d.win_rate?.toFixed(1)}%
                </div>
                <div className="text-[0.66rem] text-muted-foreground">
                  Avg: <span className={d.avg_return >= 0 ? 'text-emerald-400' : 'text-red-400'}>{d.avg_return >= 0 ? '+' : ''}{d.avg_return?.toFixed(2)}%</span>
                  {' '}| {d.count} señales
                </div>
              </Card>
            )
          })}
          {pf.score_correlation != null && (
            <Card className="glass p-5 stagger-4">
              <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">Correlacion Score-Return</div>
              <div className={`text-3xl font-extrabold tracking-tight tabular-nums leading-none mb-2 ${pf.score_correlation > 0.1 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {pf.score_correlation.toFixed(3)}
              </div>
              <div className="text-[0.66rem] text-muted-foreground">
                {pf.score_correlation > 0.1 ? 'Scores predicen retornos' : 'Correlacion debil'}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Waiting state — no returns yet */}
      {!hasReturns && activeCount > 0 && (
        <Card className="glass p-5 mb-5 border border-primary/20 animate-fade-in-up">
          <div className="flex items-start gap-3">
            <div className="text-2xl opacity-60 mt-0.5">⏳</div>
            <div>
              <p className="text-sm font-semibold text-foreground mb-1">
                {activeCount} señales activas — primeras métricas disponibles
                {daysToFirst !== null && daysToFirst > 0
                  ? ` en ${daysToFirst} días`
                  : ' pronto'}
              </p>
              <p className="text-xs text-muted-foreground">
                El tracker graba el precio de cada señal y calcula el retorno real a los 7, 14 y 30 días.
                Vuelve en unos días para ver el rendimiento.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Stats bar */}
      {pf.avg_max_drawdown != null && (
        <div className="grid grid-cols-2 gap-3 mb-5">
          <Card className="glass p-5">
            <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">Avg Max Drawdown</div>
            <div className="text-3xl font-extrabold tracking-tight tabular-nums leading-none mb-2 text-red-400">{pf.avg_max_drawdown.toFixed(2)}%</div>
            <div className="text-[0.66rem] text-muted-foreground">riesgo promedio</div>
          </Card>
          <Card className="glass p-5">
            <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">Total Señales</div>
            <div className="text-3xl font-extrabold tracking-tight tabular-nums leading-none mb-2">{pf.total_signals}</div>
            <div className="text-[0.66rem] text-muted-foreground">{pf.unique_tickers} tickers únicos</div>
          </Card>
        </div>
      )}

      {/* Top / Worst performers — al horizonte de tesis que publique el
          tracker (90d hoy), no a 14 días. */}
      <div className="grid grid-cols-1 gap-4 mb-5 sm:grid-cols-2">
        {pf.top_performers && pf.top_performers.length > 0 && (
          <Card className="glass">
            <div className="px-5 py-3 border-b border-border/50 flex items-center gap-2">
              <h3 className="text-sm font-semibold text-emerald-400">Top Performers</h3>
              <Badge variant="green" className="text-[0.6rem]">{pf.top_performers.length}</Badge>
            </div>
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead>Ticker</TableHead>
                  <TableHead>Empresa</TableHead>
                  <TableHead>Return {horizonteLabel}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(pf.top_performers as Performer[]).map((p, i) => (
                  <TableRow key={`top_${typeof p.ticker === 'string' ? p.ticker : ''}_${i}`}>
                    <TableCell className="font-mono font-bold text-primary text-[0.8rem]">
                      <div className="flex items-center gap-1.5">
                        <TickerLogo ticker={typeof p.ticker === 'string' ? p.ticker : ''} size="xs" />
                        <span>{typeof p.ticker === 'string' ? p.ticker : ''}</span>
                      </div>
                      <Badge variant={stratVariant(p.strategy)} className="text-[0.55rem] px-1 py-0 mt-0.5">
                        {stratLabel(p.strategy)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-[0.75rem]">
                      {typeof p.company_name === 'string' ? p.company_name : typeof p.ticker === 'string' ? p.ticker : ''}
                    </TableCell>
                    <TableCell><span className="text-emerald-400 font-semibold">+{Number(p.return_pct ?? 0).toFixed(2)}%</span></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )}

        {pf.worst_performers && pf.worst_performers.length > 0 && (
          <Card className="glass">
            <div className="px-5 py-3 border-b border-border/50 flex items-center gap-2">
              <h3 className="text-sm font-semibold text-red-400">Worst Performers</h3>
              <Badge variant="red" className="text-[0.6rem]">{pf.worst_performers.length}</Badge>
            </div>
            <Table>
              <TableHeader>
                <TableRow className="border-border/50 hover:bg-transparent">
                  <TableHead>Ticker</TableHead>
                  <TableHead>Empresa</TableHead>
                  <TableHead>Return {horizonteLabel}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(pf.worst_performers as Performer[]).map((p, i) => (
                  <TableRow key={`worst_${typeof p.ticker === 'string' ? p.ticker : ''}_${i}`}>
                    <TableCell className="font-mono font-bold text-primary text-[0.8rem]">
                      <div className="flex items-center gap-1.5">
                        <TickerLogo ticker={typeof p.ticker === 'string' ? p.ticker : ''} size="xs" />
                        <span>{typeof p.ticker === 'string' ? p.ticker : ''}</span>
                      </div>
                      <Badge variant={stratVariant(p.strategy)} className="text-[0.55rem] px-1 py-0 mt-0.5">
                        {stratLabel(p.strategy)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-[0.75rem]">
                      {typeof p.company_name === 'string' ? p.company_name : typeof p.ticker === 'string' ? p.ticker : ''}
                    </TableCell>
                    <TableCell><span className="text-red-400 font-semibold">{Number(p.return_pct ?? 0).toFixed(2)}%</span></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )}
      </div>

      {/* Correlation Matrix Heatmap */}
      {corrData && corrData.tickers.length > 1 && (
        <Card className="glass mb-5 animate-fade-in-up overflow-clip">
          <div className="px-5 py-3 border-b border-border/50 flex items-center gap-2">
            <h3 className="text-sm font-semibold">Correlación de Señales</h3>
            <span className="text-[0.6rem] text-muted-foreground/50">{corrData.days}d · {corrData.as_of}</span>
          </div>
          <div className="table-x-wrap">
            <table className="text-[0.6rem] tabular-nums">
              <thead>
                <tr>
                  <th className="px-2 py-1.5 text-left text-muted-foreground/50 font-medium w-16"></th>
                  {corrData.tickers.map(t => (
                    <th key={t} className="px-1.5 py-1.5 text-center text-muted-foreground font-mono font-bold whitespace-nowrap">{t}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {corrData.tickers.map((rowTicker, ri) => (
                  <tr key={rowTicker} className="border-t border-border/10">
                    <td className="px-2 py-1 font-mono font-bold text-muted-foreground whitespace-nowrap">{rowTicker}</td>
                    {corrData.tickers.map((colTicker, ci) => {
                      const val = corrData.matrix[ri]?.[colTicker] ?? 0
                      const abs = Math.abs(val)
                      const isHigh = ri !== ci && abs >= 0.7
                      const bg = ri === ci
                        ? 'bg-muted/20'
                        : abs >= 0.7
                          ? val > 0 ? 'bg-red-500/20' : 'bg-blue-500/20'
                          : abs >= 0.4
                            ? val > 0 ? 'bg-red-500/8' : 'bg-blue-500/8'
                            : ''
                      const textColor = ri === ci
                        ? 'text-muted-foreground/30'
                        : abs >= 0.7
                          ? val > 0 ? 'text-red-400 font-bold' : 'text-blue-400 font-bold'
                          : 'text-muted-foreground/60'
                      return (
                        <td key={colTicker} className={`px-1.5 py-1 text-center ${bg} ${textColor}`}
                          title={isHigh ? `${rowTicker}/${colTicker}: correlación ${val > 0 ? 'positiva' : 'negativa'} alta (${val.toFixed(2)})` : ''}>
                          {ri === ci ? '1.0' : val.toFixed(2)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-2 border-t border-border/20 flex gap-4 text-[0.6rem] text-muted-foreground/40">
            <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-sm bg-red-500/25" /> ≥0.7 correlación positiva (concentración)</span>
            <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-sm bg-blue-500/25" /> ≥0.7 correlación negativa (diversificación)</span>
          </div>
        </Card>
      )}

      {/* Active Signals Table — always visible */}
      {recentSignals && recentSignals.length > 0 && (
        <Card className="glass animate-fade-in-up">
          <div className="px-5 py-3 border-b border-border/50 flex items-center gap-2">
            <h3 className="text-sm font-semibold">En seguimiento</h3>
            <Badge variant="gray" className="text-[0.6rem]">{activeCount}</Badge>
            <span className="text-xs text-muted-foreground ml-auto">
              señales de &lt;30 días, aún midiéndose · últimas 20
            </span>
          </div>
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead>Ticker</TableHead>
                <TableHead>Empresa</TableHead>
                <TableHead>Estrategia</TableHead>
                <TableHead>Sector</TableHead>
                <TableHead>Señal</TableHead>
                <TableHead className="text-right">Precio</TableHead>
                <TableHead className="text-right">Score</TableHead>
                <TableHead>1ª Métrica</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentSignals.map((s, i) => (
                <TableRow key={`sig_${String(s.ticker)}_${i}`}>
                  <TableCell className="font-mono font-bold text-primary text-[0.8rem] tracking-wide">
                    <div className="flex items-center gap-1.5">
                      <TickerLogo ticker={String(s.ticker || '')} size="xs" />
                      <span>{String(s.ticker || '')}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-[0.75rem] text-muted-foreground max-w-[120px] truncate">
                    {String(s.company_name ?? s.ticker ?? '')}
                  </TableCell>
                  <TableCell>
                    <Badge variant={stratVariant(s.strategy)} className="text-[0.6rem]">
                      {stratLabel(s.strategy)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-[0.75rem] text-muted-foreground">{String(s.sector ?? '')}</TableCell>
                  <TableCell className="text-[0.75rem] text-muted-foreground">{String(s.signal_date ?? '')}</TableCell>
                  <TableCell className="text-right tabular-nums text-[0.8rem]">
                    ${Number(s.signal_price ?? 0).toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-[0.8rem] text-primary">
                    {s.value_score != null ? Number(s.value_score).toFixed(0) : '—'}
                  </TableCell>
                  <TableCell className="text-[0.75rem]">
                    <span className={Number(s.days_active ?? 0) >= 7 ? 'text-emerald-400' : 'text-amber-400'}>
                      {Number(s.days_active ?? 0) >= 7 ? '✓ lista' : `${String(s.first_result_date ?? '')}`}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Full Signal History */}
      {signalsData && signalsData.data.length > 0 && (() => {
        const onSigSort = (key: SortKey) => {
          if (sigSortKey === key) setSigSortDir(d => d === 'asc' ? 'desc' : 'asc')
          else { setSigSortKey(key); setSigSortDir('desc') }
        }
        const thS = (key: SortKey) =>
          `cursor-pointer select-none whitespace-nowrap transition-colors hover:text-foreground text-xs ${sigSortKey === key ? 'text-primary' : ''}`

        const sigFiltered = signalsData.data.filter(s => {
          if (sigFilter === 'ACTIVE') return s.status === 'ACTIVE'
          if (sigFilter === 'COMPLETED') return s.status !== 'ACTIVE'
          return true
        })
        const sigVisible = sigPage * SIG_PAGE_SIZE

        const sigSorted = [...sigFiltered].sort((a, b) => {
          const av = a[sigSortKey] ?? ''
          const bv = b[sigSortKey] ?? ''
          if (typeof av === 'string' && typeof bv === 'string') {
            return sigSortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
          }
          const an = Number(av); const bn = Number(bv)
          if (an < bn) return sigSortDir === 'asc' ? -1 : 1
          if (an > bn) return sigSortDir === 'asc' ? 1 : -1
          return 0
        })

        const sigPaged = sigSorted.slice(0, sigVisible)

        return (
          <div className="mt-6">
            <div className="flex items-center gap-3 mb-3">
              <h3 className="text-sm font-semibold">Historial de Señales</h3>
              <Badge variant="gray" className="text-[0.6rem]">{signalsData.count}</Badge>
              <div className="flex gap-1 ml-2">
                {(['ALL', 'ACTIVE', 'COMPLETED'] as const).map(f => (
                  <button
                    key={f}
                    onClick={() => { setSigFilter(f); setSigPage(1) }}
                    className={`filter-btn ${sigFilter === f ? 'active' : ''}`}
                  >
                    {f === 'ALL' ? 'Todas' : f === 'ACTIVE' ? 'Activas' : 'Completadas'}
                  </button>
                ))}
              </div>
              <span className="text-xs text-muted-foreground ml-auto">{sigFiltered.length} señales</span>
            </div>

            {/* Mobile cards */}
            <div className="sm:hidden space-y-2 mb-2">
              {sigPaged.map((r) => (
                <div key={`${r.ticker}-${r.signal_date}`} className="glass rounded-2xl p-3.5 cursor-default">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <TickerLogo ticker={r.ticker} size="xs" />
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono font-bold text-sm">{r.ticker}</span>
                          <Badge variant={stratVariant(r.strategy)}>{stratLabel(r.strategy)}</Badge>
                        </div>
                        <span className="text-[0.6rem] text-muted-foreground">{r.signal_date?.slice(0, 10)}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      {r.return_14d != null && (
                        <div className={`text-sm font-bold ${r.return_14d > 0 ? 'text-emerald-400' : r.return_14d < 0 ? 'text-red-400' : 'text-muted-foreground'}`}>
                          {r.return_14d > 0 ? '+' : ''}{r.return_14d.toFixed(1)}%
                        </div>
                      )}
                      {r.status && <div className="text-[0.6rem] text-muted-foreground">{r.status}</div>}
                    </div>
                  </div>
                  <div className="flex gap-3 mt-2 text-[0.62rem] text-muted-foreground/60">
                    {r.value_score != null && <span>Score {r.value_score.toFixed(0)}</span>}
                    {r.return_7d != null && <span>7d: {r.return_7d > 0 ? '+' : ''}{r.return_7d.toFixed(1)}%</span>}
                    {r.return_30d != null && <span>30d: {r.return_30d > 0 ? '+' : ''}{r.return_30d.toFixed(1)}%</span>}
                    {r.sector && <span className="truncate">{r.sector}</span>}
                  </div>
                </div>
              ))}
            </div>

            {/* Desktop table */}
            <div className="hidden sm:block">
              <Card className="glass animate-fade-in-up">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border/50 hover:bg-transparent">
                      <TableHead className={thS('ticker')} onClick={() => onSigSort('ticker')}>Ticker</TableHead>
                      <TableHead className={thS('strategy')} onClick={() => onSigSort('strategy')}>Estrategia</TableHead>
                      <TableHead className={thS('signal_date')} onClick={() => onSigSort('signal_date')}>Fecha</TableHead>
                      <TableHead className={thS('signal_price')} onClick={() => onSigSort('signal_price')}>Precio Entrada</TableHead>
                      <TableHead className={thS('value_score')} onClick={() => onSigSort('value_score')}>Score</TableHead>
                      <TableHead className={thS('return_7d')} onClick={() => onSigSort('return_7d')}>Ret. 7d</TableHead>
                      <TableHead className={thS('return_14d')} onClick={() => onSigSort('return_14d')}>Ret. 14d</TableHead>
                      <TableHead className={thS('return_30d')} onClick={() => onSigSort('return_30d')}>Ret. 30d</TableHead>
                      <TableHead className={thS('alpha_7d')} onClick={() => onSigSort('alpha_7d')} title="Retorno vs SPY/VGK a 7 días">α 7d</TableHead>
                      <TableHead className={thS('alpha_30d')} onClick={() => onSigSort('alpha_30d')} title="Retorno vs SPY/VGK a 30 días">α 30d</TableHead>
                      <TableHead className={thS('max_drawdown_30d')} onClick={() => onSigSort('max_drawdown_30d')}>Max DD</TableHead>
                      <TableHead className={thS('sector')} onClick={() => onSigSort('sector')}>Sector</TableHead>
                      <TableHead>Estado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sigPaged.map((s, i) => (
                      <TableRow key={`${s.ticker}_${i}`}>
                        <TableCell className="font-mono font-bold text-primary text-[0.8rem] tracking-wide">
                          <div className="flex items-center gap-1.5">
                            <TickerLogo ticker={s.ticker} size="xs" />
                            <span>{s.ticker}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={stratVariant(s.strategy)} className="text-[0.6rem]">
                            {stratLabel(s.strategy)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-[0.75rem] text-muted-foreground tabular-nums">{s.signal_date ?? '—'}</TableCell>
                        <TableCell className="text-[0.8rem] tabular-nums">
                          {s.signal_price != null ? `$${s.signal_price.toFixed(2)}` : '—'}
                        </TableCell>
                        <TableCell className="tabular-nums text-[0.8rem] text-primary">
                          {s.value_score != null ? s.value_score.toFixed(0) : '—'}
                        </TableCell>
                        <TableCell className={`tabular-nums text-[0.8rem] font-semibold ${retColor(s.return_7d)}`}>
                          {s.return_7d != null ? `${s.return_7d >= 0 ? '+' : ''}${s.return_7d.toFixed(2)}%` : '—'}
                        </TableCell>
                        <TableCell className={`tabular-nums text-[0.8rem] font-semibold ${retColor(s.return_14d)}`}>
                          {s.return_14d != null ? `${s.return_14d >= 0 ? '+' : ''}${s.return_14d.toFixed(2)}%` : '—'}
                        </TableCell>
                        <TableCell className={`tabular-nums text-[0.8rem] font-semibold ${retColor(s.return_30d)}`}>
                          {s.return_30d != null ? `${s.return_30d >= 0 ? '+' : ''}${s.return_30d.toFixed(2)}%` : '—'}
                        </TableCell>
                        <TableCell className={`tabular-nums text-[0.8rem] font-semibold ${retColor(s.alpha_7d ?? undefined)}`}>
                          {s.alpha_7d != null ? `${s.alpha_7d >= 0 ? '+' : ''}${s.alpha_7d.toFixed(2)}%` : '—'}
                        </TableCell>
                        <TableCell className={`tabular-nums text-[0.8rem] font-semibold ${retColor(s.alpha_30d ?? undefined)}`}>
                          {s.alpha_30d != null ? `${s.alpha_30d >= 0 ? '+' : ''}${s.alpha_30d.toFixed(2)}%` : '—'}
                        </TableCell>
                        <TableCell className="tabular-nums text-[0.8rem] text-red-400">
                          {s.max_drawdown_30d != null ? `${s.max_drawdown_30d.toFixed(2)}%` : '—'}
                        </TableCell>
                        <TableCell className="text-[0.75rem] text-muted-foreground max-w-[110px] truncate">{s.sector ?? '—'}</TableCell>
                        <TableCell>
                          <Badge variant={s.status === 'ACTIVE' ? 'green' : 'gray'} className="text-[0.6rem]">
                            {s.status ?? 'ACTIVE'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            </div>

            {sigVisible < sigFiltered.length && (
              <div className="mt-3 flex justify-center">
                <button
                  onClick={() => setSigPage(p => p + 1)}
                  className="text-xs px-4 py-1.5 rounded-lg border border-border/40 text-muted-foreground hover:border-primary/40 hover:text-primary transition-colors"
                >
                  Ver más ({sigFiltered.length - sigVisible} restantes)
                </button>
              </div>
            )}
          </div>
        )
      })()}

      {/* Correlation Matrix */}
      {corrData && corrData.tickers.length >= 3 && (
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-muted-foreground mb-1 uppercase tracking-wider">
            Correlación entre picks VALUE (últimos {corrData.days}d)
          </h2>
          <p className="text-xs text-muted-foreground/60 mb-3">
            Riesgo de concentración oculto — correlación &gt;0.7 significa que los picks se mueven juntos
          </p>
          <Card className="glass border border-border/40">
            <CardContent className="p-3 table-x-wrap">
              <table className="text-[0.62rem] border-collapse w-full">
                <thead>
                  <tr>
                    <th className="text-muted-foreground/60 font-normal p-1 text-left w-12"></th>
                    {corrData.tickers.map(t => (
                      <th key={t} className="text-muted-foreground font-mono font-semibold p-1 text-center whitespace-nowrap">{t}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {corrData.tickers.map((rowT, ri) => (
                    <tr key={rowT}>
                      <td className="text-muted-foreground font-mono font-semibold p-1 whitespace-nowrap">{rowT}</td>
                      {corrData.tickers.map((colT) => {
                        const val = corrData.matrix[ri]?.[colT]
                        const isDiag = rowT === colT
                        const absVal = Math.abs(val ?? 0)
                        const bg = isDiag ? 'bg-muted/20' :
                          absVal >= 0.8 ? 'bg-red-500/25' :
                          absVal >= 0.6 ? 'bg-orange-500/15' :
                          absVal >= 0.4 ? 'bg-yellow-500/10' : ''
                        const textColor = isDiag ? 'text-muted-foreground/40' :
                          absVal >= 0.8 ? 'text-red-400 font-bold' :
                          absVal >= 0.6 ? 'text-orange-400' : 'text-foreground/60'
                        return (
                          <td key={colT} className={`p-1 text-center rounded ${bg} ${textColor}`}>
                            {val != null ? val.toFixed(2) : '—'}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="flex gap-4 mt-3 text-[0.6rem] text-muted-foreground/60">
                <span><span className="text-red-400 font-bold">■</span> &gt;0.8 — Muy correlados (riesgo alto)</span>
                <span><span className="text-orange-400">■</span> 0.6–0.8 — Correlados (vigilar)</span>
                <span><span className="text-yellow-400">■</span> 0.4–0.6 — Correlación moderada</span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── Alpha vs benchmark ── */}
      {pf.alpha?.['90d']?.count != null && pf.alpha['90d'].count >= 3 && (
        <div className="mt-6 animate-fade-in-up">
          <h2 className="text-base font-bold uppercase tracking-widest text-muted-foreground/60 pb-1 border-b border-border/30 mb-4">
            Alpha vs benchmark
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(['90d', '180d', '365d'] as const).map(period => {
              const a = pf.alpha![period]
              if (!a || a.count < 3) return null
              const alphaColor = (a.avg_alpha ?? 0) > 0 ? 'text-emerald-400' : 'text-red-400'
              const bench = 'SPY/VGK'
              return (
                <Card key={period} className="glass border-border/20">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground/60">{period}</span>
                      <Badge variant={(a.avg_alpha ?? 0) > 0 ? 'green' : 'red'} className="text-[0.65rem]">
                        {(a.avg_alpha ?? 0) > 0 ? '↑ OUTPERFORM' : '↓ UNDERPERFORM'}
                      </Badge>
                    </div>
                    <div className={`text-3xl font-extrabold tabular-nums leading-none mb-1 ${alphaColor}`}>
                      {(a.avg_alpha ?? 0) > 0 ? '+' : ''}{a.avg_alpha?.toFixed(2)}%
                    </div>
                    <div className="text-[0.65rem] text-muted-foreground/50 mb-3">alpha medio vs {bench}</div>
                    <div className="space-y-1.5 text-xs">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Nuestras señales</span>
                        <span className={a.avg_signal_return != null && a.avg_signal_return > 0 ? 'text-emerald-400 font-semibold' : 'text-red-400 font-semibold'}>
                          {a.avg_signal_return != null ? `${a.avg_signal_return > 0 ? '+' : ''}${a.avg_signal_return.toFixed(2)}%` : '—'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Benchmark ({bench})</span>
                        <span className="text-muted-foreground/70 font-semibold">
                          {a.avg_benchmark_return != null ? `${a.avg_benchmark_return > 0 ? '+' : ''}${a.avg_benchmark_return.toFixed(2)}%` : '—'}
                        </span>
                      </div>
                      <div className="flex justify-between pt-1 border-t border-border/20">
                        <span className="text-muted-foreground">% señales con alpha+</span>
                        <span className={`font-semibold ${(a.positive_alpha_rate ?? 0) >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {a.positive_alpha_rate?.toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between text-[0.65rem] text-muted-foreground/50">
                        <span>{a.count} señales</span>
                        <span>mejor {a.best_alpha != null ? `+${a.best_alpha.toFixed(1)}%` : '—'} / peor {a.worst_alpha?.toFixed(1)}%</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      )}

      {/* ── US vs EU ──
          OJO: no siempre son comparables. US a 90d sale del periodo limpio
          (27 señales) y EU del histórico completo (727), porque las señales
          EU limpias aún no cumplen 90 días. El JSON lo dice en `basis`, pero
          la pantalla lo ignoraba y coronaba un "MEJOR A 90D" comparando dos
          poblaciones distintas — y encima el histórico EU incluye el periodo
          que el propio tracker marca como política muerta. Si las bases no
          coinciden, no hay ganador que declarar. */}
      {((pf.value_strategy?.['90d']?.count ?? 0) >= 10 || (pf.eu_value_strategy?.['90d']?.count ?? 0) >= 10) && (
        <div className="mt-6 animate-fade-in-up">
          <h2 className="text-base font-bold uppercase tracking-widest text-muted-foreground/60 pb-1 border-b border-border/30 mb-1">
            VALUE US vs EU — horizonte de tesis
          </h2>
          <p className="text-xs text-muted-foreground/60 mb-2">
            Una tesis value se juega en trimestres, no en semanas. Estas son las cifras a 90d /
            6 meses / 1 año — el 7-30d mide ruido de corto plazo y no dice nada útil aquí.
            180d y 365d se llenan conforme envejecen las señales (el tracking empezó en feb-2026).
          </p>
          {basesDistintas && (
            <p className="mb-4 rounded-lg border border-amber-500/25 bg-amber-500/5 px-3 py-2 text-xs text-amber-300/90">
              <strong>No son comparables entre sí a 90 días.</strong> US mide solo el periodo
              con filtrado correcto; EU aún no tiene señales limpias con 90 días cumplidos, así
              que usa todo el histórico — incluido el tramo que el propio tracker descarta por
              describir una política que ya no se aplica. Cada columna es válida por separado;
              la resta entre ellas no.
            </p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {([
              { label: 'VALUE US', strat: pf.value_strategy, alpha: pf.alpha_us, badge: 'US', bench: 'SPY' },
              { label: 'VALUE EU', strat: pf.eu_value_strategy, alpha: pf.alpha_eu, badge: 'EU', bench: 'VGK' },
            ] as const).map(({ label, strat, alpha, badge, bench }) => {
              const s90 = strat?.['90d']
              const a90 = alpha?.['90d']
              const wr = s90?.win_rate ?? null
              const otherWr = (badge === 'US' ? pf.eu_value_strategy : pf.value_strategy)?.['90d']?.win_rate ?? -1
              const leads = !basesDistintas && wr != null && wr > otherWr
              return (
                <Card key={badge} className={`glass border ${leads ? 'border-primary/40' : 'border-border/20'}`}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-bold tracking-wide">{label}</span>
                      {leads && <Badge variant="blue" className="text-[0.65rem]">↑ MEJOR A 90D</Badge>}
                    </div>

                    {/* 90d — la cifra principal */}
                    {wr != null && s90?.count ? (
                      <div className="mb-3">
                        <div className="text-[0.65rem] uppercase tracking-widest text-muted-foreground/60 mb-1">90 días · win rate</div>
                        <div className={`text-3xl font-extrabold tabular-nums leading-none ${wr >= 55 ? 'text-emerald-400' : wr >= 45 ? 'text-amber-400' : 'text-red-400'}`}>
                          {wr.toFixed(1)}%
                        </div>
                        {/* El intervalo al lado del dato, no escondido: un
                            100% con n=8 abarca del 67% al 100% y sin esto se
                            lee igual que un 66,7% con n=27. */}
                        {s90.ci_low != null && s90.ci_high != null && (
                          <div className="mt-1 text-[0.7rem] tabular-nums text-muted-foreground/70">
                            IC 95%: {s90.ci_low.toFixed(0)}–{s90.ci_high.toFixed(0)}%
                          </div>
                        )}
                        <div className="text-xs text-muted-foreground mt-1.5">
                          retorno medio {s90.avg_return != null ? `${s90.avg_return > 0 ? '+' : ''}${s90.avg_return.toFixed(2)}%` : '—'}
                          <span className="text-muted-foreground/50"> · {s90.count} señales</span>
                        </div>
                        <div className="mt-1 text-[0.68rem] text-muted-foreground/50">
                          {BASIS_LABEL[s90.basis ?? ''] ?? s90.basis}
                        </div>
                        {a90?.avg_alpha != null && (
                          <div className="text-xs mt-1">
                            <span className="text-muted-foreground/60">vs {bench}: </span>
                            <span className={a90.avg_alpha >= 0 ? 'text-emerald-400 font-semibold' : 'text-red-400 font-semibold'}>
                              {a90.avg_alpha > 0 ? '+' : ''}{a90.avg_alpha.toFixed(1)}% alpha
                            </span>
                            <span className="text-muted-foreground/50">
                              {' '}(señal {a90.avg_signal_return != null ? `${a90.avg_signal_return > 0 ? '+' : ''}${a90.avg_signal_return.toFixed(1)}%` : '—'} vs índice {a90.avg_benchmark_return != null ? `${a90.avg_benchmark_return > 0 ? '+' : ''}${a90.avg_benchmark_return.toFixed(1)}%` : '—'})
                            </span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="mb-3 text-sm text-muted-foreground/60">Aún sin datos a 90 días.</div>
                    )}

                    {/* 180d / 365d — acumulando */}
                    <div className="grid grid-cols-2 gap-3 pt-3 border-t border-border/20">
                      {([
                        { p: '180d' as const, label: '6 meses', eta: 'ago-2026' },
                        { p: '365d' as const, label: '1 año', eta: 'feb-2027' },
                      ]).map(({ p, label: plabel, eta }) => {
                        const sp = strat?.[p]
                        if (sp?.count && sp.win_rate != null) {
                          const w = sp.win_rate
                          return (
                            <div key={p}>
                              <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground/60 mb-1">{plabel}</div>
                              <div className={`text-xl font-extrabold tabular-nums leading-none ${w >= 55 ? 'text-emerald-400' : w >= 45 ? 'text-amber-400' : 'text-red-400'}`}>
                                {w.toFixed(1)}%
                              </div>
                              <div className="text-[0.68rem] text-muted-foreground mt-1">
                                avg {sp.avg_return != null ? `${sp.avg_return > 0 ? '+' : ''}${sp.avg_return.toFixed(1)}%` : '—'} · {sp.count}
                              </div>
                            </div>
                          )
                        }
                        return (
                          <div key={p}>
                            <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground/60 mb-1">{plabel}</div>
                            <div className="text-sm text-muted-foreground/40 leading-tight mt-1.5">
                              Acumulando<br /><span className="text-[0.68rem]">~{eta}</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Estadísticas del sistema ── */}
      {calibData && (
        <div className="mt-8 space-y-4 animate-fade-in-up">
          <div className="pb-1 border-b border-border/30">
            <h2 className="text-base font-bold uppercase tracking-widest text-muted-foreground/60">
              Estadísticas del sistema
            </h2>
            {/* El horizonte no es un detalle: hasta el 9-sep-2026 todo esto se
                medía a 14 días y las conclusiones ("el score no predice")
                describían qué rebota en dos semanas, no qué tesis acierta. */}
            <p className="mt-1 text-xs text-muted-foreground">
              Medido a <strong className="text-foreground">{calibHorizonte}</strong> sobre {calibData.total_completed} señales
              {calibData.poblacion && <> · {calibData.poblacion}</>}
            </p>
            {/* El rango de emisión es la advertencia que faltaba: a 180d solo
                tienen dato las señales más viejas, así que 293 señales pueden
                venir de una ventana de 10 días. Con eso a la vista, "el score
                predice" se lee como lo que es. */}
            {calibData.muestra_desde && calibData.muestra_hasta && (
              <p className="mt-1 text-xs text-amber-300/80">
                Ojo: todas emitidas entre {calibData.muestra_desde} y {calibData.muestra_hasta}.
                A este horizonte solo tienen dato las señales más antiguas, así que esto
                describe ese periodo concreto — no la estrategia en general.
              </p>
            )}
          </div>

          {/* Win rate por régimen */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="glass border-border/20">
              <CardContent className="p-4">
                <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground/60 mb-3">Win rate por régimen de mercado</p>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={calibData.regime_analysis} layout="vertical" margin={{ left: 8, right: 32 }}>
                    <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 10 }} />
                    <YAxis type="category" dataKey="regime" tick={{ fontSize: 10 }} width={120} />
                    <Tooltip formatter={fmtPct} contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border) / 0.5)', fontSize: 12 }} />
                    <ReferenceLine x={50} stroke="rgba(255,255,255,0.2)" strokeDasharray="4 2" />
                    <Bar dataKey="win_rate" radius={[0, 4, 4, 0]} fill="#06b6d4"
                      label={false}
                      isAnimationActive={false}
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      shape={(props: any) => <rect {...props} fill={winColor(props.win_rate ?? props.value)} />}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Win rate por sector */}
            <Card className="glass border-border/20">
              <CardContent className="p-4">
                <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground/60 mb-3">Win rate por sector (top 8)</p>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart
                    data={[...calibData.sector_calibration]
                      .filter(s => s.count >= 10)
                      .sort((a, b) => b.win_rate - a.win_rate)
                      .slice(0, 8)}
                    layout="vertical"
                    margin={{ left: 8, right: 32 }}
                  >
                    <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 10 }} />
                    <YAxis type="category" dataKey="sector" tick={{ fontSize: 9 }} width={130} />
                    <Tooltip formatter={fmtPct} contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border) / 0.5)', fontSize: 12 }} />
                    <ReferenceLine x={50} stroke="rgba(255,255,255,0.2)" strokeDasharray="4 2" />
                    <Bar dataKey="win_rate" radius={[0, 4, 4, 0]} fill="#06b6d4"
                      isAnimationActive={false}
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      shape={(props: any) => <rect {...props} fill={winColor(props.win_rate ?? props.value)} />}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Win rate por score bucket (línea) */}
          <Card className="glass border-border/20">
            <CardContent className="p-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground/60 mb-1">Win rate por score bucket — ¿el score predice?</p>
              <p className="text-[0.7rem] text-muted-foreground/50 mb-3">Cada punto = rango de value_score. Por encima de la línea 50% = el score añade valor real.</p>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={calibData.score_buckets} margin={{ left: 8, right: 16, top: 8 }}>
                  <XAxis dataKey="range" tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={fmtPct} contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border) / 0.5)', fontSize: 12 }} />
                  <ReferenceLine y={50} stroke="rgba(255,255,255,0.25)" strokeDasharray="4 2" label={{ value: '50%', position: 'insideTopRight', fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} />
                  <Line type="monotone" dataKey="win_rate" stroke="#06b6d4" strokeWidth={2} dot={{ fill: '#06b6d4', r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* FCF yield buckets */}
          {calibData.fcf_yield_buckets?.length > 0 && (
            <Card className="glass border-border/20">
              <CardContent className="p-4">
                <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground/60 mb-1">Win rate por FCF Yield % — el factor más predictivo</p>
                <p className="text-[0.7rem] text-muted-foreground/50 mb-3">El modelo ML detectó FCF Yield como la feature más importante (26.8%). Aquí la evidencia.</p>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={calibData.fcf_yield_buckets} margin={{ left: 8, right: 16 }}>
                    <XAxis dataKey="range" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 10 }} />
                    <Tooltip formatter={fmtPct} contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border) / 0.5)', fontSize: 12 }} />
                    <ReferenceLine y={50} stroke="rgba(255,255,255,0.25)" strokeDasharray="4 2" />
                    <Bar dataKey="win_rate" radius={[4, 4, 0, 0]} fill="#06b6d4"
                      isAnimationActive={false}
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      shape={(props: any) => <rect {...props} fill={winColor(props.win_rate ?? props.value)} />}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Stats summary row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Señales analizadas', value: calibData.total_completed, color: 'text-foreground' },
              { label: 'Accuracy modelo ML', value: '82.3%', color: 'text-violet-400' },
              { label: 'ROC-AUC modelo ML', value: '0.912', color: 'text-violet-400' },
              { label: 'Feature #1', value: 'FCF Yield', color: 'text-cyan-400' },
            ].map(s => (
              <Card key={s.label} className="glass border-border/20">
                <CardContent className="p-3 text-center">
                  <div className={`text-xl font-extrabold tabular-nums ${s.color}`}>{s.value}</div>
                  <div className="text-[0.65rem] text-muted-foreground/60 mt-0.5">{s.label}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
