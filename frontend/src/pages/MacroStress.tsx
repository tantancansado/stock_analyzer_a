import { AlertTriangle, ArrowUpRight, Gauge, Sparkles } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { fetchMacroStress, type MacroStressMarket, type MacroStressResponse } from '../api/client'
import { useApi } from '../hooks/useApi'
import Loading, { ErrorState } from '../components/Loading'
import StaleDataBanner from '../components/StaleDataBanner'

const BAND_STYLES: Record<string, { badge: string; bar: string; copy: string }> = {
  CALM: {
    badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    bar: 'from-emerald-500 to-teal-400',
    copy: 'Normalidad operativa',
  },
  WATCH: {
    badge: 'bg-lime-500/15 text-lime-300 border-lime-500/30',
    bar: 'from-lime-500 to-emerald-400',
    copy: 'Vigilancia activa',
  },
  STRESS: {
    badge: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    bar: 'from-amber-500 to-orange-400',
    copy: 'Estrés creciente',
  },
  ALERT: {
    badge: 'bg-orange-500/15 text-orange-300 border-orange-500/30',
    bar: 'from-orange-500 to-red-400',
    copy: 'Dislocación relevante',
  },
  CRISIS: {
    badge: 'bg-red-500/15 text-red-300 border-red-500/30',
    bar: 'from-red-500 to-fuchsia-500',
    copy: 'Riesgo sistémico alto',
  },
}

function bandStyle(band?: string) {
  return BAND_STYLES[(band || '').toUpperCase()] ?? {
    badge: 'bg-muted/20 text-muted-foreground border-border/30',
    bar: 'from-slate-500 to-slate-400',
    copy: 'Lectura parcial',
  }
}

function formatScore(score: number | null | undefined) {
  return score == null ? 'N/A' : score.toFixed(1)
}

function ScoreBar({ score, band }: { score: number | null | undefined; band: string }) {
  const pct = score == null ? 0 : Math.max(0, Math.min(100, score))
  const style = bandStyle(band)
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[0.62rem] uppercase tracking-[0.16em] text-muted-foreground/60">
        <span>Stress Score</span>
        <span className="font-bold text-foreground/80">{formatScore(score)} / 100</span>
      </div>
      <div className="h-2 rounded-full bg-white/8 overflow-hidden">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${style.bar} transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function ExposureChip({ label, tone }: { label: string; tone: 'long' | 'short' }) {
  const cls = tone === 'long'
    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
    : 'bg-red-500/10 text-red-300 border-red-500/20'
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[0.66rem] font-semibold ${cls}`}>
      {label}
    </span>
  )
}

function SignalTile({ name, signal }: { name: string; signal: MacroStressMarket['signals'][string] }) {
  const score = signal?.score
  const tone = score == null
    ? 'text-muted-foreground/55 border-border/20 bg-muted/10'
    : score >= 70
      ? 'text-red-300 border-red-500/25 bg-red-500/10'
      : score >= 45
        ? 'text-amber-300 border-amber-500/25 bg-amber-500/10'
        : 'text-emerald-300 border-emerald-500/20 bg-emerald-500/10'
  return (
    <div className={`rounded-xl border p-3 ${tone}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[0.62rem] uppercase tracking-[0.16em]">{name.replaceAll('_', ' ')}</span>
        <span className="font-mono text-sm font-bold">{formatScore(score)}</span>
      </div>
      <div className="mt-1 text-[0.72rem] text-foreground/70">
        peso {signal?.weight != null ? `${Math.round(signal.weight * 100)}%` : 'N/A'}
      </div>
    </div>
  )
}

function MarketCard({ marketId, market }: { marketId: string; market: MacroStressMarket }) {
  const style = bandStyle(market.band)
  const longs = market.equity_exposure?.long_benefits ?? []
  const shorts = market.equity_exposure?.short_benefits ?? []
  const analogues = market.analogues?.analogues ?? []

  return (
    <Card className="glass border-white/10 overflow-hidden">
      <CardContent className="p-0">
        <div className="relative px-5 py-5 border-b border-white/10 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.08),transparent_42%),linear-gradient(135deg,rgba(255,255,255,0.03),transparent)]">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/35 to-transparent" />
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[0.62rem] uppercase tracking-[0.22em] text-primary/70 font-bold">
                  {market.category ?? 'macro'}
                </span>
                <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[0.68rem] font-bold ${style.badge}`}>
                  {market.band}
                </span>
              </div>
              <h3 className="text-2xl font-black tracking-tight text-foreground">{market.name}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {style.copy} {market.primary_ticker ? `· driver principal ${market.primary_ticker}` : ''}
              </p>
            </div>
            <div className="w-full max-w-sm space-y-3">
              <ScoreBar score={market.stress_score} band={market.band} />
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5">
                  <div className="text-[0.58rem] uppercase tracking-[0.16em] text-muted-foreground/60">Market ID</div>
                  <div className="mt-1 font-mono text-sm font-bold text-foreground/80">{marketId}</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5">
                  <div className="text-[0.58rem] uppercase tracking-[0.16em] text-muted-foreground/60">Signals used</div>
                  <div className="mt-1 text-sm font-bold text-foreground/80">{market.signals_used ?? 0}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-5 p-5 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            <div>
              <div className="mb-3 flex items-center gap-2 text-[0.68rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/70">
                <Gauge size={13} className="text-primary" />
                Signal Breakdown
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                {Object.entries(market.signals || {}).map(([name, signal]) => (
                  <SignalTile key={name} name={name} signal={signal} />
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="mb-3 flex items-center gap-2 text-[0.68rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/70">
                <ArrowUpRight size={13} className="text-cyan-300" />
                Equity Map
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <div className="mb-2 text-[0.62rem] uppercase tracking-[0.16em] text-muted-foreground/55">Long benefits</div>
                  <div className="flex flex-wrap gap-1.5">
                    {longs.length > 0 ? longs.map(ticker => <ExposureChip key={ticker} label={ticker} tone="long" />) : (
                      <span className="text-sm text-muted-foreground/50">No definido</span>
                    )}
                  </div>
                </div>
                <div>
                  <div className="mb-2 text-[0.62rem] uppercase tracking-[0.16em] text-muted-foreground/55">Short / losers</div>
                  <div className="flex flex-wrap gap-1.5">
                    {shorts.length > 0 ? shorts.map(ticker => <ExposureChip key={ticker} label={ticker} tone="short" />) : (
                      <span className="text-sm text-muted-foreground/50">No definido</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-primary/8 to-transparent p-4">
              <div className="mb-3 flex items-center gap-2 text-[0.68rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/70">
                <Sparkles size={13} className="text-primary" />
                Historical Analogues
              </div>
              {analogues.length > 0 ? (
                <div className="space-y-3">
                  {analogues.slice(0, 3).map((item, idx) => (
                    <div key={idx} className="rounded-xl border border-white/10 bg-black/10 px-3 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-semibold text-foreground/85">{String((item as { name?: string }).name ?? `Analog ${idx + 1}`)}</div>
                        <div className="text-xs font-bold text-primary">
                          {typeof (item as { similarity?: number }).similarity === 'number'
                            ? `${Math.round(((item as { similarity: number }).similarity) * 100)}% sim`
                            : 'sim N/A'}
                        </div>
                      </div>
                      {typeof (item as { date?: string }).date === 'string' && (
                        <div className="mt-1 text-[0.7rem] text-muted-foreground/65">
                          {(item as { date: string }).date}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground/60">
                  Aún no hay histórico suficiente para analogías robustas. El framework ya deja preparado el replay futuro.
                </p>
              )}
              {market.analogues?.note && (
                <p className="mt-3 text-[0.72rem] text-muted-foreground/55">{market.analogues.note}</p>
              )}
            </div>

            <div className="rounded-2xl border border-amber-500/20 bg-amber-500/8 p-4">
              <div className="mb-2 flex items-center gap-2 text-[0.68rem] font-bold uppercase tracking-[0.18em] text-amber-300/90">
                <AlertTriangle size={13} />
                Reading Guide
              </div>
              <p className="text-sm leading-relaxed text-foreground/78">
                Este radar no intenta predecir el precio diario del activo. Sirve para detectar dislocaciones macro antes de que
                se filtren a equities sensibles: energía, transporte, industriales o consumidores de input cost.
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function MacroStress() {
  const { data, loading, error } = useApi<MacroStressResponse>(() => fetchMacroStress(), [])

  if (loading) return <Loading />
  if (error) {
    const friendly = error.includes('404')
      ? 'Macro Stress Radar aún no está generado. Se poblará cuando corra el pipeline diario.'
      : error
    return <ErrorState message={friendly} />
  }
  if (!data?.markets || Object.keys(data.markets).length === 0) {
    return <ErrorState message="No hay mercados configurados todavía." />
  }

  const markets = Object.entries(data.markets)
    .sort((a, b) => (b[1].stress_score ?? -1) - (a[1].stress_score ?? -1))

  return (
    <div className="space-y-5">
      <StaleDataBanner module="macro_stress" />

      <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.06),rgba(255,255,255,0.01)),radial-gradient(circle_at_top_right,rgba(255,115,0,0.18),transparent_28%),radial-gradient(circle_at_bottom_left,rgba(14,165,233,0.14),transparent_26%)] px-5 py-6">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/35 to-transparent" />
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-2 text-[0.68rem] font-bold uppercase tracking-[0.24em] text-primary/75">Commodity dislocations</div>
            <h2 className="text-3xl font-black tracking-tight text-foreground">Macro Stress Radar</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Marco declarativo para vigilar shocks macro con lectura operativa en equities. La idea es detectar tensión real
              en inventarios, curva, geopolítica y positioning antes de que el mercado lo cuente del todo.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:w-auto">
            <div className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
              <div className="text-[0.58rem] uppercase tracking-[0.16em] text-muted-foreground/60">Markets</div>
              <div className="mt-1 text-2xl font-black text-foreground">{markets.length}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/10 px-3 py-3">
              <div className="text-[0.58rem] uppercase tracking-[0.16em] text-muted-foreground/60">Updated</div>
              <div className="mt-1 text-sm font-bold text-foreground/85">{String(data.generated_at).slice(0, 10)}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-5">
        {markets.map(([marketId, market]) => (
          <MarketCard key={marketId} marketId={marketId} market={market} />
        ))}
      </div>
    </div>
  )
}
