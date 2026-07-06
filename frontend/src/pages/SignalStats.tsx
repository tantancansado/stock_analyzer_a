import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { fetchTimeseries, type TimeseriesRow, type StrategyRow } from '../api/client'
import Loading, { ErrorState } from '@/components/Loading'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

type Tab = 'week' | 'month' | 'quarter' | 'weekday'

const TABS: { id: Tab; label: string }[] = [
  { id: 'week',    label: 'Semana' },
  { id: 'month',   label: 'Mes' },
  { id: 'quarter', label: 'Quarter' },
  { id: 'weekday', label: 'Día semana' },
]

function ReturnBadge({ v }: { v: number | null }) {
  if (v === null || v === undefined) return <span className="text-white/30 text-xs">—</span>
  const color = v > 0 ? '#10b981' : v > -2 ? '#f59e0b' : '#ef4444'
  return <span className="text-xs font-mono" style={{ color }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>
}

function WinBadge({ v }: { v: number | null }) {
  if (v === null || v === undefined) return <span className="text-white/30 text-xs">—</span>
  const color = v >= 50 ? '#10b981' : v >= 35 ? '#f59e0b' : '#ef4444'
  return <span className="text-xs font-mono font-semibold" style={{ color }}>{v.toFixed(1)}%</span>
}

function MiniBar({ value, max, color = '#22d3ee' }: { value: number; max: number; color?: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.07)' }}>
        <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-mono text-white/60">{value}</span>
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

function TimeseriesTable({ rows, tab }: { rows: TimeseriesRow[]; tab: Tab }) {
  const maxSignals = Math.max(...rows.map(r => r.signals), 1)
  const showStrategy = tab !== 'weekday'
  return (
    <div className="table-x-wrap">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10 text-left">
            <th className="pb-2 text-xs text-white/40 font-medium w-28">Período</th>
            <th className="pb-2 text-xs text-white/40 font-medium">Señales</th>
            <th className="pb-2 text-xs text-white/40 font-medium pl-3">Win 14d</th>
            <th className="pb-2 text-xs text-white/40 font-medium pl-3">Win 30d</th>
            <th className="pb-2 text-xs text-white/40 font-medium text-right">Ret. 14d</th>
            <th className="pb-2 text-xs text-white/40 font-medium text-right">Ret. 30d</th>
            {showStrategy && <th className="pb-2 text-xs text-white/40 font-medium text-right">US/EU</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={row.label} className="border-b border-white/5 hover:bg-white/5 transition-colors">
              <td className="py-2.5 text-white font-medium text-xs">{fmtLabel(tab, row.label)}</td>
              <td className="py-2.5">
                <MiniBar value={row.signals} max={maxSignals} />
              </td>
              <td className="py-2.5 pl-3 min-w-[130px]">
                <WinBar value={row.win_rate_14d} />
              </td>
              <td className="py-2.5 pl-3 min-w-[130px]">
                <WinBar value={row.win_rate_30d} />
              </td>
              <td className="py-2.5 text-right"><ReturnBadge v={row.avg_return_14d} /></td>
              <td className="py-2.5 text-right"><ReturnBadge v={row.avg_return_30d} /></td>
              {showStrategy && (
                <td className="py-2.5 text-right">
                  <span className="text-xs font-mono text-emerald-400">{row.value_us ?? 0}</span>
                  <span className="text-white/30 mx-1">/</span>
                  <span className="text-xs font-mono text-blue-400">{row.value_eu ?? 0}</span>
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
  const color: Record<string, string> = {
    VALUE: '#22c55e',
    EU_VALUE: '#3b82f6',
    MOMENTUM: '#f97316',
  }
  const c = color[row.strategy] ?? '#94a3b8'
  const name = label[row.strategy] ?? row.strategy

  return (
    <Card className="glass">
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-white">{name}</span>
          <span className="text-xs font-mono text-white/40">{row.signals} señales</span>
        </div>
        <div className="space-y-2.5">
          <div>
            <div className="flex justify-between text-xs text-white/40 mb-1">
              <span>Win Rate 14d</span>
              <WinBadge v={row.win_rate_14d} />
            </div>
            <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.07)' }}>
              <div className="h-1.5 rounded-full" style={{
                width: `${Math.min((row.win_rate_14d ?? 0) / 80 * 100, 100)}%`,
                background: c,
              }} />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-xs text-white/40 mb-1">
              <span>Win Rate 30d</span>
              <WinBadge v={row.win_rate_30d} />
            </div>
            <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.07)' }}>
              <div className="h-1.5 rounded-full" style={{
                width: `${Math.min((row.win_rate_30d ?? 0) / 80 * 100, 100)}%`,
                background: c,
              }} />
            </div>
          </div>
          <div className="flex justify-between pt-1 border-t border-white/5">
            <div className="text-center">
              <div className="text-xs text-white/40 mb-0.5">Ret. 14d</div>
              <ReturnBadge v={row.avg_return_14d} />
            </div>
            <div className="text-center">
              <div className="text-xs text-white/40 mb-0.5">Ret. 30d</div>
              <ReturnBadge v={row.avg_return_30d} />
            </div>
            <div className="text-center">
              <div className="text-xs text-white/40 mb-0.5">Drawdown</div>
              <span className="text-xs font-mono text-red-400">{row.avg_drawdown.toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function BestWorstRows({ rows, tab }: { rows: TimeseriesRow[]; tab: Tab }) {
  const completed = rows.filter(r => r.win_rate_14d !== null && r.signals >= 5)
  if (completed.length < 2) return null
  const sorted = [...completed].sort((a, b) => (b.win_rate_14d ?? 0) - (a.win_rate_14d ?? 0))
  const best = sorted.slice(0, 3)
  const worst = sorted.slice(-3).reverse()
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card className="glass">
        <CardContent className="p-5">
          <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-3">Mejores períodos</div>
          <div className="space-y-2">
            {best.map(r => (
              <div key={r.label} className="flex items-center justify-between">
                <span className="text-sm text-white">{fmtLabel(tab, r.label)}</span>
                <div className="flex items-center gap-3">
                  <WinBadge v={r.win_rate_14d} />
                  <ReturnBadge v={r.avg_return_14d} />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card className="glass">
        <CardContent className="p-5">
          <div className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-3">Peores períodos</div>
          <div className="space-y-2">
            {worst.map(r => (
              <div key={r.label} className="flex items-center justify-between">
                <span className="text-sm text-white">{fmtLabel(tab, r.label)}</span>
                <div className="flex items-center gap-3">
                  <WinBadge v={r.win_rate_14d} />
                  <ReturnBadge v={r.avg_return_14d} />
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

  if (loading) return <Loading />
  if (error) return <ErrorState message={typeof error === 'string' ? error : 'Error cargando datos'} />
  if (!data) return null

  const rows: TimeseriesRow[] = tab === 'week' ? data.by_week
    : tab === 'month' ? data.by_month
    : tab === 'quarter' ? data.by_quarter
    : data.by_weekday

  const avgWin14 = data.by_strategy.reduce((s, r) => s + (r.win_rate_14d ?? 0) * r.signals, 0)
    / Math.max(data.by_strategy.reduce((s, r) => s + r.signals, 0), 1)

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Estadísticas de señales</h1>
        <p className="text-sm text-white/40 mt-1">
          {data.total_completed.toLocaleString()} señales completadas · {data.date_range.from} → {data.date_range.to}
        </p>
      </div>

      {/* KPIs globales */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="glass">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold font-mono text-white">{data.total_completed.toLocaleString()}</div>
            <div className="text-xs text-white/40 mt-0.5">Señales completadas</div>
          </CardContent>
        </Card>
        <Card className="glass">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold font-mono" style={{ color: avgWin14 >= 50 ? '#10b981' : '#f59e0b' }}>
              {avgWin14.toFixed(1)}%
            </div>
            <div className="text-xs text-white/40 mt-0.5">Win rate global 14d</div>
          </CardContent>
        </Card>
        <Card className="glass">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold font-mono text-white">{data.by_strategy.length}</div>
            <div className="text-xs text-white/40 mt-0.5">Estrategias activas</div>
          </CardContent>
        </Card>
      </div>

      {/* Por estrategia */}
      <div>
        <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-3">Por estrategia</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.by_strategy.map(s => <StrategyCard key={s.strategy} row={s} />)}
        </div>
      </div>

      {/* Tabla temporal */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider">Evolución temporal</h2>
          <div className="flex gap-1 p-1 rounded-lg" style={{ background: 'rgba(255,255,255,0.05)' }}>
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  'px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                  tab === t.id
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'text-white/40 hover:text-white/70',
                )}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <Card className="glass">
          <CardContent className="p-5">
            <TimeseriesTable rows={rows} tab={tab} />
          </CardContent>
        </Card>
      </div>

      {/* Mejores / peores */}
      {tab !== 'weekday' && (
        <div>
          <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider mb-3">Ranking de períodos</h2>
          <BestWorstRows rows={rows} tab={tab} />
        </div>
      )}

      {/* Nota */}
      <p className="text-xs text-white/25 text-center pb-4">
        Solo señales completadas · mín. 5 señales para ranking · win rate = retorno positivo a vencimiento
      </p>
    </div>
  )
}
