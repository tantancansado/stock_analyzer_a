import { useState } from 'react'
import { FlaskConical, TrendingUp, TrendingDown, Info } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { fetchBacktest } from '../api/client'
import Loading, { ErrorState } from '../components/Loading'

// ── Types ──────────────────────────────────────────────────────────────────────

interface PeriodStats {
  count: number
  win_rate: number | null
  avg_return: number | null
  median_return: number | null
  best: number | null
  worst: number | null
}

interface Trade {
  ticker: string
  company_name?: string
  strategy: string
  signal_date: string
  signal_price?: number
  value_score?: number
  sector?: string
  return_7d: number
  win_7d: boolean
  max_drawdown_30d?: number
}

interface BacktestData {
  type: string
  date_range?: { from: string; to: string }
  total_signals?: number
  market_context?: string
  periods?: {
    '7d': {
      overall: PeriodStats
      by_strategy: Record<string, PeriodStats>
      by_score: Record<string, PeriodStats>
    }
  }
  top_performers_7d?: Trade[]
  worst_performers_7d?: Trade[]
  trades?: Trade[]
  error?: string
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function pct(v: number | null, decimals = 1) {
  if (v == null) return '—'
  return `${v >= 0 ? '+' : ''}${v.toFixed(decimals)}%`
}

function StatCard({ label, value, sub, color = '' }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="glass rounded-2xl p-5">
      <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">{label}</div>
      <div className={`text-2xl sm:text-3xl font-extrabold tracking-tight tabular-nums leading-none mb-1 ${color}`}>{value}</div>
      {sub && <div className="text-[0.66rem] text-muted-foreground">{sub}</div>}
    </div>
  )
}

function WinBar({ winRate }: { winRate: number | null }) {
  if (winRate == null) return <span className="text-muted-foreground">—</span>
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-muted/40 overflow-hidden">
        <div
          className={`h-full rounded-full ${winRate >= 50 ? 'bg-emerald-500' : 'bg-red-500'}`}
          style={{ width: `${Math.min(winRate, 100)}%` }}
        />
      </div>
      <span className={`text-[0.75rem] font-bold tabular-nums w-10 text-right ${winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
        {winRate.toFixed(1)}%
      </span>
    </div>
  )
}

const STRATEGY_LABELS: Record<string, string> = {
  VALUE:      'Value US 🇺🇸',
  EU_VALUE:   'Value EU 🇪🇺',
  GLOBAL_VALUE: 'Value Global 🌍',
  MOMENTUM:   'Momentum',
  MEAN_REVERSION: 'Mean Reversion',
}

const SCORE_COLORS: Record<string, string> = {
  '≥70':   'text-emerald-400',
  '60-69': 'text-blue-400',
  '50-59': 'text-amber-400',
  '<50':   'text-red-400',
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function Backtest() {
  const { data, loading, error } = useApi(() => fetchBacktest(), [])
  const [activeTab, setActiveTab] = useState<'overview' | 'strategies' | 'scores' | 'trades'>('overview')
  const [tradeFilter, setTradeFilter] = useState('ALL')

  if (loading) return <Loading />
  if (error)   return <ErrorState message={error} />

  const bt = data as BacktestData | null
  if (!bt || bt.error) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-extrabold text-foreground flex items-center gap-2">
          <FlaskConical size={22} className="text-primary" /> Backtest
        </h1>
        <div className="glass rounded-2xl p-12 text-center">
          <FlaskConical size={40} className="mx-auto text-muted-foreground/20 mb-4" />
          <p className="text-muted-foreground">{bt?.error ?? 'Sin datos'}</p>
        </div>
      </div>
    )
  }

  // Support both legacy format (bt.metrics) and new live-tracker format (bt.periods)
  const isLiveTracker = bt.type === 'live_tracker'
  const btAny = bt as unknown as Record<string, unknown>
  const legacyMetrics = btAny.metrics as Record<string, unknown> | undefined

  const p7 = bt.periods?.['7d']
  const overall: PeriodStats | undefined = p7?.overall ?? (legacyMetrics ? {
    count:          legacyMetrics.total_trades as number ?? 0,
    win_rate:       legacyMetrics.win_rate as number ?? null,
    avg_return:     legacyMetrics.avg_trade as number ?? null,
    median_return:  null,
    best:           (legacyMetrics.best_trade as Record<string,unknown>)?.profit_loss_pct as number ?? null,
    worst:          (legacyMetrics.worst_trade as Record<string,unknown>)?.profit_loss_pct as number ?? null,
  } : undefined)

  const strategies = p7?.by_strategy ?? {}
  const scoreBuckets = p7?.by_score ?? {}
  const allTrades = bt.trades ?? []
  const filteredTrades = tradeFilter === 'ALL' ? allTrades : allTrades.filter(t => t.strategy === tradeFilter)
  const strategyKeys = Object.keys(strategies)

  const tabs = [
    { id: 'overview',   label: 'Resumen' },
    { id: 'strategies', label: 'Por Estrategia' },
    { id: 'scores',     label: 'Por Score' },
    { id: 'trades',     label: `Señales (${allTrades.length})` },
  ] as const

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-foreground flex items-center gap-2">
          <FlaskConical size={22} className="text-primary" />
          Backtest — Live Tracker
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          {isLiveTracker
            ? `Rendimiento real de señales generadas · ${bt.date_range?.from} → ${bt.date_range?.to} · ${bt.total_signals} señales`
            : `Backtest histórico · ${(btAny.backtest_date as string ?? '').slice(0,10)} · ${overall?.count ?? 0} trades`
          }
        </p>
      </div>

      {/* Market context warning */}
      {bt.market_context && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-500/8 border border-amber-500/20">
          <Info size={15} className="text-amber-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-amber-400">Contexto de mercado: {bt.market_context}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              El sistema empezó a registrar señales el {bt.date_range?.from} en régimen de CORRECTION.
              Los resultados negativos reflejan el entorno, no los parámetros del sistema.
              Resultados a 14d y 30d disponibles cuando las señales maduren.
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-xl bg-muted/20 border border-border/30 w-fit">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === t.id
                ? 'bg-background text-foreground shadow-sm border border-border/40'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW ── */}
      {activeTab === 'overview' && overall && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatCard
              label="Señales con resultado"
              value={String(overall.count)}
              sub={`de ${bt.total_signals} totales`}
            />
            <StatCard
              label="Win Rate 7d"
              value={overall.win_rate != null ? `${overall.win_rate.toFixed(1)}%` : '—'}
              sub={overall.win_rate != null && overall.win_rate >= 50 ? 'positivo' : 'entorno bajista'}
              color={overall.win_rate != null && overall.win_rate >= 50 ? 'text-emerald-400' : 'text-red-400'}
            />
            <StatCard
              label="Retorno medio 7d"
              value={pct(overall.avg_return, 2)}
              sub={`mediana ${pct(overall.median_return, 2)}`}
              color={(overall.avg_return ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}
            />
            <StatCard
              label="Mejor / Peor"
              value={`${pct(overall.best, 1)} / ${pct(overall.worst, 1)}`}
              sub="rango de retornos"
            />
          </div>

          {/* Top + Worst performers */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="glass rounded-2xl overflow-hidden">
              <div className="px-5 py-3 border-b border-border/30 flex items-center gap-2">
                <TrendingUp size={14} className="text-emerald-400" />
                <span className="text-sm font-semibold">Top 7d</span>
              </div>
              <div className="divide-y divide-border/20">
                {(bt.top_performers_7d ?? []).slice(0, 8).map((t, i) => (
                  <div key={i} className="flex items-center gap-3 px-5 py-2.5">
                    <span className="font-mono font-bold text-primary text-sm w-20 truncate">{t.ticker}</span>
                    <span className="text-[0.7rem] text-muted-foreground flex-1 truncate">{t.company_name}</span>
                    <span className="text-[0.65rem] text-muted-foreground/60">{STRATEGY_LABELS[t.strategy] ?? t.strategy}</span>
                    <span className="text-sm font-bold text-emerald-400 tabular-nums w-16 text-right">{pct(t.return_7d)}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="glass rounded-2xl overflow-hidden">
              <div className="px-5 py-3 border-b border-border/30 flex items-center gap-2">
                <TrendingDown size={14} className="text-red-400" />
                <span className="text-sm font-semibold">Peores 7d</span>
              </div>
              <div className="divide-y divide-border/20">
                {(bt.worst_performers_7d ?? []).slice(0, 8).map((t, i) => (
                  <div key={i} className="flex items-center gap-3 px-5 py-2.5">
                    <span className="font-mono font-bold text-primary text-sm w-20 truncate">{t.ticker}</span>
                    <span className="text-[0.7rem] text-muted-foreground flex-1 truncate">{t.company_name}</span>
                    <span className="text-[0.65rem] text-muted-foreground/60">{STRATEGY_LABELS[t.strategy] ?? t.strategy}</span>
                    <span className="text-sm font-bold text-red-400 tabular-nums w-16 text-right">{pct(t.return_7d)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── STRATEGIES ── */}
      {activeTab === 'strategies' && (
        <div className="space-y-3">
          {strategyKeys.length === 0 ? (
            <p className="text-muted-foreground text-sm">Sin datos por estrategia todavía.</p>
          ) : (
            strategyKeys.map(s => {
              const st = strategies[s]
              return (
                <div key={s} className="glass rounded-2xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-bold text-foreground">{STRATEGY_LABELS[s] ?? s}</h3>
                    <span className="text-xs text-muted-foreground">{st.count} señales con resultado</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div>
                      <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-1">Win Rate</div>
                      <WinBar winRate={st.win_rate} />
                    </div>
                    <div>
                      <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-1">Retorno medio</div>
                      <div className={`text-xl font-extrabold tabular-nums ${(st.avg_return ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {pct(st.avg_return, 2)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-1">Mediana</div>
                      <div className={`text-xl font-extrabold tabular-nums ${(st.median_return ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {pct(st.median_return, 2)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-1">Mejor / Peor</div>
                      <div className="text-sm font-semibold">
                        <span className="text-emerald-400">{pct(st.best)}</span>
                        <span className="text-muted-foreground"> / </span>
                        <span className="text-red-400">{pct(st.worst)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })
          )}
          <p className="text-[0.7rem] text-muted-foreground/50 px-1">
            Momentum y Mean Reversion aparecerán aquí cuando el pipeline genere señales en régimen favorable.
          </p>
        </div>
      )}

      {/* ── SCORE BUCKETS ── */}
      {activeTab === 'scores' && (
        <div className="space-y-4">
          <div className="glass rounded-2xl p-4 border border-primary/20 bg-primary/5">
            <p className="text-xs text-primary font-semibold mb-1">¿El score predice los retornos?</p>
            <p className="text-[0.72rem] text-muted-foreground">
              Aquí puedes ver si las señales con score alto realmente rinden mejor. Si el sistema funciona,
              el bucket ≥70 debería tener mayor win rate y mayor retorno medio.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {Object.entries(scoreBuckets).map(([bucket, st]) => (
              <div key={bucket} className="glass rounded-2xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className={`text-lg font-extrabold ${SCORE_COLORS[bucket] ?? 'text-foreground'}`}>
                    Score {bucket}
                  </span>
                  <span className="text-xs text-muted-foreground">{st.count} señales</span>
                </div>
                {st.count === 0 ? (
                  <p className="text-xs text-muted-foreground">Sin señales en este rango</p>
                ) : (
                  <div className="space-y-2">
                    <div>
                      <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-1">Win Rate</div>
                      <WinBar winRate={st.win_rate} />
                    </div>
                    <div className="flex gap-6 mt-2">
                      <div>
                        <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-0.5">Avg retorno</div>
                        <div className={`text-xl font-extrabold tabular-nums ${(st.avg_return ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {pct(st.avg_return, 2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-0.5">Mediana</div>
                        <div className={`text-xl font-extrabold tabular-nums ${(st.median_return ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {pct(st.median_return, 2)}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── TRADES TABLE ── */}
      {activeTab === 'trades' && (
        <div className="space-y-3">
          {/* Filter */}
          <div className="flex gap-2 flex-wrap">
            {['ALL', ...strategyKeys].map(s => (
              <button
                key={s}
                onClick={() => setTradeFilter(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                  tradeFilter === s
                    ? 'bg-primary/15 border-primary/30 text-primary'
                    : 'bg-muted/20 border-border/30 text-muted-foreground hover:text-foreground'
                }`}
              >
                {s === 'ALL' ? 'Todas' : (STRATEGY_LABELS[s] ?? s)} {s !== 'ALL' && `(${strategies[s]?.count ?? 0})`}
              </button>
            ))}
          </div>

          <div className="glass rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-border/30 flex items-center justify-between">
              <span className="text-sm font-semibold">Señales registradas</span>
              <span className="text-xs text-muted-foreground">{filteredTrades.length} entradas</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/30 text-[0.65rem] uppercase tracking-widest text-muted-foreground">
                    <th className="px-4 py-2.5 text-left">Ticker</th>
                    <th className="px-4 py-2.5 text-left hidden sm:table-cell">Empresa</th>
                    <th className="px-4 py-2.5 text-left hidden md:table-cell">Sector</th>
                    <th className="px-4 py-2.5 text-left hidden md:table-cell">Estrategia</th>
                    <th className="px-4 py-2.5 text-right">Score</th>
                    <th className="px-4 py-2.5 text-right">Ret 7d</th>
                    <th className="px-4 py-2.5 text-center hidden sm:table-cell">Resultado</th>
                    <th className="px-4 py-2.5 text-left hidden lg:table-cell">Fecha señal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/15">
                  {filteredTrades.slice(0, 200).map((t, i) => (
                    <tr key={i} className="hover:bg-muted/10 transition-colors">
                      <td className="px-4 py-2 font-mono font-bold text-primary text-[0.8rem]">{t.ticker}</td>
                      <td className="px-4 py-2 text-[0.74rem] text-muted-foreground hidden sm:table-cell max-w-[130px] truncate">{t.company_name}</td>
                      <td className="px-4 py-2 text-[0.72rem] text-muted-foreground hidden md:table-cell">{t.sector}</td>
                      <td className="px-4 py-2 text-[0.72rem] text-muted-foreground hidden md:table-cell">{STRATEGY_LABELS[t.strategy] ?? t.strategy}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-[0.8rem]">
                        <span className={t.value_score != null && t.value_score >= 60 ? 'text-emerald-400 font-bold' : 'text-muted-foreground'}>
                          {t.value_score != null ? t.value_score.toFixed(1) : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-right">
                        <span className={`font-bold tabular-nums text-[0.8rem] ${t.return_7d >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {pct(t.return_7d)}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-center hidden sm:table-cell">
                        <span className={`text-[0.65rem] font-bold px-1.5 py-0.5 rounded ${t.win_7d ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                          {t.win_7d ? 'WIN' : 'LOSS'}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-[0.72rem] text-muted-foreground/60 hidden lg:table-cell">{t.signal_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredTrades.length > 200 && (
                <p className="text-center text-xs text-muted-foreground py-3">Mostrando 200 de {filteredTrades.length}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
