import { BotonMasDatos, useMasDatos } from '../components/MasDatos'
import { useState, useMemo } from 'react'
import { fetchUnusualFlow } from '../api/client'
import { precio } from '@/lib/moneda'
import { useApi } from '../hooks/useApi'
import TickerLogo from '../components/TickerLogo'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import PageHeader from '@/components/PageHeader'
import CsvDownload from '@/components/CsvDownload'
import PageShell from '@/components/PageShell'
import { Zap, ChartColumn } from 'lucide-react'
import CifrasClave from '../components/CifrasClave'

interface TopContract {
  side: 'CALL' | 'PUT'
  strike: number
  expiry: string
  dte: number
  volume: number
  open_interest?: number
  vol_oi_ratio?: number
  last_price: number
  last_trade_date?: string | null
  premium_usd: number
  iv?: number
  itm: boolean
  speculative: boolean
}

interface FlowResult {
  ticker: string
  signal: 'BULLISH' | 'BEARISH' | 'MIXED'
  flow_interpretation?: string
  interpretation_reason?: string
  current_price?: number
  drawdown_from_high_pct?: number
  call_pct: number
  total_call_premium: number
  total_put_premium: number
  total_premium: number
  net_premium: number
  total_call_volume: number
  total_put_volume: number
  avg_iv?: number
  unusual_score: number
  top_contracts: TopContract[]
  has_large_premium: boolean
  max_single_premium: number
  detected_at: string
}

interface FlowData {
  scan_date: string
  total_tickers_with_flow: number
  unusual_count: number
  bullish_count: number
  bearish_count: number
  results: FlowResult[]
}

const fmtPremium = (v?: number) => {
  if (v == null) return '—'
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

const fmtIV = (v?: number) => v != null ? `${(v * 100).toFixed(0)}%` : '—'

// Sin verde ni rojo: más dinero en puts no es una mala señal (22-nov-2026). Tras
// una caída las puts quedan dentro del dinero y su prima sube sola.
function CallPutBar({ callPct }: { callPct: number }) {
  const putPct = 100 - callPct
  return (
    <div className="flex items-center gap-1.5 min-w-[90px]">
      <div className="flex-1 h-1.5 rounded-full overflow-clip barra-pista flex">
        <div className="h-full" style={{ width: `${callPct}%`, background: 'color-mix(in oklab, var(--primary) 70%, transparent)' }} />
        <div className="h-full" style={{ width: `${putPct}%`, background: 'color-mix(in oklab, var(--muted-foreground) 45%, transparent)' }} />
      </div>
      <span className="text-micro text-muted-foreground tabular-nums w-16 text-right">
        {callPct.toFixed(0)}C / {putPct.toFixed(0)}P
      </span>
    </div>
  )
}

function ContractRow({ c, ticker }: { c: TopContract; ticker: string }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-micro py-0.5">
      <span className="font-bold w-8">{c.side}</span>
      <span className="font-mono">{precio(c.strike, ticker)}</span>
      <span className="text-muted-foreground">{c.expiry} ({c.dte}d)</span>
      <span className="text-muted-foreground">vol {c.volume?.toLocaleString() ?? '—'}</span>
      {c.vol_oi_ratio != null && (
        <span className="text-muted-foreground">v/OI {c.vol_oi_ratio.toFixed(1)}x</span>
      )}
      <span className="font-bold">{fmtPremium(c.premium_usd)}</span>
      {c.iv != null && <span className="text-muted-foreground">IV {fmtIV(c.iv)}</span>}
      {c.speculative && <span className="text-amber-400 font-semibold inline-flex items-center gap-0.5"><Zap size={12} strokeWidth={2.5} />SWEEP</span>}
      {c.itm && <span className="text-muted-foreground">[ITM]</span>}
      {c.last_trade_date && (
        <span className="text-muted-foreground ml-1">
          {c.last_trade_date.includes('T') ? c.last_trade_date.slice(0, 16).replace('T', ' ') : c.last_trade_date}
        </span>
      )}
    </div>
  )
}

export default function OptionsFlow() {
  const { data, loading, error } = useApi(() => fetchUnusualFlow(), [])
  const [sortKey, setSortKey] = useState<keyof FlowResult>('total_premium')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [onlyLarge, setOnlyLarge] = useState(false)
  // Vista sencilla por defecto (12-nov-2026); cifras y filtros, en la avanzada.
  const [avanzada, alternarAvanzada] = useMasDatos('opciones')

  const raw = data as FlowData | null
  const results: FlowResult[] = raw?.results ?? []

  const filtered = useMemo(() => {
    let r = results
    if (onlyLarge) r = r.filter(x => x.has_large_premium)
    return [...r].sort((a, b) => {
      const av = (a[sortKey] as number) ?? 0
      const bv = (b[sortKey] as number) ?? 0
      return sortDir === 'asc' ? (av < bv ? -1 : 1) : (av > bv ? -1 : 1)
    })
  }, [results, onlyLarge, sortKey, sortDir])

  const onSort = (key: keyof FlowResult) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const thCls = (key: keyof FlowResult) =>
    `cursor-pointer select-none whitespace-nowrap transition-colors hover:text-foreground ${sortKey === key ? 'text-primary' : ''}`

  const cabecera = {
    title: 'Opciones inusuales',
    subtitle: 'Dónde va el dinero en opciones. Medido, no anticipa lo que hará la acción: cuando cae, sus puts valen más y el dinero en puts sube solo',
  } as const
  if (loading || error) return <PageShell {...cabecera} loading={loading} error={error} />

  const totalPremium = results.reduce((s, r) => s + r.total_premium, 0)
  const scanDate = raw?.scan_date ? new Date(raw.scan_date) : null

  return (
    <>
      <PageHeader
        title="Opciones inusuales"
        subtitle={<>
          Dónde va el dinero en opciones. Medido, no anticipa lo que hará la acción: cuando cae, sus puts valen más y el dinero en puts sube solo
          {scanDate && (
            <span className="ml-2 opacity-50 text-mini">
              · {scanDate.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })} ET
            </span>
          )}
        </>}
      >
        {avanzada && <CsvDownload dataset="unusual-flow" label="CSV" />}
        <BotonMasDatos activo={avanzada} onClick={alternarAvanzada} />
      </PageHeader>

      {avanzada && (
      <>
      <CifrasClave cifras={[
        { etiqueta: 'Tickers con flujo', valor: raw?.total_tickers_with_flow ?? 0, sub: 'con actividad opciones' },
        { etiqueta: 'Premium total', valor: fmtPremium(totalPremium), sub: `${raw?.unusual_count ?? 0} con bloque >$100K` },
      ]} />

      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setOnlyLarge(v => !v)}
          className={`text-micro px-2.5 py-0.5 rounded border transition-colors ${
            onlyLarge ? 'border-yellow-500/60 bg-yellow-500/10 text-yellow-400' : 'border-border/40 text-muted-foreground hover:border-border/70'
          }`}
        >
          <Zap size={12} strokeWidth={2.25} />Solo bloques &gt;$100K
        </button>
      </div>

      </>
      )}

      {/* Mobile cards */}
      <div className="sm:hidden space-y-2 mb-2">
        {filtered.slice(0, 20).map(r => (
          <div
            key={r.ticker}
            onClick={() => setExpanded(expanded === r.ticker ? null : r.ticker)}
            className="glass rounded-2xl p-4 cursor-pointer active:scale-[0.98] transition-transform"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <TickerLogo ticker={r.ticker} size="xs" />
                <span className="font-mono font-bold text-cuerpo text-primary">{r.ticker}</span>
              </div>
              <span className="text-mini font-mono font-bold">{fmtPremium(r.total_premium)}</span>
            </div>
            <CallPutBar callPct={r.call_pct} />
            {expanded === r.ticker && r.top_contracts.map((c, i) => (
              <ContractRow key={i} c={c} ticker={r.ticker} />
            ))}
          </div>
        ))}
      </div>

      {/* Desktop table */}
      <div className="hidden sm:block">
        <Card className="glass animate-fade-in-up">
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead className={thCls('ticker')} onClick={() => onSort('ticker')}>Ticker</TableHead>
                <TableHead>Calls / Puts</TableHead>
                <TableHead className={thCls('total_premium')} onClick={() => onSort('total_premium')}>Premium Total</TableHead>
                <TableHead className={thCls('max_single_premium')} onClick={() => onSort('max_single_premium')}>Mayor Contrato</TableHead>
                <TableHead className={thCls('unusual_score')} onClick={() => onSort('unusual_score')}>Score</TableHead>
                <TableHead>Top Contratos</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map(r => (
                <>
                  <TableRow
                    key={r.ticker}
                    className="cursor-pointer hover:bg-muted/5 transition-colors"
                    onClick={() => setExpanded(expanded === r.ticker ? null : r.ticker)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <TickerLogo ticker={r.ticker} size="xs" />
                        <span className="font-mono font-bold text-primary text-apoyo tracking-wide">{r.ticker}</span>
                        {r.has_large_premium && <Zap size={12} strokeWidth={2.5} className="text-amber-400 shrink-0" />}
                      </div>
                    </TableCell>
                    <TableCell><CallPutBar callPct={r.call_pct} /></TableCell>
                    <TableCell className="tabular-nums font-semibold">{fmtPremium(r.total_premium)}</TableCell>
                    <TableCell className="tabular-nums text-muted-foreground">{fmtPremium(r.max_single_premium)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <div className="h-1.5 w-16 rounded-full barra-pista overflow-clip">
                          <div className="h-full bg-primary/60 rounded-full" style={{ width: `${r.unusual_score}%` }} />
                        </div>
                        <span className="text-micro tabular-nums text-muted-foreground">{r.unusual_score}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-micro">
                      {r.top_contracts.slice(0, 1).map((c, i) => (
                        <span key={i}>
                          {c.side} {precio(c.strike, r.ticker)} {c.expiry} {fmtPremium(c.premium_usd)}
                          {c.speculative && <Zap size={12} strokeWidth={2.5} className="inline ml-0.5 -mt-px text-amber-400" />}
                        </span>
                      ))}
                      {r.top_contracts.length > 1 && (
                        <span className="text-muted-foreground ml-1">+{r.top_contracts.length - 1}</span>
                      )}
                    </TableCell>
                  </TableRow>
                  {expanded === r.ticker && (
                    <TableRow key={`${r.ticker}-expanded`} className="bg-muted/5">
                      <TableCell colSpan={6} className="py-3 px-4">
                        <div className="space-y-1">
                          {r.top_contracts.map((c, i) => <ContractRow key={i} c={c} ticker={r.ticker} />)}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </>
              ))}
            </TableBody>
          </Table>
          {filtered.length === 0 && (
            <CardContent className="py-16 text-center">
              <ChartColumn size={32} strokeWidth={1.5} className="mx-auto mb-4 opacity-20" />
              <p className="font-medium text-muted-foreground">
                {results.length === 0
                  ? 'Esperando datos del escáner, que corre cada noche'
                  : 'Ningún ticker pasa el filtro seleccionado'}
              </p>
            </CardContent>
          )}
        </Card>
      </div>

    </>
  )
}
