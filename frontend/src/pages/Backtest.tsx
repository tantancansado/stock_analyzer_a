import { fetchBacktest } from '../api/client'
import { useApi } from '../hooks/useApi'
import Loading, { ErrorState } from '../components/Loading'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'

export default function Backtest() {
  const { data, loading, error } = useApi(() => fetchBacktest(), [])

  if (loading) return <Loading />
  if (error) return <ErrorState message={error} />

  const bt = (data as Record<string, unknown>) || {}

  if (bt.error) {
    return (
      <>
        <div className="mb-7 animate-fade-in-up">
          <h2 className="text-2xl font-extrabold tracking-tight mb-2 gradient-title">Backtest</h2>
          <p className="text-sm text-muted-foreground">Resultados historicos del backtesting</p>
        </div>
        <Card className="glass">
          <CardContent className="py-16 text-center">
            <div className="text-4xl mb-4 opacity-20">📈</div>
            <p className="font-medium text-muted-foreground">{typeof bt.error === 'string' ? bt.error : 'Error desconocido'}</p>
          </CardContent>
        </Card>
      </>
    )
  }

  const type = typeof bt.type === 'string' ? bt.type : 'general'
  const metrics = (bt.metrics || bt) as Record<string, unknown>

  const totalTrades = metrics.total_trades as number ?? metrics.total_signals as number ?? null
  const winRate = metrics.win_rate as number ?? null
  const avgReturn = metrics.avg_return as number ?? metrics.average_return as number ?? null
  const totalReturn = metrics.total_return as number ?? null
  const maxDrawdown = metrics.max_drawdown as number ?? null
  const profitFactor = metrics.profit_factor as number ?? null

  const strategies = (bt.strategies || bt.strategy_results) as Record<string, Record<string, unknown>> ?? null

  const statCards = [
    totalTrades != null && { label: 'Total Trades', value: String(totalTrades), sub: 'operaciones ejecutadas', color: '' },
    winRate != null && { label: 'Win Rate', value: `${winRate.toFixed(1)}%`, sub: winRate >= 50 ? 'rentable' : 'por debajo del 50%', color: winRate >= 50 ? 'text-emerald-400' : 'text-red-400' },
    avgReturn != null && { label: 'Avg Return', value: `${avgReturn >= 0 ? '+' : ''}${avgReturn.toFixed(2)}%`, sub: 'por operacion', color: avgReturn >= 0 ? 'text-emerald-400' : 'text-red-400' },
    totalReturn != null && { label: 'Total Return', value: `${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%`, sub: 'retorno acumulado', color: totalReturn >= 0 ? 'text-emerald-400' : 'text-red-400' },
    maxDrawdown != null && { label: 'Max Drawdown', value: `${maxDrawdown.toFixed(2)}%`, sub: 'peor caida', color: 'text-red-400' },
    profitFactor != null && { label: 'Profit Factor', value: profitFactor.toFixed(2), sub: profitFactor >= 1.5 ? 'excelente' : profitFactor >= 1 ? 'positivo' : 'negativo', color: profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400' },
  ].filter(Boolean) as { label: string; value: string; sub: string; color: string }[]

  return (
    <>
      <div className="mb-7 animate-fade-in-up">
        <h2 className="text-2xl font-extrabold tracking-tight mb-2 flex items-center gap-2">
          <span className="gradient-title">Backtest</span>
          <Badge variant="blue" className="text-[0.65rem]">{type.toUpperCase()}</Badge>
        </h2>
        <p className="text-sm text-muted-foreground">Resultados historicos del backtesting</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-5">
        {statCards.map(({ label, value, sub, color }, idx) => (
          <Card key={label} className={`glass p-5 stagger-${idx + 1}`}>
            <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">{label}</div>
            <div className={`text-3xl font-extrabold tracking-tight tabular-nums leading-none mb-2 ${color}`}>{value}</div>
            <div className="text-[0.66rem] text-muted-foreground">{sub}</div>
          </Card>
        ))}
      </div>

      {strategies && Object.keys(strategies).length > 0 && (
        <Card className="glass overflow-hidden animate-fade-in-up">
          <div className="px-5 py-3 border-b border-border/50">
            <h3 className="text-sm font-semibold">Desglose por Estrategia</h3>
          </div>
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead>Estrategia</TableHead>
                <TableHead>Trades</TableHead>
                <TableHead>Win Rate</TableHead>
                <TableHead>Avg Return</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(strategies).map(([name, s]) => (
                <TableRow key={name}>
                  <TableCell className="font-mono font-bold text-primary text-[0.8rem]">{name}</TableCell>
                  <TableCell className="tabular-nums">{typeof s.total_trades !== 'undefined' ? String(s.total_trades) : typeof s.count !== 'undefined' ? String(s.count) : '—'}</TableCell>
                  <TableCell>
                    <span className={`font-semibold ${(s.win_rate as number) >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {s.win_rate != null ? `${Number(s.win_rate).toFixed(1)}%` : '—'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className={`font-semibold ${(s.avg_return as number) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {s.avg_return != null ? `${Number(s.avg_return).toFixed(2)}%` : '—'}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </>
  )
}
