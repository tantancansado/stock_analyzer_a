import { useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import { fetchPortfolioSignals } from '../api/client'
import Loading, { ErrorState } from '../components/Loading'
import { Card, CardContent } from '@/components/ui/card'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Signal {
  ticker: string
  strategy: string
  signal_date: string
  return_14d: number | null
  return_30d: number | null
  win_14d: boolean | null
  win_30d: boolean | null
  market_regime: string
  sector: string
  value_score: number | null
  analyst_upside_pct: number | null
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, dec = 1) {
  if (n == null) return '—'
  return (n >= 0 ? '+' : '') + n.toFixed(dec) + '%'
}

function pct(n: number | null | undefined) {
  if (n == null) return '—'
  return (n * 100).toFixed(0) + '%'
}

function StatCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <Card className="bg-card/50">
      <CardContent className="p-4">
        <p className="text-[0.7rem] text-muted-foreground/60 uppercase tracking-wider mb-1">{label}</p>
        <p className={`text-xl font-bold tabular-nums ${color ?? 'text-foreground'}`}>{value}</p>
        {sub && <p className="text-[0.68rem] text-muted-foreground/50 mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  )
}

const REGIME_ORDER = ['CONFIRMED_UPTREND', 'UPTREND', 'UPTREND_PRESSURE', 'NEUTRAL', 'CORRECTION', 'BEAR']
const REGIME_LABEL: Record<string, string> = {
  CONFIRMED_UPTREND: 'Tendencia',
  UPTREND: 'Alcista',
  UPTREND_PRESSURE: 'Presión',
  NEUTRAL: 'Neutral',
  CORRECTION: 'Corrección',
  BEAR: 'Bajista',
}

// ── Main ─────────────────────────────────────────────────────────────────────

export default function BacktestResults() {
  const { data, loading, error } = useApi(() => fetchPortfolioSignals(), [])

  const { weekly, regimeStats, sectorStats, stats14d, stats30d, scoreQuartiles } = useMemo(() => {
    const raw: Signal[] = (data as unknown as Signal[]) ?? []
    const val = raw.filter(s =>
      ['VALUE', 'EU_VALUE'].includes(s.strategy) &&
      s.signal_date
    )

    // ── Global stats ─────────────────────────────────────────────────────────
    const valid14 = val.filter(s => s.return_14d != null && s.return_14d > -95 && s.return_14d < 200)
    const valid30 = val.filter(s => s.return_30d != null && s.return_30d > -95 && s.return_30d < 500)

    const avg = (arr: number[]) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null
    const winRate = (arr: Signal[], ret: keyof Signal) =>
      arr.filter(s => s[ret] != null).length
        ? arr.filter(s => (s[ret] as number | null) != null && (s[ret] as number) > 0).length /
          arr.filter(s => s[ret] != null).length
        : null

    const stats14d = {
      n: valid14.length,
      avg: avg(valid14.map(s => s.return_14d!)),
      wr: winRate(valid14, 'return_14d'),
      best: valid14.length ? Math.max(...valid14.map(s => s.return_14d!)) : null,
      worst: valid14.length ? Math.min(...valid14.map(s => s.return_14d!)) : null,
    }
    const stats30d = {
      n: valid30.length,
      avg: avg(valid30.map(s => s.return_30d!)),
      wr: winRate(valid30, 'return_30d'),
      best: valid30.length ? Math.max(...valid30.map(s => s.return_30d!)) : null,
      worst: valid30.length ? Math.min(...valid30.map(s => s.return_30d!)) : null,
    }

    // ── Weekly equity curve ──────────────────────────────────────────────────
    const byWeek = new Map<string, number[]>()
    for (const s of valid14) {
      const d = new Date(s.signal_date)
      // ISO week key
      const day = d.getDay()
      const monday = new Date(d)
      monday.setDate(d.getDate() - ((day + 6) % 7))
      const key = monday.toISOString().slice(0, 10)
      if (!byWeek.has(key)) byWeek.set(key, [])
      byWeek.get(key)!.push(s.return_14d! / 100)
    }
    const weekKeys = Array.from(byWeek.keys()).sort()
    let cum = 1
    const weekly = weekKeys.map(w => {
      const rets = byWeek.get(w)!
      const avgRet = rets.reduce((a, b) => a + b, 0) / rets.length
      cum *= (1 + avgRet)
      return {
        week: w.slice(5), // MM-DD
        ret: +(avgRet * 100).toFixed(2),
        cum: +((cum - 1) * 100).toFixed(2),
        n: rets.length,
      }
    })

    // ── By market regime ─────────────────────────────────────────────────────
    const regimeMap = new Map<string, number[]>()
    for (const s of valid14) {
      const r = s.market_regime ?? 'UNKNOWN'
      if (!regimeMap.has(r)) regimeMap.set(r, [])
      regimeMap.get(r)!.push(s.return_14d!)
    }
    const regimeStats = REGIME_ORDER
      .filter(r => regimeMap.has(r))
      .map(r => {
        const rets = regimeMap.get(r)!
        const avgR = avg(rets)!
        const wr = rets.filter(x => x > 0).length / rets.length
        return { regime: REGIME_LABEL[r] ?? r, avg: +avgR.toFixed(2), wr: +(wr * 100).toFixed(1), n: rets.length }
      })

    // ── By sector ────────────────────────────────────────────────────────────
    const sectorMap = new Map<string, number[]>()
    for (const s of valid14) {
      const sec = s.sector || 'Other'
      if (!sectorMap.has(sec)) sectorMap.set(sec, [])
      sectorMap.get(sec)!.push(s.return_14d!)
    }
    const sectorStats = Array.from(sectorMap.entries())
      .filter(([, rets]) => rets.length >= 5)
      .map(([sec, rets]) => ({
        sector: sec.replace('Communication Services', 'Comms').replace('Consumer ', ''),
        avg: +(avg(rets)!).toFixed(2),
        wr: +(rets.filter(x => x > 0).length / rets.length * 100).toFixed(1),
        n: rets.length,
      }))
      .sort((a, b) => b.avg - a.avg)

    // ── Score quartiles ───────────────────────────────────────────────────────
    const scored = valid14.filter(s => s.value_score != null).sort((a, b) => a.value_score! - b.value_score!)
    const q = (arr: Signal[], lo: number, hi: number) => {
      const slice = arr.slice(Math.floor(arr.length * lo), Math.floor(arr.length * hi))
      const r = slice.map(s => s.return_14d!)
      return r.length ? { avg: +(avg(r)!).toFixed(2), wr: +(r.filter(x => x > 0).length / r.length * 100).toFixed(1), n: r.length } : null
    }
    const scoreQuartiles = [
      { label: 'Q1 bajo', ...q(scored, 0, 0.25) },
      { label: 'Q2', ...q(scored, 0.25, 0.5) },
      { label: 'Q3', ...q(scored, 0.5, 0.75) },
      { label: 'Q4 alto', ...q(scored, 0.75, 1) },
    ].filter(q => q.avg != null)

    return { weekly, regimeStats, sectorStats, stats14d, stats30d, scoreQuartiles }
  }, [data])

  if (loading) return <Loading />
  if (error) return <ErrorState message={error} />
  if (!stats14d.n) return (
    <Card><CardContent className="py-16 text-center text-muted-foreground text-sm">Sin datos de señales completadas</CardContent></Card>
  )

  const cumFinal = weekly.at(-1)?.cum ?? 0
  const cumColor = cumFinal >= 0 ? '#22c55e' : '#ef4444'

  return (
    <div className="space-y-6">

      {/* Global KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Señales VALUE" value={stats14d.n.toString()} sub={`${stats30d.n} con 30d`} />
        <StatCard
          label="Ret. medio 14d"
          value={fmt(stats14d.avg)}
          sub={`30d: ${fmt(stats30d.avg)}`}
          color={stats14d.avg != null && stats14d.avg >= 0 ? 'text-emerald-400' : 'text-red-400'}
        />
        <StatCard
          label="Win rate 14d"
          value={pct(stats14d.wr)}
          sub={`30d: ${pct(stats30d.wr)}`}
          color={(stats14d.wr ?? 0) >= 0.5 ? 'text-emerald-400' : (stats14d.wr ?? 0) >= 0.4 ? 'text-amber-400' : 'text-red-400'}
        />
        <StatCard
          label="Mejor / peor"
          value={`${fmt(stats14d.best, 0)} / ${fmt(stats14d.worst, 0)}`}
          sub="retorno 14d"
        />
      </div>

      {/* Equity curve */}
      {weekly.length > 1 && (
        <Card className="bg-card/50">
          <CardContent className="p-4">
            <p className="text-[0.72rem] font-semibold text-muted-foreground/70 uppercase tracking-wider mb-3">
              Curva de capital acumulada (retorno medio por semana, base 0)
            </p>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={weekly} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="cumGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={cumColor} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={cumColor} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="week" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.35)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.35)' }} tickFormatter={v => `${v}%`} />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" />
                <Tooltip
                  contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                  formatter={(v) => { const n = v as number ?? 0; return [`${n > 0 ? '+' : ''}${n.toFixed(2)}%`, 'Acum.'] }}
                />
                <Area type="monotone" dataKey="cum" stroke={cumColor} strokeWidth={2} fill="url(#cumGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* By regime */}
        <Card className="bg-card/50">
          <CardContent className="p-4">
            <p className="text-[0.72rem] font-semibold text-muted-foreground/70 uppercase tracking-wider mb-3">
              Retorno medio por régimen de mercado (14d)
            </p>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={regimeStats} layout="vertical" margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.35)' }} tickFormatter={v => `${v}%`} />
                <YAxis dataKey="regime" type="category" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.45)' }} width={70} />
                <ReferenceLine x={0} stroke="rgba(255,255,255,0.15)" />
                <Tooltip
                  contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                  formatter={(v, name) => { const n = v as number ?? 0; return [name === 'avg' ? `${n > 0 ? '+' : ''}${n.toFixed(2)}%` : `${n}%`, name === 'avg' ? 'Retorno' : 'Win rate'] }}
                />
                <Bar dataKey="avg" radius={[0, 4, 4, 0]}>
                  {regimeStats.map((r, i) => (
                    <Cell key={i} fill={r.avg >= 0 ? '#22c55e' : '#ef4444'} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Score quartiles */}
        <Card className="bg-card/50">
          <CardContent className="p-4">
            <p className="text-[0.72rem] font-semibold text-muted-foreground/70 uppercase tracking-wider mb-3">
              Retorno por cuartil de value_score — ¿el score predice resultados?
            </p>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={scoreQuartiles} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="label" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.45)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.35)' }} tickFormatter={v => `${v}%`} />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" />
                <Tooltip
                  contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                  formatter={(v) => { const n = v as number ?? 0; return [`${n > 0 ? '+' : ''}${n.toFixed(2)}%`, 'Retorno medio'] }}
                />
                <Bar dataKey="avg" radius={[4, 4, 0, 0]}>
                  {scoreQuartiles.map((q, i) => (
                    <Cell key={i} fill={q.avg! >= 0 ? '#22c55e' : '#ef4444'} fillOpacity={0.7 + i * 0.075} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

      </div>

      {/* By sector */}
      {sectorStats.length > 0 && (
        <Card className="bg-card/50">
          <CardContent className="p-4">
            <p className="text-[0.72rem] font-semibold text-muted-foreground/70 uppercase tracking-wider mb-3">
              Retorno medio por sector (14d, mín. 5 señales)
            </p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={sectorStats} layout="vertical" margin={{ top: 0, right: 8, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.35)' }} tickFormatter={v => `${v}%`} />
                <YAxis dataKey="sector" type="category" tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.45)' }} width={90} />
                <ReferenceLine x={0} stroke="rgba(255,255,255,0.15)" />
                <Tooltip
                  contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                  formatter={(v) => { const n = v as number ?? 0; return [`${n > 0 ? '+' : ''}${n.toFixed(2)}%`, 'Retorno'] }}
                />
                <Bar dataKey="avg" radius={[0, 4, 4, 0]}>
                  {sectorStats.map((s, i) => (
                    <Cell key={i} fill={s.avg >= 0 ? '#22c55e' : '#ef4444'} fillOpacity={0.75} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      <p className="text-[0.68rem] text-muted-foreground/40 text-center">
        Datos reales de señales VALUE generadas por el sistema · Retornos sin costes de transacción ni slippage · No es una promesa de rentabilidad futura
      </p>
    </div>
  )
}
