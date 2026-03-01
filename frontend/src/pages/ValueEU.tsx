import React, { useState } from 'react'
import { fetchEUValueOpportunities, fetchMarketRegime, fetchThesis, type ValueOpportunity } from '../api/client'
import { useApi } from '../hooks/useApi'
import Loading, { ErrorState } from '../components/Loading'
import ScoreBar from '../components/ScoreBar'
import GradeBadge from '../components/GradeBadge'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import ThesisBody from '../components/ThesisBody'
import CsvDownload from '../components/CsvDownload'
import WatchlistButton from '../components/WatchlistButton'
import InfoTooltip from '../components/InfoTooltip'

const MARKET_FLAGS: Record<string, string> = {
  DAX40: '🇩🇪', FTSE100: '🇬🇧', CAC40: '🇫🇷',
  IBEX35: '🇪🇸', AEX25: '🇳🇱', SMI20: '🇨🇭', FTSEMIB: '🇮🇹',
}

type SortKey = keyof ValueOpportunity
type SortDir = 'asc' | 'desc'

function ConvictionPanel({ row }: { row: ValueOpportunity }) {
  const reasons = row.conviction_reasons
    ? row.conviction_reasons.split(' | ').filter(Boolean)
    : []
  const pos = row.conviction_positives ?? 0
  const flags = row.conviction_red_flags ?? 0
  const score = row.conviction_score
  const grade = row.conviction_grade

  if (!reasons.length && score == null) return null

  return (
    <div className="border-t border-border/40 pt-4 mt-4">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Conviction Filter</span>
        {grade && score != null && (
          <span className={`text-xs font-bold px-2 py-0.5 rounded ${grade === 'A' ? 'bg-emerald-500/20 text-emerald-400' : grade === 'B' ? 'bg-blue-500/20 text-blue-400' : 'bg-amber-500/20 text-amber-400'}`}>
            {grade} — {score.toFixed(0)}pts
          </span>
        )}
        {pos > 0 && <span className="text-[0.7rem] text-emerald-400">+{pos} positivos</span>}
        {flags > 0 && <span className="text-[0.7rem] text-red-400">{flags} alertas</span>}
      </div>
      {reasons.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {reasons.map((r, i) => (
            <span key={i} className="text-[0.65rem] px-2 py-0.5 rounded-full bg-white/5 border border-border/50 text-muted-foreground">
              {r}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ValueEU() {
  const { data, loading, error } = useApi(() => fetchEUValueOpportunities(), [])
  const { data: regime } = useApi(() => fetchMarketRegime(), [])
  const [sortKey, setSortKey] = useState<SortKey>('value_score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null)
  const [expandedRow, setExpandedRow] = useState<ValueOpportunity | null>(null)
  const [thesisText, setThesisText] = useState<string>('')

  // Filters
  const [filterGrade, setFilterGrade] = useState<string>('ALL')
  const [filterSector, setFilterSector] = useState<string>('ALL')
  const [filterMarket, setFilterMarket] = useState<string>('ALL')
  const [minFcf, setMinFcf] = useState<string>('')
  const [minRr, setMinRr] = useState<string>('')

  if (loading) return <Loading />
  if (error) return <ErrorState message={error} />

  const rows = data?.data ?? []
  const source = data?.source ?? ''

  // Unique sectors + markets for filters
  const sectors = ['ALL', ...Array.from(new Set(rows.map(r => r.sector).filter(Boolean) as string[])).sort()]
  const marketList = ['ALL', ...Array.from(new Set(rows.map(r => r.market).filter(Boolean) as string[])).sort()]

  const filtered = rows.filter(r => {
    if (filterGrade !== 'ALL' && r.conviction_grade !== filterGrade) return false
    if (filterSector !== 'ALL' && r.sector !== filterSector) return false
    if (filterMarket !== 'ALL' && r.market !== filterMarket) return false
    if (minFcf !== '' && (r.fcf_yield_pct == null || r.fcf_yield_pct < Number(minFcf))) return false
    if (minRr !== '' && (r.risk_reward_ratio == null || r.risk_reward_ratio < Number(minRr))) return false
    return true
  })

  const sorted = [...filtered].sort((a, b) => {
    const av = a[sortKey] ?? 0; const bv = b[sortKey] ?? 0
    if (av < bv) return sortDir === 'asc' ? -1 : 1
    if (av > bv) return sortDir === 'asc' ? 1 : -1
    return 0
  })
  const top = sorted.slice(0, 20)

  const onSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const toggleThesis = async (ticker: string, row: ValueOpportunity) => {
    if (expandedTicker === ticker) { setExpandedTicker(null); setExpandedRow(null); return }
    setExpandedTicker(ticker)
    setExpandedRow(row)
    setThesisText('Cargando tesis...')
    try {
      const res = await fetchThesis(ticker)
      const t = res.data.thesis
      const text = !t ? 'Sin tesis disponible'
        : typeof t === 'string' ? t
        : (t as Record<string, string>).thesis_narrative || (t as Record<string, string>).overview || JSON.stringify(t)
      setThesisText(text)
    } catch { setThesisText('Error cargando tesis') }
  }

  const thCls = (key: SortKey) =>
    `cursor-pointer select-none whitespace-nowrap transition-colors hover:text-foreground ${sortKey === key ? 'text-primary' : ''}`

  const euRegime = regime?.eu as Record<string, string> | undefined
  const regimeLabel = euRegime?.regime || euRegime?.market_regime || ''
  const getCurrency = (ticker: string) => ticker.endsWith('.L') ? '£' : ticker.endsWith('.SW') ? 'CHF ' : '€'

  const avgScore = filtered.length ? filtered.reduce((s, r) => s + (r.value_score || 0), 0) / filtered.length : 0
  const avgDiv = filtered.filter(r => r.dividend_yield_pct && r.dividend_yield_pct > 0)
  const avgDivYield = avgDiv.length ? avgDiv.reduce((s, r) => s + (r.dividend_yield_pct || 0), 0) / avgDiv.length : 0
  const bestUpside = Math.max(...filtered.map(r => r.analyst_upside_pct || 0), 0)
  const markets = new Set(rows.map(r => r.market || ''))

  const sectorCounts: Record<string, number> = {}
  top.forEach(d => { const s = d.sector || 'Unknown'; sectorCounts[s] = (sectorCounts[s] || 0) + 1 })
  const concentrated = Object.entries(sectorCounts).filter(([, c]) => c >= 3)

  const hasActiveFilters = filterGrade !== 'ALL' || filterSector !== 'ALL' || filterMarket !== 'ALL' || minFcf !== '' || minRr !== ''
  const resetFilters = () => { setFilterGrade('ALL'); setFilterSector('ALL'); setFilterMarket('ALL'); setMinFcf(''); setMinRr('') }

  const fmtFcf = (v?: number) => {
    if (v == null) return <span className="text-muted-foreground">—</span>
    const cls = v >= 5 ? 'text-emerald-400' : v >= 3 ? 'text-amber-400' : v < 0 ? 'text-red-400' : ''
    return <span className={cls}>{v.toFixed(1)}%</span>
  }
  const fmtRR = (v?: number) => {
    if (v == null) return <span className="text-muted-foreground">—</span>
    const cls = v >= 2 ? 'text-emerald-400' : v >= 1 ? 'text-amber-400' : 'text-red-400'
    return <span className={cls}>{v.toFixed(1)}</span>
  }

  return (
    <>
      <div className="mb-7 animate-fade-in-up flex items-start justify-between gap-4">
        <div className="flex-1">
        <h2 className="text-2xl font-extrabold tracking-tight mb-2 flex items-center gap-2 flex-wrap">
          <span className="gradient-title">VALUE Europa</span>
          {regimeLabel && (
            <Badge variant={regimeLabel.includes('UP') ? 'green' : regimeLabel.includes('CORR') ? 'red' : 'yellow'}>
              {regimeLabel}
            </Badge>
          )}
          {source && <span className="text-[0.58rem] font-bold uppercase tracking-widest text-muted-foreground/60 border border-border/50 rounded px-1.5 py-0.5">{source}</span>}
        </h2>
        <p className="text-sm text-muted-foreground">Blue chips europeos seleccionados por fundamentales, FCF y dividendos</p>
        </div>
        <div className="flex gap-2 shrink-0 mt-1">
          <CsvDownload dataset="value-eu" label="CSV" />
          <CsvDownload dataset="value-eu-full" label="CSV Full" />
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        {[
          { label: 'Oportunidades', value: rows.length, sub: `${markets.size} mercados`, idx: 1 },
          { label: 'Score Medio', value: avgScore.toFixed(1), sub: 'de 100 puntos', color: avgScore >= 50 ? 'text-emerald-400' : 'text-amber-400', idx: 2 },
          { label: 'Dividendo Medio', value: `${avgDivYield.toFixed(1)}%`, sub: `${avgDiv.length} con dividendo`, color: 'text-emerald-400', idx: 3 },
          { label: 'Mejor Upside', value: `+${bestUpside.toFixed(0)}%`, sub: 'potencial analistas', color: 'text-emerald-400', idx: 4 },
        ].map(({ label, value, sub, color, idx }) => (
          <Card key={label} className={`glass p-5 stagger-${idx}`}>
            <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">{label}</div>
            <div className={`text-3xl font-extrabold tracking-tight tabular-nums leading-none mb-2 ${color ?? ''}`}>{value}</div>
            <div className="text-[0.66rem] text-muted-foreground">{sub}</div>
          </Card>
        ))}
      </div>

      {concentrated.length > 0 && (
        <Card className="glass mb-4 px-5 py-3 border-amber-500/30">
          <span className="text-amber-400 text-sm font-medium">
            Concentración sectorial: {concentrated.map(([s, c]) => `${s} (${c})`).join(', ')}
          </span>
        </Card>
      )}

      {/* Filter Bar */}
      <Card className="glass px-4 py-3 mb-3 animate-fade-in-up">
        <div className="flex flex-wrap gap-x-5 gap-y-2.5 items-center">

          {/* Grade */}
          <div className="flex items-center gap-1.5">
            <span className="text-[0.58rem] font-bold uppercase tracking-wider text-muted-foreground/60 mr-0.5">Grado</span>
            {['ALL', 'A', 'B', 'C'].map(g => (
              <button key={g} onClick={() => setFilterGrade(g)}
                className={`text-[0.68rem] font-semibold px-2 py-0.5 rounded border transition-colors ${filterGrade === g ? 'border-primary/60 bg-primary/15 text-primary' : 'border-border/40 text-muted-foreground hover:border-border/70 hover:text-foreground'}`}>
                {g}
              </button>
            ))}
          </div>

          {/* Market */}
          {marketList.length > 2 && (
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[0.58rem] font-bold uppercase tracking-wider text-muted-foreground/60 mr-0.5">Mercado</span>
              {marketList.map(m => (
                <button key={m} onClick={() => setFilterMarket(m)}
                  className={`text-[0.65rem] px-2 py-0.5 rounded border transition-colors ${filterMarket === m ? 'border-primary/60 bg-primary/15 text-primary' : 'border-border/40 text-muted-foreground hover:border-border/70 hover:text-foreground'}`}>
                  {m === 'ALL' ? 'Todos' : `${MARKET_FLAGS[m] ?? ''} ${m}`}
                </button>
              ))}
            </div>
          )}

          {/* Sector */}
          {sectors.length > 2 && (
            <div className="flex items-center gap-1.5 flex-wrap max-w-[380px]">
              <span className="text-[0.58rem] font-bold uppercase tracking-wider text-muted-foreground/60 mr-0.5">Sector</span>
              {sectors.slice(0, 6).map(s => (
                <button key={s} onClick={() => setFilterSector(s)}
                  className={`text-[0.65rem] px-2 py-0.5 rounded border transition-colors ${filterSector === s ? 'border-primary/60 bg-primary/15 text-primary' : 'border-border/40 text-muted-foreground hover:border-border/70 hover:text-foreground'}`}>
                  {s === 'ALL' ? 'Todos' : s}
                </button>
              ))}
            </div>
          )}

          {/* FCF% min */}
          <div className="flex items-center gap-1.5">
            <span className="text-[0.58rem] font-bold uppercase tracking-wider text-muted-foreground/60">FCF%≥</span>
            <input type="number" value={minFcf} onChange={e => setMinFcf(e.target.value)} placeholder="0"
              className="w-14 text-[0.72rem] px-2 py-0.5 rounded border border-border/40 bg-transparent text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50" />
          </div>

          {/* R:R min */}
          <div className="flex items-center gap-1.5">
            <span className="text-[0.58rem] font-bold uppercase tracking-wider text-muted-foreground/60">R:R≥</span>
            <input type="number" value={minRr} onChange={e => setMinRr(e.target.value)} placeholder="0"
              className="w-14 text-[0.72rem] px-2 py-0.5 rounded border border-border/40 bg-transparent text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50" />
          </div>

          {hasActiveFilters && (
            <button onClick={resetFilters} className="text-[0.65rem] text-muted-foreground/60 hover:text-foreground underline underline-offset-2 transition-colors ml-auto">
              Limpiar filtros
            </button>
          )}
          <span className="text-[0.65rem] text-muted-foreground/50 ml-auto">
            {filtered.length !== rows.length ? `${filtered.length} / ${rows.length}` : `${rows.length} picks`}
          </span>
        </div>
      </Card>

      <Card className="glass overflow-hidden animate-fade-in-up">
        <Table>
          <TableHeader>
            <TableRow className="border-border/50 hover:bg-transparent">
              <TableHead className={thCls('ticker')} onClick={() => onSort('ticker')}>Ticker</TableHead>
              <TableHead className={thCls('company_name')} onClick={() => onSort('company_name')}>Empresa</TableHead>
              <TableHead>Mercado</TableHead>
              <TableHead className={thCls('current_price')} onClick={() => onSort('current_price')}>Precio</TableHead>
              <TableHead className={thCls('value_score')} onClick={() => onSort('value_score')}>
                Score
                <InfoTooltip
                  text="Score VALUE propio (0-100): fundamentales 40pts, insiders 15pts, institucionales 15pts, opciones 10pts, ML 5pts, sector/reversion 20pts. Bonificaciones por FCF, dividendo, recompras y R:R."
                  align="left"
                />
              </TableHead>
              <TableHead>
                Grade
                <InfoTooltip
                  text={
                    <span>
                      Grado de convicción del filtro IA:<br />
                      <span className="text-emerald-400">A</span> — alta convicción (pocas alertas, múltiples positivos)<br />
                      <span className="text-blue-400">B</span> — convicción moderada<br />
                      <span className="text-amber-400">C</span> — baja convicción (revisar antes de entrar)
                    </span>
                  }
                />
              </TableHead>
              <TableHead className={thCls('sector')} onClick={() => onSort('sector')}>Sector</TableHead>
              <TableHead className={thCls('analyst_upside_pct')} onClick={() => onSort('analyst_upside_pct')}>
                Objetivo
                <InfoTooltip text="Upside según precio objetivo de analistas = (precio objetivo − precio actual) / precio actual. Negativo = analistas ven el valor sobrevalorado." />
              </TableHead>
              <TableHead className={thCls('fcf_yield_pct')} onClick={() => onSort('fcf_yield_pct')}>
                FCF%
                <InfoTooltip text="FCF Yield = Free Cash Flow / Market Cap. ≥5% excelente (verde), 3-5% bueno (ámbar), <0% negativo (rojo). Indica cuánto cash genera la empresa respecto a su valor de mercado." />
              </TableHead>
              <TableHead className={thCls('risk_reward_ratio')} onClick={() => onSort('risk_reward_ratio')}>
                R:R
                <InfoTooltip text="Risk:Reward = upside analista / 8% stop loss estándar. ≥3 excelente (verde), ≥2 bueno, <1 desfavorable (rojo). Mide si el potencial de ganancia justifica el riesgo." />
              </TableHead>
              <TableHead>
                Div/BB
                <InfoTooltip text="Dividend yield del ticker. 'BB' indica que la empresa está recomprando acciones propias activamente (buyback), lo que también retorna capital al accionista." align="right" />
              </TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {top.map(d => {
              const market = d.market || ''
              const flag = MARKET_FLAGS[market] || ''
              const cur = getCurrency(d.ticker)
              return (
                <React.Fragment key={d.ticker}>
                  <TableRow className="cursor-pointer" onClick={() => toggleThesis(d.ticker, d)}>
                    <TableCell className="font-mono font-bold text-primary text-[0.8rem] tracking-wide">{d.ticker}</TableCell>
                    <TableCell className="max-w-[150px] truncate text-muted-foreground text-[0.76rem]">{d.company_name}</TableCell>
                    <TableCell><Badge variant="blue">{flag} {market}</Badge></TableCell>
                    <TableCell className="tabular-nums">{cur}{d.current_price?.toFixed(2)}</TableCell>
                    <TableCell><ScoreBar score={d.value_score} /></TableCell>
                    <TableCell><GradeBadge grade={d.conviction_grade} score={d.conviction_score} /></TableCell>
                    <TableCell className="max-w-[120px] truncate text-muted-foreground text-[0.76rem]">{d.sector}</TableCell>
                    <TableCell className="tabular-nums">
                      {d.target_price_analyst ? `${cur}${d.target_price_analyst.toFixed(0)}` : '—'}
                      {d.analyst_upside_pct != null && (
                        <span className={`ml-1 text-xs font-semibold ${d.analyst_upside_pct > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {d.analyst_upside_pct > 0 ? '+' : ''}{d.analyst_upside_pct.toFixed(0)}%
                        </span>
                      )}
                    </TableCell>
                    <TableCell>{fmtFcf(d.fcf_yield_pct)}</TableCell>
                    <TableCell>{fmtRR(d.risk_reward_ratio)}</TableCell>
                    <TableCell>
                      {d.dividend_yield_pct != null && d.dividend_yield_pct > 0
                        ? <span className="text-emerald-400">{d.dividend_yield_pct.toFixed(1)}%{d.buyback_active ? '+BB' : ''}</span>
                        : <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    <TableCell>
                      <WatchlistButton ticker={d.ticker} company_name={d.company_name} sector={d.sector} current_price={d.current_price} value_score={d.value_score} conviction_grade={d.conviction_grade} analyst_upside_pct={d.analyst_upside_pct} fcf_yield_pct={d.fcf_yield_pct} />
                    </TableCell>
                  </TableRow>
                  {expandedTicker === d.ticker && (
                    <tr className="thesis-row">
                      <td colSpan={12}>
                        <div className="thesis-text">
                          <ThesisBody text={thesisText} />
                          {expandedRow && <ConvictionPanel row={expandedRow} />}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </TableBody>
        </Table>
        {top.length === 0 && (
          <CardContent className="py-16 text-center">
            <div className="text-4xl mb-4 opacity-20">🇪🇺</div>
            <p className="font-medium text-muted-foreground">
              {rows.length === 0 ? 'Sin oportunidades VALUE europeas en este momento' : 'Sin resultados con los filtros aplicados'}
            </p>
          </CardContent>
        )}
      </Card>
    </>
  )
}
