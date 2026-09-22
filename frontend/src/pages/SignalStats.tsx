import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { fetchTimeseries, type TimeseriesRow, type StrategyRow } from '../api/client'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import PageHeader from '@/components/PageHeader'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid,
} from 'recharts'
import PageShell from '@/components/PageShell'

type Tab = 'week' | 'month' | 'quarter' | 'weekday'

const TABS: { id: Tab; label: string }[] = [
  { id: 'week',    label: 'Semana' },
  { id: 'month',   label: 'Mes' },
  { id: 'quarter', label: 'Quarter' },
  { id: 'weekday', label: 'Día semana' },
]

function ReturnBadge({ v }: { v: number | null }) {
  if (v === null || v === undefined) return <span className="text-muted-foreground text-mini">—</span>
  const color = v > 0 ? '#10b981' : v > -2 ? '#f59e0b' : '#ef4444'
  return <span className="text-mini font-mono" style={{ color }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>
}

function WinBadge({ v }: { v: number | null }) {
  if (v === null || v === undefined) return <span className="text-muted-foreground text-mini">—</span>
  const color = v >= 50 ? '#10b981' : v >= 35 ? '#f59e0b' : '#ef4444'
  return <span className="text-mini font-mono font-semibold" style={{ color }}>{v.toFixed(1)}%</span>
}

function MiniBar({ value, max, color = '#22d3ee' }: { value: number; max: number; color?: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.07)' }}>
        <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-mini font-mono text-muted-foreground">{value}</span>
    </div>
  )
}

function WinBar({ value, max = 80 }: { value: number | null; max?: number }) {
  const v = value ?? 0
  const pct = Math.min((v / max) * 100, 100)
  const color = v >= 50 ? '#10b981' : v >= 35 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.07)' }}>
        <div className="h-1.5 rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <WinBadge v={value} />
    </div>
  )
}

/**
 * Intervalo de confianza al 95% bajo el win rate.
 *
 * Momentum salía con "100.0%" en verde y 18 señales, sin nada que dijera que
 * su intervalo real va del 82% al 100%. Al lado, VALUE con 42,1% y 801
 * señales tiene un intervalo de tres puntos. En pantalla los dos se leían
 * igual de firmes.
 */
/** Por debajo de esto el win rate no concluye nada. Es el mismo umbral que
 *  usa cerebro.py para no destacar un patrón (MUESTRA_MINIMA = 30). */
const MUESTRA_MINIMA = 30

function Intervalo({ low, high, n }: { readonly low: number | null; readonly high: number | null; readonly n: number }) {
  if (low == null || high == null) return null
  return (
    <div className="mt-1 flex flex-wrap items-baseline gap-x-1.5 text-micro text-muted-foreground tabular-nums">
      <span>IC 95%: {low}–{high}%</span>
      {n < MUESTRA_MINIMA && (
        <span className="text-amber-400" title={`Con ${n} señales el intervalo real va del ${low}% al ${high}%`}>
          · solo {n} señales
        </span>
      )}
    </div>
  )
}

function fmtLabel(tab: Tab, label: string) {
  if (tab === 'month') {
    const d = new Date(label)
    return d.toLocaleDateString('es-ES', { month: 'short', year: 'numeric' })
  }
  if (tab === 'week') {
    const d = new Date(label)
    return `${d.getDate()} ${d.toLocaleDateString('es-ES', { month: 'short' })}`
  }
  return label
}

/**
 * "¿Qué funciona y qué no?" era una tabla de números que había que leer fila
 * a fila para notar una tendencia. Aquí la misma serie como curva: una racha
 * mala o una mejora sostenida se ve en medio segundo, sin sumar en la cabeza.
 * La tabla de abajo sigue para el detalle.
 *
 * Los plazos ya no están escritos aquí: los manda el backend (90 y 180 días).
 * Eran 14 y 30, y a esos plazos una tesis VALUE no ha hecho nada todavía — el
 * gráfico enseñaba ruido con forma de tendencia.
 */
function WinRateTrend({ rows, tab }: { rows: TimeseriesRow[]; tab: Tab }) {
  const h1 = rows.find(r => r.horizonte)?.horizonte ?? '90d'
  const h2 = rows.find(r => r.horizonte_2)?.horizonte_2 ?? '180d'
  const data = rows
    .filter(r => r.win_rate != null || r.win_rate_2 != null)
    .map(r => ({ label: fmtLabel(tab, r.label), principal: r.win_rate, secundario: r.win_rate_2, signals: r.signals }))
  if (data.length < 2) return null
  return (
    <div className="h-40 -ml-2">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.35)' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.35)' }} axisLine={false} tickLine={false}
            width={32} tickFormatter={v => `${v}%`} />
          {/* 50% es el umbral de "gana más de lo que pierde", no un cero arbitrario */}
          <ReferenceLine y={50} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4" />
          <Tooltip
            contentStyle={{ background: 'rgba(15,23,35,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
            formatter={(v, name) => [`${Number(v).toFixed(1)}%`, name === 'principal' ? `Win ${h1}` : `Win ${h2}`]}
          />
          <Line type="monotone" dataKey="principal" stroke="#22d3ee" strokeWidth={2} dot={false} connectNulls />
          <Line type="monotone" dataKey="secundario" stroke="#a78bfa" strokeWidth={2} dot={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function TimeseriesTable({ rows, tab }: { rows: TimeseriesRow[]; tab: Tab }) {
  const maxSignals = Math.max(...rows.map(r => r.signals), 1)
  const showStrategy = tab !== 'weekday'
  const h1 = rows.find(r => r.horizonte)?.horizonte ?? '90d'
  const h2 = rows.find(r => r.horizonte_2)?.horizonte_2 ?? '180d'
  return (
    <div className="table-x-wrap">
      <table className="w-full text-cuerpo">
        <thead>
          <tr className="border-b border-foreground/10 text-left">
            <th className="pb-2 text-mini text-muted-foreground font-medium w-28">Período</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium">Señales</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium pl-3">Win {h1}</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium pl-3">Win {h2}</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium text-right">Ret. {h1}</th>
            <th className="pb-2 text-mini text-muted-foreground font-medium text-right">Ret. {h2}</th>
            {showStrategy && <th className="pb-2 text-mini text-muted-foreground font-medium text-right">US/EU</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={row.label} className="border-b border-foreground/5 hover:bg-foreground/5 transition-colors">
              <td className="py-2.5 text-foreground font-medium text-mini">{fmtLabel(tab, row.label)}</td>
              <td className="py-2.5">
                <MiniBar value={row.signals} max={maxSignals} />
              </td>
              <td className="py-2.5 pl-3 min-w-[130px]">
                <WinBar value={row.win_rate} />
              </td>
              <td className="py-2.5 pl-3 min-w-[130px]">
                <WinBar value={row.win_rate_2} />
              </td>
              <td className="py-2.5 text-right"><ReturnBadge v={row.avg_return} /></td>
              <td className="py-2.5 text-right"><ReturnBadge v={row.avg_return_2} /></td>
              {showStrategy && (
                <td className="py-2.5 text-right">
                  <span className="text-mini font-mono text-emerald-400">{row.value_us ?? 0}</span>
                  <span className="text-muted-foreground mx-1">/</span>
                  <span className="text-mini font-mono text-blue-400">{row.value_eu ?? 0}</span>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function StrategyCard({ row }: { row: StrategyRow }) {
  const label: Record<string, string> = {
    VALUE: 'Value US',
    EU_VALUE: 'Value EU',
    MOMENTUM: 'Momentum',
  }
  // La barra se pintaba con un color POR ESTRATEGIA: Momentum salía naranja
  // al 100% y Value US verde al 42%, así que el color no decía nada del dato
  // y encima sugería lo contrario. El win rate ya lleva su propio color en el
  // badge de la derecha; aquí basta con una barra neutra que muestre magnitud.
  const c = 'color-mix(in oklab, var(--muted-foreground) 55%, transparent)'
  const name = label[row.strategy] ?? row.strategy

  return (
    <Card className="glass">
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-cuerpo font-semibold text-foreground">{name}</span>
          <span className="text-mini font-mono text-muted-foreground">{row.signals} señales</span>
        </div>
        {/* Los rebotes técnicos SÍ son de corto plazo por diseño: medirlos a 90
            días mezclaría el rebote con lo que viniera después. El backend
            manda el plazo de cada estrategia y aquí solo se rotula. */}
        {row.corto_plazo && (
          <p className="text-micro text-muted-foreground mb-2.5">
            Estrategia de corto plazo — se mide a {row.horizonte.replace('d', ' días')},
            no a los {row.horizonte_2.replace('d', ' días')} del resto.
          </p>
        )}
        <div className="space-y-2.5">
          <div>
            <div className="flex justify-between text-mini text-muted-foreground mb-1">
              <span>Win Rate {row.horizonte}</span>
              <WinBadge v={row.win_rate} />
            </div>
            <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.07)' }}>
              <div className="h-1.5 rounded-full" style={{
                width: `${Math.min((row.win_rate ?? 0) / 80 * 100, 100)}%`,
                background: c,
              }} />
            </div>
            <Intervalo low={row.ci_low} high={row.ci_high} n={row.muestra} />
          </div>
          <div>
            <div className="flex justify-between text-mini text-muted-foreground mb-1">
              <span>Win Rate {row.horizonte_2}</span>
              <WinBadge v={row.win_rate_2} />
            </div>
            <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.07)' }}>
              <div className="h-1.5 rounded-full" style={{
                width: `${Math.min((row.win_rate_2 ?? 0) / 80 * 100, 100)}%`,
                background: c,
              }} />
            </div>
            <Intervalo low={row.ci_low_2} high={row.ci_high_2} n={row.muestra_2} />
          </div>
          <div className="flex justify-between pt-1 border-t border-foreground/5">
            <div className="text-center">
              <div className="text-mini text-muted-foreground mb-0.5">Ret. {row.horizonte}</div>
              <ReturnBadge v={row.avg_return} />
            </div>
            <div className="text-center">
              <div className="text-mini text-muted-foreground mb-0.5">Ret. {row.horizonte_2}</div>
              <ReturnBadge v={row.avg_return_2} />
            </div>
            <div className="text-center">
              <div className="text-mini text-muted-foreground mb-0.5">Drawdown</div>
              <span className="text-mini font-mono text-red-400">{row.avg_drawdown.toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function BestWorstRows({ rows, tab }: { rows: TimeseriesRow[]; tab: Tab }) {
  const completed = rows.filter(r => r.win_rate !== null && r.signals >= 5)
  if (completed.length < 2) return null
  const sorted = [...completed].sort((a, b) => (b.win_rate ?? 0) - (a.win_rate ?? 0))
  const best = sorted.slice(0, 3)
  const worst = sorted.slice(-3).reverse()
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card className="glass">
        <CardContent className="p-5">
          <div className="etiqueta-seccion text-emerald-400 mb-3">Mejores períodos</div>
          <div className="space-y-2">
            {best.map(r => (
              <div key={r.label} className="flex items-center justify-between">
                <span className="text-cuerpo text-foreground">{fmtLabel(tab, r.label)}</span>
                <div className="flex items-center gap-3">
                  <WinBadge v={r.win_rate} />
                  <ReturnBadge v={r.avg_return} />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card className="glass">
        <CardContent className="p-5">
          <div className="etiqueta-seccion text-red-400 mb-3">Peores períodos</div>
          <div className="space-y-2">
            {worst.map(r => (
              <div key={r.label} className="flex items-center justify-between">
                <span className="text-cuerpo text-foreground">{fmtLabel(tab, r.label)}</span>
                <div className="flex items-center gap-3">
                  <WinBadge v={r.win_rate} />
                  <ReturnBadge v={r.avg_return} />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default function SignalStats() {
  const [tab, setTab] = useState<Tab>('month')
  const { data, loading, error } = useApi(() => fetchTimeseries(), [])

  // Cabecera también mientras carga o si la API falla: si no, la pantalla
  // de error no dice en qué sección estás. Ver PageShell.
  if (loading || error) return (
    <PageShell
      title="Estadísticas de señales"
      loading={loading}
      error={loading ? null : (typeof error === 'string' ? error : 'Error cargando datos')}
    />
  )
  if (!data) return null

  const rows: TimeseriesRow[] = tab === 'week' ? data.by_week
    : tab === 'month' ? data.by_month
    : tab === 'quarter' ? data.by_quarter
    : data.by_weekday

  // Solo las estrategias de plazo largo: promediar un rebote medido a 30 días
  // con una tesis VALUE medida a 90 da un número que no significa nada.
  // Y se pondera por MUESTRA, no por señales totales: el win rate se calcula
  // sobre las que tienen dato a ese plazo, y usar el otro denominador
  // infrapondera justo a las estrategias con menos cobertura.
  const largoPlazo = data.by_strategy.filter(r => !r.corto_plazo && r.win_rate != null)
  const muestraTotal = largoPlazo.reduce((s, r) => s + (r.muestra || 0), 0)
  const winGlobal = muestraTotal > 0
    ? largoPlazo.reduce((s, r) => s + (r.win_rate ?? 0) * (r.muestra || 0), 0) / muestraTotal
    : null
  const horizonteGlobal = largoPlazo[0]?.horizonte ?? '90d'

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <PageHeader
        title="Estadísticas de señales"
        subtitle={`${data.total_completed.toLocaleString()} señales completadas · ${data.date_range.from} → ${data.date_range.to}`}
      />

      {/* KPIs globales */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="glass">
          <CardContent className="p-4 text-center">
            <div className="text-pagina font-bold font-mono text-foreground">{data.total_completed.toLocaleString()}</div>
            <div className="text-mini text-muted-foreground mt-0.5">Señales completadas</div>
          </CardContent>
        </Card>
        <Card className="glass">
          <CardContent className="p-4 text-center">
            <div className="text-pagina font-bold font-mono" style={{ color: (winGlobal ?? 0) >= 50 ? '#10b981' : '#f59e0b' }}>
              {winGlobal != null ? `${winGlobal.toFixed(1)}%` : '—'}
            </div>
            <div className="text-mini text-muted-foreground mt-0.5">Win rate global {horizonteGlobal}</div>
          </CardContent>
        </Card>
        <Card className="glass">
          <CardContent className="p-4 text-center">
            <div className="text-pagina font-bold font-mono text-foreground">{data.by_strategy.length}</div>
            <div className="text-mini text-muted-foreground mt-0.5">Estrategias activas</div>
          </CardContent>
        </Card>
      </div>

      {/* Por estrategia */}
      <div>
        <h2 className="text-cuerpo font-semibold text-muted-foreground uppercase tracking-wider mb-3">Por estrategia</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.by_strategy.map(s => <StrategyCard key={s.strategy} row={s} />)}
        </div>
      </div>

      {/* Tabla temporal */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-cuerpo font-semibold text-muted-foreground uppercase tracking-wider">Evolución temporal</h2>
          <div className="flex gap-1 p-1 rounded-lg" style={{ background: 'rgba(255,255,255,0.05)' }}>
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  'px-3 py-1.5 rounded-md text-mini font-medium transition-all',
                  tab === t.id
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'text-muted-foreground hover:text-foreground/70',
                )}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <Card className="glass">
          <CardContent className="p-5">
            {/* by_weekday no es una serie cronológica (lunes→viernes se
                repite cada semana), así que una curva ahí mentiría sobre una
                tendencia que no existe. Solo en las pestañas con orden real. */}
            {tab !== 'weekday' && (
              <div className="mb-4 pb-4 border-b border-foreground/5">
                <div className="flex items-center gap-4 mb-2 text-micro">
                  <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                    <span className="w-2.5 h-0.5 rounded-full" style={{ background: '#22d3ee' }} /> Win {rows.find(r => r.horizonte)?.horizonte ?? '90d'}
                  </span>
                  <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                    <span className="w-2.5 h-0.5 rounded-full" style={{ background: '#a78bfa' }} /> Win {rows.find(r => r.horizonte_2)?.horizonte_2 ?? '180d'}
                  </span>
                </div>
                <WinRateTrend rows={rows} tab={tab} />
              </div>
            )}
            <TimeseriesTable rows={rows} tab={tab} />
          </CardContent>
        </Card>
      </div>

      {/* Mejores / peores */}
      {tab !== 'weekday' && (
        <div>
          <h2 className="text-cuerpo font-semibold text-muted-foreground uppercase tracking-wider mb-3">Ranking de períodos</h2>
          <BestWorstRows rows={rows} tab={tab} />
        </div>
      )}

      {/* Nota */}
      <p className="text-mini text-muted-foreground text-center pb-4">
        Solo señales completadas · mín. 5 señales para ranking · win rate = retorno positivo a vencimiento
      </p>
    </div>
  )
}
