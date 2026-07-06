import { useState, useEffect } from 'react'
import { fetchLeaps, fetchLeapsTicker, type LeapsData, type LeapsOpportunity, type LeapsContract, type LeapsSituation } from '../api/client'
import PageHeader from '../components/PageHeader'
import TickerLogo from '../components/TickerLogo'
import Loading, { ErrorState } from '../components/Loading'
import StaleDataBanner from '../components/StaleDataBanner'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Rocket, Search, Brain, TrendingUp, Info, Layers, ChevronDown, ChevronUp, Target, RefreshCw, AlertTriangle, Bell, BellRing, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/context/AuthContext'
import { supabase } from '@/lib/supabase'

const fmtUsd = (n: number, d = 2) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: d }).format(n)

const scoreColor = (s: number) =>
  s >= 75 ? 'text-emerald-400' : s >= 60 ? 'text-cyan-400' : s >= 45 ? 'text-amber-400' : 'text-red-400'

const carryColor = (c: number | null) =>
  c == null ? 'text-muted-foreground' : c <= 5 ? 'text-emerald-400' : c <= 9 ? 'text-amber-400' : 'text-red-400'

const SITUATION_CONFIG: Record<LeapsSituation, { label: string; cls: string }> = {
  CAIDA_CIRCUNSTANCIAL: { label: '🎯 Caída circunstancial', cls: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30' },
  CALIDAD_RAZONABLE:    { label: '💎 Calidad a buen precio', cls: 'text-cyan-300 bg-cyan-500/10 border-cyan-500/25' },
  DIP_GANADOR:          { label: '📈 Dip de ganador', cls: 'text-amber-300 bg-amber-500/10 border-amber-500/25' },
  DETERIORO:            { label: '⚠️ Posible deterioro', cls: 'text-red-300 bg-red-500/10 border-red-500/30' },
}

const VERDICT_CONFIG: Record<string, { label: string; cls: string }> = {
  OPORTUNIDAD: { label: 'OPORTUNIDAD', cls: 'text-emerald-400 bg-emerald-500/15 border-emerald-500/40' },
  RAZONABLE:   { label: 'RAZONABLE',   cls: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30' },
  EVITAR:      { label: 'EVITAR',      cls: 'text-red-400 bg-red-500/15 border-red-500/40' },
}

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

function StrikeComparator({ contracts, bestStrike }: { contracts: LeapsContract[]; bestStrike: number }) {
  const rows = [...contracts].sort((a, b) => a.strike - b.strike)
  return (
    <div className="mt-3 table-x-wrap rounded-md border border-border/30">
      <table className="w-full text-[0.68rem] tabular-nums">
        <thead>
          <tr className="text-muted-foreground/60 text-left">
            <th className="font-normal px-2 py-1.5">Strike</th>
            <th className="font-normal px-2 py-1.5">Δ</th>
            <th className="font-normal px-2 py-1.5">Lev</th>
            <th className="font-normal px-2 py-1.5">Coste/a</th>
            <th className="font-normal px-2 py-1.5">B/E</th>
            <th className="font-normal px-2 py-1.5">@target</th>
            <th className="font-normal px-2 py-1.5">Coste</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => {
            const isBest = r.strike === bestStrike
            return (
              <tr key={`${r.expiry}-${r.strike}`} className={cn('border-t border-border/20', isBest && 'bg-primary/10')}>
                <td className="px-2 py-1.5 font-bold">
                  ${r.strike.toFixed(0)}
                  {isBest && <span className="ml-1.5 text-[0.55rem] text-primary font-extrabold">★ MEJOR</span>}
                </td>
                <td className="px-2 py-1.5 text-cyan-300">{r.delta?.toFixed(2) ?? '—'}</td>
                <td className="px-2 py-1.5">{r.leverage ? `${r.leverage.toFixed(1)}x` : '—'}</td>
                <td className={cn('px-2 py-1.5', carryColor(r.total_annual_cost_pct ?? r.annual_carry_pct))}>{(r.total_annual_cost_pct ?? r.annual_carry_pct) != null ? `${(r.total_annual_cost_pct ?? r.annual_carry_pct)!.toFixed(1)}%` : '—'}</td>
                <td className="px-2 py-1.5">{r.breakeven_move_pct != null ? `${r.breakeven_move_pct >= 0 ? '+' : ''}${r.breakeven_move_pct.toFixed(1)}%` : '—'}</td>
                <td className="px-2 py-1.5 text-emerald-400 font-semibold">+{r.target_return_pct?.toFixed(0)}%</td>
                <td className="px-2 py-1.5 text-muted-foreground">{fmtUsd(r.cost_per_contract, 0)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <div className="px-2 py-1.5 text-[0.6rem] text-muted-foreground/50 border-t border-border/20">
        Mismo vencimiento ({rows[0]?.expiry}). Más deep (strike bajo) = menos carry/riesgo, menos leverage. La marcada ★ es la de mejor equilibrio.
      </div>
    </div>
  )
}

type TrackState = 'idle' | 'saving' | 'done' | 'login' | 'error'

function OpportunityCard({ o, rank }: { o: LeapsOpportunity; rank?: number }) {
  const c = o.recommended_contract
  const pat = o.profit_at_target
  const ex = o.exit_plan
  const alts = o.alternative_contracts ?? []
  const [showStrikes, setShowStrikes] = useState(false)
  const { user } = useAuth()
  const [track, setTrack] = useState<TrackState>('idle')

  async function followLeaps() {
    if (!user) { setTrack('login'); return }
    setTrack('saving')
    const { error } = await supabase.from('personal_portfolio_positions').insert({
      user_id: user.id, ticker: o.ticker, shares: 1, avg_price: c.mid, currency: 'USD',
      asset_type: 'option', option_type: 'call', option_strike: c.strike, option_expiry: c.expiry,
    })
    setTrack(error ? 'error' : 'done')
  }

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
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-extrabold tracking-tight">{o.ticker}</span>
                {o.in_value_list && <Badge variant="green" className="text-[0.6rem]">VALUE</Badge>}
                {o.conviction_grade && <Badge variant="blue" className="text-[0.6rem]">{o.conviction_grade}</Badge>}
                {o.situation && SITUATION_CONFIG[o.situation] && (
                  <span className={cn('text-[0.6rem] font-semibold px-1.5 py-0.5 rounded border', SITUATION_CONFIG[o.situation].cls)}>
                    {SITUATION_CONFIG[o.situation].label}
                  </span>
                )}
              </div>
              <div className="text-xs text-muted-foreground truncate">{o.company_name}</div>
              {(o.pct_from_52w_high != null || o.ytd_pct != null || o.forward_pe != null) && (
                <div className="text-[0.65rem] text-muted-foreground/60 mt-0.5">
                  {o.pct_from_52w_high != null && <span>{o.pct_from_52w_high.toFixed(0)}% desde máx. 52s</span>}
                  {o.pct_from_52w_high != null && o.ytd_pct != null && <span> · </span>}
                  {o.ytd_pct != null && <span>YTD {o.ytd_pct >= 0 ? '+' : ''}{o.ytd_pct.toFixed(0)}%</span>}
                  {o.forward_pe != null && <span> · P/E {o.forward_pe.toFixed(0)}</span>}
                </div>
              )}
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className={cn('text-2xl font-extrabold tabular-nums leading-none', scoreColor(o.opportunity_score))}>
              {o.opportunity_score.toFixed(0)}
            </div>
            <div className="text-[0.6rem] uppercase tracking-widest text-muted-foreground/50">score</div>
          </div>
        </div>

        {/* Earnings inminentes: la IV está inflada — mejor esperar al evento */}
        {o.earnings_warning && (
          <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 mb-3 text-xs text-amber-300 flex items-start gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span><strong>Earnings en {o.days_to_earnings} días</strong> — la IV suele estar inflada antes del evento; comprar el LEAPS ahora es pagar de más. Valora esperar a después.</span>
          </div>
        )}

        {/* Aviso de datos dudosos (verificación de Claude) */}
        {o.data_warning && (
          <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 mb-3 text-xs text-amber-300 flex items-start gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span><strong>Datos a verificar:</strong> {o.data_warning}</span>
          </div>
        )}

        {/* Claude's honest verdict: ¿oportunidad value real o no? */}
        {o.situation_verdict && VERDICT_CONFIG[o.situation_verdict.verdict] && (
          <div className={cn('rounded-md border px-3 py-2 mb-3', VERDICT_CONFIG[o.situation_verdict.verdict].cls)}>
            <div className="flex items-center gap-1.5 text-[0.7rem] font-extrabold tracking-wide mb-0.5">
              <Brain className="w-3 h-3" /> VEREDICTO: {VERDICT_CONFIG[o.situation_verdict.verdict].label}
            </div>
            {o.situation_verdict.reason && (
              <div className="text-xs opacity-90 leading-snug">{o.situation_verdict.reason}</div>
            )}
          </div>
        )}

        {/* The recommended order — the headline */}
        <div className="rounded-md bg-primary/5 border border-primary/20 px-3 py-2.5 mb-3">
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="text-[0.62rem] uppercase tracking-widest text-primary/70 flex items-center gap-1">
              <Rocket className="w-3 h-3" /> Contrato recomendado
            </div>
            <button
              onClick={followLeaps}
              disabled={track === 'saving' || track === 'done'}
              className={cn(
                'flex items-center gap-1 text-[0.62rem] font-semibold px-2 py-1 rounded border transition-colors',
                track === 'done'
                  ? 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10'
                  : 'border-primary/30 text-primary hover:bg-primary/15'
              )}
              title="Guardar este LEAPS y recibir alertas (rolar, tomar beneficios, tesis rota)"
            >
              {track === 'done'
                ? (<><Check className="w-3 h-3" /> Siguiendo</>)
                : track === 'saving'
                  ? (<><BellRing className="w-3 h-3 animate-pulse" /> Guardando…</>)
                  : (<><Bell className="w-3 h-3" /> Seguir</>)}
            </button>
          </div>
          <div className="font-bold text-sm leading-snug">
            COMPRAR 1× CALL <span className="text-primary">{o.ticker} ${c.strike.toFixed(0)}</span> · exp {c.expiry}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            Prima ≈ <span className="text-foreground font-semibold">{fmtUsd(c.mid)}</span>/acción ·
            {' '}<span className="text-foreground font-semibold">{fmtUsd(c.cost_per_contract, 0)}</span> por contrato (100 acc.) ·
            {' '}límite sugerido ≤ {fmtUsd(c.ask)}
          </div>
          {track === 'login' && <div className="text-[0.65rem] text-amber-400 mt-1">Inicia sesión para guardar y recibir alertas de esta posición.</div>}
          {track === 'error' && <div className="text-[0.65rem] text-red-400 mt-1">No se pudo guardar. Inténtalo de nuevo.</div>}
          {track === 'done' && <div className="text-[0.65rem] text-emerald-400 mt-1">Guardado en tu cartera. Te avisaré por Telegram si toca rolar, tomar beneficios o la tesis se rompe.</div>}
        </div>

        {/* Metrics grid */}
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-3">
          <Metric label="Acción" value={fmtUsd(o.spot)} />
          <Metric label="Delta" value={c.delta?.toFixed(2) ?? '—'} hint="Cuánto sigue a la acción (1.0 = idéntico)" className="text-cyan-300" />
          <Metric label="Leverage" value={c.leverage ? `${c.leverage.toFixed(1)}x` : '—'} hint="Exposición controlada ÷ capital invertido" />
          <Metric
            label="Coste/año"
            value={(c.total_annual_cost_pct ?? c.annual_carry_pct) != null ? `${(c.total_annual_cost_pct ?? c.annual_carry_pct)!.toFixed(1)}%` : '—'}
            hint={`Coste REAL de tener la call en vez de la acción: carry ${c.annual_carry_pct?.toFixed(1) ?? '?'}% + dividendo renunciado ${c.forgone_dividend_pct?.toFixed(1) ?? '0'}% (la call no cobra el dividendo)`}
            className={carryColor(c.total_annual_cost_pct ?? c.annual_carry_pct)}
          />
          <Metric label="Break-even" value={fmtUsd(c.breakeven)} hint="Precio al que empatas al vencimiento" />
          <Metric label="B/E move" value={c.breakeven_move_pct != null ? `${c.breakeven_move_pct >= 0 ? '+' : ''}${c.breakeven_move_pct.toFixed(1)}%` : '—'} hint="Cuánto debe subir la acción para empatar" />
        </div>

        <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-3 text-muted-foreground">
          <Metric label="Calidad" value={o.quality_score?.toFixed(0) ?? '—'} className={o.quality_score ? scoreColor(o.quality_score) : ''} />
          <Metric label="Momento" value={o.timing_score.toFixed(0)} className={scoreColor(o.timing_score)} />
          <Metric label="Upside" value={o.analyst_upside_pct != null ? `${o.analyst_upside_pct.toFixed(0)}%` : '—'} />
          <Metric label="Extrínseco" value={c.extrinsic_pct != null ? `${c.extrinsic_pct.toFixed(1)}%` : '—'} hint="Prima temporal sobre el precio de la acción" />
          <Metric
            label="IV vs real"
            value={c.iv_richness ? (
              <span className={c.iv_richness === 'cara' ? 'text-red-400' : c.iv_richness === 'barata' ? 'text-emerald-400' : ''}>
                {c.iv_pct.toFixed(0)}% · {c.iv_richness}
              </span>
            ) : `${c.iv_pct.toFixed(0)}%`}
            hint={`IV ${c.iv_pct.toFixed(0)}% vs volatilidad realizada 1a ${o.hv_1y_pct?.toFixed(0) ?? '?'}% (ratio ${c.iv_vs_hv ?? '?'}). Compras 2+ años de vega: si la IV está cara, pagas volatilidad que la acción no muestra`}
          />
          <Metric
            label="Salida (spread)"
            value={c.roundtrip_spread_usd != null ? fmtUsd(c.roundtrip_spread_usd, 0) : `${c.spread_pct.toFixed(0)}%`}
            hint={`Coste de cruzar el spread ida+vuelta por contrato (OI ${c.open_interest}, volumen diario ${c.volume ?? 0}, spread ${c.spread_pct.toFixed(1)}%). Con volumen ~0 este número manda más que el OI`}
            className={c.roundtrip_spread_usd != null && c.roundtrip_spread_usd > 300 ? 'text-amber-400' : ''}
          />
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

        {/* Exit plan (Claude): cuándo vender / rolar / qué rompe la tesis */}
        {ex && (ex.take_profit || ex.roll || ex.thesis_break) && (
          <div className="mt-3 grid gap-2 sm:grid-cols-3 text-[0.7rem] leading-snug">
            {ex.take_profit && (
              <div className="rounded-md bg-emerald-500/5 border border-emerald-500/20 px-2.5 py-2">
                <div className="flex items-center gap-1 text-emerald-400 font-semibold mb-0.5"><Target className="w-3 h-3" /> Tomar beneficios</div>
                <div className="text-muted-foreground/90">{ex.take_profit}</div>
              </div>
            )}
            {ex.roll && (
              <div className="rounded-md bg-cyan-500/5 border border-cyan-500/20 px-2.5 py-2">
                <div className="flex items-center gap-1 text-cyan-400 font-semibold mb-0.5"><RefreshCw className="w-3 h-3" /> Cuándo rolar</div>
                <div className="text-muted-foreground/90">{ex.roll}</div>
              </div>
            )}
            {ex.thesis_break && (
              <div className="rounded-md bg-red-500/5 border border-red-500/20 px-2.5 py-2">
                <div className="flex items-center gap-1 text-red-400 font-semibold mb-0.5"><AlertTriangle className="w-3 h-3" /> Tesis rota</div>
                <div className="text-muted-foreground/90">{ex.thesis_break}</div>
              </div>
            )}
          </div>
        )}

        {/* Strike comparator */}
        {alts.length > 0 && (
          <div className="mt-3 border-t border-border/30 pt-2.5">
            <button
              onClick={() => setShowStrikes(v => !v)}
              className="flex items-center gap-1.5 text-[0.7rem] font-semibold text-muted-foreground hover:text-primary transition-colors"
            >
              <Layers className="w-3 h-3" />
              Comparar strikes ({alts.length + 1})
              {showStrikes ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            {showStrikes && <StrikeComparator contracts={[c, ...alts]} bestStrike={c.strike} />}
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
  const [sitFilter, setSitFilter] = useState<LeapsSituation | 'ALL'>('ALL')

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
        (<em>carry</em>). Es la <strong className="text-foreground">filosofía value aplicada a LEAPS</strong>: buenas
        empresas baratas por circunstancia o ciclo (no por deterioro). Claude da un veredicto honesto por cada una
        — y el ranking premia justo ese tipo de oportunidad. Las empresas con <strong className="text-foreground">múltiplo
        caro</strong> (forward P/E &gt; 30) ni se muestran: no son value, y con apalancamiento el margen de seguridad importa más.
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
          <div className="flex items-center justify-between mb-2 mt-1">
            <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground/60">
              Mejores oportunidades ({data.opportunities.length})
            </h2>
            <span className="text-[0.65rem] text-muted-foreground/50">
              tipo libre de riesgo {data.risk_free_rate_pct}% · {data.analyzed} analizadas de {data.universe_size}
            </span>
          </div>

          {/* Filtro por situación (tu filosofía value) */}
          <div className="flex flex-wrap gap-1.5 mb-3">
            {([['ALL', 'Todas'], ['CAIDA_CIRCUNSTANCIAL', '🎯 Caída circunstancial'], ['CALIDAD_RAZONABLE', '💎 Calidad a buen precio'], ['DIP_GANADOR', '📈 Dip de ganador']] as const).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setSitFilter(key as LeapsSituation | 'ALL')}
                className={`filter-btn ${sitFilter === key ? 'active' : ''}`}
              >
                {label}
              </button>
            ))}
          </div>

          {(() => {
            const shown = sitFilter === 'ALL' ? data.opportunities : data.opportunities.filter(o => o.situation === sitFilter)
            if (data.opportunities.length === 0) {
              return <div className="text-sm text-muted-foreground text-center py-10">No hay oportunidades LEAPS que cumplan los criterios hoy. Vuelve tras el próximo scan diario.</div>
            }
            if (shown.length === 0) {
              return <div className="text-sm text-muted-foreground text-center py-10">Ninguna oportunidad de este tipo hoy. Prueba otro filtro.</div>
            }
            return (
              <div className="space-y-3">
                {shown.map((o, i) => <OpportunityCard key={o.ticker} o={o} rank={i + 1} />)}
              </div>
            )
          })()}
        </>
      )}
    </div>
  )
}
