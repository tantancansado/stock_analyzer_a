import { Link } from 'react-router-dom'
import { Zap } from 'lucide-react'
import { fetchBounceBroad, type BounceBroadSetup } from '../api/client'
import { useApi } from '../hooks/useApi'
import Loading, { ErrorState } from '../components/Loading'
import TickerLogo from '../components/TickerLogo'
import EmptyState from '../components/EmptyState'

function Card({ s }: Readonly<{ s: BounceBroadSetup }>) {
  const potentialLoss = Math.abs(s.stop_pct)
  return (
    <div className="glass rounded-2xl p-4 border border-purple-500/20 hover:border-purple-500/40 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <TickerLogo ticker={s.ticker} size="sm" />
          <div>
            <Link to={`/search?q=${s.ticker}`} className="font-mono font-bold text-[0.9rem] text-purple-300 hover:underline">
              {s.ticker}
            </Link>
            <div className="text-[0.65rem] text-muted-foreground/70">SP500 ampliado · {s.horizon_days}d</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[0.9rem] font-bold tabular-nums">${s.price.toFixed(2)}</div>
          <div className="text-[0.62rem] text-muted-foreground/60">R/R <b className="text-purple-300">{s.rr.toFixed(1)}</b></div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-[0.7rem] mb-3">
        <div className="flex flex-col">
          <span className="text-muted-foreground/60 text-[0.6rem] uppercase tracking-wider">Target</span>
          <span className="font-semibold text-emerald-400 tabular-nums">${s.target.toFixed(2)} <span className="text-[0.6rem]">(+{s.target_pct}%)</span></span>
        </div>
        <div className="flex flex-col">
          <span className="text-muted-foreground/60 text-[0.6rem] uppercase tracking-wider">Stop</span>
          <span className="font-semibold text-red-400 tabular-nums">${s.stop.toFixed(2)} <span className="text-[0.6rem]">(-{potentialLoss}%)</span></span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-1.5 text-[0.62rem]">
        <div className="px-2 py-1 rounded bg-red-500/10 text-red-300 border border-red-500/20">RSI2 <b>{s.rsi2}</b></div>
        <div className="px-2 py-1 rounded bg-orange-500/10 text-orange-300 border border-orange-500/20">RSI14 <b>{s.rsi14}</b></div>
        <div className="px-2 py-1 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">Vol <b>{s.vol_ratio.toFixed(1)}×</b></div>
        <div className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">&gt;SMA200</div>
        <div className="px-2 py-1 rounded bg-muted/10 text-muted-foreground border border-border/30">DD {s.drawdown_20d.toFixed(1)}%</div>
        <div className="px-2 py-1 rounded bg-muted/10 text-muted-foreground border border-border/30">ATR {s.atr_pct}%</div>
      </div>
    </div>
  )
}

export default function BroadBounceView() {
  const { data, loading, error } = useApi(() => fetchBounceBroad(), [])

  if (loading) return <Loading />
  if (error) return <ErrorState message={error} />

  const resp = data
  const setups: BounceBroadSetup[] = resp?.setups ?? []
  const universeSize = resp?.universe_size ?? 0
  const scanDate = resp?.scan_date

  return (
    <section className="animate-fade-in-up">
      <div className="mb-5">
        <h2 className="text-xl font-extrabold tracking-tight flex items-center gap-2 text-purple-300">
          <Zap size={18} className="text-purple-400" />
          Rebote corto plazo — Universo Ampliado
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          S&amp;P 500 (excl. universo curado) · Filtros estrictos multi-confirmación · Horizonte 1–5 días
          {scanDate && <span className="text-muted-foreground/40 ml-2">· Scan {scanDate}</span>}
        </p>
        <div className="flex flex-wrap gap-2 mt-3">
          <div className="text-[0.68rem] px-2.5 py-1 rounded-lg bg-purple-500/8 border border-purple-500/20 text-purple-300">
            Universo: <b>{universeSize}</b> tickers
          </div>
          <div className="text-[0.68rem] px-2.5 py-1 rounded-lg bg-purple-500/8 border border-purple-500/20 text-purple-300">
            Setups hoy: <b>{setups.length}</b>
          </div>
          <div className="text-[0.68rem] px-2.5 py-1 rounded-lg bg-muted/10 border border-border/30 text-muted-foreground">
            RSI(2) &le;10 · &gt;SMA200 · Vol &ge;1.3× · R/R &ge;1.5
          </div>
        </div>
      </div>

      {setups.length === 0 ? (
        <EmptyState
          icon="🎯"
          title="Sin setups de alta fiabilidad hoy"
          subtitle="Ningún ticker del universo ampliado cumple los filtros estrictos — menos es más."
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {setups.map(s => <Card key={s.ticker} s={s} />)}
        </div>
      )}
    </section>
  )
}
