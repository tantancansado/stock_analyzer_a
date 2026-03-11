import { useState } from 'react'
import { FlaskConical, TrendingUp, TrendingDown, Info } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { fetchBacktest } from '../api/client'
import Loading, { ErrorState } from '../components/Loading'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Trade {
  ticker: string
  company_name?: string
  strategy: string
  signal_date?: string
  signal_price?: number
  value_score?: number
  sector?: string
  return_7d: number
  win_7d: boolean
}

// ── Client-side stats from trades array ───────────────────────────────────────

function calcStats(trades: Trade[]) {
  if (!trades.length) return null
  const rets  = trades.map(t => t.return_7d).sort((a, b) => a - b)
  const wins  = trades.filter(t => t.win_7d).length
  const mid   = Math.floor(rets.length / 2)
  const median = rets.length % 2 === 0 ? (rets[mid - 1] + rets[mid]) / 2 : rets[mid]
  return {
    count:         trades.length,
    win_rate:      Math.round((wins / trades.length) * 1000) / 10,
    avg_return:    Math.round(rets.reduce((a, b) => a + b, 0) / rets.length * 100) / 100,
    median_return: Math.round(median * 100) / 100,
    best:          rets[rets.length - 1],
    worst:         rets[0],
  }
}

function groupBy<T>(arr: T[], key: (item: T) => string): Record<string, T[]> {
  const out: Record<string, T[]> = {}
  for (const item of arr) {
    const k = key(item)
    ;(out[k] ??= []).push(item)
  }
  return out
}

function scoreBucket(score?: number): string {
  if (score == null) return 'Sin score'
  if (score >= 70)  return '≥70'
  if (score >= 60)  return '60-69'
  if (score >= 50)  return '50-59'
  return '<50'
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function pct(v: number | null | undefined, decimals = 1) {
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

function WinBar({ winRate }: { winRate: number | null | undefined }) {
  if (winRate == null) return <span className="text-muted-foreground text-sm">—</span>
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-muted/40 overflow-hidden">
        <div
          className={`h-full rounded-full ${winRate >= 50 ? 'bg-emerald-500' : 'bg-red-500'}`}
          style={{ width: `${Math.min(winRate, 100)}%` }}
        />
      </div>
      <span className={`text-[0.75rem] font-bold tabular-nums w-12 text-right ${winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
        {winRate.toFixed(1)}%
      </span>
    </div>
  )
}

const STRATEGY_LABELS: Record<string, string> = {
  VALUE:           'Value US 🇺🇸',
  EU_VALUE:        'Value EU 🇪🇺',
  GLOBAL_VALUE:    'Value Global 🌍',
  MOMENTUM:        'Momentum',
  MEAN_REVERSION:  'Mean Reversion',
  'Oversold Bounce': 'Oversold Bounce',
}

const SCORE_ORDER = ['≥70', '60-69', '50-59', '<50', 'Sin score']
const SCORE_COLORS: Record<string, string> = {
  '≥70':     'text-emerald-400',
  '60-69':   'text-blue-400',
  '50-59':   'text-amber-400',
  '<50':     'text-red-400',
  'Sin score': 'text-muted-foreground',
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function Backtest() {
  const { data, loading, error } = useApi(() => fetchBacktest(), [])
  const [activeTab, setActiveTab] = useState<'overview' | 'strategies' | 'scores' | 'trades'>('overview')
  const [tradeFilter, setTradeFilter] = useState('ALL')

  if (loading) return <Loading />
  if (error)   return <ErrorState message={error} />

  const raw = data as unknown as Record<string, unknown> | null
  if (!raw || raw.error) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-extrabold text-foreground flex items-center gap-2">
          <FlaskConical size={22} className="text-primary" /> Backtest
        </h1>
        <div className="glass rounded-2xl p-12 text-center">
          <FlaskConical size={40} className="mx-auto text-muted-foreground/20 mb-4" />
          <p className="text-muted-foreground">{(raw?.error as string) ?? 'Sin datos'}</p>
        </div>
      </div>
    )
  }

  // ── Normalize trades from either API format ──────────────────────────────────
  const isLiveTracker = raw.type === 'live_tracker'
  const rawTrades = (raw.trades as Record<string, unknown>[] | undefined) ?? []

  const allTrades: Trade[] = rawTrades.map(t => {
    const ret = (t.return_7d as number | undefined) ?? (t.profit_loss_pct as number | undefined) ?? 0
    return {
      ticker:      String(t.ticker ?? ''),
      company_name: t.company_name as string | undefined,
      strategy:    String(t.strategy ?? 'Unknown'),
      signal_date: (t.signal_date ?? t.backtest_date ?? '') as string,
      signal_price: t.signal_price as number | undefined,
      value_score:  t.value_score as number | undefined,
      sector:       t.sector as string | undefined,
      return_7d:   ret,
      win_7d:      (t.win_7d as boolean | undefined) ?? (t.win as boolean | undefined) ?? (ret > 0),
    }
  }).sort((a, b) => b.return_7d - a.return_7d)

  // ── Compute everything client-side ──────────────────────────────────────────
  const overall   = calcStats(allTrades)
  const byStrat   = groupBy(allTrades, t => t.strategy)
  const byScore   = groupBy(allTrades, t => scoreBucket(t.value_score))
  const topTrades = allTrades.slice(0, 10)
  const worseTrades = allTrades.slice(-10).reverse()

  const stratKeys  = Object.keys(byStrat).sort()
  const filteredTrades = tradeFilter === 'ALL' ? allTrades : allTrades.filter(t => t.strategy === tradeFilter)

  // Meta
  const marketContext = raw.market_context as string | undefined
  const dateFrom = (raw.date_range as Record<string,string> | undefined)?.from ?? (raw.backtest_date as string | undefined)?.slice(0,10) ?? ''
  const dateTo   = (raw.date_range as Record<string,string> | undefined)?.to ?? ''

  const tabs = [
    { id: 'overview',   label: 'Resumen' },
    { id: 'strategies', label: `Estrategias (${stratKeys.length})` },
    { id: 'scores',     label: 'Por Score' },
    { id: 'trades',     label: `Señales (${allTrades.length})` },
  ] as const

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-foreground flex items-center gap-2">
          <FlaskConical size={22} className="text-primary" />
          Backtest {isLiveTracker ? '— Live Tracker' : '— Histórico'}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          {dateFrom}{dateTo && dateTo !== dateFrom ? ` → ${dateTo}` : ''} · {allTrades.length} señales registradas
        </p>
      </div>

      {/* Market context */}
      {marketContext && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-500/8 border border-amber-500/20">
          <Info size={15} className="text-amber-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-amber-400">Régimen de mercado: {marketContext}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Las señales se registraron durante una CORRECTION — los retornos negativos reflejan el entorno.
              Los resultados a 14d y 30d estarán disponibles conforme maduren las señales.
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-xl bg-muted/20 border border-border/30 w-fit flex-wrap">
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
              label="Señales"
              value={String(overall.count)}
              sub="con resultado disponible"
            />
            <StatCard
              label={isLiveTracker ? 'Win Rate 7d' : 'Win Rate'}
              value={`${overall.win_rate.toFixed(1)}%`}
              sub={overall.win_rate >= 50 ? 'sobre el 50%' : 'entorno bajista'}
              color={overall.win_rate >= 50 ? 'text-emerald-400' : 'text-red-400'}
            />
            <StatCard
              label={isLiveTracker ? 'Retorno medio 7d' : 'P&L medio por trade'}
              value={pct(overall.avg_return, 2)}
              sub={isLiveTracker ? `mediana ${pct(overall.median_return, 2)}` : `mediana ${pct(overall.median_return, 2)} · holding variable`}
              color={overall.avg_return >= 0 ? 'text-emerald-400' : 'text-red-400'}
            />
            <StatCard
              label="Mejor / Peor"
              value={`${pct(overall.best)} / ${pct(overall.worst)}`}
              sub="rango de retornos"
            />
          </div>

          {/* Top + Worst */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="glass rounded-2xl overflow-hidden">
              <div className="px-5 py-3 border-b border-border/30 flex items-center gap-2">
                <TrendingUp size={14} className="text-emerald-400" />
                <span className="text-sm font-semibold">Mejores 7d</span>
              </div>
              <div className="divide-y divide-border/15">
                {topTrades.map((t, i) => (
                  <div key={i} className="flex items-center gap-3 px-5 py-2.5">
                    <span className="font-mono font-bold text-primary text-sm w-16 shrink-0">{t.ticker}</span>
                    <span className="text-[0.7rem] text-muted-foreground flex-1 truncate">{t.company_name ?? t.sector ?? '—'}</span>
                    <span className="text-[0.62rem] text-muted-foreground/50 shrink-0">{STRATEGY_LABELS[t.strategy] ?? t.strategy}</span>
                    <span className="text-sm font-bold text-emerald-400 tabular-nums w-14 text-right shrink-0">{pct(t.return_7d)}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="glass rounded-2xl overflow-hidden">
              <div className="px-5 py-3 border-b border-border/30 flex items-center gap-2">
                <TrendingDown size={14} className="text-red-400" />
                <span className="text-sm font-semibold">Peores 7d</span>
              </div>
              <div className="divide-y divide-border/15">
                {worseTrades.map((t, i) => (
                  <div key={i} className="flex items-center gap-3 px-5 py-2.5">
                    <span className="font-mono font-bold text-primary text-sm w-16 shrink-0">{t.ticker}</span>
                    <span className="text-[0.7rem] text-muted-foreground flex-1 truncate">{t.company_name ?? t.sector ?? '—'}</span>
                    <span className="text-[0.62rem] text-muted-foreground/50 shrink-0">{STRATEGY_LABELS[t.strategy] ?? t.strategy}</span>
                    <span className="text-sm font-bold text-red-400 tabular-nums w-14 text-right shrink-0">{pct(t.return_7d)}</span>
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
          {stratKeys.map(s => {
            const st = calcStats(byStrat[s])!
            return (
              <div key={s} className="glass rounded-2xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold text-foreground">{STRATEGY_LABELS[s] ?? s}</h3>
                  <span className="text-xs text-muted-foreground">{st.count} señales</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div>
                    <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-1.5">Win Rate</div>
                    <WinBar winRate={st.win_rate} />
                  </div>
                  <div>
                    <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-1">Retorno medio</div>
                    <div className={`text-xl font-extrabold tabular-nums ${st.avg_return >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {pct(st.avg_return, 2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-1">Mediana</div>
                    <div className={`text-xl font-extrabold tabular-nums ${st.median_return >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
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
          })}
        </div>
      )}

      {/* ── SCORE BUCKETS ── */}
      {activeTab === 'scores' && (
        <div className="space-y-4">
          <div className="glass rounded-2xl p-4 border border-primary/20 bg-primary/5">
            <p className="text-xs text-primary font-semibold mb-1">¿El score predice los retornos?</p>
            <p className="text-[0.72rem] text-muted-foreground">
              Si el sistema funciona, el bucket ≥70 debería tener mayor win rate y mayor retorno que el &lt;50.
            </p>
          </div>
          {byScore['Sin score']?.length === allTrades.length && (
            <div className="glass rounded-2xl p-4 border border-amber-500/20 bg-amber-500/5">
              <p className="text-xs text-amber-400 font-semibold">Sin datos de score en este backtest</p>
              <p className="text-[0.72rem] text-muted-foreground mt-0.5">El backtest histórico no incluye value_score. Cuando Railway actualice con las 680+ señales del live tracker, este tab mostrará si el score predice los retornos.</p>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SCORE_ORDER.filter(b => b !== 'Sin score' && byScore[b]?.length).map(bucket => {
              const st = calcStats(byScore[bucket])!
              return (
                <div key={bucket} className="glass rounded-2xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className={`text-lg font-extrabold ${SCORE_COLORS[bucket]}`}>Score {bucket}</span>
                    <span className="text-xs text-muted-foreground">{st.count} señales</span>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-1">Win Rate</div>
                      <WinBar winRate={st.win_rate} />
                    </div>
                    <div className="flex gap-6">
                      <div>
                        <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-0.5">Avg retorno</div>
                        <div className={`text-xl font-extrabold tabular-nums ${st.avg_return >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {pct(st.avg_return, 2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground mb-0.5">Mediana</div>
                        <div className={`text-xl font-extrabold tabular-nums ${st.median_return >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {pct(st.median_return, 2)}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── TRADES ── */}
      {activeTab === 'trades' && (
        <div className="space-y-3">
          <div className="flex gap-2 flex-wrap">
            {['ALL', ...stratKeys].map(s => (
              <button
                key={s}
                onClick={() => setTradeFilter(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                  tradeFilter === s
                    ? 'bg-primary/15 border-primary/30 text-primary'
                    : 'bg-muted/20 border-border/30 text-muted-foreground hover:text-foreground'
                }`}
              >
                {s === 'ALL' ? `Todas (${allTrades.length})` : `${STRATEGY_LABELS[s] ?? s} (${byStrat[s]?.length ?? 0})`}
              </button>
            ))}
          </div>

          <div className="glass rounded-2xl overflow-hidden">
            {/* Header row */}
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border/30 text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">
              <span className="w-16 shrink-0">Ticker</span>
              <span className="flex-1 min-w-0 hidden sm:block">Empresa</span>
              <span className="w-28 shrink-0 hidden md:block">Estrategia</span>
              <span className="w-14 text-right shrink-0">Score</span>
              <span className="w-16 text-right shrink-0">{isLiveTracker ? 'Ret 7d' : 'P&L'}</span>
              <span className="w-12 text-center shrink-0 hidden sm:block">Res.</span>
              <span className="w-20 shrink-0 hidden lg:block ml-2">Fecha</span>
            </div>
            {/* Data rows */}
            <div className="divide-y divide-border/10">
              {filteredTrades.slice(0, 300).map((t, i) => (
                <div key={i} className="flex items-center gap-2 px-4 py-2 hover:bg-muted/10 transition-colors">
                  <span className="w-16 shrink-0 font-mono font-bold text-primary text-[0.8rem]">{t.ticker}</span>
                  <span className="flex-1 min-w-0 hidden sm:block text-[0.74rem] text-muted-foreground truncate">{t.company_name ?? '—'}</span>
                  <span className="w-28 shrink-0 hidden md:block text-[0.72rem] text-muted-foreground truncate">{STRATEGY_LABELS[t.strategy] ?? t.strategy}</span>
                  <span className="w-14 text-right shrink-0 tabular-nums text-[0.8rem]">
                    {t.value_score != null
                      ? <span className={t.value_score >= 60 ? 'text-emerald-400 font-bold' : 'text-muted-foreground'}>{t.value_score.toFixed(1)}</span>
                      : <span className="text-muted-foreground/30">—</span>
                    }
                  </span>
                  <span className={`w-16 text-right shrink-0 font-bold tabular-nums text-[0.8rem] ${t.return_7d >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {pct(t.return_7d)}
                  </span>
                  <span className="w-12 text-center shrink-0 hidden sm:block">
                    <span className={`text-[0.62rem] font-bold px-1.5 py-0.5 rounded ${t.win_7d ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                      {t.win_7d ? 'WIN' : 'LOSS'}
                    </span>
                  </span>
                  <span className="w-20 shrink-0 hidden lg:block text-[0.7rem] text-muted-foreground/50 ml-2">{t.signal_date?.slice(0, 10) ?? '—'}</span>
                </div>
              ))}
            </div>
            {filteredTrades.length > 300 && (
              <p className="text-center text-xs text-muted-foreground py-3 border-t border-border/20">Mostrando 300 de {filteredTrades.length}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
