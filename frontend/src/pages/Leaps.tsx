import { useState, useEffect } from 'react'
import { fetchLeaps, fetchLeapsTicker, type LeapsData, type LeapsOpportunity } from '../api/client'
import PageHeader from '../components/PageHeader'
import TickerLogo from '../components/TickerLogo'
import Loading, { ErrorState } from '../components/Loading'
import StaleDataBanner from '../components/StaleDataBanner'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Rocket, Search, Brain, TrendingUp, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

const fmtUsd = (n: number, d = 2) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: d }).format(n)

const scoreColor = (s: number) =>
  s >= 75 ? 'text-emerald-400' : s >= 60 ? 'text-cyan-400' : s >= 45 ? 'text-amber-400' : 'text-red-400'

const carryColor = (c: number | null) =>
  c == null ? 'text-muted-foreground' : c <= 5 ? 'text-emerald-400' : c <= 9 ? 'text-amber-400' : 'text-red-400'

function Metric({ label, value, hint, className }: { label: string; value: React.ReactNode; hint?: string; className?: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground/60 mb-0.5 flex items-center gap-1">
        {label}{hint && <span title={hint}><Info className="w-2.5 h-2.5 opacity-40" /></span>}
      </div>
      <div className={cn('text-sm font-bold tabular-nums leading-none', className)}>{value}</div>
    </div>
  )
}

function OpportunityCard({ o, rank }: { o: LeapsOpportunity; rank?: number }) {
  const c = o.recommended_contract
  const pat = o.profit_at_target
  return (
    <Card className="glass border border-border/40 hover:border-primary/30 transition-colors">
      <CardContent className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-3 min-w-0">
            {rank != null && (
              <span className="text-lg font-extrabold text-muted-foreground/40 tabular-nums w-6 shrink-0">{rank}</span>
            )}
            <TickerLogo ticker={o.ticker} size="md" />
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-extrabold tracking-tight">{o.ticker}</span>
                {o.in_value_list && <Badge variant="green" className="text-[0.6rem]">VALUE</Badge>}
                {o.conviction_grade && <Badge variant="blue" className="text-[0.6rem]">{o.conviction_grade}</Badge>}
              </div>
              <div className="text-xs text-muted-foreground truncate">{o.company_name}</div>
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className={cn('text-2xl font-extrabold tabular-nums leading-none', scoreColor(o.opportunity_score))}>
              {o.opportunity_score.toFixed(0)}
            </div>
            <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground/50">score</div>
          </div>
        </div>

        {/* The recommended order — the headline */}
        <div className="rounded-md bg-primary/5 border border-primary/20 px-3 py-2.5 mb-3">
          <div className="text-[0.62rem] uppercase tracking-widest text-primary/70 mb-1 flex items-center gap-1">
            <Rocket className="w-3 h-3" /> Contrato recomendado
          </div>
          <div className="font-bold text-sm leading-snug">
            COMPRAR 1× CALL <span className="text-primary">{o.ticker} ${c.strike.toFixed(0)}</span> · exp {c.expiry}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            Prima ≈ <span className="text-foreground font-semibold">{fmtUsd(c.mid)}</span>/acción ·
            {' '}<span className="text-foreground font-semibold">{fmtUsd(c.cost_per_contract, 0)}</span> por contrato (100 acc.) ·
            {' '}límite sugerido ≤ {fmtUsd(c.ask)}
          </div>
        </div>

        {/* Metrics grid */}
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-3">
          <Metric label="Acción" value={fmtUsd(o.spot)} />
          <Metric label="Delta" value={c.delta?.toFixed(2) ?? '—'} hint="Cuánto sigue a la acción (1.0 = idéntico)" className="text-cyan-300" />
          <Metric label="Leverage" value={c.leverage ? `${c.leverage.toFixed(1)}x` : '—'} hint="Exposición controlada ÷ capital invertido" />
          <Metric label="Carry/año" value={c.annual_carry_pct != null ? `${c.annual_carry_pct.toFixed(1)}%` : '—'} hint="Coste temporal anualizado del apalancamiento" className={carryColor(c.annual_carry_pct)} />
          <Metric label="Break-even" value={fmtUsd(c.breakeven)} hint="Precio al que empatas al vencimiento" />
          <Metric label="B/E move" value={c.breakeven_move_pct != null ? `${c.breakeven_move_pct >= 0 ? '+' : ''}${c.breakeven_move_pct.toFixed(1)}%` : '—'} hint="Cuánto debe subir la acción para empatar" />
        </div>

        <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-3 text-muted-foreground">
          <Metric label="Calidad" value={o.quality_score?.toFixed(0) ?? '—'} className={o.quality_score ? scoreColor(o.quality_score) : ''} />
          <Metric label="Momento" value={o.timing_score.toFixed(0)} className={scoreColor(o.timing_score)} />
          <Metric label="Upside" value={o.analyst_upside_pct != null ? `${o.analyst_upside_pct.toFixed(0)}%` : '—'} />
          <Metric label="Extrínseco" value={c.extrinsic_pct != null ? `${c.extrinsic_pct.toFixed(1)}%` : '—'} hint="Prima temporal sobre el precio de la acción" />
          <Metric label="IV" value={`${c.iv_pct.toFixed(0)}%`} hint="Volatilidad implícita" />
          <Metric label="Liquidez" value={`OI ${c.open_interest} · ${c.spread_pct.toFixed(0)}%`} hint="Open interest y spread bid/ask" />
        </div>

        {/* Profit scenario at analyst target */}
        {pat && (
          <div className="rounded-md bg-emerald-500/5 border border-emerald-500/20 px-3 py-2 mb-3 text-xs">
            <span className="text-emerald-400 font-semibold inline-flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> Si llega al target {fmtUsd(pat.target_price)}:
            </span>{' '}
            el LEAPS rinde <span className="font-bold text-emerald-400">{pat.option_return_pct >= 0 ? '+' : ''}{pat.option_return_pct.toFixed(0)}%</span>{' '}
            vs <span className="text-foreground">{pat.stock_return_pct >= 0 ? '+' : ''}{pat.stock_return_pct.toFixed(0)}%</span> la acción
            {pat.leverage_realized != null && <span className="text-muted-foreground"> ({pat.leverage_realized.toFixed(1)}x)</span>}
          </div>
        )}

        {/* AI narrative */}
        {o.ai_narrative && (
          <div className="text-xs text-muted-foreground/90 leading-relaxed border-t border-border/30 pt-2.5">
            <span className="inline-flex items-center gap-1 text-primary/70 font-semibold mr-1">
              <Brain className="w-3 h-3" />
            </span>
            {o.ai_narrative}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function Leaps() {
  const [data, setData] = useState<LeapsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [query, setQuery] = useState('')
  const [onDemand, setOnDemand] = useState<LeapsOpportunity | null>(null)
  const [odLoading, setOdLoading] = useState(false)
  const [odError, setOdError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchLeaps()
      .then(d => { if (!cancelled) { if (d) setData(d); else setError(true) } })
      .catch(() => { if (!cancelled) setError(true) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  async function runOnDemand(e: React.FormEvent) {
    e.preventDefault()
    const t = query.trim().toUpperCase()
    if (!t) return
    setOdLoading(true); setOdError(null); setOnDemand(null)
    try {
      const res = await fetchLeapsTicker(t)
      if (res.error) setOdError(res.error)
      else setOnDemand(res)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error
      setOdError(msg || `No se pudo analizar ${t}. Puede no tener LEAPS líquidos.`)
    } finally {
      setOdLoading(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <PageHeader
        title={<span className="flex items-center gap-2"><Rocket className="w-6 h-6 text-purple-400" /> LEAPS deep-ITM</span>}
        subtitle="Calls largas (2027-2028) como sustituto apalancado de acciones — empresas de calidad en buen momento, no especulación"
      />

      {/* What is this */}
      <div className="rounded-lg bg-muted/10 border border-border/30 px-4 py-3 mb-5 text-xs text-muted-foreground leading-relaxed">
        Un <strong className="text-foreground">LEAPS deep-in-the-money</strong> (delta ~0.80) replica casi 1:1 el
        movimiento de la acción con ~2x apalancamiento y menos capital, pagando una pequeña prima temporal
        (<em>carry</em>). Solo tiene sentido sobre negocios buenos con tesis intacta. El ranking cruza calidad
        fundamental + momento técnico + métricas del contrato (carry barato, delta sano, liquidez).
      </div>

      {/* On-demand search */}
      <form onSubmit={runOnDemand} className="flex gap-2 mb-5">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/50" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Analiza cualquier ticker en vivo (ej. UBER, GOOGL, AMZN)…"
            className="w-full bg-background/60 border border-border/40 rounded-md pl-9 pr-3 py-2 text-sm focus:border-primary/50 focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={odLoading}
          className="px-4 py-2 rounded-md bg-primary/15 border border-primary/30 text-primary text-sm font-semibold hover:bg-primary/25 transition-colors disabled:opacity-50"
        >
          {odLoading ? 'Analizando…' : 'Analizar'}
        </button>
      </form>

      {odError && (
        <div className="rounded-md bg-red-500/10 border border-red-500/25 text-red-300 text-xs px-3 py-2 mb-5">{odError}</div>
      )}
      {onDemand && (
        <div className="mb-6">
          <div className="text-[0.65rem] uppercase tracking-widest text-muted-foreground/60 mb-2">Análisis en vivo</div>
          <OpportunityCard o={onDemand} />
        </div>
      )}

      {/* Ranked list */}
      {loading && <Loading />}
      {error && <ErrorState message="No se pudo cargar el ranking LEAPS" />}
      {data && (
        <>
          <StaleDataBanner dataDate={data.generated_at?.slice(0, 10)} />
          <div className="flex items-center justify-between mb-3 mt-1">
            <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground/60">
              Mejores oportunidades ({data.opportunities.length})
            </h2>
            <span className="text-[0.65rem] text-muted-foreground/50">
              tipo libre de riesgo {data.risk_free_rate_pct}% · {data.analyzed} analizadas de {data.universe_size}
            </span>
          </div>
          {data.opportunities.length === 0 ? (
            <div className="text-sm text-muted-foreground text-center py-10">
              No hay oportunidades LEAPS que cumplan los criterios hoy. Vuelve tras el próximo scan diario.
            </div>
          ) : (
            <div className="space-y-3">
              {data.opportunities.map((o, i) => (
                <OpportunityCard key={o.ticker} o={o} rank={i + 1} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
