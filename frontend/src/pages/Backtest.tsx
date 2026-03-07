import { fetchBacktest } from '../api/client'
import { useApi } from '../hooks/useApi'
import Loading, { ErrorState } from '../components/Loading'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'

type Trade = {
  ticker: string
  company_name?: string
  strategy?: string
  entry_price?: number
  exit_price?: number
  profit_loss_pct?: number
  win?: boolean
  holding_days?: number
  reversion_score?: number
  exit_reason?: string
}

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
  const backtestDate = typeof bt.backtest_date === 'string' ? bt.backtest_date.slice(0, 10) : null
  const initialCapital = typeof bt.initial_capital === 'number' ? bt.initial_capital : null
  const metrics = (bt.metrics || bt) as Record<string, unknown>

  const totalTrades    = metrics.total_trades as number ?? metrics.total_signals as number ?? null
  const winningTrades  = metrics.winning_trades as number ?? null
  const losingTrades   = metrics.losing_trades as number ?? null
  const winRate        = metrics.win_rate as number ?? null
  const avgReturn      = metrics.avg_return as number ?? metrics.average_return as number ?? metrics.avg_trade as number ?? null
  const avgWin         = metrics.avg_win as number ?? null
  const avgLoss        = metrics.avg_loss as number ?? null
  const totalReturn    = metrics.total_return as number ?? metrics.total_return_pct as number ?? null
  const maxDrawdown    = metrics.max_drawdown as number ?? null
  const profitFactor   = metrics.profit_factor as number ?? null
  const bestTrade      = metrics.best_trade  as Trade | undefined
  const worstTrade     = metrics.worst_trade as Trade | undefined

  const trades = (bt.trades as Trade[] | undefined) ?? []

  // Build strategy breakdown from trades
  const stratMap: Record<string, { wins: number; losses: number; totalPct: number }> = {}
  for (const t of trades) {
    const s = t.strategy ?? 'Unknown'
    if (!stratMap[s]) stratMap[s] = { wins: 0, losses: 0, totalPct: 0 }
    if (t.win) stratMap[s].wins++
    else stratMap[s].losses++
    stratMap[s].totalPct += t.profit_loss_pct ?? 0
  }
  const strategyRows = Object.entries(stratMap).map(([name, v]) => ({
    name,
    total: v.wins + v.losses,
    wins: v.wins,
    winRate: v.wins + v.losses > 0 ? (v.wins / (v.wins + v.losses)) * 100 : 0,
    avgReturn: v.wins + v.losses > 0 ? v.totalPct / (v.wins + v.losses) : 0,
  }))

  const statCards = [
    totalTrades != null && { label: 'Total Trades', value: String(totalTrades), sub: `${winningTrades ?? '—'} wins · ${losingTrades ?? '—'} losses`, color: '' },
    winRate != null && { label: 'Win Rate', value: `${winRate.toFixed(1)}%`, sub: winRate >= 60 ? 'muy alto' : winRate >= 50 ? 'rentable' : 'por debajo del 50%', color: winRate >= 50 ? 'text-emerald-400' : 'text-red-400' },
    avgReturn != null && { label: 'Avg Return', value: `${avgReturn >= 0 ? '+' : ''}${avgReturn.toFixed(2)}%`, sub: 'por operacion', color: avgReturn >= 0 ? 'text-emerald-400' : 'text-red-400' },
    totalReturn != null && { label: 'Total Return', value: `${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%`, sub: 'retorno acumulado', color: totalReturn >= 0 ? 'text-emerald-400' : 'text-red-400' },
    maxDrawdown != null && { label: 'Max Drawdown', value: `${maxDrawdown.toFixed(2)}%`, sub: 'peor caida', color: 'text-red-400' },
    profitFactor != null && { label: 'Profit Factor', value: profitFactor.toFixed(2), sub: profitFactor >= 1.5 ? 'excelente' : profitFactor >= 1 ? 'positivo' : 'negativo', color: profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400' },
  ].filter(Boolean) as { label: string; value: string; sub: string; color: string }[]

  return (
    <>
      <div className="mb-7 animate-fade-in-up">
        <h2 className="text-2xl font-extrabold tracking-tight mb-2 flex items-center gap-2 flex-wrap">
          <span className="gradient-title">Backtest</span>
          <Badge variant="blue" className="text-[0.65rem]">{type.toUpperCase()}</Badge>
        </h2>
        <p className="text-sm text-muted-foreground">
          Resultados historicos del backtesting
          {backtestDate && <span className="ml-2 text-muted-foreground/60">· {backtestDate}</span>}
          {initialCapital && <span className="ml-1 text-muted-foreground/60">· ${initialCapital.toLocaleString()} capital inicial</span>}
        </p>
      </div>

      {/* Main metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-5">
        {statCards.map(({ label, value, sub, color }, idx) => (
          <Card key={label} className={`glass p-5 stagger-${idx + 1}`}>
            <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">{label}</div>
            <div className={`text-2xl sm:text-3xl font-extrabold tracking-tight tabular-nums leading-none mb-2 ${color}`}>{value}</div>
            <div className="text-[0.66rem] text-muted-foreground">{sub}</div>
          </Card>
        ))}
      </div>

      {/* Win/Loss detail row */}
      {(avgWin != null || avgLoss != null) && (
        <div className="grid grid-cols-2 gap-3 mb-5">
          {avgWin != null && (
            <Card className="glass p-4">
              <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-1">Avg Win</div>
              <div className="text-2xl font-extrabold text-emerald-400 tabular-nums">+{avgWin.toFixed(2)}%</div>
            </Card>
          )}
          {avgLoss != null && (
            <Card className="glass p-4">
              <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-1">Avg Loss</div>
              <div className="text-2xl font-extrabold text-red-400 tabular-nums">{avgLoss.toFixed(2)}%</div>
            </Card>
          )}
        </div>
      )}

      {/* Best / Worst trades */}
      {(bestTrade || worstTrade) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
          {bestTrade && (
            <Card className="glass p-4 border-emerald-500/20">
              <div className="text-[0.6rem] font-bold uppercase tracking-widest text-emerald-400/70 mb-2">Mejor Trade</div>
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-mono font-bold text-primary">{bestTrade.ticker}</span>
                <span className="text-xs text-muted-foreground truncate">{bestTrade.company_name}</span>
              </div>
              <div className="text-2xl font-extrabold text-emerald-400 tabular-nums">
                +{bestTrade.profit_loss_pct?.toFixed(2)}%
              </div>
              <div className="text-[0.65rem] text-muted-foreground mt-1">
                {bestTrade.strategy} · {bestTrade.holding_days}d holding
              </div>
            </Card>
          )}
          {worstTrade && (
            <Card className="glass p-4 border-red-500/20">
              <div className="text-[0.6rem] font-bold uppercase tracking-widest text-red-400/70 mb-2">Peor Trade</div>
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-mono font-bold text-primary">{worstTrade.ticker}</span>
                <span className="text-xs text-muted-foreground truncate">{worstTrade.company_name}</span>
              </div>
              <div className="text-2xl font-extrabold text-red-400 tabular-nums">
                {worstTrade.profit_loss_pct?.toFixed(2)}%
              </div>
              <div className="text-[0.65rem] text-muted-foreground mt-1">
                {worstTrade.strategy} · {worstTrade.holding_days}d holding
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Strategy breakdown (from trades or direct) */}
      {strategyRows.length > 0 && (
        <Card className="glass animate-fade-in-up mb-5">
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
              {strategyRows.map(s => (
                <TableRow key={s.name}>
                  <TableCell className="font-mono font-bold text-primary text-[0.8rem]">{s.name}</TableCell>
                  <TableCell className="tabular-nums">{s.total}</TableCell>
                  <TableCell>
                    <span className={`font-semibold ${s.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {s.winRate.toFixed(1)}%
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className={`font-semibold ${s.avgReturn >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {s.avgReturn >= 0 ? '+' : ''}{s.avgReturn.toFixed(2)}%
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Trades list */}
      {trades.length > 0 && (
        <Card className="glass animate-fade-in-up">
          <div className="px-5 py-3 border-b border-border/50 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Operaciones</h3>
            <span className="text-[0.65rem] text-muted-foreground">{trades.length} trades</span>
          </div>
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead>Ticker</TableHead>
                <TableHead className="hidden sm:table-cell">Empresa</TableHead>
                <TableHead className="hidden md:table-cell">Estrategia</TableHead>
                <TableHead>P&L</TableHead>
                <TableHead className="hidden sm:table-cell">Entrada</TableHead>
                <TableHead className="hidden sm:table-cell">Salida</TableHead>
                <TableHead className="hidden md:table-cell">Días</TableHead>
                <TableHead>Resultado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trades.map((t, i) => (
                <TableRow key={i}>
                  <TableCell className="font-mono font-bold text-primary text-[0.8rem]">{t.ticker}</TableCell>
                  <TableCell className="hidden sm:table-cell text-[0.76rem] text-muted-foreground max-w-[140px] truncate">{t.company_name}</TableCell>
                  <TableCell className="hidden md:table-cell text-[0.75rem] text-muted-foreground">{t.strategy}</TableCell>
                  <TableCell>
                    <span className={`font-bold text-[0.8rem] tabular-nums ${(t.profit_loss_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {(t.profit_loss_pct ?? 0) >= 0 ? '+' : ''}{(t.profit_loss_pct ?? 0).toFixed(2)}%
                    </span>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell tabular-nums text-[0.8rem]">
                    {t.entry_price != null ? `$${t.entry_price.toFixed(2)}` : '—'}
                  </TableCell>
                  <TableCell className="hidden sm:table-cell tabular-nums text-[0.8rem]">
                    {t.exit_price != null ? `$${t.exit_price.toFixed(2)}` : '—'}
                  </TableCell>
                  <TableCell className="hidden md:table-cell tabular-nums text-[0.8rem] text-muted-foreground">
                    {t.holding_days ?? '—'}d
                  </TableCell>
                  <TableCell>
                    <span className={`text-[0.7rem] font-bold px-1.5 py-0.5 rounded ${t.win ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                      {t.win ? 'WIN' : 'LOSS'}
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
