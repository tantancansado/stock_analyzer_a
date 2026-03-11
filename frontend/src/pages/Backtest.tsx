import { useState, useEffect } from 'react'
import { FlaskConical, Info } from 'lucide-react'
import Loading from '../components/Loading'

// ── CSV fetch from GitHub Pages ────────────────────────────────────────────────

const CSV_BASE = (import.meta.env.VITE_CSV_BASE as string | undefined)
  ?? 'https://tantancansado.github.io/stock_analyzer_a'

interface Signal {
  ticker: string
  company_name: string
  strategy: string
  signal_date: string
  signal_price: number
  value_score: number | null
  sector: string
  return_7d: number | null
  return_14d: number | null
  return_30d: number | null
}

function parseCSV(text: string): Signal[] {
  const lines = text.trim().split('\n')
  if (lines.length < 2) return []
  const headers = lines[0].split(',').map(h => h.trim())
  const idx = (name: string) => headers.indexOf(name)

  return lines.slice(1).map(line => {
    const cols = line.split(',')
    const get  = (name: string) => cols[idx(name)]?.trim() ?? ''
    const num  = (name: string) => { const v = parseFloat(get(name)); return isNaN(v) ? null : v }
    return {
      ticker:       get('ticker'),
      company_name: get('company_name'),
      strategy:     get('strategy'),
      signal_date:  get('signal_date'),
      signal_price: parseFloat(get('signal_price')) || 0,
      value_score:  num('value_score'),
      sector:       get('sector'),
      return_7d:    num('return_7d'),
      return_14d:   num('return_14d'),
      return_30d:   num('return_30d'),
    }
  }).filter(s => s.ticker)
}

// ── Helpers ────────────────────────────────────────────────────────────────────

type Period = '7d' | '14d' | '30d'
const PERIODS: { key: Period; label: string }[] = [
  { key: '7d',  label: '+7 días' },
  { key: '14d', label: '+14 días' },
  { key: '30d', label: '+30 días' },
]

function retOf(s: Signal, p: Period) {
  return p === '7d' ? s.return_7d : p === '14d' ? s.return_14d : s.return_30d
}

function pct(v: number | null, d = 1) {
  if (v == null) return null
  return `${v >= 0 ? '+' : ''}${v.toFixed(d)}%`
}

function Stats({ signals, period }: { signals: Signal[]; period: Period }) {
  const withData = signals.filter(s => retOf(s, period) != null)
  if (!withData.length) return (
    <div className="glass rounded-2xl p-4 text-center text-sm text-muted-foreground">
      Sin resultados a {period} todavía — llegarán conforme pasen los días
    </div>
  )
  const rets  = withData.map(s => retOf(s, period)!)
  const wins  = rets.filter(r => r > 0).length
  const avg   = rets.reduce((a, b) => a + b, 0) / rets.length
  const wr    = (wins / rets.length) * 100
  const sorted = [...rets].sort((a,b) => a - b)
  const mid   = Math.floor(sorted.length / 2)
  const median = sorted.length % 2 === 0 ? (sorted[mid-1] + sorted[mid]) / 2 : sorted[mid]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div className="glass rounded-2xl p-4">
        <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-1">Señales evaluadas</div>
        <div className="text-2xl font-extrabold text-foreground">{withData.length}</div>
        <div className="text-[0.66rem] text-muted-foreground">de {signals.length} totales</div>
      </div>
      <div className="glass rounded-2xl p-4">
        <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-1">Win Rate</div>
        <div className={`text-2xl font-extrabold ${wr >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>{wr.toFixed(1)}%</div>
        <div className="text-[0.66rem] text-muted-foreground">{wins} ganaron · {withData.length - wins} perdieron</div>
      </div>
      <div className="glass rounded-2xl p-4">
        <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-1">Retorno medio</div>
        <div className={`text-2xl font-extrabold ${avg >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{pct(avg, 2)}</div>
        <div className="text-[0.66rem] text-muted-foreground">mediana {pct(median, 2)}</div>
      </div>
      <div className="glass rounded-2xl p-4">
        <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-1">Mejor / Peor</div>
        <div className="text-lg font-extrabold">
          <span className="text-emerald-400">{pct(Math.max(...rets))}</span>
          <span className="text-muted-foreground text-sm"> / </span>
          <span className="text-red-400">{pct(Math.min(...rets))}</span>
        </div>
      </div>
    </div>
  )
}

const STRAT_LABEL: Record<string, string> = {
  VALUE: 'Value US 🇺🇸', EU_VALUE: 'Value EU 🇪🇺', GLOBAL_VALUE: 'Value Global 🌍',
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function Backtest() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [period,  setPeriod]  = useState<Period>('7d')
  const [strat,   setStrat]   = useState('ALL')
  const [sort,    setSort]    = useState<'date' | 'ret' | 'score'>('ret')

  useEffect(() => {
    fetch(`${CSV_BASE}/portfolio_tracker/recommendations.csv`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.text() })
      .then(text => { setSignals(parseCSV(text)); setLoading(false) })
      .catch(e => { setError(String(e)); setLoading(false) })
  }, [])

  if (loading) return <Loading />
  if (error)   return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold text-foreground flex items-center gap-2">
        <FlaskConical size={22} className="text-primary" /> Backtest
      </h1>
      <div className="glass rounded-2xl p-8 text-center text-sm text-muted-foreground">{error}</div>
    </div>
  )

  const strategies  = [...new Set(signals.map(s => s.strategy))].sort()
  const filtered    = strat === 'ALL' ? signals : signals.filter(s => s.strategy === strat)
  const withResult  = filtered.filter(s => retOf(s, period) != null)
  const pending     = filtered.filter(s => retOf(s, period) == null)

  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'date') return b.signal_date.localeCompare(a.signal_date)
    if (sort === 'score') return (b.value_score ?? 0) - (a.value_score ?? 0)
    // 'ret': with results first (sorted by return), then pending
    const ra = retOf(a, period), rb = retOf(b, period)
    if (ra == null && rb == null) return 0
    if (ra == null) return 1
    if (rb == null) return -1
    return rb - ra
  })

  const dateRange = signals.length
    ? `${signals.reduce((a,b) => a < b.signal_date ? a : b.signal_date, signals[0].signal_date)} → ${signals.reduce((a,b) => a > b.signal_date ? a : b.signal_date, signals[0].signal_date)}`
    : ''

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-foreground flex items-center gap-2">
          <FlaskConical size={22} className="text-primary" />
          Backtest — Señales Reales
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          {signals.length} señales generadas · {dateRange} · resultados forward-looking (sin hindsight)
        </p>
      </div>

      {/* Info */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-primary/5 border border-primary/20">
        <Info size={14} className="text-primary mt-0.5 shrink-0" />
        <p className="text-xs text-muted-foreground">
          Estas son señales que el sistema generó en tiempo real. Los retornos se calculan desde el precio de la señal.
          Las señales recientes todavía no tienen resultado — se irán completando con el tiempo (7d, 14d, 30d).
        </p>
      </div>

      {/* Strategy filter */}
      <div className="flex gap-2 flex-wrap items-center">
        {['ALL', ...strategies].map(s => (
          <button key={s} onClick={() => setStrat(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
              strat === s ? 'bg-primary/15 border-primary/30 text-primary' : 'bg-muted/20 border-border/30 text-muted-foreground hover:text-foreground'
            }`}>
            {s === 'ALL' ? `Todas (${signals.length})` : `${STRAT_LABEL[s] ?? s} (${signals.filter(x=>x.strategy===s).length})`}
          </button>
        ))}
      </div>

      {/* Period tabs */}
      <div className="flex gap-1 p-1 rounded-xl bg-muted/20 border border-border/30 w-fit">
        {PERIODS.map(p => (
          <button key={p.key} onClick={() => setPeriod(p.key)}
            className={`px-5 py-2 rounded-lg text-xs font-semibold transition-all ${
              period === p.key ? 'bg-background text-foreground shadow-sm border border-border/40' : 'text-muted-foreground hover:text-foreground'
            }`}>
            {p.label}
            {' '}
            <span className="text-muted-foreground/60">
              ({filtered.filter(s => retOf(s, p.key) != null).length})
            </span>
          </button>
        ))}
      </div>

      {/* Stats for current period */}
      <Stats signals={filtered} period={period} />

      {/* Table */}
      <div className="glass rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border/30 text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">
          <button onClick={() => setSort('date')} className={`w-20 shrink-0 text-left hover:text-foreground ${sort==='date'?'text-primary':''}`}>Fecha ↕</button>
          <span className="flex-1 min-w-0">Ticker / Empresa</span>
          <span className="w-24 shrink-0 hidden md:block">Sector</span>
          <button onClick={() => setSort('score')} className={`w-12 text-right shrink-0 hover:text-foreground ${sort==='score'?'text-primary':''}`}>Score ↕</button>
          <span className="w-18 text-right shrink-0">Entrada</span>
          <button onClick={() => setSort('ret')} className={`w-16 text-right shrink-0 hover:text-foreground ${sort==='ret'?'text-primary':''}`}>Ret {period} ↕</button>
          <span className="w-12 text-center shrink-0 hidden sm:block">Res.</span>
        </div>

        {/* Rows with result */}
        {withResult.length > 0 && sorted.filter(s => retOf(s, period) != null).map((s, i) => {
          const ret = retOf(s, period)!
          return (
            <div key={i} className="flex items-center gap-2 px-4 py-2.5 border-b border-border/10 hover:bg-muted/10 transition-colors">
              <span className="w-20 shrink-0 text-[0.7rem] text-muted-foreground/60">{s.signal_date.slice(5)}</span>
              <div className="flex-1 min-w-0">
                <span className="font-mono font-bold text-primary text-[0.85rem]">{s.ticker}</span>
                {s.company_name && <span className="ml-2 text-[0.72rem] text-muted-foreground truncate hidden sm:inline">{s.company_name}</span>}
              </div>
              <span className="w-24 shrink-0 hidden md:block text-[0.7rem] text-muted-foreground truncate">{s.sector}</span>
              <span className={`w-12 text-right shrink-0 text-[0.78rem] font-bold tabular-nums ${s.value_score != null && s.value_score >= 60 ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                {s.value_score != null ? s.value_score.toFixed(0) : '—'}
              </span>
              <span className="w-18 text-right shrink-0 text-[0.75rem] text-muted-foreground tabular-nums">${s.signal_price.toFixed(2)}</span>
              <span className={`w-16 text-right shrink-0 font-bold tabular-nums text-[0.85rem] ${ret >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {pct(ret)}
              </span>
              <span className="w-12 text-center shrink-0 hidden sm:block">
                <span className={`text-[0.62rem] font-bold px-1.5 py-0.5 rounded ${ret > 0 ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                  {ret > 0 ? '↑ WIN' : '↓ LOSS'}
                </span>
              </span>
            </div>
          )
        })}

        {/* Pending rows */}
        {pending.length > 0 && (
          <>
            <div className="px-4 py-2 bg-muted/5 border-b border-border/20">
              <span className="text-[0.65rem] font-bold uppercase tracking-widest text-muted-foreground/50">
                Pendientes — sin resultado a {period} todavía ({pending.length})
              </span>
            </div>
            {sorted.filter(s => retOf(s, period) == null).slice(0, 50).map((s, i) => (
              <div key={i} className="flex items-center gap-2 px-4 py-2 border-b border-border/8 opacity-50">
                <span className="w-20 shrink-0 text-[0.7rem] text-muted-foreground/60">{s.signal_date.slice(5)}</span>
                <div className="flex-1 min-w-0">
                  <span className="font-mono font-bold text-primary text-[0.85rem]">{s.ticker}</span>
                  {s.company_name && <span className="ml-2 text-[0.72rem] text-muted-foreground truncate hidden sm:inline">{s.company_name}</span>}
                </div>
                <span className="w-24 shrink-0 hidden md:block text-[0.7rem] text-muted-foreground truncate">{s.sector}</span>
                <span className={`w-12 text-right shrink-0 text-[0.78rem] font-bold tabular-nums ${s.value_score != null && s.value_score >= 60 ? 'text-emerald-400' : 'text-muted-foreground'}`}>
                  {s.value_score != null ? s.value_score.toFixed(0) : '—'}
                </span>
                <span className="w-18 text-right shrink-0 text-[0.75rem] text-muted-foreground tabular-nums">${s.signal_price.toFixed(2)}</span>
                <span className="w-16 text-right shrink-0 text-[0.75rem] text-muted-foreground/40">pendiente</span>
                <span className="w-12 hidden sm:block" />
              </div>
            ))}
            {pending.length > 50 && (
              <p className="text-center text-xs text-muted-foreground py-2 border-t border-border/20">
                + {pending.length - 50} señales pendientes más
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
