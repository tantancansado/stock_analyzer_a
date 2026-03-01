import { useState } from 'react'
import { fetchMomentumOpportunities, type MomentumOpportunity, downloadCsv } from '../api/client'
import { useApi } from '../hooks/useApi'
import Loading, { ErrorState } from '../components/Loading'
import ScoreBar from '../components/ScoreBar'
import { Badge } from '@/components/ui/badge'
import InfoTooltip from '../components/InfoTooltip'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'

type SortKey = keyof MomentumOpportunity
type SortDir = 'asc' | 'desc'

export default function Momentum() {
  const { data, loading, error } = useApi(() => fetchMomentumOpportunities(), [])
  const [sortKey, setSortKey] = useState<SortKey>('momentum_score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  if (loading) return <Loading />
  if (error) return <ErrorState message={error} />

  const rows = data?.data ?? []
  const source = data?.source ?? ''

  const sorted = [...rows].sort((a, b) => {
    const av = a[sortKey] ?? 0; const bv = b[sortKey] ?? 0
    return sortDir === 'asc' ? (av < bv ? -1 : 1) : (av > bv ? -1 : 1)
  })

  const onSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const thCls = (key: SortKey) =>
    `cursor-pointer select-none whitespace-nowrap transition-colors hover:text-foreground ${sortKey === key ? 'text-primary' : ''}`

  const avgScore = rows.length ? rows.reduce((s, r) => s + (r.momentum_score || 0), 0) / rows.length : 0
  const vcpHigh = rows.filter(r => (r.vcp_score || 0) >= 70).length
  const nearHigh = rows.filter(r => r.proximity_to_52w_high != null && r.proximity_to_52w_high > -10).length
  const trendStrong = rows.filter(r => (r.trend_template_score || 0) >= 7).length

  return (
    <>
      <div className="mb-7 animate-fade-in-up flex items-start justify-between gap-4">
        <div className="flex-1">
          <h2 className="text-2xl font-extrabold tracking-tight mb-2 flex items-center gap-2">
            <span className="gradient-title">Momentum</span>
            {source && <span className="text-[0.58rem] font-bold uppercase tracking-widest text-muted-foreground/60 border border-border/50 rounded px-1.5 py-0.5">{source}</span>}
          </h2>
          <p className="text-sm text-muted-foreground">Setups VCP y momentum Minervini — filtrados por tendencia y volumen</p>
        </div>
        <button
          onClick={() => downloadCsv('momentum')}
          className="text-xs px-3 py-1 rounded border border-border/50 text-muted-foreground hover:text-foreground hover:border-primary transition-colors mt-1 shrink-0"
        >↓ CSV</button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        {[
          { label: 'Setups', value: rows.length, sub: 'configuraciones activas', idx: 1 },
          { label: 'Score Medio', value: avgScore.toFixed(1), sub: 'momentum score', color: avgScore >= 60 ? 'text-emerald-400' : 'text-amber-400', idx: 2 },
          { label: 'VCP Alto', value: vcpHigh, sub: 'VCP score 70+', color: 'text-blue-400', idx: 3 },
          { label: 'Cerca de Máximos', value: nearHigh, sub: `dentro del 10% | ${trendStrong} tendencia 7+/8`, color: 'text-emerald-400', idx: 4 },
        ].map(({ label, value, sub, color, idx }) => (
          <Card key={label} className={`glass p-5 stagger-${idx}`}>
            <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">{label}</div>
            <div className={`text-3xl font-extrabold tracking-tight tabular-nums leading-none mb-2 ${color ?? ''}`}>{value}</div>
            <div className="text-[0.66rem] text-muted-foreground">{sub}</div>
          </Card>
        ))}
      </div>

      <Card className="glass overflow-hidden animate-fade-in-up">
        <Table>
          <TableHeader>
            <TableRow className="border-border/50 hover:bg-transparent">
              <TableHead className={thCls('ticker')} onClick={() => onSort('ticker')}>Ticker</TableHead>
              <TableHead className={thCls('company_name')} onClick={() => onSort('company_name')}>Empresa</TableHead>
              <TableHead className={thCls('current_price')} onClick={() => onSort('current_price')}>Precio</TableHead>
              <TableHead className={thCls('momentum_score')} onClick={() => onSort('momentum_score')}>Score</TableHead>
              <TableHead className={thCls('vcp_score')} onClick={() => onSort('vcp_score')}>
                VCP
                <InfoTooltip
                  text="Volatility Contraction Pattern (Minervini): patrón de consolidación con contracciones de rango y volumen decreciente. Score 0-100. ≥70 = patrón de alta calidad."
                  align="left"
                />
              </TableHead>
              <TableHead className={thCls('proximity_to_52w_high')} onClick={() => onSort('proximity_to_52w_high')}>
                Dist.Max
                <InfoTooltip text="Distancia en % respecto al máximo de 52 semanas. Negativo = está por debajo del máximo. >-5% = muy cerca del máximo (zona de ruptura potencial)." />
              </TableHead>
              <TableHead className={thCls('trend_template_score')} onClick={() => onSort('trend_template_score')}>
                Tendencia
                <InfoTooltip
                  text={
                    <span>
                      Score Minervini Trend Template (0-8 criterios):<br />
                      precio &gt; MA50 · precio &gt; MA150 · precio &gt; MA200<br />
                      MA50 &gt; MA150 · MA150 &gt; MA200 · MA200 subiendo<br />
                      RS vs. mercado · precio cerca de máximos<br />
                      <span className="text-emerald-400">≥7/8</span> fuerte · <span className="text-amber-400">5-6/8</span> moderado
                    </span>
                  }
                  align="right"
                />
              </TableHead>
              <TableHead className={thCls('analyst_upside_pct')} onClick={() => onSort('analyst_upside_pct')}>Objetivo</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.slice(0, 20).map(d => (
              <TableRow key={d.ticker}>
                <TableCell className="font-mono font-bold text-primary text-[0.8rem] tracking-wide">{d.ticker}</TableCell>
                <TableCell className="max-w-[150px] truncate text-muted-foreground text-[0.76rem]">{d.company_name}</TableCell>
                <TableCell className="tabular-nums">${d.current_price?.toFixed(2)}</TableCell>
                <TableCell><ScoreBar score={d.momentum_score} /></TableCell>
                <TableCell><ScoreBar score={d.vcp_score} /></TableCell>
                <TableCell>
                  {d.proximity_to_52w_high != null
                    ? <span className={d.proximity_to_52w_high > -5 ? 'text-emerald-400' : d.proximity_to_52w_high > -15 ? 'text-amber-400' : 'text-red-400'}>
                        {d.proximity_to_52w_high.toFixed(1)}%
                      </span>
                    : <span className="text-muted-foreground">—</span>}
                </TableCell>
                <TableCell>
                  {d.trend_template_score != null
                    ? <Badge variant={d.trend_template_score >= 7 ? 'green' : d.trend_template_score >= 5 ? 'yellow' : 'red'}>
                        {d.trend_template_score}/8
                      </Badge>
                    : <span className="text-muted-foreground">—</span>}
                </TableCell>
                <TableCell className="tabular-nums">
                  {d.target_price_analyst ? `$${d.target_price_analyst.toFixed(0)}` : '—'}
                  {d.analyst_upside_pct != null && (
                    <span className={`ml-1 text-xs font-semibold ${d.analyst_upside_pct > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {d.analyst_upside_pct > 0 ? '+' : ''}{d.analyst_upside_pct.toFixed(0)}%
                    </span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {rows.length === 0 && (
          <CardContent className="py-16 text-center">
            <div className="text-4xl mb-4 opacity-20">📉</div>
            <p className="font-medium text-muted-foreground mb-1">Sin setups momentum en este momento</p>
            <span className="text-xs text-muted-foreground">Normal durante correcciones de mercado</span>
          </CardContent>
        )}
      </Card>
    </>
  )
}
