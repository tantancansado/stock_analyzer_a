import { useState } from 'react'
import { fetchOptionsFlow, fetchOptionsFlowInsight, downloadCsv } from '../api/client'
import { useApi } from '../hooks/useApi'
import AiNarrativeCard from '../components/AiNarrativeCard'
import TickerLogo from '../components/TickerLogo'
import Loading, { ErrorState } from '../components/Loading'
import ScoreBar from '../components/ScoreBar'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'

interface FlowItem {
  ticker: string
  company_name?: string
  sentiment: string
  flow_score: number
  quality: string
  current_price?: number
  total_premium?: number
  put_call_ratio?: number
  unusual_calls?: number
  unusual_puts?: number
  sentiment_emoji?: string
  [key: string]: unknown
}

export default function OptionsFlow() {
  const { data, loading, error } = useApi(() => fetchOptionsFlow(), [])
  const { data: insightRaw } = useApi(() => fetchOptionsFlowInsight(), [])
  const [sortKey, setSortKey] = useState<string>('flow_score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  if (loading) return <Loading />
  if (error) return <ErrorState message={error} />

  const raw = data as Record<string, unknown>
  let flows: FlowItem[] = []
  if (Array.isArray(raw?.flows)) flows = raw.flows as FlowItem[]
  else if (Array.isArray(raw?.data)) flows = raw.data as FlowItem[]

  const sorted = [...flows].sort((a, b) => {
    const av = (a[sortKey] as number) ?? 0
    const bv = (b[sortKey] as number) ?? 0
    return sortDir === 'asc' ? (av < bv ? -1 : 1) : (av > bv ? -1 : 1)
  })

  const onSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const thCls = (key: string) =>
    `cursor-pointer select-none whitespace-nowrap transition-colors hover:text-foreground ${sortKey === key ? 'text-primary' : ''}`

  const sentVariant = (s: string): 'green' | 'red' | 'yellow' => {
    const upper = (s || '').toUpperCase()
    if (upper.includes('BULL')) return 'green'
    if (upper.includes('BEAR')) return 'red'
    return 'yellow'
  }

  const fmtPremium = (v?: number) => {
    if (v == null) return '—'
    if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
    if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`
    return `$${v.toFixed(0)}`
  }

  const bullish = flows.filter(f => (f.sentiment || '').toUpperCase().includes('BULL')).length
  const bearish = flows.filter(f => (f.sentiment || '').toUpperCase().includes('BEAR')).length
  const totalPremium = flows.reduce((s, f) => s + (f.total_premium || 0), 0)
  const avgScore = flows.length ? flows.reduce((s, f) => s + (f.flow_score || 0), 0) / flows.length : 0

  return (
    <>
      <div className="mb-7 animate-fade-in-up flex items-start justify-between gap-4">
        <div className="flex-1">
          <h2 className="text-2xl font-extrabold tracking-tight mb-2 gradient-title">Options Flow</h2>
          <p className="text-sm text-muted-foreground">Flujo de opciones inusual — actividad institucional y whale</p>
        </div>
        <button
          onClick={() => downloadCsv('options-flow')}
          className="text-xs px-3 py-1 rounded border border-border/50 text-muted-foreground hover:text-foreground hover:border-primary transition-colors mt-1 shrink-0"
        >↓ CSV</button>
      </div>

      {insightRaw?.narrative && (
        <AiNarrativeCard narrative={insightRaw.narrative} label="Análisis de Flujo Institucional" className="mb-5" />
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        {[
          { label: 'Flujos Detectados', value: flows.length, sub: 'tickers con actividad', idx: 1 },
          { label: 'Bullish', value: bullish, sub: `${flows.length ? ((bullish / flows.length) * 100).toFixed(0) : 0}% del total`, color: 'text-emerald-400', idx: 2 },
          { label: 'Bearish', value: bearish, sub: `${flows.length ? ((bearish / flows.length) * 100).toFixed(0) : 0}% del total`, color: 'text-red-400', idx: 3 },
          { label: 'Premium Total', value: fmtPremium(totalPremium), sub: `score medio: ${avgScore.toFixed(0)}`, idx: 4 },
        ].map(({ label, value, sub, color, idx }) => (
          <Card key={label} className={`glass p-5 stagger-${idx}`}>
            <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">{label}</div>
            <div className={`text-3xl font-extrabold tracking-tight tabular-nums leading-none mb-2 ${color ?? ''}`}>{value}</div>
            <div className="text-[0.66rem] text-muted-foreground">{sub}</div>
          </Card>
        ))}
      </div>

      <Card className="glass animate-fade-in-up">
        <Table>
          <TableHeader>
            <TableRow className="border-border/50 hover:bg-transparent">
              <TableHead className={thCls('ticker')} onClick={() => onSort('ticker')}>Ticker</TableHead>
              <TableHead>Sentimiento</TableHead>
              <TableHead className={thCls('flow_score')} onClick={() => onSort('flow_score')}>Score</TableHead>
              <TableHead>Calidad</TableHead>
              <TableHead className={thCls('total_premium')} onClick={() => onSort('total_premium')}>Premium</TableHead>
              <TableHead className={thCls('put_call_ratio')} onClick={() => onSort('put_call_ratio')}>P/C</TableHead>
              <TableHead>Calls</TableHead>
              <TableHead>Puts</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.slice(0, 30).map(d => (
              <TableRow key={d.ticker}>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <TickerLogo ticker={d.ticker} size="xs" />
                    <span className="font-mono font-bold text-primary text-[0.8rem] tracking-wide">{d.ticker}</span>
                  </div>
                </TableCell>
                <TableCell><Badge variant={sentVariant(d.sentiment)}>{d.sentiment_emoji || ''} {d.sentiment}</Badge></TableCell>
                <TableCell><ScoreBar score={d.flow_score} /></TableCell>
                <TableCell className="text-muted-foreground">{d.quality || '—'}</TableCell>
                <TableCell className="tabular-nums">{fmtPremium(d.total_premium)}</TableCell>
                <TableCell className="tabular-nums">{d.put_call_ratio?.toFixed(2) ?? '—'}</TableCell>
                <TableCell className="text-emerald-400 font-semibold">{d.unusual_calls ?? '—'}</TableCell>
                <TableCell className="text-red-400 font-semibold">{d.unusual_puts ?? '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {flows.length === 0 && (
          <CardContent className="py-16 text-center">
            <div className="text-4xl mb-4 opacity-20">📊</div>
            <p className="font-medium text-muted-foreground">Sin flujos de opciones disponibles</p>
          </CardContent>
        )}
      </Card>
    </>
  )
}
