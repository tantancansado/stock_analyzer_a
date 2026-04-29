import { useMemo, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { fetchCerebroSectorRV, type SectorStandout, type SectorSummary } from '../api/client'
import Loading, { ErrorState } from '../components/Loading'
import TickerLogo from '../components/TickerLogo'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import InfoTooltip from '../components/InfoTooltip'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fcfColor(v: number): string {
  if (v >= 8)  return 'text-emerald-400'
  if (v >= 5)  return 'text-emerald-300'
  if (v >= 3)  return 'text-amber-400'
  if (v < 0)   return 'text-red-400'
  return 'text-muted-foreground'
}

function scoreColor(v: number): string {
  if (v >= 60) return 'text-emerald-400'
  if (v >= 50) return 'text-amber-400'
  return 'text-muted-foreground'
}

// ── Sector bar chart (pure CSS) ───────────────────────────────────────────────

function SectorBar({ sectors }: Readonly<{ sectors: SectorSummary[] }>) {
  const max = Math.max(...sectors.map(s => s.avg_value_score ?? 0), 1)
  const sorted = [...sectors].sort((a, b) => (b.avg_value_score ?? 0) - (a.avg_value_score ?? 0))
  return (
    <div className="space-y-2">
      {sorted.map(s => (
        <div key={s.sector} className="grid grid-cols-[140px_1fr_60px_56px] gap-2 items-center">
          <span className="text-[0.72rem] text-muted-foreground truncate text-right">{s.sector}</span>
          <div className="h-5 rounded bg-muted/20 overflow-clip">
            <div
              className="h-full rounded bg-primary/40 transition-all"
              style={{ width: `${((s.avg_value_score ?? 0) / max) * 100}%` }}
            />
          </div>
          <span className={`text-[0.72rem] font-bold tabular-nums text-right ${scoreColor(s.avg_value_score ?? 0)}`}>
            {(s.avg_value_score ?? 0).toFixed(1)}
          </span>
          <span className={`text-[0.72rem] tabular-nums text-right ${fcfColor(s.avg_fcf_yield ?? 0)}`}>
            {(s.avg_fcf_yield ?? 0).toFixed(1)}%
          </span>
        </div>
      ))}
      <div className="grid grid-cols-[140px_1fr_60px_56px] gap-2 items-center mt-1">
        <span />
        <span className="text-[0.6rem] text-muted-foreground/40 uppercase tracking-wider">Score VALUE promedio</span>
        <span className="text-[0.6rem] text-muted-foreground/40 text-right">Score</span>
        <span className="text-[0.6rem] text-muted-foreground/40 text-right">FCF%</span>
      </div>
    </div>
  )
}

// ── Standout row ──────────────────────────────────────────────────────────────

function StandoutRow({ d }: Readonly<{ d: SectorStandout }>) {
  const isBest = d.label === 'BEST_IN_SECTOR'
  const labelCls = isBest
    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
    : 'bg-red-500/15 text-red-400 border-red-500/30'
  return (
    <TableRow className="border-border/30 align-middle">
      <TableCell className="font-mono font-bold text-primary text-[0.8rem]">
        <div className="flex items-center gap-2">
          <TickerLogo ticker={d.ticker} size="sm" />
          <div>
            <div>{d.ticker}</div>
            <div className="text-[0.65rem] text-muted-foreground/60 font-normal hidden sm:block max-w-[100px] truncate">
              {d.company_name}
            </div>
          </div>
        </div>
      </TableCell>
      <TableCell className="hidden md:table-cell text-[0.72rem] text-muted-foreground">
        {d.sector}
      </TableCell>
      <TableCell>
        <span className={`text-[0.6rem] font-bold px-1.5 py-0.5 rounded border whitespace-nowrap ${labelCls}`}>
          {isBest ? '⭐ Mejor FCF' : '⚠ Caro vs peers'}
        </span>
      </TableCell>
      <TableCell className="tabular-nums text-sm">
        <span className={fcfColor(d.fcf_yield_pct)}>{d.fcf_yield_pct.toFixed(1)}%</span>
        <span className="text-muted-foreground/40 text-xs ml-1">
          (vs {(d.sector_avg_fcf ?? 0).toFixed(1)}% avg)
        </span>
      </TableCell>
      <TableCell className="hidden sm:table-cell tabular-nums text-[0.72rem] text-muted-foreground">
        #{d.fcf_rank} / {d.fcf_rank_of}
      </TableCell>
      <TableCell className="tabular-nums text-sm">
        <span className={scoreColor(d.value_score)}>{d.value_score.toFixed(0)}</span>
      </TableCell>
      <TableCell className="hidden lg:table-cell tabular-nums text-sm">
        {d.analyst_upside_pct != null ? (
          <span className={d.analyst_upside_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}>
            {d.analyst_upside_pct > 0 ? '+' : ''}{d.analyst_upside_pct.toFixed(0)}%
          </span>
        ) : '—'}
      </TableCell>
    </TableRow>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

type LabelFilter = 'ALL' | 'BEST_IN_SECTOR' | 'PRICEY_VS_PEERS'

export default function SectorComparison() {
  const { data, loading, error } = useApi(() => fetchCerebroSectorRV(), [])
  const [labelFilter, setLabelFilter] = useState<LabelFilter>('ALL')
  const [sectorFilter, setSectorFilter] = useState('ALL')
  const [activeView, setActiveView] = useState<'table' | 'chart'>('chart')

  const standouts     = data?.standouts     ?? []
  const sectorSummary = data?.sector_summary ?? []

  const sectors = useMemo(
    () => ['ALL', ...Array.from(new Set(standouts.map(s => s.sector))).sort((a, b) => a.localeCompare(b))],
    [standouts]
  )

  const filtered = useMemo(() => {
    let rows = standouts
    if (labelFilter  !== 'ALL') rows = rows.filter(r => r.label  === labelFilter)
    if (sectorFilter !== 'ALL') rows = rows.filter(r => r.sector === sectorFilter)
    return [...rows].sort((a, b) => {
      if (a.label !== b.label) return a.label === 'BEST_IN_SECTOR' ? -1 : 1
      return b.fcf_yield_pct - a.fcf_yield_pct
    })
  }, [standouts, labelFilter, sectorFilter])

  if (loading) return <Loading />
  if (error)   return <ErrorState message={error} />

  const bestCount   = standouts.filter(s => s.label === 'BEST_IN_SECTOR').length
  const priceyCount = standouts.filter(s => s.label === 'PRICEY_VS_PEERS').length

  const labelButtonText = (l: LabelFilter) => {
    if (l === 'ALL')            return `Todos (${standouts.length})`
    if (l === 'BEST_IN_SECTOR') return `⭐ Mejor FCF (${bestCount})`
    return `⚠ Caro vs peers (${priceyCount})`
  }

  return (
    <div className="space-y-5">

      {/* View toggle */}
      <div className="flex gap-1 p-1 rounded-xl bg-muted/20 border border-border/30 w-fit">
        {(['chart', 'table'] as const).map(v => (
          <button
            key={v}
            onClick={() => setActiveView(v)}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeView === v
                ? 'bg-background text-foreground shadow-sm border border-border/40'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {v === 'chart' ? '📊 Ranking sectores' : '🏆 Standouts FCF'}
          </button>
        ))}
      </div>

      {/* ── CHART VIEW ── */}
      {activeView === 'chart' && (
        <div className="space-y-5">
          {sectorSummary.length === 0 ? (
            <Card><CardContent className="py-14 text-center text-sm text-muted-foreground">Sin datos de sectores</CardContent></Card>
          ) : (
            <Card className="border border-border/40">
              <CardContent className="pt-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold">Score VALUE promedio por sector</h3>
                  <div className="flex items-center gap-3 text-[0.65rem] text-muted-foreground/60">
                    <span>Score</span>
                    <span>FCF%</span>
                  </div>
                </div>
                <SectorBar sectors={sectorSummary} />
              </CardContent>
            </Card>
          )}

          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-4 rounded-xl border border-border/40 bg-card/50">
              <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-1">Sectores</div>
              <div className="text-2xl font-extrabold text-foreground">{sectorSummary.length}</div>
              <div className="text-[0.65rem] text-muted-foreground/60 mt-0.5">{data?.total ?? 0} tickers analizados</div>
            </div>
            <div className="p-4 rounded-xl border border-border/40 bg-card/50">
              <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-1">Mejores FCF</div>
              <div className="text-2xl font-extrabold text-emerald-400">{bestCount}</div>
              <div className="text-[0.65rem] text-muted-foreground/60 mt-0.5">Nº 1 de su sector</div>
            </div>
            <div className="p-4 rounded-xl border border-border/40 bg-card/50">
              <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-1">Caro vs peers</div>
              <div className="text-2xl font-extrabold text-red-400">{priceyCount}</div>
              <div className="text-[0.65rem] text-muted-foreground/60 mt-0.5">FCF bajo vs sector</div>
            </div>
          </div>
        </div>
      )}

      {/* ── TABLE VIEW ── */}
      {activeView === 'table' && (
        <div className="space-y-4">

          {/* Filters */}
          <div className="flex flex-wrap gap-2">
            {(['ALL', 'BEST_IN_SECTOR', 'PRICEY_VS_PEERS'] as const).map(l => (
              <button
                key={l}
                onClick={() => setLabelFilter(l)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                  labelFilter === l
                    ? 'bg-primary/15 border-primary/30 text-primary'
                    : 'bg-muted/20 border-border/30 text-muted-foreground hover:text-foreground'
                }`}
              >
                {labelButtonText(l)}
              </button>
            ))}
            <div className="h-6 w-px bg-border/40 self-center" />
            <select
              value={sectorFilter}
              onChange={e => setSectorFilter(e.target.value)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold border bg-muted/20 border-border/30 text-muted-foreground hover:text-foreground transition-all"
            >
              {sectors.map(s => (
                <option key={s} value={s}>{s === 'ALL' ? 'Todos los sectores' : s}</option>
              ))}
            </select>
          </div>

          {filtered.length === 0 ? (
            <Card><CardContent className="py-14 text-center text-sm text-muted-foreground">Sin resultados con los filtros actuales</CardContent></Card>
          ) : (
            <div className="rounded-xl border border-border/40 overflow-clip">
              <Table>
                <TableHeader>
                  <TableRow className="border-border/40">
                    <TableHead>Ticker</TableHead>
                    <TableHead className="hidden md:table-cell">Sector</TableHead>
                    <TableHead>Señal</TableHead>
                    <TableHead>
                      FCF Yield
                      <InfoTooltip text="FCF yield del ticker vs promedio de su sector" />
                    </TableHead>
                    <TableHead className="hidden sm:table-cell">
                      Rank
                      <InfoTooltip text="Posición por FCF dentro del sector" />
                    </TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead className="hidden lg:table-cell">
                      Upside
                      <InfoTooltip text="Upside analistas vs precio actual" />
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map(d => <StandoutRow key={`${d.ticker}-${d.label}`} d={d} />)}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
