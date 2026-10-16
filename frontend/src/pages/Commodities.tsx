import { useState, useEffect, useMemo } from 'react'
import { fetchCommodities, type CommodityOpportunity } from '../api/client'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp } from 'lucide-react'
import PageHeader from '../components/PageHeader'
import PageShell from '@/components/PageShell'
import EmptyState from '@/components/EmptyState'

// ─── Config ───────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  Precious_Metal: 'Metales preciosos',
  Energy:         'Energía',
  Industrial:     'Metales industriales',
  Agricultural:   'Agrícolas',
  Diversified:    'Diversificados',
}

// El tipo es una etiqueta de clasificación, no una señal: va neutra. Con un
// color por tipo competía con el rating, el momentum y la barra de rango, y
// cuatro tonos fuertes por fila hacían que nada destacara.
const TYPE_BADGE = 'text-muted-foreground bg-foreground/5 border-border/40'

const ESTRUCTURA_TEXTO: Record<string, string> = {
  fisico:  'Fondo físico: el precio es el de la materia prima.',
  futuros: 'Fondo de futuros: el precio incluye el coste de renovar contratos, así que puede caer sin que la materia prima baje.',
  mineras: 'Fondo de mineras: es renta variable de empresas, no el metal.',
}

/** El rating que se puede afirmar: un «atractivo» sin verificar no es una señal. */
function ratingEfectivo(item: CommodityOpportunity): string {
  const atractivo = item.value_rating === 'MUY_ATRACTIVO' || item.value_rating === 'ATRACTIVO'
  return atractivo && item.ai_verified !== true ? 'SIN_VERIFICAR' : item.value_rating
}

const RATING_CONFIG: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  MUY_ATRACTIVO: { label: 'MUY ATRACTIVO', bg: 'bg-emerald-500/15 border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  ATRACTIVO:     { label: 'ATRACTIVO',     bg: 'bg-green-500/10 border-green-500/25',     text: 'text-green-400',   dot: 'bg-green-400'   },
  NEUTRAL:       { label: 'NEUTRAL',       bg: 'bg-muted/30 border-border/40',     text: 'text-muted-foreground',   dot: 'bg-muted-foreground'   },
  CARO:          { label: 'CARO',          bg: 'bg-red-500/10 border-red-500/25',          text: 'text-red-400',     dot: 'bg-red-400'     },
  SIN_VERIFICAR: { label: 'SIN VERIFICAR', bg: 'bg-amber-500/10 border-amber-500/25',        text: 'text-amber-400',   dot: 'bg-amber-400'   },
  SIN_DATO:      { label: 'SIN DATO',      bg: 'bg-muted/20 border-muted/30',             text: 'text-muted-foreground', dot: 'bg-muted'  },
}

const MOMENTUM_CONFIG: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  SOBRECOMPRADO: { icon: <TrendingUp className="w-3 h-3" />, label: 'Sobrecomprado', color: 'text-red-400' },
  NEUTRAL:       { icon: <Minus className="w-3 h-3" />,      label: 'Neutral',       color: 'text-muted-foreground' },
  SOBREVENDIDO:  { icon: <TrendingDown className="w-3 h-3" />, label: 'Sobrevendido', color: 'text-cyan-400' },
}

const SEAS_CONFIG: Record<string, { label: string; color: string }> = {
  bullish:  { label: '↑ Estacional', color: 'text-emerald-400' },
  bearish:  { label: '↓ Estacional', color: 'text-red-400' },
  neutral:  { label: '— Neutro',     color: 'text-muted-foreground' },
}

const ALL_TYPES = ['Precious_Metal', 'Energy', 'Industrial', 'Agricultural', 'Diversified']

// ─── Components ───────────────────────────────────────────────────────────────

function RangeBar({ position }: { position: number | null }) {
  if (position === null) return <span className="text-muted-foreground text-mini">—</span>
  const pct = Math.min(Math.max(position * 100, 0), 100)
  const color = position < 0.3 ? 'var(--success)' : position > 0.7 ? 'var(--danger)' : 'var(--warn)'
  return (
    <div className="flex items-center gap-2 min-w-[90px]">
      <div className="flex-1 h-1.5 rounded-full barra-pista relative">
        <div className="absolute h-1.5 rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-mini font-mono text-muted-foreground">{pct.toFixed(0)}%</span>
    </div>
  )
}

function PctBadge({ v, inverse = false }: { v: number | null; inverse?: boolean }) {
  if (v === null) return <span className="text-muted-foreground text-mini">—</span>
  const positive = inverse ? v < 0 : v > 0
  /* Estaban en hexadecimal —tonos para fondo casi negro— y sobre la tarjeta
     blanca el verde se quedaba en 2,54 de contraste. El neutro era `#94a3b8`,
     un slate fijo que no cambia con el tema. */
  const color = positive ? 'var(--success)' : v === 0 ? 'var(--muted-foreground)' : 'var(--danger)'
  return (
    <span className="text-mini font-mono" style={{ color }}>
      {v > 0 ? '+' : ''}{v.toFixed(1)}%
    </span>
  )
}

function CommodityRow({ item }: { item: CommodityOpportunity }) {
  const [open, setOpen] = useState(false)
  const rating = RATING_CONFIG[ratingEfectivo(item)] ?? RATING_CONFIG['SIN_DATO']
  const momentum = MOMENTUM_CONFIG[item.momentum_signal] ?? MOMENTUM_CONFIG['NEUTRAL']
  const seas = SEAS_CONFIG[item.seasonality] ?? SEAS_CONFIG['neutral']

  return (
    <>
      <tr
        className="border-b border-foreground/5 hover:bg-foreground/5 transition-colors cursor-pointer"
        onClick={() => setOpen(o => !o)}
      >
        {/* Ticker + nombre */}
        <td className="px-4 py-3 pr-3">
          <div className="flex items-center gap-2">
            <span className="text-foreground font-semibold text-cuerpo font-mono w-16 shrink-0">{item.ticker}</span>
            <span className="text-muted-foreground text-mini truncate max-w-[140px] hidden sm:block">{item.sector}</span>
          </div>
        </td>

        {/* Tipo */}
        <td className="py-3 pr-3 hidden md:table-cell">
          <span className={cn('text-mini px-2 py-0.5 rounded border whitespace-nowrap', TYPE_BADGE)}>
            {TYPE_LABELS[item.commodity_type] ?? item.commodity_type}
          </span>
        </td>

        {/* Precio */}
        <td className="py-3 pr-3">
          <span className="text-foreground text-cuerpo font-mono">
            {item.price !== null ? `$${item.price.toFixed(2)}` : '—'}
          </span>
        </td>

        {/* Rango 52s — oculto en móvil: es contexto, y sin ocultarlo la tabla
            medía 393px sobre un hueco de 348 y desbordaba */}
        <td className="py-3 pr-4 hidden sm:table-cell">
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
          <span className={cn('flex items-center gap-1 text-mini', momentum.color)}>
            {momentum.icon} {momentum.label}
          </span>
        </td>

        {/* Estacional */}
        <td className="py-3 pr-3 hidden lg:table-cell">
          <span className={cn('text-mini whitespace-nowrap', seas.color)}>{seas.label}</span>
        </td>

        {/* Rating VALUE */}
        <td className="py-3 pr-3">
          <div className={cn('flex items-center gap-1.5 px-2 py-0.5 rounded border text-mini font-medium whitespace-nowrap', rating.bg, rating.text)}>
            <div className={cn('w-1.5 h-1.5 rounded-full', rating.dot)} />
            {rating.label}
          </div>
        </td>

        {/* Expand */}
        <td className="py-3 pr-4 text-right">
          {open
            ? <ChevronUp className="w-4 h-4 text-muted-foreground ml-auto" />
            : <ChevronDown className="w-4 h-4 text-muted-foreground ml-auto" />
          }
        </td>
      </tr>

      {/* Expanded detail */}
      {open && (
        <tr className="border-b border-foreground/5 bg-white/[0.02]">
          <td colSpan={10} className="px-4 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Recomendación */}
              <div>
                <div className="etiqueta-seccion mb-2">Qué dice la regla</div>
                <p className="text-cuerpo text-foreground/80 leading-relaxed">{item.recommendation || '—'}</p>
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

              {/* Verificación y narrativa: lo que sostiene (o no) el rating */}
              <div className="md:col-span-2 space-y-2">
                <div className="etiqueta-seccion">Verificación</div>
                {!item.data_ok && (
                  <p className="text-cuerpo text-foreground/80">Sin dato fiable: {item.data_motivo}.</p>
                )}
                {item.data_ok && ratingEfectivo(item) === 'SIN_VERIFICAR' && (
                  <p className="text-cuerpo text-foreground/80">
                    La regla lo marca barato, pero {item.ai_verified === false
                      ? `la revisión no lo avala: ${item.ai_gate_motivo}`
                      : 'todavía no se ha revisado, y hasta entonces no es una señal.'}
                  </p>
                )}
                {item.data_ok && item.value_rating !== 'SIN_DATO' && ratingEfectivo(item) !== 'SIN_VERIFICAR'
                  && item.ai_verified === true && item.ai_gate_motivo && (
                  <p className="text-cuerpo text-foreground/80">Revisado: {item.ai_gate_motivo}</p>
                )}
                {ESTRUCTURA_TEXTO[item.etf_estructura] && (
                  <p className="text-mini text-muted-foreground">{ESTRUCTURA_TEXTO[item.etf_estructura]}</p>
                )}
                {item.ai_narrative_resumen && (
                  <div className="rounded-lg bg-foreground/5 px-3 py-2">
                    <div className="text-mini text-muted-foreground mb-1">
                      Qué mueve el precio{item.ai_narrative_fecha && ` · investigado el ${item.ai_narrative_fecha}`}
                    </div>
                    <p className="text-mini text-foreground/70">{item.ai_narrative_resumen}</p>
                  </div>
                )}
              </div>

              {/* Ciclo */}
              {item.cycle_driver && (
                <div className="md:col-span-2">
                  <div className="etiqueta-seccion mb-2">Contexto de ciclo</div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {item.cycle_driver && (
                      <div className="rounded-lg bg-foreground/5 px-3 py-2">
                        <div className="text-mini text-muted-foreground mb-1">Motor</div>
                        <p className="text-mini text-foreground/70">{item.cycle_driver}</p>
                      </div>
                    )}
                    {item.cycle_bullish && (
                      <div className="rounded-lg bg-emerald-500/5 border border-emerald-500/15 px-3 py-2">
                        <div className="text-mini text-emerald-400 mb-1">Factores alcistas</div>
                        <p className="text-mini text-foreground/70">{item.cycle_bullish}</p>
                      </div>
                    )}
                    {item.cycle_bearish && (
                      <div className="rounded-lg bg-red-500/5 border border-red-500/15 px-3 py-2">
                        <div className="text-mini text-red-400 mb-1">Factores bajistas</div>
                        <p className="text-mini text-foreground/70">{item.cycle_bearish}</p>
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
      <span className="text-mini text-muted-foreground">{label}</span>
      <span className={cn('text-mini font-mono text-foreground/70', color)}>{value}</span>
    </div>
  )
}

// ─── Summary cards ─────────────────────────────────────────────────────────────

function SummaryCards({ data }: { data: CommodityOpportunity[] }) {
  const attractive = data.filter(d => ratingEfectivo(d) === 'MUY_ATRACTIVO' || ratingEfectivo(d) === 'ATRACTIVO').length
  const porVerificar = data.filter(d => ratingEfectivo(d) === 'SIN_VERIFICAR').length
  const oversold   = data.filter(d => d.momentum_signal === 'SOBREVENDIDO').length
  const seasonal   = data.filter(d => d.seasonality === 'bullish').length

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {[
        { label: 'Atractivos verificados', value: attractive,   color: 'var(--success)' },
        { label: 'Por verificar',          value: porVerificar, color: 'var(--warn)' },
        { label: 'Sobrevendidos',          value: oversold,     color: 'var(--info)' },
        { label: 'Estacional ↑',           value: seasonal,     color: 'var(--special)' },
      ].map(({ label, value, color }) => (
        <Card key={label} className="glass">
          <CardContent className="p-4 text-center">
            <div className="text-pagina font-bold font-mono" style={{ color }}>{value}</div>
            <div className="text-mini text-muted-foreground mt-0.5">{label}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────


function CommodityCard({ item }: Readonly<{ item: CommodityOpportunity }>) {
  const [abierto, setAbierto] = useState(false)
  const rating = RATING_CONFIG[ratingEfectivo(item)] ?? RATING_CONFIG['SIN_DATO']
  const dato = (etiqueta: string, valor: string) => (
    <div>
      <div className="etiqueta-seccion">{etiqueta}</div>
      <div className="text-cuerpo font-bold tabular-nums">{valor}</div>
    </div>
  )
  return (
    <button
      onClick={() => setAbierto(a => !a)}
      className="glass w-full rounded-xl border border-border/25 p-3.5 text-left active:bg-foreground/5"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-cuerpo font-bold text-primary">{item.ticker}</span>
        <span className={`rounded border px-1.5 py-0.5 text-micro font-bold ${rating.bg} ${rating.text}`}>
          {rating.label}
        </span>
      </div>
      <div className="truncate text-mini text-muted-foreground">{item.sector}</div>
      <div className="mt-2.5 grid grid-cols-3 gap-2">
        {dato('Precio', item.price != null ? `$${item.price.toFixed(2)}` : '—')}
        {dato('Del máx.', item.pct_from_high != null ? `${item.pct_from_high.toFixed(0)}%` : '—')}
        {dato('vs 2a', item.pct_vs_2y_avg != null ? `${item.pct_vs_2y_avg > 0 ? '+' : ''}${item.pct_vs_2y_avg.toFixed(0)}%` : '—')}
      </div>
      {abierto && (
        <div className="mt-2.5 space-y-1.5 text-mini leading-relaxed text-foreground/70">
          {!item.data_ok && <p>Sin dato fiable: {item.data_motivo}.</p>}
          {item.data_ok && item.recommendation && <p>{item.recommendation}</p>}
          {item.data_ok && ratingEfectivo(item) === 'SIN_VERIFICAR' && (
            <p>
              Sin verificar{item.ai_verified === false ? `: ${item.ai_gate_motivo}` : ' todavía: hasta entonces no es una señal.'}
            </p>
          )}
          {ESTRUCTURA_TEXTO[item.etf_estructura] && (
            <p className="text-muted-foreground">{ESTRUCTURA_TEXTO[item.etf_estructura]}</p>
          )}
          {item.ai_narrative_resumen && <p>{item.ai_narrative_resumen}</p>}
        </div>
      )}
    </button>
  )
}


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
      const efectivo = ratingEfectivo(d)
      if (ratingFilter === 'BUYS' && efectivo !== 'MUY_ATRACTIVO' && efectivo !== 'ATRACTIVO') return false
      if (ratingFilter !== 'BUYS' && ratingFilter !== 'ALL' && efectivo !== ratingFilter) return false
      return true
    })
  }, [data, typeFilter, ratingFilter])

  // Cabecera también mientras carga o si la API falla: si no, la pantalla
  // de error no dice en qué sección estás. Ver PageShell.
  if (loading || error || !data) return (
    <PageShell
      title="Materias Primas"
      loading={loading}
      error={loading ? null : (typeof error === 'string' ? error : 'Error cargando materias primas')}
    />
  )

  const generatedAt = data[0]?.generated_at ? new Date(data[0].generated_at).toLocaleString('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : null

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <PageHeader
        title="Materias Primas"
        subtitle={<>{data.length} ETFs y ETC · rating por precio frente a su media de 2 años · solo cuenta lo que la revisión avala{generatedAt && <span className="ml-2">· actualizado {generatedAt}</span>}</>}
      />

      <SummaryCards data={data} />

      {/* Filtros.
          Eran dos grupos de píldoras hechas a mano, pegados y los dos
          empezando por «Todos», sin nada que dijera qué filtraba cada uno: se
          leía como una sola barra con el mismo botón repetido. Y el estado
          activo iba en `bg-cyan-500/20 text-cyan-400`, el cian del tema oscuro
          escrito a pelo, que sobre fondo claro no significa nada.
          Ahora usan `.filter-label` + `.filter-btn`, que es lo que usa el resto
          de la app, con el separador de por medio. */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="flex flex-wrap items-center gap-1">
          <span className="filter-label mr-0.5">Tipo</span>
          {[{ id: 'ALL', label: 'Todos' }, ...ALL_TYPES.map(t => ({ id: t, label: TYPE_LABELS[t] ?? t }))].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setTypeFilter(id)}
              className={cn('filter-btn', typeFilter === id && 'active')}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-1">
          <span className="filter-label mr-0.5">Valoración</span>
          {[
            { id: 'ALL',  label: 'Todas' },
            { id: 'BUYS', label: 'Atractivos' },
            { id: 'SIN_VERIFICAR', label: 'Por verificar' },
            { id: 'NEUTRAL', label: 'Neutral' },
            { id: 'CARO', label: 'Caro' },
          ].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setRatingFilter(id)}
              className={cn('filter-btn', ratingFilter === id && 'active')}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Móvil: tarjetas. La tabla tiene 10 columnas y en 390px sobrevivían
          cuatro; el veredicto (rating) competía por sitio con el precio y el
          rango. Aquí manda, que es lo que se viene a mirar. */}
      <div className="sm:hidden space-y-2.5">
        {filtered.map(item => <CommodityCard key={item.ticker} item={item} />)}
      </div>

      {/* Table */}
      <Card className="glass hidden sm:block">
        <CardContent className="p-0">
          <div className="table-x-wrap">
            <table className="w-full text-cuerpo">
              <thead>
                <tr className="border-b border-foreground/10 text-left">
                  <th className="px-4 py-3 text-mini text-muted-foreground font-medium">Ticker</th>
                  <th className="py-3 pr-3 text-mini text-muted-foreground font-medium hidden md:table-cell">Tipo</th>
                  <th className="py-3 pr-3 text-mini text-muted-foreground font-medium">Precio</th>
                  <th className="py-3 pr-4 text-mini text-muted-foreground font-medium hidden sm:table-cell">Rango 52s</th>
                  <th className="py-3 pr-3 text-mini text-muted-foreground font-medium hidden sm:table-cell whitespace-nowrap">Vs 2a avg</th>
                  <th className="py-3 pr-3 text-mini text-muted-foreground font-medium hidden lg:table-cell">1d</th>
                  <th className="py-3 pr-3 text-mini text-muted-foreground font-medium hidden md:table-cell">Momentum</th>
                  <th className="py-3 pr-3 text-mini text-muted-foreground font-medium hidden lg:table-cell">Estacional</th>
                  <th className="py-3 pr-3 text-mini text-muted-foreground font-medium">Rating</th>
                  <th className="py-3 px-4" />
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="p-0">
                      <EmptyState compact title="Sin resultados con los filtros seleccionados" />
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
      <div className="flex flex-wrap gap-4 text-mini text-muted-foreground pb-4">
        <span><strong className="text-muted-foreground">Rango 52s:</strong> 0% = mínimo anual · 100% = máximo anual</span>
        <span><strong className="text-muted-foreground">Vs 2a avg:</strong> % sobre/bajo media de 2 años (negativo = barato)</span>
        <span><strong className="text-muted-foreground">VALUE rating:</strong> basado en posición de precio histórica + estacionalidad</span>
      </div>
    </div>
  )
}
