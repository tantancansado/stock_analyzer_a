import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Flame, Radar, ShieldAlert, Siren, Waves } from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, CardContent } from '@/components/ui/card'
import {
  fetchMacroStress,
  type MacroStressAnalogue,
  type MacroStressMarket,
  type MacroStressResponse,
  type MacroStressSignal,
} from '../api/client'
import { useApi } from '../hooks/useApi'
import Loading, { ErrorState } from '../components/Loading'
import StaleDataBanner from '../components/StaleDataBanner'

const BAND_THEME: Record<string, { tile: string; ring: string; glow: string; label: string }> = {
  green: {
    tile: 'border-emerald-500/25 bg-[linear-gradient(140deg,rgba(16,185,129,0.14),rgba(6,78,59,0.08))]',
    ring: 'bg-emerald-400',
    glow: 'shadow-[0_0_0_1px_rgba(16,185,129,0.25),0_18px_40px_rgba(16,185,129,0.08)]',
    label: 'Verde',
  },
  amber: {
    tile: 'border-amber-500/25 bg-[linear-gradient(140deg,rgba(245,158,11,0.16),rgba(120,53,15,0.1))]',
    ring: 'bg-amber-400',
    glow: 'shadow-[0_0_0_1px_rgba(245,158,11,0.25),0_18px_40px_rgba(245,158,11,0.08)]',
    label: 'Ámbar',
  },
  red: {
    tile: 'border-red-500/25 bg-[linear-gradient(140deg,rgba(239,68,68,0.18),rgba(127,29,29,0.12))]',
    ring: 'bg-red-400',
    glow: 'shadow-[0_0_0_1px_rgba(239,68,68,0.25),0_18px_40px_rgba(239,68,68,0.10)]',
    label: 'Rojo',
  },
  unknown: {
    tile: 'border-white/10 bg-white/[0.03]',
    ring: 'bg-slate-400',
    glow: 'shadow-[0_0_0_1px_rgba(255,255,255,0.08)]',
    label: 'Parcial',
  },
}

function fmt(value: number | null | undefined, digits = 0) {
  return value == null ? 'N/A' : value.toFixed(digits)
}

function retTone(value: number | null) {
  if (value == null) return 'text-muted-foreground/55'
  if (value > 0) return 'text-emerald-300'
  if (value < 0) return 'text-red-300'
  return 'text-muted-foreground'
}

function bandTheme(band?: string) {
  return BAND_THEME[band || 'unknown'] ?? BAND_THEME.unknown
}

function scoreBarClass(score: number | null | undefined) {
  if (score == null) return 'from-slate-500 to-slate-400'
  if (score < 30) return 'from-emerald-500 to-lime-400'
  if (score < 60) return 'from-amber-500 to-orange-400'
  return 'from-red-500 to-fuchsia-500'
}

function SignalCard({ signal }: { signal: MacroStressSignal }) {
  const width = signal.score == null ? 0 : Math.max(0, Math.min(100, signal.score))
  return (
    <div className="rounded-2xl border border-white/10 bg-black/10 p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-[0.62rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/60">
            {signal.label}
          </div>
          <div className="mt-1 text-sm font-semibold text-foreground/85">
            {signal.value != null ? `${fmt(signal.value, Math.abs(signal.value) >= 10 ? 1 : 2)}` : 'Sin dato'}
          </div>
        </div>
        <div className="text-right">
          <div className="text-base font-black text-foreground">{fmt(signal.score, 1)}</div>
          <div className="text-[0.62rem] uppercase tracking-[0.16em] text-muted-foreground/50">
            {Math.round(signal.weight * 100)}%
          </div>
        </div>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/8">
        <div className={`h-full rounded-full bg-gradient-to-r ${scoreBarClass(signal.score)}`} style={{ width: `${width}%` }} />
      </div>
      <div className="mt-2 flex flex-wrap gap-2 text-[0.68rem] text-muted-foreground/60">
        {signal.percentile != null && <span>pct {fmt(signal.percentile, 0)}</span>}
        {signal.z != null && <span>z {fmt(signal.z, 2)}</span>}
        {signal.contribution != null && <span>+{fmt(signal.contribution, 1)} pts</span>}
      </div>
    </div>
  )
}

function HeatTile({
  marketId,
  market,
  active,
  onClick,
}: {
  marketId: string
  market: MacroStressMarket
  active: boolean
  onClick: () => void
}) {
  const theme = bandTheme(market.band)
  const score = market.stress_score ?? 0
  return (
    <button
      onClick={onClick}
      className={`relative rounded-[24px] border p-4 text-left transition-all duration-300 ${theme.tile} ${theme.glow} ${
        active ? 'scale-[1.01] border-white/30' : 'hover:-translate-y-0.5 hover:border-white/20'
      }`}
    >
      <div className="absolute right-3 top-3 flex items-center gap-1.5 rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[0.58rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/70">
        <span className={`h-1.5 w-1.5 rounded-full ${theme.ring}`} />
        {theme.label}
      </div>
      <div className="pr-14">
        <div className="text-[0.62rem] font-bold uppercase tracking-[0.18em] text-primary/70">{market.category ?? 'macro'}</div>
        <h3 className="mt-2 text-xl font-black tracking-tight text-foreground">{market.label}</h3>
        <p className="mt-1 text-sm text-muted-foreground/70">{market.regime} · {market.primary_ticker} · {marketId}</p>
      </div>
      <div className="mt-6 flex items-end justify-between gap-3">
        <div>
          <div className="text-[0.58rem] uppercase tracking-[0.18em] text-muted-foreground/55">Stress score</div>
          <div className="mt-1 text-4xl font-black tabular-nums text-foreground">{fmt(market.stress_score, 0)}</div>
        </div>
        <div className="min-w-[92px]">
          <div className="mb-1 flex items-center justify-between text-[0.6rem] uppercase tracking-[0.16em] text-muted-foreground/55">
            <span>Coverage</span>
            <span>{fmt(market.coverage_pct, 0)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div className={`h-full rounded-full bg-gradient-to-r ${scoreBarClass(score)}`} style={{ width: `${Math.max(6, score)}%` }} />
          </div>
        </div>
      </div>
    </button>
  )
}

function PriceStressChart({
  market,
  analogues,
}: {
  market: MacroStressMarket
  analogues: MacroStressAnalogue[]
}) {
  const data = market.chart_series ?? []
  if (!data.length) {
    return (
      <div className="rounded-2xl border border-white/10 bg-black/10 p-6 text-sm text-muted-foreground/60">
        Sin serie histórica suficiente para dibujar el drill-down.
      </div>
    )
  }

  const analoguePriceMap = new Map<string, number>()
  for (const point of data) {
    analoguePriceMap.set(point.date, point.price)
  }

  return (
    <div className="rounded-[26px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01))] p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <div className="text-[0.62rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/55">Drill-down</div>
          <div className="mt-1 text-lg font-black tracking-tight text-foreground">Precio y stress histórico</div>
        </div>
        <div className="text-right text-[0.68rem] text-muted-foreground/60">
          <div>{market.primary_ticker}</div>
          <div>{data.length} puntos</div>
        </div>
      </div>

      <div style={{ height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 12, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="macro-price-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f97316" stopOpacity={0.24} />
                <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              tickFormatter={(value) => String(value).slice(2, 7)}
              axisLine={false}
              tickLine={false}
              minTickGap={28}
            />
            <YAxis
              yAxisId="price"
              orientation="left"
              tick={{ fontSize: 10, fill: '#f8fafc' }}
              axisLine={false}
              tickLine={false}
              width={54}
            />
            <YAxis
              yAxisId="stress"
              orientation="right"
              domain={[0, 100]}
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              axisLine={false}
              tickLine={false}
              width={38}
            />
            <Tooltip
              contentStyle={{
                background: 'rgba(15,17,23,0.96)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '14px',
                fontSize: '12px',
              }}
            />
            <Area
              yAxisId="price"
              type="monotone"
              dataKey="price"
              stroke="#fb923c"
              fill="url(#macro-price-fill)"
              strokeWidth={2.2}
              dot={false}
              activeDot={{ r: 3, fill: '#fb923c' }}
            />
            <Line
              yAxisId="stress"
              type="monotone"
              dataKey="stress_score"
              stroke="#38bdf8"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
            {analogues.map((item, idx) => {
              const price = analoguePriceMap.get(item.date)
              if (price == null) return null
              return (
                <ReferenceDot
                  key={`${item.date}-${idx}`}
                  yAxisId="price"
                  x={item.date}
                  y={price}
                  r={5}
                  fill={item.forward_30d_return != null && item.forward_30d_return < 0 ? '#ef4444' : '#facc15'}
                  stroke="rgba(15,17,23,0.9)"
                />
              )
            })}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function AnalogueCard({ item, index }: { item: MacroStressAnalogue; index: number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[0.6rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/45">Análogo #{index + 1}</div>
          <div className="mt-1 text-sm font-bold text-foreground">{item.name}</div>
          <div className="text-[0.72rem] text-muted-foreground/60">{item.date}</div>
        </div>
        <div className="rounded-full border border-cyan-400/20 bg-cyan-400/8 px-2.5 py-1 text-[0.68rem] font-bold text-cyan-300">
          {fmt(item.similarity, 0)}% sim
        </div>
      </div>
      {item.event && (
        <p className="mt-2 text-[0.72rem] leading-relaxed text-foreground/70">{item.event}</p>
      )}
      <div className="mt-3 grid grid-cols-3 gap-2">
        {[
          ['30d', item.forward_30d_return],
          ['60d', item.forward_60d_return],
          ['90d', item.forward_90d_return],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-white/8 bg-white/[0.03] px-2.5 py-2 text-center">
            <div className="text-[0.58rem] font-bold uppercase tracking-[0.16em] text-muted-foreground/50">{label}</div>
            <div className={`mt-1 text-sm font-black ${retTone(value as number | null)}`}>
              {value == null ? 'N/A' : `${(value as number) > 0 ? '+' : ''}${value}%`}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-3 text-[0.68rem] text-muted-foreground/55">
        Señales compartidas: {item.shared_signals.join(', ')}
      </div>
    </div>
  )
}

function ExposurePanel({ market }: { market: MacroStressMarket }) {
  const beneficiaries = market.equity_exposure?.beneficiaries ?? []
  const losers = market.equity_exposure?.losers ?? []
  const isRed = (market.stress_score ?? 0) >= 60

  return (
    <div className={`rounded-[26px] border p-4 ${isRed ? 'border-red-500/20 bg-red-500/[0.06]' : 'border-white/10 bg-white/[0.03]'}`}>
      <div className="flex items-center gap-2 text-[0.62rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/55">
        <ShieldAlert size={13} className={isRed ? 'text-red-300' : 'text-cyan-300'} />
        Equity Exposure Map
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <div className="mb-2 text-[0.62rem] font-bold uppercase tracking-[0.16em] text-emerald-300/80">Beneficiarios</div>
          <div className="flex flex-wrap gap-2">
            {beneficiaries.map((ticker) => (
              <span key={ticker} className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[0.68rem] font-semibold text-emerald-300">
                {ticker}
              </span>
            ))}
          </div>
        </div>
        <div>
          <div className="mb-2 text-[0.62rem] font-bold uppercase tracking-[0.16em] text-red-300/80">Perdedores</div>
          <div className="flex flex-wrap gap-2">
            {losers.map((ticker) => (
              <span key={ticker} className="rounded-full border border-red-500/20 bg-red-500/10 px-2.5 py-1 text-[0.68rem] font-semibold text-red-300">
                {ticker}
              </span>
            ))}
          </div>
        </div>
      </div>
      <p className="mt-4 text-[0.72rem] leading-relaxed text-muted-foreground/65">
        {isRed
          ? 'Mercado en rojo: estas equities son las primeras candidatas a revisar en cartera.'
          : 'Mapa curado para traducir el stress de commodity a nombres operables en equity.'}
      </p>
    </div>
  )
}

export default function MacroStress() {
  const { data, loading, error } = useApi<MacroStressResponse>(() => fetchMacroStress(), [])
  const [selectedId, setSelectedId] = useState<string>('')
  const [sortBy, setSortBy] = useState<'stress' | 'name'>('stress')

  const markets = useMemo(() => {
    if (!data?.markets) return []
    const entries = Object.entries(data.markets)
    entries.sort((a, b) => {
      if (sortBy === 'name') return a[1].label.localeCompare(b[1].label)
      return (b[1].stress_score ?? -1) - (a[1].stress_score ?? -1)
    })
    return entries
  }, [data, sortBy])

  useEffect(() => {
    if (!selectedId && markets.length > 0) {
      setSelectedId(markets[0][0])
    }
  }, [markets, selectedId])

  if (loading) return <Loading />
  if (error) {
    const friendly = error.includes('404')
      ? 'Macro Stress Radar aún no está generado. Se poblará cuando corra el pipeline diario.'
      : error
    return <ErrorState message={friendly} />
  }
  if (!markets.length) {
    return <ErrorState message="No hay mercados configurados todavía." />
  }

  const selected = data!.markets[selectedId] ?? markets[0][1]
  const selectedAnalogues = selected.historical_analogues ?? []
  const redCount = Object.values(data!.markets).filter((market) => (market.stress_score ?? 0) >= 60).length
  const topScore = data?.summary?.top_stress_score ?? markets[0][1].stress_score

  return (
    <div className="space-y-5">
      <StaleDataBanner module="macro_stress" />

      <div className="relative overflow-hidden rounded-[30px] border border-white/10 bg-[radial-gradient(circle_at_top_left,rgba(249,115,22,0.18),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(6,182,212,0.14),transparent_24%),linear-gradient(135deg,rgba(255,255,255,0.06),rgba(255,255,255,0.015))] px-5 py-6">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/35 to-transparent" />
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/15 px-3 py-1 text-[0.62rem] font-bold uppercase tracking-[0.2em] text-primary/80">
              <Radar size={12} />
              Macro Stress Framework
            </div>
            <h2 className="text-3xl font-black tracking-tight text-foreground">Heatmap de dislocaciones macro</h2>
            <p className="mt-2 text-sm leading-relaxed text-foreground/72">
              El score no intenta adivinar el próximo tick. Compacta inventarios, curva, geopolítica y positioning para detectar
              cuándo un mercado commodity entra en régimen operativo peligroso.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-black/15 px-4 py-3">
              <div className="text-[0.58rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/55">Mercados</div>
              <div className="mt-1 text-3xl font-black text-foreground">{data?.summary?.markets_total ?? markets.length}</div>
            </div>
            <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3">
              <div className="text-[0.58rem] font-bold uppercase tracking-[0.18em] text-red-200/70">En rojo</div>
              <div className="mt-1 text-3xl font-black text-red-300">{redCount}</div>
            </div>
            <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3">
              <div className="text-[0.58rem] font-bold uppercase tracking-[0.18em] text-cyan-200/70">Pico actual</div>
              <div className="mt-1 text-3xl font-black text-cyan-200">{fmt(topScore, 0)}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-[0.68rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/55">
          <Flame size={13} className="text-orange-300" />
          Heatmap Grid
        </div>
        <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.03] p-1">
          {([
            ['stress', 'Por score'],
            ['name', 'Por nombre'],
          ] as const).map(([value, label]) => (
            <button
              key={value}
              onClick={() => setSortBy(value)}
              className={`rounded-full px-3 py-1.5 text-[0.68rem] font-semibold transition-colors ${
                sortBy === value ? 'bg-white/10 text-foreground' : 'text-muted-foreground/55 hover:text-foreground'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {markets.map(([marketId, market]) => (
          <HeatTile
            key={marketId}
            marketId={marketId}
            market={market}
            active={selectedId === marketId}
            onClick={() => setSelectedId(marketId)}
          />
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-5">
          <PriceStressChart market={selected} analogues={selectedAnalogues} />

          <Card className="glass overflow-hidden border-white/10">
            <CardContent className="p-0">
              <div className="border-b border-white/10 px-5 py-4">
                <div className="flex flex-wrap items-center gap-3">
                  <div>
                    <div className="text-[0.62rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/55">Mercado activo</div>
                    <h3 className="mt-1 text-xl font-black tracking-tight text-foreground">{selected.label}</h3>
                  </div>
                  <div className="ml-auto flex flex-wrap items-center gap-2">
                    <span className={`rounded-full border px-2.5 py-1 text-[0.68rem] font-bold ${
                      selected.band === 'red'
                        ? 'border-red-500/30 bg-red-500/12 text-red-300'
                        : selected.band === 'amber'
                        ? 'border-amber-500/30 bg-amber-500/12 text-amber-300'
                        : 'border-emerald-500/30 bg-emerald-500/12 text-emerald-300'
                    }`}>
                      {selected.regime}
                    </span>
                    <span className="rounded-full border border-white/10 bg-black/15 px-2.5 py-1 text-[0.68rem] font-semibold text-muted-foreground/70">
                      {fmt(selected.coverage_pct, 0)}% coverage
                    </span>
                  </div>
                </div>
                {selected.narrative && (
                  <p className="mt-3 text-sm leading-relaxed text-foreground/72">{selected.narrative}</p>
                )}
              </div>
              <div className="grid gap-3 p-5 md:grid-cols-2">
                {Object.entries(selected.signals || {}).map(([key, signal]) => (
                  <SignalCard key={key} signal={signal} />
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-5">
          <ExposurePanel market={selected} />

          <Card className="glass overflow-hidden border-white/10">
            <CardContent className="p-0">
              <div className="border-b border-white/10 px-5 py-4">
                <div className="flex items-center gap-2 text-[0.62rem] font-bold uppercase tracking-[0.18em] text-muted-foreground/55">
                  <Waves size={13} className="text-cyan-300" />
                  Historical Analogues
                </div>
                <p className="mt-2 text-sm text-foreground/70">
                  No te doy una “probabilidad” fabricada. Te enseño episodios históricos parecidos y qué pasó después.
                </p>
              </div>
              <div className="space-y-3 p-5">
                {selectedAnalogues.length > 0 ? selectedAnalogues.map((item, index) => (
                  <AnalogueCard key={`${item.date}-${index}`} item={item} index={index} />
                )) : (
                  <div className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm text-muted-foreground/60">
                    {selected.history_note ?? 'Todavía no hay análogos suficientes para este mercado.'}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <div className="rounded-[26px] border border-amber-500/20 bg-amber-500/[0.08] p-4">
            <div className="flex items-center gap-2 text-[0.62rem] font-bold uppercase tracking-[0.18em] text-amber-300/85">
              <Siren size={13} />
              Reading Guide
            </div>
            <p className="mt-3 text-sm leading-relaxed text-foreground/76">
              Verde significa normalidad operativa. Ámbar pide vigilancia. Rojo no equivale a “sube seguro” o “cae seguro”:
              significa que la commodity se ha vuelto lo bastante tensa como para contaminar rápidamente a las equities expuestas.
            </p>
            {selected.history_note && (
              <div className="mt-3 flex items-start gap-2 rounded-2xl border border-white/10 bg-black/10 px-3 py-3 text-[0.72rem] text-muted-foreground/65">
                <AlertTriangle size={13} className="mt-0.5 shrink-0 text-amber-300" />
                <span>{selected.history_note}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
