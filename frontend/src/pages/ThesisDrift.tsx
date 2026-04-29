import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { fetchCerebroThesisDrift, type ThesisDrift } from '../api/client'
import Loading, { ErrorState } from '../components/Loading'
import TickerLogo from '../components/TickerLogo'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import InfoTooltip from '../components/InfoTooltip'

const SEV_CFG = {
  HIGH:   { cls: 'bg-red-500/15 text-red-400 border-red-500/30',     label: '🔴 ALTO' },
  MEDIUM: { cls: 'bg-amber-500/15 text-amber-400 border-amber-500/30', label: '🟡 MEDIO' },
  LOW:    { cls: 'bg-muted/20 text-muted-foreground border-border/30',  label: '⚪ BAJO' },
}

function ScoreDelta({ now, prev }: { now: number; prev: number }) {
  const delta = now - prev
  const cls = delta >= 0 ? 'text-emerald-400' : 'text-red-400'
  return (
    <span className="tabular-nums text-sm">
      <span className="text-muted-foreground">{prev.toFixed(0)}</span>
      <span className="text-muted-foreground/50 mx-1">→</span>
      <span className={cls}>{now.toFixed(0)}</span>
      <span className={`ml-1 text-xs font-bold ${cls}`}>
        {delta >= 0 ? '+' : ''}{delta.toFixed(0)}
      </span>
    </span>
  )
}

export default function ThesisDrift() {
  const { data, loading, error } = useApi(() => fetchCerebroThesisDrift(), [])
  const [filter, setFilter] = useState<'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL')

  if (loading) return <Loading />
  if (error) return <ErrorState message={error} />

  const drifts = data?.drifts ?? []
  const filtered = filter === 'ALL' ? drifts : drifts.filter(d => d.severity === filter)
  const sorted = [...filtered].sort((a, b) => b.drift_score - a.drift_score)

  const counts = {
    HIGH:   drifts.filter(d => d.severity === 'HIGH').length,
    MEDIUM: drifts.filter(d => d.severity === 'MEDIUM').length,
    LOW:    drifts.filter(d => d.severity === 'LOW').length,
  }

  return (
    <div className="space-y-5">

      {/* Header stats */}
      <div className="grid grid-cols-3 gap-3">
        {(['HIGH', 'MEDIUM', 'LOW'] as const).map(sev => {
          const cfg = SEV_CFG[sev]
          const active = filter === sev
          return (
            <button
              key={sev}
              onClick={() => setFilter(active ? 'ALL' : sev)}
              className={`text-left p-3 rounded-xl border transition-all ${
                active ? 'border-primary/50 bg-primary/8' : 'border-border/40 bg-card/50 hover:border-border/70'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-[0.6rem] font-bold px-1.5 py-0.5 rounded border ${cfg.cls}`}>
                  {cfg.label}
                </span>
                <span className={`text-xl font-bold tabular-nums ${counts[sev] === 0 ? 'text-muted-foreground/20' : sev === 'HIGH' ? 'text-red-400' : sev === 'MEDIUM' ? 'text-amber-400' : 'text-muted-foreground'}`}>
                  {counts[sev]}
                </span>
              </div>
              <p className="text-[0.68rem] text-muted-foreground/60">
                {sev === 'HIGH' ? 'Tesis posiblemente rota' : sev === 'MEDIUM' ? 'Deterioro moderado' : 'Cambio menor'}
              </p>
            </button>
          )
        })}
      </div>

      {sorted.length === 0 ? (
        <Card>
          <CardContent className="py-14 text-center">
            <p className="text-3xl mb-3 opacity-20">✅</p>
            <p className="text-sm text-muted-foreground">Sin deterioro detectado con el filtro actual</p>
          </CardContent>
        </Card>
      ) : (
        <div className="rounded-xl border border-border/40 overflow-clip">
          <Table>
            <TableHeader>
              <TableRow className="border-border/40">
                <TableHead>Ticker</TableHead>
                <TableHead className="hidden sm:table-cell">Severidad</TableHead>
                <TableHead>
                  Score
                  <InfoTooltip text="Valor anterior → actual. Variación absoluta." />
                </TableHead>
                <TableHead className="hidden md:table-cell">
                  Días
                  <InfoTooltip text="Días desde la baseline con la que se compara." />
                </TableHead>
                <TableHead>Señales de deterioro</TableHead>
                <TableHead className="hidden lg:table-cell">Mejoras</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map(d => {
                const cfg = SEV_CFG[d.severity]
                return (
                  <TableRow key={d.ticker} className="border-border/30 align-top">
                    <TableCell className="font-mono font-bold text-primary text-[0.8rem]">
                      <div className="flex items-center gap-2">
                        <TickerLogo ticker={d.ticker} size="sm" />
                        <div>
                          <div>{d.ticker}</div>
                          <div className="text-[0.65rem] text-muted-foreground/60 font-normal hidden sm:block max-w-[120px] truncate">
                            {d.company_name}
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">
                      <span className={`text-[0.6rem] font-bold px-1.5 py-0.5 rounded border ${cfg.cls}`}>
                        {cfg.label}
                      </span>
                    </TableCell>
                    <TableCell>
                      <ScoreDelta now={d.value_score_now} prev={d.value_score_prev} />
                    </TableCell>
                    <TableCell className="hidden md:table-cell tabular-nums text-sm text-muted-foreground">
                      {d.days_tracked}d
                    </TableCell>
                    <TableCell className="max-w-[280px]">
                      <ul className="space-y-0.5">
                        {d.drift_flags.map((f, i) => (
                          <li key={i} className="text-[0.68rem] text-red-400/80 leading-snug">
                            ↘ {f}
                          </li>
                        ))}
                      </ul>
                    </TableCell>
                    <TableCell className="hidden lg:table-cell max-w-[200px]">
                      {d.improvements.length > 0 ? (
                        <ul className="space-y-0.5">
                          {d.improvements.map((imp, i) => (
                            <li key={i} className="text-[0.68rem] text-emerald-400/80 leading-snug">
                              ↗ {imp}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-muted-foreground/30 text-xs">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
