import { useState, useEffect } from 'react'
import { fetchContrarianPicks, type ContrarianPick } from '../api/client'
import Loading, { ErrorState } from '../components/Loading'
import TickerLogo from '../components/TickerLogo'
import { TrendingDown, ShieldCheck, AlertTriangle, Eye, RefreshCw } from 'lucide-react'

function VerdictBadge({ verdict, confidence }: Readonly<{ verdict: ContrarianPick['verdict']; confidence: number }>) {
  if (verdict === 'CONTRARIAN_BUY') return (
    <span className="inline-flex items-center gap-1 text-[0.65rem] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
      <ShieldCheck size={10} /> CONTRARIAN BUY · {confidence}%
    </span>
  )
  if (verdict === 'WATCH') return (
    <span className="inline-flex items-center gap-1 text-[0.65rem] font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
      <Eye size={10} /> WATCH · {confidence}%
    </span>
  )
  return (
    <span className="inline-flex items-center gap-1 text-[0.65rem] font-bold px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30">
      <AlertTriangle size={10} /> AVOID · {confidence}%
    </span>
  )
}

function Stat({ label, value, color }: Readonly<{ label: string; value: string; color?: string }>) {
  return (
    <div className="flex flex-col items-center gap-0.5 px-2.5 py-1.5 rounded-lg bg-muted/15 border border-border/20 min-w-[52px]">
      <span className="text-[0.5rem] font-bold uppercase tracking-widest text-muted-foreground/40">{label}</span>
      <span className={`text-[0.8rem] font-bold tabular-nums ${color ?? 'text-foreground/70'}`}>{value}</span>
    </div>
  )
}

function piotroskiColor(v: number) {
  if (v >= 7) return 'text-emerald-400'
  if (v >= 5) return 'text-amber-400'
  return 'text-red-400'
}

function roeColor(v: number) {
  if (v >= 15) return 'text-emerald-400'
  if (v >= 5)  return 'text-amber-400'
  return 'text-red-400'
}

function fcfColor(v: number) {
  if (v >= 5) return 'text-emerald-400'
  if (v > 0)  return 'text-amber-400'
  return 'text-red-400'
}

function marginColor(v: number) {
  if (v >= 15) return 'text-emerald-400'
  if (v >= 5)  return 'text-amber-400'
  return 'text-muted-foreground'
}

const VERDICT_BORDER: Record<ContrarianPick['verdict'], string> = {
  CONTRARIAN_BUY: 'border-emerald-500/20 hover:border-emerald-500/40',
  WATCH:          'border-amber-500/20 hover:border-amber-500/40',
  AVOID:          'border-border/20 hover:border-border/40',
}

function ddColor(drawdown: number) {
  if (drawdown <= -40) return 'text-red-400'
  if (drawdown <= -25) return 'text-amber-400'
  return 'text-orange-400'
}

function PickCard({ pick }: Readonly<{ pick: ContrarianPick }>) {
  return (
    <div className={`rounded-xl border bg-muted/10 p-4 transition-colors ${VERDICT_BORDER[pick.verdict]}`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <TickerLogo ticker={pick.ticker} size="sm" />
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono font-extrabold text-primary text-base">{pick.ticker}</span>
              <VerdictBadge verdict={pick.verdict} confidence={pick.confidence} />
            </div>
            <div className="text-[0.7rem] text-muted-foreground/60 truncate">{pick.company_name}</div>
            {pick.sector && <div className="text-[0.6rem] text-muted-foreground/40">{pick.sector}</div>}
          </div>
        </div>
        <div className="text-right shrink-0">
          {pick.current_price != null && (
            <div className="text-base font-extrabold tabular-nums">${pick.current_price.toFixed(2)}</div>
          )}
          <div className={`text-xs font-bold tabular-nums flex items-center gap-1 justify-end ${ddColor(pick.drawdown_from_52w)}`}>
            <TrendingDown size={11} />
            {pick.drawdown_from_52w.toFixed(1)}% desde máx
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {pick.analyst_upside_pct != null && (
          <Stat label="Upside" value={`+${pick.analyst_upside_pct.toFixed(1)}%`} color="text-emerald-400" />
        )}
        {pick.piotroski_score != null && (
          <Stat label="F-Score" value={`${pick.piotroski_score.toFixed(0)}/9`} color={piotroskiColor(pick.piotroski_score)} />
        )}
        {pick.roe_pct != null && (
          <Stat label="ROE" value={`${pick.roe_pct.toFixed(1)}%`} color={roeColor(pick.roe_pct)} />
        )}
        {pick.fcf_yield_pct != null && (
          <Stat label="FCF%" value={`${pick.fcf_yield_pct.toFixed(1)}%`} color={fcfColor(pick.fcf_yield_pct)} />
        )}
        {pick.profit_margin_pct != null && (
          <Stat label="Margen" value={`${pick.profit_margin_pct.toFixed(1)}%`} color={marginColor(pick.profit_margin_pct)} />
        )}
        {pick.analyst_count != null && (
          <Stat label="Analistas" value={String(pick.analyst_count)} />
        )}
      </div>

      <div className="space-y-2 text-[0.72rem]">
        <div className="flex gap-2">
          <span className="shrink-0 font-semibold text-muted-foreground/50 w-16">Por qué cayó</span>
          <span className="text-foreground/70 leading-relaxed">{pick.drop_reason}</span>
        </div>
        {pick.recovery_thesis && (
          <div className="flex gap-2">
            <span className="shrink-0 font-semibold text-emerald-400/60 w-16">Tesis</span>
            <span className="text-foreground/70 leading-relaxed">{pick.recovery_thesis}</span>
          </div>
        )}
        {pick.key_risks && (
          <div className="flex gap-2">
            <span className="shrink-0 font-semibold text-red-400/60 w-16">Riesgo</span>
            <span className="text-foreground/70 leading-relaxed">{pick.key_risks}</span>
          </div>
        )}
      </div>

      {pick.is_circumstantial && (
        <div className="mt-2.5 inline-flex items-center gap-1 text-[0.6rem] font-medium text-emerald-400/70 bg-emerald-500/8 border border-emerald-500/15 px-2 py-0.5 rounded-full">
          <ShieldCheck size={9} /> Caída circunstancial — fundamentales intactos
        </div>
      )}
    </div>
  )
}

export default function ContrarianDiscovery() {
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchContrarianPicks>>>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetchContrarianPicks()
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading />
  if (error || !data) return <ErrorState message="No se pudo cargar el scanner contrarian" />

  const buys    = data.picks.filter(p => p.verdict === 'CONTRARIAN_BUY')
  const watches = data.picks.filter(p => p.verdict === 'WATCH')
  const avoids  = data.picks.filter(p => p.verdict === 'AVOID')

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-1.5">
          <h3 className="text-lg font-extrabold tracking-tight">Contrarian Discovery</h3>
          <span className="text-[0.65rem] font-bold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
            {data.contrarian_buys} oportunidades
          </span>
        </div>
        <p className="text-[0.72rem] text-muted-foreground/60 max-w-2xl">
          Empresas de calidad del universo curado caídas ≥20% desde máximos por razones circunstanciales —
          fundamentales intactos, analistas ven upside, Piotroski ≥5.
        </p>
        <div className="flex items-center gap-1.5 mt-1.5 text-[0.6rem] text-muted-foreground/40">
          <RefreshCw size={9} />
          Actualizado {new Date(data.generated_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>

      {data.picks.length === 0 && (
        <div className="text-center py-12 text-muted-foreground/50 text-sm">
          Sin candidatos hoy — el universo curado no tiene caídas significativas con fundamentales intactos.
        </div>
      )}

      {buys.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck size={14} className="text-emerald-400" />
            <h4 className="text-[0.7rem] font-bold uppercase tracking-widest text-emerald-400">
              Contrarian Buy ({buys.length})
            </h4>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {buys.map(p => <PickCard key={p.ticker} pick={p} />)}
          </div>
        </section>
      )}

      {watches.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Eye size={14} className="text-amber-400" />
            <h4 className="text-[0.7rem] font-bold uppercase tracking-widest text-amber-400">
              Vigilancia ({watches.length})
            </h4>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {watches.map(p => <PickCard key={p.ticker} pick={p} />)}
          </div>
        </section>
      )}

      {avoids.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={14} className="text-muted-foreground/40" />
            <h4 className="text-[0.7rem] font-bold uppercase tracking-widest text-muted-foreground/40">
              Estructural / Evitar ({avoids.length})
            </h4>
          </div>
          <div className="flex flex-wrap gap-2">
            {avoids.map(p => (
              <span key={p.ticker} className="text-[0.65rem] px-2 py-0.5 rounded-lg bg-muted/15 border border-border/20 text-muted-foreground/50 font-mono">
                {p.ticker}
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
