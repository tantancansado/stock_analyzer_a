import { useState, useEffect, useCallback } from 'react'
import { Plus, Trash2, RefreshCw, TrendingUp, TrendingDown, Wallet, AlertTriangle, X } from 'lucide-react'
import axios from 'axios'
import TickerLogo from '../components/TickerLogo'

const API_BASE = import.meta.env.VITE_API_URL || ''
const STORAGE_KEY = 'sa-personal-portfolio-v1'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Position {
  id: string
  ticker: string
  shares: number
  avg_price: number
  currency: 'USD' | 'EUR'
}

interface PositionResult {
  ticker: string
  company_name: string
  sector: string
  shares: number
  avg_price: number
  current_price: number
  currency: string
  market_value: number
  pl_pct: number
  pl_abs: number
  portfolio_pct: number
  forward_pe?: number
  analyst_target?: number
  analyst_upside?: number
  fcf_yield?: number
  fifty_two_week_high?: number
  fifty_two_week_low?: number
  action: 'MANTENER' | 'AÑADIR' | 'REDUCIR' | 'VENDER'
  conviction: 'ALTA' | 'MEDIA' | 'BAJA'
  target_price?: number
  stop_loss?: number
  recommended_weight_pct: number
  analysis: string
  key_risk: string
}

interface PortfolioAnalysis {
  summary?: string
  concentration_warning?: string | null
  overall_recommendation?: string
}

interface AnalysisResult {
  total_value: number
  portfolio_analysis: PortfolioAnalysis
  positions: PositionResult[]
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const ACTION_STYLES: Record<string, string> = {
  MANTENER: 'bg-blue-500/15 text-blue-400 border-blue-500/25',
  AÑADIR:   'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
  REDUCIR:  'bg-amber-500/15 text-amber-400 border-amber-500/25',
  VENDER:   'bg-red-500/15 text-red-400 border-red-500/25',
}

const CONVICTION_DOT: Record<string, string> = {
  ALTA:  'bg-emerald-400',
  MEDIA: 'bg-amber-400',
  BAJA:  'bg-red-400',
}

function fmt(n: number | undefined | null, decimals = 2, prefix = '') {
  if (n == null) return '—'
  return `${prefix}${n.toFixed(decimals)}`
}

function uid() {
  return Math.random().toString(36).slice(2, 9)
}

// ── Add Position Form ─────────────────────────────────────────────────────────

function AddForm({ onAdd }: { onAdd: (p: Position) => void }) {
  const [ticker, setTicker]     = useState('')
  const [shares, setShares]     = useState('')
  const [price, setPrice]       = useState('')
  const [currency, setCurrency] = useState<'USD' | 'EUR'>('USD')
  const [error, setError]       = useState('')

  const submit = () => {
    const t = ticker.trim().toUpperCase()
    const s = parseFloat(shares)
    const p = parseFloat(price)
    if (!t) return setError('Introduce el ticker')
    if (!s || s <= 0) return setError('Acciones inválidas')
    if (!p || p <= 0) return setError('Precio inválido')
    setError('')
    onAdd({ id: uid(), ticker: t, shares: s, avg_price: p, currency })
    setTicker(''); setShares(''); setPrice('')
  }

  return (
    <div className="glass rounded-2xl p-5">
      <h2 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
        <Plus size={14} className="text-primary" />
        Añadir posición
      </h2>
      <div className="flex flex-wrap gap-2 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Ticker</label>
          <input
            value={ticker}
            onChange={e => setTicker(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && submit()}
            placeholder="AAPL"
            className="w-24 px-3 py-2 rounded-lg bg-muted/30 border border-border/40 text-sm font-mono font-bold text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Acciones</label>
          <input
            value={shares}
            onChange={e => setShares(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            placeholder="100"
            type="number"
            min="0"
            className="w-24 px-3 py-2 rounded-lg bg-muted/30 border border-border/40 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Precio medio</label>
          <input
            value={price}
            onChange={e => setPrice(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            placeholder="150.00"
            type="number"
            min="0"
            step="0.01"
            className="w-28 px-3 py-2 rounded-lg bg-muted/30 border border-border/40 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Moneda</label>
          <select
            value={currency}
            onChange={e => setCurrency(e.target.value as 'USD' | 'EUR')}
            className="px-3 py-2 rounded-lg bg-muted/30 border border-border/40 text-sm text-foreground focus:outline-none focus:border-primary/50"
          >
            <option value="USD">USD $</option>
            <option value="EUR">EUR €</option>
          </select>
        </div>
        <button
          onClick={submit}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors"
        >
          <Plus size={13} strokeWidth={2.5} />
          Añadir
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
    </div>
  )
}

// ── Position Card (with analysis) ─────────────────────────────────────────────

function PositionCard({
  result, pos, onRemove
}: {
  result?: PositionResult
  pos: Position
  onRemove: () => void
}) {
  const ticker  = pos.ticker
  const cur     = result?.current_price ?? pos.avg_price
  const pl      = result?.pl_pct ?? 0
  const curSym  = pos.currency === 'EUR' ? '€' : '$'
  const action  = result?.action ?? 'MANTENER'

  return (
    <div className="glass rounded-2xl overflow-hidden">
      {/* Header row */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-border/30">
        <TickerLogo ticker={ticker} size="sm" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono font-extrabold text-foreground text-base">{ticker}</span>
            {result?.company_name && result.company_name !== ticker && (
              <span className="text-xs text-muted-foreground truncate">{result.company_name}</span>
            )}
            {result?.sector && (
              <span className="text-[0.6rem] px-1.5 py-0.5 rounded bg-muted/40 border border-border/30 text-muted-foreground/60 uppercase tracking-wide">
                {result.sector}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-0.5 flex-wrap">
            <span className="text-xs text-muted-foreground">
              {pos.shares} acc · coste {curSym}{pos.avg_price.toFixed(2)}
            </span>
            <span className={`text-xs font-bold flex items-center gap-0.5 ${pl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {pl >= 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
              {pl >= 0 ? '+' : ''}{pl.toFixed(2)}%
              {result && ` (${result.pl_abs >= 0 ? '+' : ''}${curSym}${result.pl_abs.toFixed(0)})`}
            </span>
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-start gap-3 shrink-0">
          <div className="text-right">
            <div className="font-extrabold text-lg tabular-nums text-foreground">{curSym}{cur.toFixed(2)}</div>
            {result && (
              <div className="text-[0.62rem] text-muted-foreground tabular-nums">
                {curSym}{result.market_value.toFixed(0)} · {result.portfolio_pct.toFixed(1)}%
              </div>
            )}
          </div>
          {/* Action badge */}
          {result && (
            <span className={`text-[0.65rem] font-bold px-2.5 py-1 rounded-full border uppercase tracking-wide ${ACTION_STYLES[action]}`}>
              {action}
            </span>
          )}
          <button
            onClick={onRemove}
            className="p-1.5 rounded-lg text-muted-foreground hover:bg-red-500/10 hover:text-red-400 transition-colors"
            title="Eliminar posición"
          >
            <X size={13} />
          </button>
        </div>
      </div>

      {/* Metrics strip */}
      {result && (
        <div className="flex gap-4 px-5 py-2.5 bg-muted/10 border-b border-border/20 overflow-x-auto scrollbar-hide text-[0.72rem] text-muted-foreground">
          {result.forward_pe != null && (
            <span>PE fwd <strong className="text-foreground">{result.forward_pe.toFixed(1)}x</strong></span>
          )}
          {result.fcf_yield != null && (
            <span>FCF yield <strong className={result.fcf_yield >= 5 ? 'text-emerald-400' : result.fcf_yield < 0 ? 'text-red-400' : 'text-foreground'}>
              {result.fcf_yield.toFixed(1)}%
            </strong></span>
          )}
          {result.analyst_target != null && (
            <span>Target <strong className="text-foreground">{curSym}{result.analyst_target.toFixed(2)}</strong>
              {result.analyst_upside != null && (
                <span className={result.analyst_upside >= 0 ? ' text-emerald-400' : ' text-red-400'}>
                  {' '}({result.analyst_upside >= 0 ? '+' : ''}{result.analyst_upside.toFixed(1)}%)
                </span>
              )}
            </span>
          )}
          {result.target_price != null && result.target_price !== result.analyst_target && (
            <span>IA objetivo <strong className="text-primary">{curSym}{result.target_price.toFixed(2)}</strong></span>
          )}
          {result.stop_loss != null && (
            <span>Stop <strong className="text-red-400">{curSym}{result.stop_loss.toFixed(2)}</strong></span>
          )}
          {result.fifty_two_week_high != null && (
            <span>52w <strong className="text-foreground">{curSym}{result.fifty_two_week_low?.toFixed(0)}–{result.fifty_two_week_high.toFixed(0)}</strong></span>
          )}
          <span className="ml-auto shrink-0">
            Peso actual <strong className="text-foreground">{result.portfolio_pct.toFixed(1)}%</strong>
            {' '}→ recomendado{' '}
            <strong className={
              result.recommended_weight_pct > result.portfolio_pct + 3 ? 'text-emerald-400' :
              result.recommended_weight_pct < result.portfolio_pct - 3 ? 'text-amber-400' :
              'text-foreground'
            }>
              {result.recommended_weight_pct.toFixed(1)}%
            </strong>
          </span>
          <span className="shrink-0 flex items-center gap-1">
            <span className={`w-1.5 h-1.5 rounded-full ${CONVICTION_DOT[result.conviction]}`} />
            conv. {result.conviction.toLowerCase()}
          </span>
        </div>
      )}

      {/* AI analysis */}
      {result?.analysis && (
        <div className="px-5 py-3.5 space-y-2">
          <p className="text-sm text-foreground/80 leading-relaxed">{result.analysis}</p>
          {result.key_risk && (
            <div className="flex items-start gap-2 mt-2 p-2.5 rounded-lg bg-red-500/6 border border-red-500/15">
              <AlertTriangle size={12} className="text-red-400 mt-0.5 shrink-0" />
              <p className="text-[0.75rem] text-red-300/80 leading-relaxed">{result.key_risk}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function PersonalPortfolio() {
  const [positions, setPositions] = useState<Position[]>(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') } catch { return [] }
  })
  const [result, setResult]     = useState<AnalysisResult | null>(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [analyzed, setAnalyzed] = useState(false)

  // Persist positions
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(positions))
  }, [positions])

  const analyze = useCallback(async () => {
    if (!positions.length) return
    setLoading(true); setError('')
    try {
      const resp = await axios.post(`${API_BASE}/api/analyze-personal-portfolio`, { positions })
      setResult(resp.data)
      setAnalyzed(true)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error
      setError(msg || 'Error al analizar. Inténtalo de nuevo.')
    } finally {
      setLoading(false)
    }
  }, [positions])

  // Auto-analyze on first mount if positions exist
  useEffect(() => {
    if (positions.length > 0 && !analyzed) {
      analyze()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const addPosition = (p: Position) => {
    setPositions(prev => {
      const exists = prev.find(x => x.ticker === p.ticker)
      if (exists) {
        // Update existing
        return prev.map(x => x.ticker === p.ticker ? { ...x, shares: x.shares + p.shares, avg_price: ((x.shares * x.avg_price) + (p.shares * p.avg_price)) / (x.shares + p.shares) } : x)
      }
      return [...prev, p]
    })
    setAnalyzed(false)
    setResult(null)
  }

  const removePosition = (id: string) => {
    setPositions(prev => prev.filter(p => p.id !== id))
    setResult(null)
    setAnalyzed(false)
  }

  const totalCost  = positions.reduce((s, p) => s + p.shares * p.avg_price, 0)
  const totalValue = result?.total_value ?? totalCost
  const totalPL    = totalValue - totalCost
  const totalPLPct = totalCost > 0 ? (totalPL / totalCost * 100) : 0

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-extrabold text-foreground flex items-center gap-2">
          <Wallet size={22} className="text-primary" />
          Mi Cartera Personal
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Añade tus posiciones y obtén un análisis IA actualizado en cada visita.
        </p>
      </div>

      {/* Summary bar (only when we have results) */}
      {result && (
        <div className="glass rounded-2xl p-5 space-y-3">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div className="flex gap-6 flex-wrap">
              <div>
                <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-0.5">Valor total</div>
                <div className="text-2xl font-extrabold tabular-nums text-foreground">${result.total_value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>
              </div>
              <div>
                <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-0.5">P&L total</div>
                <div className={`text-2xl font-extrabold tabular-nums flex items-center gap-1 ${totalPL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {totalPL >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                  {totalPL >= 0 ? '+' : ''}${totalPL.toFixed(0)}
                  <span className="text-sm font-semibold ml-1">({totalPLPct >= 0 ? '+' : ''}{totalPLPct.toFixed(2)}%)</span>
                </div>
              </div>
              <div>
                <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-0.5">Posiciones</div>
                <div className="text-2xl font-extrabold text-foreground">{positions.length}</div>
              </div>
            </div>
            <button
              onClick={analyze}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/10 border border-primary/25 text-primary text-sm font-semibold hover:bg-primary/20 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              {loading ? 'Analizando...' : 'Re-analizar'}
            </button>
          </div>

          {/* AI portfolio summary */}
          {result.portfolio_analysis?.summary && (
            <div className="pt-3 border-t border-border/30 space-y-2">
              <p className="text-sm text-foreground/80 leading-relaxed">{result.portfolio_analysis.summary}</p>
              {result.portfolio_analysis.overall_recommendation && (
                <p className="text-sm text-muted-foreground leading-relaxed">{result.portfolio_analysis.overall_recommendation}</p>
              )}
              {result.portfolio_analysis.concentration_warning && (
                <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-500/8 border border-amber-500/20">
                  <AlertTriangle size={12} className="text-amber-400 mt-0.5 shrink-0" />
                  <p className="text-[0.75rem] text-amber-300/80">{result.portfolio_analysis.concentration_warning}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Add form */}
      <AddForm onAdd={addPosition} />

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertTriangle size={14} />
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-4">
          {positions.map(p => (
            <div key={p.id} className="glass rounded-2xl p-5 animate-pulse">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-muted/40" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-24 bg-muted/40 rounded" />
                  <div className="h-3 w-40 bg-muted/30 rounded" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && positions.length === 0 && (
        <div className="glass rounded-2xl p-12 text-center">
          <Wallet size={40} className="mx-auto text-muted-foreground/30 mb-4" />
          <p className="text-foreground font-semibold mb-1">Sin posiciones todavía</p>
          <p className="text-sm text-muted-foreground">Añade tus posiciones arriba y el análisis IA se generará automáticamente.</p>
        </div>
      )}

      {/* Position cards */}
      {!loading && positions.length > 0 && (
        <div className="space-y-4">
          {/* Analyze button (before first analysis) */}
          {!analyzed && !loading && (
            <button
              onClick={analyze}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors"
            >
              <RefreshCw size={14} />
              Analizar cartera con IA
            </button>
          )}

          {positions.map(pos => (
            <PositionCard
              key={pos.id}
              pos={pos}
              result={result?.positions.find(r => r.ticker === pos.ticker)}
              onRemove={() => removePosition(pos.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
