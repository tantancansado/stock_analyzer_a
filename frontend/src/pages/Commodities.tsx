import { useState, useEffect, useMemo } from 'react'
import { fetchCommodities, type CommodityOpportunity } from '../api/client'
import Loading, { ErrorState } from '../components/Loading'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp } from 'lucide-react'

// ─── Config ───────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  Precious_Metal: 'Metales preciosos',
  Energy:         'Energía',
  Industrial:     'Metales industriales',
  Agricultural:   'Agrícolas',
}

const TYPE_COLORS: Record<string, string> = {
  Precious_Metal: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/25',
  Energy:         'text-orange-400 bg-orange-500/10 border-orange-500/25',
  Industrial:     'text-cyan-400 bg-cyan-500/10 border-cyan-500/25',
  Agricultural:   'text-green-400 bg-green-500/10 border-green-500/25',
}

const RATING_CONFIG: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  MUY_ATRACTIVO: { label: 'MUY ATRACTIVO', bg: 'bg-emerald-500/15 border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  ATRACTIVO:     { label: 'ATRACTIVO',     bg: 'bg-green-500/10 border-green-500/25',     text: 'text-green-400',   dot: 'bg-green-400'   },
  NEUTRAL:       { label: 'NEUTRAL',       bg: 'bg-slate-500/10 border-slate-500/25',     text: 'text-slate-400',   dot: 'bg-slate-400'   },
  CARO:          { label: 'CARO',          bg: 'bg-red-500/10 border-red-500/25',          text: 'text-red-400',     dot: 'bg-red-400'     },
  SIN_DATO:      { label: 'SIN DATO',      bg: 'bg-muted/20 border-muted/30',             text: 'text-muted-foreground', dot: 'bg-muted'  },
}

const MOMENTUM_CONFIG: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  SOBRECOMPRADO: { icon: <TrendingUp className="w-3 h-3" />, label: 'Sobrecomprado', color: 'text-red-400' },
  NEUTRAL:       { icon: <Minus className="w-3 h-3" />,      label: 'Neutral',       color: 'text-white/50' },
  SOBREVENDIDO:  { icon: <TrendingDown className="w-3 h-3" />, label: 'Sobrevendido', color: 'text-cyan-400' },
}

const SEAS_CONFIG: Record<string, { label: string; color: string }> = {
  bullish:  { label: '↑ Estacional', color: 'text-emerald-400' },
  bearish:  { label: '↓ Estacional', color: 'text-red-400' },
  neutral:  { label: '— Neutro',     color: 'text-white/40' },
}

const ALL_TYPES = ['Precious_Metal', 'Energy', 'Industrial', 'Agricultural']

// ─── Components ───────────────────────────────────────────────────────────────

function RangeBar({ position }: { position: number | null }) {
  if (position === null) return <span className="text-white/25 text-xs">—</span>
  const pct = Math.min(Math.max(position * 100, 0), 100)
  const color = position < 0.3 ? '#10b981' : position > 0.7 ? '#ef4444' : '#f59e0b'
  return (
    <div className="flex items-center gap-2 min-w-[90px]">
      <div className="flex-1 h-1.5 rounded-full bg-white/10 relative">
        <div className="absolute h-1.5 rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-mono text-white/50">{pct.toFixed(0)}%</span>
    </div>
  )
}

function PctBadge({ v, inverse = false }: { v: number | null; inverse?: boolean }) {
  if (v === null) return <span className="text-white/25 text-xs">—</span>
  const positive = inverse ? v < 0 : v > 0
  const color = positive ? '#10b981' : v === 0 ? '#94a3b8' : '#ef4444'
  return (
    <span className="text-xs font-mono" style={{ color }}>
      {v > 0 ? '+' : ''}{v.toFixed(1)}%
    </span>
  )
}

function CommodityRow({ item }: { item: CommodityOpportunity }) {
  const [open, setOpen] = useState(false)
  const rating = RATING_CONFIG[item.value_rating] ?? RATING_CONFIG['SIN_DATO']
  const momentum = MOMENTUM_CONFIG[item.momentum_signal] ?? MOMENTUM_CONFIG['NEUTRAL']
  const seas = SEAS_CONFIG[item.seasonality] ?? SEAS_CONFIG['neutral']
  const typeColor = TYPE_COLORS[item.commodity_type] ?? 'text-slate-400 bg-slate-500/10 border-slate-500/25'

  return (
    <>
      <tr
        className="border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer"
        onClick={() => setOpen(o => !o)}
      >
        {/* Ticker + nombre */}
        <td className="py-3 pr-3">
          <div className="flex items-center gap-2">
            <span className="text-white font-semibold text-sm font-mono w-12 shrink-0">{item.ticker}</span>
            <span className="text-white/50 text-xs truncate max-w-[140px] hidden sm:block">{item.sector}</span>
          </div>
        </td>

        {/* Tipo */}
        <td className="py-3 pr-3 hidden md:table-cell">
          <span className={cn('text-xs px-2 py-0.5 rounded border', typeColor)}>
            {TYPE_LABELS[item.commodity_type] ?? item.commodity_type}
          </span>
        </td>

        {/* Precio */}
        <td className="py-3 pr-3">
          <span className="text-white text-sm font-mono">
            {item.price !== null ? `$${item.price.toFixed(2)}` : '—'}
          </span>
        </td>

        {/* Rango 52s */}
        <td className="py-3 pr-4">
          <RangeBar position={item.range_position} />
        </td>

        {/* vs 2y avg */}
        <td className="py-3 pr-3 hidden sm:table-cell">
          <PctBadge v={item.pct_vs_2y_avg} inverse />
        </td>

        {/* 1d change */}
        <td className="py-3 pr-3 hidden lg:table-cell">
          <PctBadge v={item.change_1d} />
        </td>

        {/* Momentum */}
        <td className="py-3 pr-3 hidden md:table-cell">
          <span className={cn('flex items-center gap-1 text-xs', momentum.color)}>
            {momentum.icon} {momentum.label}
          </span>
        </td>

        {/* Estacional */}
        <td className="py-3 pr-3 hidden lg:table-cell">
          <span className={cn('text-xs', seas.color)}>{seas.label}</span>
        </td>

        {/* Rating VALUE */}
        <td className="py-3 pr-3">
          <div className={cn('flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-medium', rating.bg, rating.text)}>
            <div className={cn('w-1.5 h-1.5 rounded-full', rating.dot)} />
            {rating.label}
          </div>
        </td>

        {/* Expand */}
        <td className="py-3 text-right">
          {open
            ? <ChevronUp className="w-4 h-4 text-white/30 ml-auto" />
            : <ChevronDown className="w-4 h-4 text-white/30 ml-auto" />
          }
        </td>
      </tr>

      {/* Expanded detail */}
      {open && (
        <tr className="border-b border-white/5 bg-white/[0.02]">
          <td colSpan={10} className="px-4 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Recomendación */}
              <div>
                <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2">Señal</div>
                <p className="text-sm text-white/80 leading-relaxed">{item.recommendation || '—'}</p>
              </div>

              {/* Métricas */}
              <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                <MetricRow label="52w High" value={item.week52_high !== null ? `$${item.week52_high.toFixed(2)}` : '—'} />
                <MetricRow label="52w Low" value={item.week52_low !== null ? `$${item.week52_low.toFixed(2)}` : '—'} />
                <MetricRow label="Media 2 años" value={item.avg_2y_price !== null ? `$${item.avg_2y_price.toFixed(2)}` : '—'} />
                <MetricRow label="Vs media 2a" value={item.pct_vs_2y_avg !== null ? `${item.pct_vs_2y_avg > 0 ? '+' : ''}${item.pct_vs_2y_avg.toFixed(1)}%` : '—'} color={item.pct_vs_2y_avg !== null ? (item.pct_vs_2y_avg < 0 ? 'text-emerald-400' : 'text-red-400') : undefined} />
                <MetricRow label="Vol ratio" value={item.vol_ratio !== null ? `${item.vol_ratio.toFixed(2)}×` : '—'} />
                <MetricRow label="Dist. yield" value={item.dist_yield_pct !== null && item.dist_yield_pct > 0 ? `${item.dist_yield_pct.toFixed(2)}%` : '—'} />
                <MetricRow
                  label="IBKR Ireland"
                  value={item.ibkr_ireland ? '✓ Sí' : (item.eu_alternative ? `✗ usar ${item.eu_alternative}` : '✗ No')}
                  color={item.ibkr_ireland ? 'text-emerald-400' : item.eu_alternative ? 'text-amber-400' : 'text-red-400'}
                />
                <MetricRow label="Expense ratio" value={item.expense_ratio_pct ? `${item.expense_ratio_pct.toFixed(2)}%` : '—'} />
              </div>

              {/* Ciclo */}
              {item.cycle_driver && (
                <div className="md:col-span-2">
                  <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2">Contexto de ciclo</div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {item.cycle_driver && (
                      <div className="rounded-lg bg-white/5 px-3 py-2">
                        <div className="text-xs text-white/40 mb-1">Motor</div>
                        <p className="text-xs text-white/70">{item.cycle_driver}</p>
                      </div>
                    )}
                    {item.cycle_bullish && (
                      <div className="rounded-lg bg-emerald-500/5 border border-emerald-500/15 px-3 py-2">
                        <div className="text-xs text-emerald-400 mb-1">Factores alcistas</div>
                        <p className="text-xs text-white/70">{item.cycle_bullish}</p>
                      </div>
                    )}
                    {item.cycle_bearish && (
                      <div className="rounded-lg bg-red-500/5 border border-red-500/15 px-3 py-2">
                        <div className="text-xs text-red-400 mb-1">Factores bajistas</div>
                        <p className="text-xs text-white/70">{item.cycle_bearish}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function MetricRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex justify-between items-center py-0.5">
      <span className="text-xs text-white/40">{label}</span>
      <span className={cn('text-xs font-mono text-white/70', color)}>{value}</span>
    </div>
  )
}

// ─── Summary cards ─────────────────────────────────────────────────────────────

function SummaryCards({ data }: { data: CommodityOpportunity[] }) {
  const attractive = data.filter(d => d.value_rating === 'MUY_ATRACTIVO' || d.value_rating === 'ATRACTIVO').length
  const oversold   = data.filter(d => d.momentum_signal === 'SOBREVENDIDO').length
  const seasonal   = data.filter(d => d.seasonality === 'bullish').length
  // Todos los tickers del universo son ETFs de EEUU (bloqueados PRIIPS/KID en
  // IBKR Ireland) — lo comprable es su alternativa UCITS, no el ticker en sí
  const withEuAlt  = data.filter(d => d.ibkr_ireland || d.eu_alternative).length

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {[
        { label: 'Atractivos',    value: attractive, color: '#10b981' },
        { label: 'Sobrevendidos', value: oversold,   color: '#22d3ee' },
        { label: 'Estacional ↑',  value: seasonal,   color: '#f59e0b' },
        { label: 'Con alt. UCITS', value: withEuAlt, color: '#8b5cf6' },
      ].map(({ label, value, color }) => (
        <Card key={label} className="glass">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold font-mono" style={{ color }}>{value}</div>
            <div className="text-xs text-white/40 mt-0.5">{label}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Commodities() {
  const [data, setData] = useState<CommodityOpportunity[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState<string>('ALL')
  const [ratingFilter, setRatingFilter] = useState<string>('ALL')

  useEffect(() => {
    fetchCommodities()
      .then(rows => { setData(rows); setLoading(false) })
      .catch(err => { setError(err.message ?? 'Error'); setLoading(false) })
  }, [])

  const filtered = useMemo(() => {
    if (!data) return []
    return data.filter(d => {
      if (typeFilter !== 'ALL' && d.commodity_type !== typeFilter) return false
      if (ratingFilter === 'BUYS' && d.value_rating !== 'MUY_ATRACTIVO' && d.value_rating !== 'ATRACTIVO') return false
      if (ratingFilter !== 'BUYS' && ratingFilter !== 'ALL' && d.value_rating !== ratingFilter) return false
      return true
    })
  }, [data, typeFilter, ratingFilter])

  if (loading) return <Loading />
  if (error || !data) return <ErrorState message={typeof error === 'string' ? error : 'Error cargando materias primas'} />

  const generatedAt = data[0]?.generated_at ? new Date(data[0].generated_at).toLocaleString('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : null

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Materias Primas</h1>
          <p className="text-sm text-white/40 mt-1">
            {data.length} ETFs (EEUU) · VALUE rating vs media histórica 2 años · ver alternativa UCITS por fila para IBKR Ireland
            {generatedAt && <span className="ml-2">· actualizado {generatedAt}</span>}
          </p>
        </div>
      </div>

      <SummaryCards data={data} />

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {/* Type filter */}
        <div className="flex gap-1 p-1 rounded-lg bg-white/5">
          {[{ id: 'ALL', label: 'Todos' }, ...ALL_TYPES.map(t => ({ id: t, label: TYPE_LABELS[t] ?? t }))].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setTypeFilter(id)}
              className={cn(
                'px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                typeFilter === id ? 'bg-cyan-500/20 text-cyan-400' : 'text-white/40 hover:text-white/70',
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Rating filter */}
        <div className="flex gap-1 p-1 rounded-lg bg-white/5">
          {[
            { id: 'ALL',  label: 'Todos' },
            { id: 'BUYS', label: '★ Atractivos' },
            { id: 'NEUTRAL', label: 'Neutral' },
            { id: 'CARO', label: 'Caro' },
          ].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setRatingFilter(id)}
              className={cn(
                'px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                ratingFilter === id ? 'bg-cyan-500/20 text-cyan-400' : 'text-white/40 hover:text-white/70',
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <Card className="glass">
        <CardContent className="p-0">
          <div className="table-x-wrap">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left">
                  <th className="px-4 py-3 text-xs text-white/40 font-medium">Ticker</th>
                  <th className="py-3 pr-3 text-xs text-white/40 font-medium hidden md:table-cell">Tipo</th>
                  <th className="py-3 pr-3 text-xs text-white/40 font-medium">Precio</th>
                  <th className="py-3 pr-4 text-xs text-white/40 font-medium">Rango 52s</th>
                  <th className="py-3 pr-3 text-xs text-white/40 font-medium hidden sm:table-cell">Vs 2a avg</th>
                  <th className="py-3 pr-3 text-xs text-white/40 font-medium hidden lg:table-cell">1d</th>
                  <th className="py-3 pr-3 text-xs text-white/40 font-medium hidden md:table-cell">Momentum</th>
                  <th className="py-3 pr-3 text-xs text-white/40 font-medium hidden lg:table-cell">Estacional</th>
                  <th className="py-3 pr-3 text-xs text-white/40 font-medium">Rating</th>
                  <th className="py-3 px-4" />
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="py-12 text-center text-white/30 text-sm">
                      Sin resultados con los filtros seleccionados
                    </td>
                  </tr>
                ) : (
                  filtered.map(item => <CommodityRow key={item.ticker} item={item} />)
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-white/25 pb-4">
        <span><strong className="text-white/40">Rango 52s:</strong> 0% = mínimo anual · 100% = máximo anual</span>
        <span><strong className="text-white/40">Vs 2a avg:</strong> % sobre/bajo media de 2 años (negativo = barato)</span>
        <span><strong className="text-white/40">VALUE rating:</strong> basado en posición de precio histórica + estacionalidad</span>
      </div>
    </div>
  )
}
