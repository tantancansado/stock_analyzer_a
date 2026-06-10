import { useState, useEffect, useCallback, useMemo } from 'react'
import { Plus, RefreshCw, TrendingUp, TrendingDown, Wallet, AlertTriangle, X, Loader2, BookOpen, Send, Trash2, ChevronDown, ChevronUp, Zap, Brain, Pencil, Check, Landmark, Star } from 'lucide-react'
import { nlPositionStatus } from '@/lib/nl'
import { supabase } from '@/lib/supabase'
import { apiClient, fetchMacroStress, fetchAnalystRevisions, fetchPortfolioAlerts, refreshUserArtifacts, type MacroStressMarket, type AnalystRevision, type PortfolioAlert } from '@/api/client'
import AnalystRevisionBadge from '../components/AnalystRevisionBadge'
import { useAuth } from '@/context/AuthContext'
import TickerLogo from '../components/TickerLogo'
import PriceChart from '../components/PriceChart'
import { useCerebroSignals, type CerebroMaps } from '../hooks/useCerebroSignals'
import { usePortfolioConfluence, type ConfluenceSignals } from '../hooks/usePortfolioConfluence'
import { useApi } from '../hooks/useApi'

// ── Types ─────────────────────────────────────────────────────────────────────

type AssetType = 'stock' | 'option' | 'bond' | 'preferred' | 'covered_call'

interface Position {
  id: string
  ticker: string
  shares: number
  avg_price: number
  currency: 'USD' | 'EUR'
  asset_type?: AssetType
  // options
  option_type?: 'call' | 'put'
  option_strike?: number
  option_expiry?: string
  // bonds & preferred
  coupon_rate?: number
  par_value?: number
  maturity_date?: string
}

interface JournalEntry {
  id: string
  ticker: string
  note: string
  created_at: string
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
  asset_type?: AssetType
  // stock
  forward_pe?: number
  analyst_target?: number
  analyst_upside?: number
  fcf_yield?: number
  dividend_yield?: number
  fifty_two_week_high?: number
  fifty_two_week_low?: number
  // option
  option_type?: 'call' | 'put'
  option_strike?: number
  option_expiry?: string
  days_to_expiry?: number
  intrinsic_value?: number
  itm?: boolean
  // bond / preferred
  coupon_rate?: number
  par_value?: number
  maturity_date?: string
  ytm?: number
  days_to_maturity?: number
  current_yield?: number
  action: 'MANTENER' | 'AÑADIR' | 'REDUCIR' | 'VENDER'
  conviction: 'ALTA' | 'MEDIA' | 'BAJA'
  target_price?: number
  stop_loss?: number
  recommended_weight_pct: number
  analysis: string
  key_risk: string
  options_strategy?: string
  options_rationale?: string
  // Position sizing (stocks only)
  volatility_pct?: number
  kelly_pct?: number
  optimal_size_pct?: number
  stop_loss_atr?: number
  stop_loss_pct_atr?: number
  risk_amount?: number
  vol_multiplier?: number
}

interface RiskMetrics {
  total_risk_amount: number
  total_risk_pct: number
  kelly_base_pct: number
  oversized_positions: string[]
  win_rate_used: number
}

interface PortfolioAnalysis {
  summary?: string
  concentration_warning?: string | null
  overall_recommendation?: string
}

interface AnalysisResult {
  total_value: number
  risk_metrics?: RiskMetrics
  portfolio_analysis: PortfolioAnalysis
  positions: PositionResult[]
}

interface MacroExposureWarning {
  marketId: string
  marketLabel: string
  score: number
  regime: string
  side: 'beneficiary' | 'loser'
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const ACTION_STYLES: Record<string, string> = {
  MANTENER: 'bg-blue-500/15 text-blue-400 border-blue-500/25',
  AÑADIR:   'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
  REDUCIR:  'bg-amber-500/15 text-amber-400 border-amber-500/25',
  VENDER:   'bg-red-500/15 text-red-400 border-red-500/25',
}

const ACTION_BAR: Record<string, string> = {
  AÑADIR:   'bg-emerald-500/60',
  MANTENER: 'bg-blue-500/60',
  REDUCIR:  'bg-amber-500/60',
  VENDER:   'bg-red-500/60',
}

const CONVICTION_DOT: Record<string, string> = {
  ALTA:  'bg-emerald-400',
  MEDIA: 'bg-amber-400',
  BAJA:  'bg-red-400',
}

// ── Journal Section ───────────────────────────────────────────────────────────

function JournalSection({ ticker, userId }: { ticker: string; userId: string }) {
  const [open,    setOpen]    = useState(false)
  const [notes,   setNotes]   = useState<JournalEntry[]>([])
  const [loaded,  setLoaded]  = useState(false)
  const [text,    setText]    = useState('')
  const [saving,  setSaving]  = useState(false)
  const [count,   setCount]   = useState<number | null>(null)

  // Load count eagerly so badge shows up even when collapsed
  useEffect(() => {
    supabase
      .from('trade_journal')
      .select('id', { count: 'exact', head: true })
      .eq('user_id', userId)
      .eq('ticker', ticker)
      .then(({ count: c }) => setCount(c ?? 0))
  }, [ticker, userId])

  const load = useCallback(async () => {
    const { data } = await supabase
      .from('trade_journal')
      .select('*')
      .eq('user_id', userId)
      .eq('ticker', ticker)
      .order('created_at', { ascending: false })
    setNotes((data ?? []) as JournalEntry[])
    setCount((data ?? []).length)
    setLoaded(true)
  }, [ticker, userId])

  const toggle = () => {
    if (!open && !loaded) load()
    setOpen(o => !o)
  }

  const addNote = async () => {
    const t = text.trim()
    if (!t) return
    setSaving(true)
    const { data } = await supabase
      .from('trade_journal')
      .insert({ user_id: userId, ticker, note: t })
      .select()
      .single()
    if (data) {
      setNotes(prev => [data as JournalEntry, ...prev])
      setCount(c => (c ?? 0) + 1)
    }
    setText('')
    setSaving(false)
  }

  const deleteNote = async (id: string) => {
    await supabase.from('trade_journal').delete().eq('id', id)
    setNotes(prev => prev.filter(n => n.id !== id))
    setCount(c => Math.max(0, (c ?? 1) - 1))
  }

  return (
    <div className="border-t border-border/20">
      <button
        onClick={toggle}
        className="w-full flex items-center gap-2 px-5 py-2.5 text-[0.72rem] text-muted-foreground hover:text-foreground transition-colors"
      >
        <BookOpen size={12} />
        <span className="font-semibold">Notas del journal</span>
        {count !== null && count > 0 && (
          <span className="px-1.5 py-0.5 rounded-full bg-primary/15 text-primary text-[0.6rem] font-bold">{count}</span>
        )}
        <span className="ml-auto">{open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}</span>
      </button>

      {open && (
        <div className="px-5 pb-4 space-y-3">
          {/* Add note */}
          <div className="flex gap-2 items-start">
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              placeholder="Añade una nota: razón de compra, tesis, eventos..."
              rows={2}
              className="flex-1 px-3 py-2 rounded-lg bg-muted/30 border border-border/40 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50 resize-none"
            />
            <button
              onClick={addNote}
              disabled={saving || !text.trim()}
              className="p-2.5 rounded-lg bg-primary/10 border border-primary/20 text-primary hover:bg-primary/20 transition-colors disabled:opacity-40"
              title="Guardar nota"
            >
              {saving ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
            </button>
          </div>

          {/* Notes list */}
          {!loaded && <div className="flex justify-center py-2"><Loader2 size={14} className="animate-spin text-muted-foreground" /></div>}
          {loaded && notes.length === 0 && (
            <p className="text-[0.72rem] text-muted-foreground/50 text-center py-1">Sin notas todavía</p>
          )}
          {notes.map(n => (
            <div key={n.id} className="group flex gap-2 items-start px-4 py-3 rounded-xl bg-muted/20 border border-border/20">
              <div className="flex-1 min-w-0">
                <p className="text-[0.78rem] text-foreground/80 leading-relaxed whitespace-pre-wrap">{n.note}</p>
                <p className="text-[0.6rem] text-muted-foreground/50 mt-1">
                  {new Date(n.created_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
              <button
                onClick={() => deleteNote(n.id)}
                className="p-1 rounded text-muted-foreground/30 hover:text-red-400 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100"
              >
                <Trash2 size={11} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Add Position Form ─────────────────────────────────────────────────────────

const ASSET_TYPES: { value: AssetType; label: string; icon: React.ReactNode; color: string }[] = [
  { value: 'stock',        label: 'Acción',        icon: <TrendingUp size={12} />,   color: 'text-cyan-400' },
  { value: 'option',       label: 'Opción',        icon: <TrendingDown size={12} />, color: 'text-purple-400' },
  { value: 'covered_call', label: 'Covered Call',  icon: <Zap size={12} />,          color: 'text-amber-400' },
  { value: 'bond',         label: 'Bono',          icon: <Landmark size={12} />,     color: 'text-amber-400' },
  { value: 'preferred',    label: 'Preferred',     icon: <Star size={12} />,         color: 'text-emerald-400' },
]

const SHARES_LABEL: Record<AssetType, string> = {
  stock:        'Acciones',
  option:       'Contratos',
  covered_call: 'Acciones',
  bond:         'Nominal ($)',
  preferred:    'Acciones',
}

const PRICE_LABEL: Record<AssetType, string> = {
  stock:        'Precio medio',
  option:       'Prima pagada',
  covered_call: 'Coste base/acc',
  bond:         'Precio (% par)',
  preferred:    'Precio medio',
}

function AddForm({ onAdd, saving }: { onAdd: (p: Omit<Position, 'id'>) => Promise<void>; saving: boolean }) {
  const [assetType, setAssetType] = useState<AssetType>('stock')
  const [ticker, setTicker]       = useState('')
  const [shares, setShares]       = useState('')
  const [price, setPrice]         = useState('')
  const [currency, setCurrency]   = useState<'USD' | 'EUR'>('USD')
  // option fields
  const [optType, setOptType]     = useState<'call' | 'put'>('call')
  const [strike, setStrike]       = useState('')
  const [expiry, setExpiry]       = useState('')
  // bond/preferred fields
  const [coupon, setCoupon]       = useState('')
  const [parVal, setParVal]       = useState('1000')
  const [maturity, setMaturity]   = useState('')
  const [error, setError]         = useState('')

  const [ccPremium, setCcPremium] = useState('')

  const submit = async () => {
    const t = ticker.trim().toUpperCase()
    const s = parseFloat(shares)
    const p = parseFloat(price)
    if (!t) return setError('Introduce el ticker')
    if (!s || s <= 0) return setError('Cantidad inválida')
    if (!p || p <= 0) return setError('Precio inválido')
    if (assetType === 'option') {
      if (!strike || parseFloat(strike) <= 0) return setError('Strike inválido')
      if (!expiry) return setError('Fecha de expiración requerida')
    }
    if (assetType === 'covered_call') {
      if (!strike || parseFloat(strike) <= 0) return setError('Strike inválido')
      if (!expiry) return setError('Fecha de expiración requerida')
      if (!ccPremium || parseFloat(ccPremium) <= 0) return setError('Prima cobrada requerida')
    }
    setError('')
    const pos: Omit<Position, 'id'> = { ticker: t, shares: s, avg_price: p, currency, asset_type: assetType }
    if (assetType === 'option') {
      pos.option_type   = optType
      pos.option_strike = parseFloat(strike)
      pos.option_expiry = expiry
    }
    if (assetType === 'covered_call') {
      pos.option_strike = parseFloat(strike)
      pos.option_expiry = expiry
      pos.coupon_rate   = parseFloat(ccPremium)  // reuse field: premium received per share
    }
    if (assetType === 'bond' || assetType === 'preferred') {
      if (coupon) pos.coupon_rate = parseFloat(coupon)
      if (parVal) pos.par_value   = parseFloat(parVal)
      if (maturity) pos.maturity_date = maturity
    }
    await onAdd(pos)
    setTicker(''); setShares(''); setPrice(''); setStrike(''); setExpiry(''); setCoupon(''); setMaturity(''); setCcPremium('')
  }

  const inputCls = "px-3 py-2 rounded-lg bg-muted/30 border border-border/40 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50"

  return (
    <div className="glass rounded-2xl p-5 space-y-4">
      <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
        <Plus size={14} className="text-primary" />
        Añadir posición
      </h2>

      {/* Asset type selector */}
      <div className="flex gap-2 flex-wrap">
        {ASSET_TYPES.map(at => (
          <button
            key={at.value}
            onClick={() => setAssetType(at.value)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-all ${
              assetType === at.value
                ? `bg-primary/15 border-primary/40 text-primary`
                : 'bg-muted/20 border-border/30 text-muted-foreground hover:border-border/60'
            }`}
          >
            <span className={assetType === at.value ? 'text-primary' : at.color}>{at.icon}</span>
            {at.label}
          </button>
        ))}
      </div>

      {/* Common fields */}
      <div className="flex flex-col sm:flex-row flex-wrap gap-2 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Ticker</label>
          <input value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && submit()} placeholder="AAPL"
            className={`w-24 font-mono font-bold ${inputCls}`} />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">{SHARES_LABEL[assetType]}</label>
          <input value={shares} onChange={e => setShares(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            placeholder={assetType === 'option' ? '1' : assetType === 'bond' ? '10000' : '100'}
            type="number" min="0" className={`w-24 ${inputCls}`} />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">{PRICE_LABEL[assetType]}</label>
          <input value={price} onChange={e => setPrice(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            placeholder={assetType === 'bond' ? '98.50' : assetType === 'option' ? '3.50' : '150.00'}
            type="number" min="0" step="0.01" className={`w-28 ${inputCls}`} />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Moneda</label>
          <select value={currency} onChange={e => setCurrency(e.target.value as 'USD' | 'EUR')}
            className={inputCls}>
            <option value="USD">USD $</option>
            <option value="EUR">EUR €</option>
          </select>
        </div>
      </div>

      {/* Option-specific fields */}
      {assetType === 'option' && (
        <div className="flex flex-wrap gap-2 items-end p-3 rounded-xl bg-purple-500/5 border border-purple-500/15">
          <div className="flex flex-col gap-1">
            <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Tipo</label>
            <div className="flex rounded-lg overflow-hidden border border-border/40">
              {(['call', 'put'] as const).map(v => (
                <button key={v} onClick={() => setOptType(v)}
                  className={`px-3 py-1.5 text-xs font-bold uppercase transition-colors ${
                    optType === v ? (v === 'call' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400') : 'bg-muted/20 text-muted-foreground'
                  }`}>{v}</button>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Strike</label>
            <input value={strike} onChange={e => setStrike(e.target.value)} placeholder="150.00"
              type="number" min="0" step="0.50" className={`w-24 ${inputCls}`} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Expiración</label>
            <input value={expiry} onChange={e => setExpiry(e.target.value)} type="date"
              className={`w-36 ${inputCls}`} />
          </div>
        </div>
      )}

      {/* Covered Call specific fields */}
      {assetType === 'covered_call' && (
        <div className="flex flex-wrap gap-2 items-end p-3 rounded-xl bg-amber-500/5 border border-amber-500/15">
          <div className="flex flex-col gap-1">
            <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Strike vendido</label>
            <input value={strike} onChange={e => setStrike(e.target.value)} placeholder="60.00"
              type="number" min="0" step="0.50" className={`w-24 ${inputCls}`} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Prima cobrada/acc</label>
            <input value={ccPremium} onChange={e => setCcPremium(e.target.value)} placeholder="1.14"
              type="number" min="0" step="0.01" className={`w-28 ${inputCls}`} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Expiración</label>
            <input value={expiry} onChange={e => setExpiry(e.target.value)} type="date"
              className={`w-36 ${inputCls}`} />
          </div>
          <p className="w-full text-[0.62rem] text-amber-400/70 mt-1">
            Precio medio = coste de la acción (no la prima). Prima cobrada se guarda aparte.
          </p>
        </div>
      )}

      {/* Bond/Preferred-specific fields */}
      {(assetType === 'bond' || assetType === 'preferred') && (
        <div className="flex flex-wrap gap-2 items-end p-3 rounded-xl bg-amber-500/5 border border-amber-500/15">
          <div className="flex flex-col gap-1">
            <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Cupón %</label>
            <input value={coupon} onChange={e => setCoupon(e.target.value)} placeholder="5.25"
              type="number" min="0" step="0.01" className={`w-20 ${inputCls}`} />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Valor par</label>
            <input value={parVal} onChange={e => setParVal(e.target.value)} placeholder="1000"
              type="number" min="0" className={`w-20 ${inputCls}`} />
          </div>
          {assetType === 'bond' && (
            <div className="flex flex-col gap-1">
              <label className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Vencimiento</label>
              <input value={maturity} onChange={e => setMaturity(e.target.value)} type="date"
                className={`w-36 ${inputCls}`} />
            </div>
          )}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button onClick={submit} disabled={saving}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 active:scale-[0.98] transition-all disabled:opacity-50">
          {saving ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} strokeWidth={2.5} />}
          Añadir
        </button>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    </div>
  )
}

// ── Options Panel ─────────────────────────────────────────────────────────────

const STRAT_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  COVERED_CALL:      { label: 'Covered Call',       color: 'text-amber-400',   bg: 'bg-amber-500/8',   border: 'border-amber-500/20' },
  PROTECTIVE_PUT:    { label: 'Protective Put',      color: 'text-blue-400',    bg: 'bg-blue-500/8',    border: 'border-blue-500/20' },
  COLLAR:            { label: 'Collar',              color: 'text-purple-400',  bg: 'bg-purple-500/8',  border: 'border-purple-500/20' },
  BUY_MORE:          { label: 'Añadir posición',     color: 'text-emerald-400', bg: 'bg-emerald-500/8', border: 'border-emerald-500/20' },
  CASH_SECURED_PUT:  { label: 'Cash-Secured Put',   color: 'text-cyan-400',    bg: 'bg-cyan-500/8',    border: 'border-cyan-500/20' },
  TRAILING_STOP:     { label: 'Trailing Stop',       color: 'text-amber-400',   bg: 'bg-amber-500/8',   border: 'border-amber-500/20' },
  HOLD:              { label: 'Mantener',            color: 'text-primary',     bg: 'bg-primary/10',     border: 'border-primary/20' },
  SELL:              { label: 'Cerrar posición',     color: 'text-red-400',     bg: 'bg-red-500/8',     border: 'border-red-500/20' },
}

interface OptionsChainData {
  ticker: string
  current_price: number
  expiries: Array<{
    expiry: string
    days_out: number
    bucket: string
    covered_calls: Array<{ strike: number; bid: number; ask: number; mid: number; volume: number; open_interest: number; iv: number; pct_otm: number; annual_yield_pct: number }>
    protective_puts: Array<{ strike: number; bid: number; ask: number; mid: number; volume: number; open_interest: number; iv: number; pct_otm: number; cost_pct: number }>
  }>
  ai_recommendation: {
    recommended_strategy: string
    thesis_alignment?: string
    primary_contract: {
      action?: string; type: string; strike: number; expiry: string
      premium_approx?: number; premium?: number; total_cost_100_shares?: number
      horizon?: string; rationale?: string; order_instructions?: string
    } | null
    secondary_contract: { type: string; strike: number; expiry: string; premium: number; rationale: string } | null
    expected_outcome?: string
    profit_if_target?: string
    loss_if_drops?: string
    scenario_bull?: string
    scenario_bear?: string
    max_risk?: string
    when_to_close?: string
    step_by_step?: string
  } | null
}

function OptionsPanel({ result, sym }: { result: PositionResult; sym: string }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<OptionsChainData | null>(null)
  const [err, setErr] = useState('')

  const meta = STRAT_META[result.options_strategy ?? ''] ?? STRAT_META['HOLD']

  const fetchChain = async () => {
    if (data) { setOpen(o => !o); return }
    setOpen(true)
    setLoading(true)
    setErr('')
    try {
      const params = new URLSearchParams({
        price:      String(result.current_price ?? 0),
        pl:         String(result.pl_pct ?? 0),
        upside:     String(result.analyst_upside ?? 0),
        action:     result.action,
        conviction: result.conviction,
        thesis:     result.analysis ?? '',
        key_risk:   result.key_risk ?? '',
      })
      const { data: json } = await apiClient.get(`/api/options-chain/${result.ticker}?${params}`)
      setData(json)
    } catch {
      setErr('Error de red')
    }
    setLoading(false)
  }

  return (
    <div className="border-t border-border/20">
      {/* Header strip — always visible */}
      <div className={`mx-0 px-5 py-2.5 ${meta.bg} border-b ${meta.border}`}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <Zap size={12} className={meta.color} />
            <span className="text-[0.55rem] font-bold uppercase tracking-widest text-muted-foreground/50">Estrategia IA</span>
            <span className={`text-[0.72rem] font-bold ${meta.color}`}>{meta.label}</span>
            {result.options_rationale && (
              <span className="text-[0.7rem] text-foreground/60 truncate hidden sm:block">{result.options_rationale}</span>
            )}
          </div>
          <button
            onClick={fetchChain}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[0.65rem] font-semibold border transition-all ${meta.border} ${meta.color} hover:${meta.bg}`}
          >
            {loading ? <Loader2 size={10} className="animate-spin" /> : <ChevronDown size={10} className={open ? 'rotate-180' : ''} />}
            {data ? (open ? 'Ocultar' : 'Ver contratos') : 'Ver contratos reales'}
          </button>
        </div>
        {result.options_rationale && (
          <p className="text-[0.7rem] text-foreground/60 mt-1 sm:hidden">{result.options_rationale}</p>
        )}
      </div>

      {/* Options chain detail */}
      {open && (
        <div className="px-5 py-4 space-y-4">
          {loading && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 size={13} className="animate-spin" /> Cargando cadena de opciones desde Yahoo Finance…
            </div>
          )}
          {err && (
            <div className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
              {err.includes('no tiene opciones') ? (
                <span>{err} — Las estrategias basadas en opciones no están disponibles para este activo. Consulta el análisis de la IA arriba.</span>
              ) : err}
            </div>
          )}

          {data && (
            <>
              {/* AI recommendation */}
              {data.ai_recommendation && (() => {
                const rec = data.ai_recommendation!
                const pc = rec.primary_contract
                const premium = pc?.premium_approx ?? pc?.premium ?? 0
                return (
                <div className={`p-3 rounded-xl ${meta.bg} border ${meta.border} space-y-2.5`}>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[0.55rem] font-bold uppercase tracking-widest text-muted-foreground/50">Recomendación IA</span>
                    <span className={`text-[0.72rem] font-bold ${meta.color}`}>{rec.recommended_strategy?.replace(/_/g, ' ')}</span>
                    {rec.thesis_alignment && (
                      <span className="text-[0.68rem] text-foreground/60 flex-1">— {rec.thesis_alignment}</span>
                    )}
                  </div>

                  {pc && (
                    <div className="p-3 rounded-lg bg-background/40 border border-primary/20 space-y-2">
                      {/* Contract header */}
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded ${pc.action === 'COMPRAR' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                          {pc.action ?? (rec.recommended_strategy?.includes('COVERED') ? 'VENDER' : 'COMPRAR')}
                        </span>
                        <span className="font-bold text-foreground text-lg">{pc.type?.toUpperCase()} ${pc.strike}</span>
                        <span className="text-muted-foreground text-sm">exp {pc.expiry}</span>
                        <span className="text-[0.65rem] text-muted-foreground/50 uppercase">{pc.horizon}</span>
                      </div>
                      {/* Key numbers */}
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[0.72rem]">
                        <div>
                          <div className="text-muted-foreground/50 text-[0.58rem] uppercase mb-0.5">Prima por contrato</div>
                          <div className={`font-bold text-sm ${meta.color}`}>{sym}{premium?.toFixed(2)}</div>
                        </div>
                        {pc.total_cost_100_shares != null && (
                          <div>
                            <div className="text-muted-foreground/50 text-[0.58rem] uppercase mb-0.5">Coste total (100 acc)</div>
                            <div className="font-bold text-sm text-foreground">{sym}{pc.total_cost_100_shares?.toFixed(0)}</div>
                          </div>
                        )}
                        {(rec.profit_if_target ?? rec.expected_outcome) && (
                          <div>
                            <div className="text-muted-foreground/50 text-[0.58rem] uppercase mb-0.5">Si acierta</div>
                            <div className="text-emerald-400/80 text-[0.7rem]">{rec.profit_if_target ?? rec.expected_outcome}</div>
                          </div>
                        )}
                      </div>
                      {/* Order instructions — the "para tontos" section */}
                      {pc.order_instructions && (
                        <div className="p-2 rounded-lg bg-primary/5 border border-primary/20 text-[0.72rem] text-foreground/80">
                          <div className="text-primary font-semibold text-[0.6rem] uppercase tracking-wide mb-1">Orden exacta en tu broker</div>
                          {pc.order_instructions}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Step by step */}
                  {rec.step_by_step && (
                    <div className="p-2 rounded-lg bg-blue-500/5 border border-blue-500/15 text-[0.72rem] text-foreground/70 leading-relaxed">
                      <div className="text-blue-400 font-semibold text-[0.6rem] uppercase tracking-wide mb-1">Paso a paso</div>
                      {rec.step_by_step}
                    </div>
                  )}

                  {pc?.rationale && (
                    <p className="text-[0.72rem] text-foreground/70 leading-relaxed border-l-2 border-primary/30 pl-2.5">
                      {pc.rationale}
                    </p>
                  )}

                  {/* Bull/Bear scenarios */}
                  <div className="grid grid-cols-2 gap-2 text-[0.68rem]">
                    {(rec.profit_if_target || rec.scenario_bull) && (
                      <div className="p-2 rounded-lg bg-emerald-500/8 border border-emerald-500/15">
                        <div className="text-emerald-400 font-semibold mb-0.5">Si sube al target</div>
                        <div className="text-foreground/60">{rec.profit_if_target || rec.scenario_bull}</div>
                      </div>
                    )}
                    {(rec.loss_if_drops || rec.scenario_bear) && (
                      <div className="p-2 rounded-lg bg-red-500/8 border border-red-500/15">
                        <div className="text-red-400 font-semibold mb-0.5">Si cae -15%</div>
                        <div className="text-foreground/60">{rec.loss_if_drops || rec.scenario_bear}</div>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[0.68rem] pt-1 border-t border-border/20">
                    {rec.max_risk && <div><span className="text-red-400 font-semibold">Riesgo máx: </span><span className="text-foreground/60">{rec.max_risk}</span></div>}
                    {rec.when_to_close && <div><span className="text-amber-400 font-semibold">Cuándo cerrar: </span><span className="text-foreground/60">{rec.when_to_close}</span></div>}
                  </div>
                </div>
                )
              })()}

              {/* Raw contracts per expiry */}
              {data.expiries.map(exp => (
                <div key={exp.expiry}>
                  <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground/50 mb-2">
                    {exp.bucket === 'long' ? '🔵 LEAPS' : exp.bucket === 'medium' ? '🟡 Medio plazo' : '⚡ Corto plazo'} — {exp.expiry} · {exp.days_out} días
                  </div>

                  {exp.covered_calls.length > 0 && (
                    <div className="mb-3">
                      <div className="text-[0.62rem] font-semibold text-amber-400 mb-1.5">Covered Calls disponibles</div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-[0.7rem] border-collapse">
                          <thead>
                            <tr className="border-b border-border/30">
                              {['Strike', 'Bid', 'Ask', 'Prima', '% OTM', 'Yield anual', 'Vol', 'IV%'].map(h => (
                                <th key={h} className="text-left py-1 px-2 text-muted-foreground/50 font-semibold whitespace-nowrap">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {exp.covered_calls.map((c, i) => (
                              <tr key={i} className="border-b border-border/10 hover:bg-muted/10">
                                <td className="py-1.5 px-2 font-bold text-foreground">{sym}{c.strike}</td>
                                <td className="py-1.5 px-2 text-muted-foreground">{sym}{c.bid}</td>
                                <td className="py-1.5 px-2 text-muted-foreground">{sym}{c.ask}</td>
                                <td className="py-1.5 px-2 font-bold text-amber-400">{sym}{c.mid}</td>
                                <td className="py-1.5 px-2 text-muted-foreground">+{c.pct_otm}%</td>
                                <td className="py-1.5 px-2 font-bold text-emerald-400">{c.annual_yield_pct}%</td>
                                <td className="py-1.5 px-2 text-muted-foreground">{c.volume.toLocaleString()}</td>
                                <td className="py-1.5 px-2 text-muted-foreground">{c.iv}%</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {exp.protective_puts.length > 0 && (
                    <div>
                      <div className="text-[0.62rem] font-semibold text-blue-400 mb-1.5">Protective Puts disponibles</div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-[0.7rem] border-collapse">
                          <thead>
                            <tr className="border-b border-border/30">
                              {['Strike', 'Bid', 'Ask', 'Prima', '% OTM', 'Coste %', 'Vol', 'IV%'].map(h => (
                                <th key={h} className="text-left py-1 px-2 text-muted-foreground/50 font-semibold whitespace-nowrap">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {exp.protective_puts.map((p, i) => (
                              <tr key={i} className="border-b border-border/10 hover:bg-muted/10">
                                <td className="py-1.5 px-2 font-bold text-foreground">{sym}{p.strike}</td>
                                <td className="py-1.5 px-2 text-muted-foreground">{sym}{p.bid}</td>
                                <td className="py-1.5 px-2 text-muted-foreground">{sym}{p.ask}</td>
                                <td className="py-1.5 px-2 font-bold text-blue-400">{sym}{p.mid}</td>
                                <td className="py-1.5 px-2 text-muted-foreground">-{p.pct_otm}%</td>
                                <td className="py-1.5 px-2 text-red-400">{p.cost_pct}%</td>
                                <td className="py-1.5 px-2 text-muted-foreground">{p.volume.toLocaleString()}</td>
                                <td className="py-1.5 px-2 text-muted-foreground">{p.iv}%</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ── Covered Call Tracker ──────────────────────────────────────────────────────

function CoveredCallTracker({ pos, currentPrice }: { pos: Position; currentPrice: number }) {
  const strike      = pos.option_strike ?? 0
  const expiry      = pos.option_expiry ?? ''
  const premium     = pos.coupon_rate ?? 0   // premium received per share
  const costBasis   = pos.avg_price           // stock cost per share
  const shares      = pos.shares
  const sym         = pos.currency === 'EUR' ? '€' : '$'

  // Days to expiry
  const today    = new Date()
  today.setHours(0, 0, 0, 0)
  const expiryDate = expiry ? new Date(expiry) : null
  const dte        = expiryDate ? Math.max(0, Math.ceil((expiryDate.getTime() - today.getTime()) / 86400000)) : null

  // P&L breakdown
  const stockPL    = (currentPrice - costBasis) * shares
  const premiumPnL = premium * shares   // collected upfront, always ours
  const combined   = stockPL + premiumPnL
  const combinedPct = costBasis > 0 ? (combined / (costBasis * shares)) * 100 : 0

  // Effective cost basis after premium
  const effectiveBasis = costBasis - premium

  // Strike proximity
  const distPct    = strike > 0 ? ((strike - currentPrice) / currentPrice) * 100 : null
  const nearStrike = distPct !== null && distPct < 5   // within 5% of strike → risk
  const itm        = currentPrice >= strike

  // Recommendation
  let rec   = ''
  let recCls = ''
  if (itm) {
    rec    = 'ITM — riesgo de asignación. Considera cerrar (recomprar) o rodar el strike hacia arriba.'
    recCls = 'text-red-400'
  } else if (dte !== null && dte <= 14 && !itm) {
    rec    = `Expira en ${dte} días OTM — deja expirar y quédate la prima entera.`
    recCls = 'text-emerald-400'
  } else if (nearStrike) {
    rec    = `Precio cerca del strike (${distPct?.toFixed(1)}% OTM) — monitoriza de cerca.`
    recCls = 'text-amber-400'
  } else {
    rec    = `OTM ${distPct?.toFixed(1)}% — posición tranquila. La prima se acumula con el paso del tiempo.`
    recCls = 'text-primary'
  }

  return (
    <div className="mx-3 mb-3 rounded-xl border overflow-hidden border-amber-500/25 bg-amber-500/5">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-amber-500/20">
        <span className="text-[0.55rem] font-bold uppercase tracking-widest text-amber-400/60">Covered Call vendida</span>
        <span className="font-mono font-bold text-amber-400 text-sm">{sym}{strike} · exp {expiry}</span>
        {dte !== null && (
          <span className={`ml-auto text-[0.62rem] font-bold px-1.5 py-0.5 rounded border ${
            dte <= 7   ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25' :
            dte <= 21  ? 'bg-amber-500/15 text-amber-400 border-amber-500/25' :
                         'bg-muted/20 text-muted-foreground border-border/30'
          }`}>
            {dte}d exp
          </span>
        )}
        {itm && (
          <span className="text-[0.62rem] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">
            ITM ⚠
          </span>
        )}
      </div>

      {/* P&L grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-amber-500/10 text-[0.68rem]">
        <div className="bg-background/60 px-3 py-2.5">
          <div className="text-[0.55rem] uppercase tracking-wider text-muted-foreground/50 mb-0.5">Prima cobrada</div>
          <div className="font-bold text-emerald-400">{sym}{(premium * shares).toFixed(2)}</div>
          <div className="text-muted-foreground/40 text-[0.55rem]">{sym}{premium.toFixed(2)}/acc</div>
        </div>
        <div className="bg-background/60 px-3 py-2.5">
          <div className="text-[0.55rem] uppercase tracking-wider text-muted-foreground/50 mb-0.5">P&L acción</div>
          <div className={`font-bold ${stockPL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {stockPL >= 0 ? '+' : ''}{sym}{stockPL.toFixed(2)}
          </div>
          <div className="text-muted-foreground/40 text-[0.55rem]">base {sym}{costBasis.toFixed(2)}</div>
        </div>
        <div className="bg-background/60 px-3 py-2.5">
          <div className="text-[0.55rem] uppercase tracking-wider text-muted-foreground/50 mb-0.5">P&L combinado</div>
          <div className={`font-bold text-base ${combined >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {combined >= 0 ? '+' : ''}{sym}{combined.toFixed(2)}
          </div>
          <div className={`text-[0.62rem] font-semibold ${combinedPct >= 0 ? 'text-emerald-400/70' : 'text-red-400/70'}`}>
            {combinedPct >= 0 ? '+' : ''}{combinedPct.toFixed(2)}%
          </div>
        </div>
        <div className="bg-background/60 px-3 py-2.5">
          <div className="text-[0.55rem] uppercase tracking-wider text-muted-foreground/50 mb-0.5">Base efectiva</div>
          <div className="font-bold text-foreground">{sym}{effectiveBasis.toFixed(2)}</div>
          <div className="text-muted-foreground/40 text-[0.55rem]">
            dist strike {distPct != null ? `${distPct >= 0 ? '+' : ''}${distPct.toFixed(1)}%` : '—'}
          </div>
        </div>
      </div>

      {/* Recommendation */}
      <div className="px-4 py-2.5">
        <p className={`text-[0.72rem] leading-relaxed ${recCls}`}>{rec}</p>
      </div>
    </div>
  )
}

// ── Position Card ─────────────────────────────────────────────────────────────

function MetricChip({ label, value, valueClass = 'text-foreground' }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <span className="text-[0.58rem] font-semibold uppercase tracking-wider text-muted-foreground/50 leading-none">{label}</span>
      <span className={`text-sm font-bold tabular-nums leading-tight ${valueClass}`}>{value}</span>
    </div>
  )
}

function PriceAlertBadge({ alert }: { alert: PortfolioAlert }) {
  const cfg = alert.type === 'STOP_TRIGGERED'
    ? { label: '🚨 STOP', cls: 'bg-red-500/20 text-red-400 border-red-500/40' }
    : alert.type === 'TARGET_REACHED'
    ? { label: '🎯 TARGET', cls: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' }
    : { label: '🔔 cerca target', cls: 'bg-amber-500/15 text-amber-400 border-amber-500/30' }
  return (
    <span className={`text-[0.58rem] font-bold px-1.5 py-0.5 rounded-full border uppercase tracking-wide ${cfg.cls}`}>
      {cfg.label}
    </span>
  )
}

function PositionCard({ result, pos, userId, onRemove, onEdit, cerebro, confluence, macroWarnings, priceAlert, coveredCall }: {
  result?: PositionResult
  pos: Position
  userId: string
  onRemove: () => void
  onEdit: (id: string, shares: number, avgPrice: number, ticker?: string) => void
  cerebro: CerebroMaps
  confluence: ConfluenceSignals | null
  macroWarnings: MacroExposureWarning[]
  priceAlert?: PortfolioAlert
  coveredCall?: Position
}) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing]   = useState(false)
  const [editTicker, setEditTicker]   = useState(pos.ticker)
  const [editShares, setEditShares]   = useState(String(pos.shares))
  const [editPrice, setEditPrice]     = useState(String(pos.avg_price))
  const ticker = pos.ticker
  const cur    = result?.current_price ?? pos.avg_price
  const pl     = result?.pl_pct ?? null
  const sym    = pos.currency === 'EUR' ? '€' : '$'
  const action = result?.action ?? 'MANTENER'

  const exit   = cerebro.exitMap[ticker]
  const trap   = cerebro.trapMap[ticker]
  const sm     = cerebro.smMap[ticker]
  const div    = cerebro.divMap[ticker]
  const hasCerebro = !!(exit || trap || sm || div)

  const overweight  = result && result.portfolio_pct > (result.optimal_size_pct ?? 100) * 1.5
  const underweight = result && result.portfolio_pct < (result.optimal_size_pct ?? 0) * 0.5 && (result.optimal_size_pct ?? 0) > 0

  return (
    <div className={`glass rounded-2xl overflow-clip transition-all border h-full flex flex-col ${
      exit?.severity === 'HIGH' ? 'border-red-500/40' :
      trap ? 'border-amber-500/30' :
      action === 'AÑADIR' ? 'border-emerald-500/25' :
      action === 'VENDER' ? 'border-red-500/20' :
      'border-white/6'
    }`}>
      {/* Top accent line */}
      <div className={`h-0.5 w-full ${ACTION_BAR[action]}`} />

      {/* ── HEADER ── */}
      <div className="flex items-start gap-3 px-4 pt-4 pb-3">
        <TickerLogo ticker={ticker} size="sm" className="mt-0.5 shrink-0" />

        <div className="flex-1 min-w-0">
          {/* Row 1: ticker + company + sector */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono font-extrabold text-lg text-foreground leading-none">{ticker}</span>
            {result?.sector && (
              <span className="text-[0.58rem] px-1.5 py-0.5 rounded bg-muted/40 border border-border/20 text-muted-foreground/50 uppercase tracking-wide">
                {result.sector}
              </span>
            )}
          </div>
          {result?.company_name && result.company_name !== ticker && (
            <p className="text-xs text-muted-foreground/60 truncate mt-0.5 leading-tight">{result.company_name}</p>
          )}
          {/* Row 2: cost basis + asset type badge */}
          <p className="text-[0.65rem] text-muted-foreground/40 mt-1 flex items-center gap-1.5 flex-wrap">
            {pos.asset_type === 'option' ? (
              <>
                <span className={`px-1.5 py-0.5 rounded text-[0.58rem] font-bold uppercase border ${pos.option_type === 'call' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25' : 'bg-red-500/15 text-red-400 border-red-500/25'}`}>
                  {pos.option_type?.toUpperCase()} ${pos.option_strike}
                </span>
                {pos.option_expiry && <span>exp {pos.option_expiry}</span>}
                <span>{pos.shares} contrato{pos.shares !== 1 ? 's' : ''} · prima {sym}{pos.avg_price.toFixed(2)}</span>
              </>
            ) : pos.asset_type === 'bond' ? (
              <>
                <span className="px-1.5 py-0.5 rounded text-[0.58rem] font-bold uppercase border bg-amber-500/15 text-amber-400 border-amber-500/25">BONO</span>
                {pos.coupon_rate && <span>{pos.coupon_rate}% cupón</span>}
                {pos.maturity_date && <span>vence {pos.maturity_date}</span>}
                <span>nominal {sym}{pos.shares.toLocaleString()} · precio {pos.avg_price.toFixed(2)}%</span>
              </>
            ) : pos.asset_type === 'preferred' ? (
              <>
                <span className="px-1.5 py-0.5 rounded text-[0.58rem] font-bold uppercase border bg-emerald-500/15 text-emerald-400 border-emerald-500/25">PREFERRED</span>
                {pos.coupon_rate && <span>{pos.coupon_rate}% div</span>}
                <span>{pos.shares} acc · base {sym}{pos.avg_price.toFixed(2)}</span>
              </>
            ) : pos.asset_type === 'covered_call' ? (
              <>
                <span className="px-1.5 py-0.5 rounded text-[0.58rem] font-bold uppercase border bg-amber-500/15 text-amber-400 border-amber-500/25">COVERED CALL</span>
                <span>CALL ${pos.option_strike} exp {pos.option_expiry}</span>
                <span>{pos.shares} acc · base {sym}{pos.avg_price.toFixed(2)} · prima {sym}{(pos.coupon_rate ?? 0).toFixed(2)}/acc</span>
              </>
            ) : (
              <span>{pos.shares} acc · base {sym}{pos.avg_price.toFixed(2)}</span>
            )}
          </p>
        </div>

        {/* Right: price + action + remove + edit */}
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <div className="flex items-center gap-1.5">
            {priceAlert && <PriceAlertBadge alert={priceAlert} />}
            {result && !editing && (
              <span className={`text-[0.62rem] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wide ${ACTION_STYLES[action]}`}>
                {action}
              </span>
            )}
            <button
              onClick={() => { setEditing(e => !e); setEditTicker(pos.ticker); setEditShares(String(pos.shares)); setEditPrice(String(pos.avg_price)) }}
              className={`p-1 rounded-md transition-colors ${editing ? 'text-primary bg-primary/10' : 'text-muted-foreground/40 hover:text-primary hover:bg-primary/10'}`}
              title="Editar posición"
            >
              <Pencil size={12} />
            </button>
            <button onClick={onRemove} className="p-1 rounded-md text-muted-foreground/40 hover:text-red-400 hover:bg-red-500/10 transition-colors">
              <X size={12} />
            </button>
          </div>
          {editing ? (
            <div className="flex flex-col items-end gap-1 mt-1">
              <div className="flex items-center gap-1">
                <span className="text-[0.6rem] text-muted-foreground/50">ticker</span>
                <input
                  value={editTicker}
                  onChange={e => setEditTicker(e.target.value.toUpperCase())}
                  className="w-20 text-right text-xs font-mono font-bold bg-background/60 border border-border/40 rounded px-1 py-0.5 focus:outline-none focus:border-primary/50"
                  placeholder="AAPL"
                />
              </div>
              <div className="flex items-center gap-1">
                <span className="text-[0.6rem] text-muted-foreground/50">acc</span>
                <input
                  type="number"
                  value={editShares}
                  onChange={e => setEditShares(e.target.value)}
                  className="w-16 text-right text-xs bg-background/60 border border-border/40 rounded px-1 py-0.5 focus:outline-none focus:border-primary/50"
                  min="0"
                  step="any"
                />
              </div>
              <div className="flex items-center gap-1">
                <span className="text-[0.6rem] text-muted-foreground/50">base</span>
                <input
                  type="number"
                  value={editPrice}
                  onChange={e => setEditPrice(e.target.value)}
                  className="w-20 text-right text-xs bg-background/60 border border-border/40 rounded px-1 py-0.5 focus:outline-none focus:border-primary/50"
                  min="0"
                  step="any"
                />
              </div>
              <button
                onClick={() => {
                  const s = parseFloat(editShares)
                  const p = parseFloat(editPrice)
                  const t = editTicker.trim()
                  if (s > 0 && p > 0 && t) { onEdit(pos.id, s, p, t); setEditing(false) }
                }}
                className="flex items-center gap-1 text-[0.6rem] font-bold px-2 py-0.5 rounded bg-primary/15 border border-primary/30 text-primary hover:bg-primary/25 transition-colors"
              >
                <Check size={10} /> Guardar
              </button>
            </div>
          ) : (
            <div className="text-right">
              <div className="font-extrabold text-base tabular-nums text-foreground">{sym}{cur.toFixed(2)}</div>
              {result && (
                <div className="text-[0.6rem] text-muted-foreground/40 tabular-nums">
                  {sym}{result.market_value.toFixed(0)} · {result.portfolio_pct.toFixed(1)}%
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── P&L BAND ── */}
      <div className={`flex items-center gap-2 px-4 py-2.5 mx-3 mb-3 rounded-xl ${pl == null ? 'bg-muted/10 border border-border/20' : pl >= 0 ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-red-500/10 border border-red-500/20'}`}>
        {pl == null ? <TrendingUp size={15} className="text-muted-foreground/40 shrink-0" /> : pl >= 0 ? <TrendingUp size={15} className="text-emerald-400 shrink-0" /> : <TrendingDown size={15} className="text-red-400 shrink-0" />}
        <span className={`text-2xl font-black tabular-nums leading-none ${pl == null ? 'text-muted-foreground/30' : pl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {pl == null ? '—' : `${pl >= 0 ? '+' : ''}${pl.toFixed(2)}%`}
        </span>
        {result && (
          <span className={`text-sm font-semibold tabular-nums opacity-60 ${(pl ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {result.pl_abs >= 0 ? '+' : ''}{sym}{Math.abs(result.pl_abs).toFixed(0)}
          </span>
        )}
        {result && (
          <span className="ml-auto flex items-center gap-1.5 text-[0.6rem]">
            <span className={`w-1.5 h-1.5 rounded-full ${CONVICTION_DOT[result.conviction]}`} />
            <span className="text-muted-foreground/50 uppercase tracking-wide">{result.conviction}</span>
          </span>
        )}
      </div>

      {/* ── NL STATUS SENTENCE ── */}
      <div className="px-4 pb-2">
        <p className="text-[0.73rem] leading-relaxed text-muted-foreground/70">
          {nlPositionStatus({
            pl_pct:          pl ?? 0,
            action,
            cerebro_exit:    !!exit,
            cerebro_trap:    !!trap,
            cerebro_smart_money: !!sm,
            optimal_size_pct:    result?.optimal_size_pct,
            portfolio_pct:       result?.portfolio_pct,
          })}
        </p>
      </div>

      {/* ── CEREBRO SIGNALS (compact pills) ── */}
      {hasCerebro && (
        <div className="flex flex-wrap gap-1.5 px-4 mb-3">
          {exit && (
            <span className={`inline-flex items-center gap-1 text-[0.62rem] font-bold px-2 py-0.5 rounded-full border ${exit.severity === 'HIGH' ? 'bg-red-500/15 text-red-400 border-red-500/30' : 'bg-amber-500/15 text-amber-400 border-amber-500/30'}`}>
              <Brain size={9} />EXIT {exit.severity} · {exit.reasons[0]}
            </span>
          )}
          {trap && !exit && (
            <span className="inline-flex items-center gap-1 text-[0.62rem] font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
              <Brain size={9} />TRAP · {trap.flags[0]}
            </span>
          )}
          {sm && (
            <span className="inline-flex items-center gap-1 text-[0.62rem] font-bold px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-400 border border-violet-500/30">
              <Brain size={9} />SMART $ · {sm.n_hedge_funds}HF {sm.n_insiders}INS
            </span>
          )}
          {div && (
            <span className="inline-flex items-center gap-1 text-[0.62rem] font-bold px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
              <Brain size={9} />DIV {div.rating} · {div.div_yield.toFixed(1)}%
            </span>
          )}
        </div>
      )}

      {/* ── CONFLUENCE SIGNALS ── */}
      {confluence && (confluence.bounce || confluence.value || confluence.flow) && (
        <div className="flex flex-wrap gap-1.5 px-4 mb-3">
          {confluence.bounce && (
            <span className="inline-flex items-center gap-1 text-[0.62rem] font-bold px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30">
              🎯 Bounce
            </span>
          )}
          {confluence.value && (
            <span className="inline-flex items-center gap-1 text-[0.62rem] font-bold px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
              💎 VALUE
            </span>
          )}
          {confluence.flow === 'BULLISH' && (
            <span className="inline-flex items-center gap-1 text-[0.62rem] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
              ⚡ Flow alcista
            </span>
          )}
          {confluence.flow === 'PUT_COVERING' && (
            <span className="inline-flex items-center gap-1 text-[0.62rem] font-bold px-2 py-0.5 rounded-full bg-yellow-500/15 text-yellow-300 border border-yellow-500/30">
              🔄 Suelo probable
            </span>
          )}
        </div>
      )}

      {macroWarnings.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-4 mb-3">
          {macroWarnings.map((warning) => (
            <span
              key={`${warning.marketId}-${warning.side}`}
              className={`inline-flex items-center gap-1 text-[0.62rem] font-bold px-2 py-0.5 rounded-full border ${
                warning.side === 'beneficiary'
                  ? 'bg-orange-500/15 text-orange-300 border-orange-500/30'
                  : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
              }`}
            >
              <AlertTriangle size={9} />
              {warning.marketLabel} {warning.side === 'beneficiary' ? '↑' : '↓'} · {warning.score.toFixed(0)}
            </span>
          ))}
        </div>
      )}

      {/* ── CHART ── */}
      <div className="mx-3 rounded-xl overflow-hidden border border-border/20 mb-3">
        <PriceChart ticker={ticker} height={58} mini />
      </div>

      {/* ── KEY METRICS GRID ── */}
      {result && (() => {
        const assetT = pos.asset_type ?? 'stock'
        type MetricDef = { label: string; value: string; valueClass?: string; suffix?: string; suffixClass?: string }
        let metrics: (MetricDef | false)[] = []

        if (assetT === 'covered_call') {
          const strike  = pos.option_strike ?? 0
          const premium = pos.coupon_rate ?? 0
          const today2  = new Date(); today2.setHours(0,0,0,0)
          const expDate = pos.option_expiry ? new Date(pos.option_expiry) : null
          const dte2    = expDate ? Math.max(0, Math.ceil((expDate.getTime() - today2.getTime()) / 86400000)) : null
          const distPct2 = strike > 0 ? ((strike - cur) / cur) * 100 : null
          const itm2    = cur >= strike
          const combined2 = (cur - pos.avg_price + premium) * pos.shares
          metrics = [
            { label: 'Strike', value: `${sym}${strike}`, valueClass: itm2 ? 'text-red-400' : 'text-amber-400' },
            { label: 'Prima cobrada', value: `${sym}${(premium * pos.shares).toFixed(2)}`, valueClass: 'text-emerald-400' },
            dte2 != null && { label: 'Días exp', value: String(dte2), valueClass: dte2 <= 7 ? 'text-emerald-400' : dte2 <= 21 ? 'text-amber-400' : 'text-foreground' },
            { label: 'Estado', value: itm2 ? 'ITM ⚠' : `OTM ${distPct2?.toFixed(1)}%`, valueClass: itm2 ? 'text-red-400' : 'text-emerald-400' },
            { label: 'P&L combinado', value: `${combined2 >= 0 ? '+' : ''}${sym}${combined2.toFixed(2)}`, valueClass: combined2 >= 0 ? 'text-emerald-400' : 'text-red-400' },
            { label: 'Base efectiva', value: `${sym}${(pos.avg_price - premium).toFixed(2)}` },
          ]
        } else if (assetT === 'option') {
          const dte = result.days_to_expiry
          const itm = result.itm
          metrics = [
            { label: 'Tipo', value: (pos.option_type ?? '—').toUpperCase(), valueClass: pos.option_type === 'call' ? 'text-emerald-400' : 'text-red-400' },
            { label: 'Strike', value: `${sym}${pos.option_strike ?? '—'}` },
            dte != null && { label: 'Días exp', value: String(dte), valueClass: dte < 14 ? 'text-red-400' : dte < 30 ? 'text-amber-400' : 'text-foreground' },
            result.intrinsic_value != null && { label: 'Val intrínseco', value: `${sym}${result.intrinsic_value.toFixed(2)}`, valueClass: result.intrinsic_value > 0 ? 'text-emerald-400' : 'text-muted-foreground' },
            itm != null && { label: 'Estado', value: itm ? 'ITM' : 'OTM', valueClass: itm ? 'text-emerald-400' : 'text-amber-400' },
            { label: 'Peso', value: `${result.portfolio_pct.toFixed(1)}%` },
          ]
        } else if (assetT === 'bond') {
          metrics = [
            pos.coupon_rate != null && { label: 'Cupón', value: `${pos.coupon_rate.toFixed(2)}%`, valueClass: 'text-amber-400' },
            result.ytm != null && { label: 'YTM', value: `${result.ytm.toFixed(2)}%`, valueClass: 'text-emerald-400' },
            result.current_yield != null && { label: 'Yield actual', value: `${result.current_yield.toFixed(2)}%` },
            result.days_to_maturity != null && { label: 'Días venc.', value: String(result.days_to_maturity) },
            { label: 'Precio', value: `${result.current_price.toFixed(2)}%` },
            { label: 'Peso', value: `${result.portfolio_pct.toFixed(1)}%` },
          ]
        } else if (assetT === 'preferred') {
          metrics = [
            pos.coupon_rate != null && { label: 'Div fijo', value: `${pos.coupon_rate.toFixed(2)}%`, valueClass: 'text-emerald-400' },
            result.current_yield != null && { label: 'Yield actual', value: `${result.current_yield.toFixed(2)}%`, valueClass: 'text-emerald-400' },
            pos.par_value != null && { label: 'Par', value: `${sym}${pos.par_value}` },
            result.analyst_target != null && { label: 'Target', value: `${sym}${result.analyst_target.toFixed(0)}` },
            result.stop_loss != null && { label: 'Stop loss', value: `${sym}${result.stop_loss.toFixed(2)}`, valueClass: 'text-red-400' },
            { label: 'Peso', value: `${result.portfolio_pct.toFixed(1)}%` },
          ]
        } else {
          metrics = [
            result.forward_pe != null && { label: 'PE fwd', value: `${result.forward_pe.toFixed(1)}x` },
            result.fcf_yield != null && { label: 'FCF yield', value: `${result.fcf_yield.toFixed(1)}%`, valueClass: result.fcf_yield >= 5 ? 'text-emerald-400' : result.fcf_yield < 0 ? 'text-red-400' : 'text-foreground' },
            result.dividend_yield != null && result.dividend_yield > 0 && { label: 'Div yield', value: `${result.dividend_yield.toFixed(2)}%`, valueClass: 'text-emerald-400' },
            result.analyst_target != null && { label: 'Target', value: `${sym}${result.analyst_target.toFixed(0)}`, suffix: result.analyst_upside != null ? ` ${result.analyst_upside >= 0 ? '+' : ''}${result.analyst_upside.toFixed(0)}%` : undefined, suffixClass: result.analyst_upside != null && result.analyst_upside >= 0 ? 'text-emerald-400' : 'text-red-400' },
            result.stop_loss != null && { label: 'Stop loss', value: `${sym}${result.stop_loss.toFixed(2)}`, valueClass: 'text-red-400' },
            { label: 'Peso', value: `${result.portfolio_pct.toFixed(1)}%`, valueClass: overweight ? 'text-red-400' : underweight ? 'text-blue-400' : 'text-foreground' },
          ]
        }

        const items = metrics.filter(Boolean).slice(0, 6) as MetricDef[]
        return (
          <div className="grid grid-cols-3 gap-px bg-border/20 border border-border/20 rounded-xl overflow-hidden mx-3 mb-3">
            {items.map((m, i) => (
              <div key={i} className="bg-muted/8 px-3 py-2.5">
                <div className="text-[0.55rem] font-semibold uppercase tracking-wider text-muted-foreground/40 mb-0.5">{m.label}</div>
                <div className={`text-sm font-bold tabular-nums ${m.valueClass ?? 'text-foreground'}`}>
                  {m.value}
                  {m.suffix && <span className={`text-xs ml-1 ${m.suffixClass}`}>{m.suffix}</span>}
                </div>
              </div>
            ))}
          </div>
        )
      })()}

      {/* ── SIZING ROW (stocks only) ── */}
      {result?.volatility_pct != null && (pos.asset_type ?? 'stock') === 'stock' && (
        <div className="px-4 py-2.5 mx-3 mb-3 rounded-xl bg-primary/5 border border-primary/10">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[0.55rem] font-bold uppercase tracking-widest text-primary/50">Sizing</span>
            {(overweight || underweight) && (
              <span className={`text-[0.6rem] font-bold uppercase tracking-wide ${overweight ? 'text-red-400' : 'text-blue-400'}`}>
                {overweight ? '↑ SOBRE' : '↓ INFRA'}
              </span>
            )}
          </div>
          <div className="flex gap-4 flex-wrap">
            <MetricChip label="Vol" value={`${result.volatility_pct.toFixed(1)}%`} valueClass={(result.volatility_pct) > 15 ? 'text-red-400' : 'text-amber-400'} />
            <MetricChip label="Kelly" value={`${result.kelly_pct?.toFixed(1)}%`} />
            <MetricChip label="Óptimo" value={`${result.optimal_size_pct?.toFixed(1)}%`} valueClass={overweight ? 'text-red-400' : underweight ? 'text-blue-400' : 'text-primary'} />
            {result.stop_loss_atr != null && (
              <MetricChip label="Stop ATR" value={`${sym}${result.stop_loss_atr.toFixed(2)}`} valueClass="text-red-400" />
            )}
          </div>
        </div>
      )}

      {/* ── AI ANALYSIS (expand toggle) ── */}
      {result?.analysis && (
        <div className="mx-3 mb-3">
          <button
            onClick={() => setExpanded(v => !v)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-xl bg-muted/10 border border-border/20 text-xs text-muted-foreground hover:border-border/40 transition-colors"
          >
            <span className="flex items-center gap-1.5 font-medium">
              <Brain size={11} className="text-primary/60" />
              Análisis IA
            </span>
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {expanded && (
            <div className="mt-1.5 px-3 py-3 rounded-xl bg-muted/8 border border-border/15 space-y-2">
              <p className="text-xs text-foreground/75 leading-relaxed">{result.analysis}</p>
              {result.key_risk && (
                <div className="flex items-start gap-2 px-2.5 py-2 rounded-lg border border-amber-500/20 bg-amber-500/5">
                  <AlertTriangle size={11} className="text-amber-400 mt-0.5 shrink-0" />
                  <p className="text-[0.7rem] text-amber-300/75 leading-relaxed">{result.key_risk}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── OPTIONS PANEL (stocks only) ── */}
      {result && (pos.asset_type ?? 'stock') === 'stock' && <div className="mx-3 mb-3"><OptionsPanel result={result} sym={sym} /></div>}

      {/* ── COVERED CALL TRACKER ── */}
      {coveredCall && (
        <CoveredCallTracker pos={coveredCall} currentPrice={cur} />
      )}

      {/* ── JOURNAL ── */}
      <JournalSection ticker={ticker} userId={userId} />
    </div>
  )
}

// ── Analysis Cache ────────────────────────────────────────────────────────────
// Cache key: sorted ticker list + shares + avg_price fingerprint
// TTL: 6 hours. On mutation: invalidate immediately and re-analyze.

const CACHE_KEY   = 'sa-portfolio-analysis-v1'
const CACHE_TTL_MS = 6 * 60 * 60 * 1000  // 6 hours

interface CacheEntry {
  fingerprint: string
  result: AnalysisResult
  ts: number
}

function positionsFingerprint(positions: Position[]): string {
  return positions
    .filter(p => p.asset_type !== 'covered_call')
    .map(p => `${p.ticker}:${p.shares}:${p.avg_price}`)
    .sort()
    .join('|')
}

function readCache(fingerprint: string): AnalysisResult | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const entry: CacheEntry = JSON.parse(raw)
    if (entry.fingerprint !== fingerprint) return null
    if (Date.now() - entry.ts > CACHE_TTL_MS) return null
    return entry.result
  } catch { return null }
}

function writeCache(fingerprint: string, result: AnalysisResult) {
  try {
    const entry: CacheEntry = { fingerprint, result, ts: Date.now() }
    localStorage.setItem(CACHE_KEY, JSON.stringify(entry))
  } catch { /* quota exceeded — ignore */ }
}

function invalidateCache() {
  localStorage.removeItem(CACHE_KEY)
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function PersonalPortfolio() {
  const { user } = useAuth()
  const cerebro    = useCerebroSignals()
  const confluence = usePortfolioConfluence()
  const { data: macroStressData }    = useApi(() => fetchMacroStress(), [])
  const { data: revisionsData }      = useApi(() => fetchAnalystRevisions(), [])
  const { data: portAlertsData }     = useApi(() => fetchPortfolioAlerts().then(d => ({ data: d })), [])
  const priceAlertMap = useMemo<Record<string, PortfolioAlert>>(() => {
    const alerts = portAlertsData?.alerts ?? []
    return Object.fromEntries(alerts.map(a => [a.ticker.toUpperCase(), a]))
  }, [portAlertsData])
  const [positions, setPositions] = useState<Position[]>([])
  const [loadingDb, setLoadingDb] = useState(true)
  const [saving, setSaving]       = useState(false)
  const [result, setResult]       = useState<AnalysisResult | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError]         = useState('')
  const [analyzed, setAnalyzed]   = useState(false)
  const [cacheAge, setCacheAge]   = useState<number | null>(null)  // ms since last analysis
  const [refreshState, setRefreshState] = useState<{ status: 'idle' | 'running' | 'ok' | 'error'; message?: string }>({ status: 'idle' })

  // Trigger recompute on-demand de strategies/theses/options tras mutar la cartera.
  // No bloquea la UI: corre en background y muestra estado en un banner.
  const triggerArtifactsRefresh = useCallback(async () => {
    setRefreshState({ status: 'running', message: 'Recalculando estrategias y earnings…' })
    try {
      const res = await refreshUserArtifacts()
      const errors = Object.entries(res.summary)
        .filter(([, v]) => 'error' in v)
        .map(([k]) => k)
      if (errors.length === 0) {
        setRefreshState({ status: 'ok', message: `Estrategias recalculadas (${res.elapsed_seconds}s)` })
      } else {
        setRefreshState({ status: 'error', message: `Parcial: ${errors.join(', ')} fallaron` })
      }
      // Auto-clear el banner después de 6s
      window.setTimeout(() => setRefreshState({ status: 'idle' }), 6000)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setRefreshState({ status: 'error', message: `Refresh falló: ${msg.slice(0, 80)}` })
      window.setTimeout(() => setRefreshState({ status: 'idle' }), 8000)
    }
  }, [])

  // Load positions from Supabase on mount
  useEffect(() => {
    if (!user) return
    setLoadingDb(true)
    supabase
      .from('personal_portfolio_positions')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: true })
      .then(({ data, error: err }) => {
        if (!err && data) {
          setPositions(data.map(r => ({
            id: r.id,
            ticker: r.ticker,
            shares: r.shares,
            avg_price: r.avg_price,
            currency: r.currency,
            asset_type: (r.asset_type ?? 'stock') as AssetType,
            option_type: r.option_type ?? undefined,
            option_strike: r.option_strike ?? undefined,
            option_expiry: r.option_expiry ?? undefined,
            coupon_rate: r.coupon_rate ?? undefined,
            par_value: r.par_value ?? undefined,
            maturity_date: r.maturity_date ?? undefined,
          })))
        }
        setLoadingDb(false)
      })
  }, [user])

  // Auto-analyze once positions are loaded — uses cache when fresh
  useEffect(() => {
    if (loadingDb || positions.length === 0 || analyzed) return
    const fp = positionsFingerprint(positions)
    const cached = readCache(fp)
    if (cached) {
      setResult(cached)
      setAnalyzed(true)
      try {
        const entry: CacheEntry = JSON.parse(localStorage.getItem(CACHE_KEY) ?? '{}')
        setCacheAge(Date.now() - (entry.ts ?? 0))
      } catch { /* ignore */ }
      return
    }
    analyze()
  }, [loadingDb]) // eslint-disable-line react-hooks/exhaustive-deps

  const analyze = useCallback(async (silent = false) => {
    if (!positions.length) return
    if (!silent) { setAnalyzing(true); setError('') }
    try {
      const resp = await apiClient.post('/api/analyze-personal-portfolio', { positions }, { timeout: 120_000 })
      const fp = positionsFingerprint(positions)
      writeCache(fp, resp.data)
      setResult(resp.data)
      setAnalyzed(true)
      setCacheAge(0)
    } catch (e: unknown) {
      if (!silent) {
        const isTimeout = e && typeof e === 'object' && 'code' in e && (e as {code: string}).code === 'ECONNABORTED'
        setError(isTimeout
          ? 'El servidor tardó demasiado (cold start). Espera 30s y pulsa Re-analizar.'
          : 'Error al analizar. Pulsa Re-analizar para intentarlo de nuevo.'
        )
      }
    } finally {
      if (!silent) setAnalyzing(false)
    }
  }, [positions])

  const addPosition = async (p: Omit<Position, 'id'>) => {
    if (!user) return
    const existing = positions.find(x => x.ticker === p.ticker)
    if (existing) {
      const newShares = existing.shares + p.shares
      const newAvg    = (existing.shares * existing.avg_price + p.shares * p.avg_price) / newShares
      setSaving(true)
      const { error: err } = await supabase
        .from('personal_portfolio_positions')
        .update({ shares: newShares, avg_price: newAvg })
        .eq('id', existing.id)
      setSaving(false)
      if (!err) {
        setPositions(prev => prev.map(x => x.id === existing.id ? { ...x, shares: newShares, avg_price: newAvg } : x))
        invalidateCache(); setResult(null); setAnalyzed(false)
        triggerArtifactsRefresh()
      }
      return
    }
    setSaving(true)
    const { data, error: err } = await supabase
      .from('personal_portfolio_positions')
      .insert({
        user_id: user.id, ticker: p.ticker, shares: p.shares, avg_price: p.avg_price, currency: p.currency,
        asset_type: p.asset_type ?? 'stock',
        option_type: p.option_type ?? null, option_strike: p.option_strike ?? null, option_expiry: p.option_expiry ?? null,
        coupon_rate: p.coupon_rate ?? null, par_value: p.par_value ?? null, maturity_date: p.maturity_date ?? null,
      })
      .select()
      .single()
    setSaving(false)
    if (!err && data) {
      setPositions(prev => [...prev, {
        id: data.id, ticker: data.ticker, shares: data.shares, avg_price: data.avg_price, currency: data.currency,
        asset_type: (data.asset_type ?? 'stock') as AssetType,
        option_type: data.option_type ?? undefined, option_strike: data.option_strike ?? undefined, option_expiry: data.option_expiry ?? undefined,
        coupon_rate: data.coupon_rate ?? undefined, par_value: data.par_value ?? undefined, maturity_date: data.maturity_date ?? undefined,
      }])
      invalidateCache(); setResult(null); setAnalyzed(false)
      triggerArtifactsRefresh()
    }
  }

  const removePosition = async (id: string) => {
    await supabase.from('personal_portfolio_positions').delete().eq('id', id)
    setPositions(prev => prev.filter(p => p.id !== id))
    invalidateCache(); setResult(null); setAnalyzed(false)
    triggerArtifactsRefresh()
  }

  const updatePosition = async (id: string, shares: number, avgPrice: number, ticker?: string) => {
    const update: Record<string, unknown> = { shares, avg_price: avgPrice }
    if (ticker) update.ticker = ticker
    await supabase
      .from('personal_portfolio_positions')
      .update(update)
      .eq('id', id)
    setPositions(prev => prev.map(p => p.id === id ? { ...p, shares, avg_price: avgPrice, ...(ticker ? { ticker } : {}) } : p))
    invalidateCache(); setResult(null); setAnalyzed(false)
    triggerArtifactsRefresh()
  }

  const totalCost  = positions.reduce((s, p) => s + p.shares * p.avg_price, 0)
  const totalValue = result?.total_value ?? totalCost
  const totalPL    = totalValue - totalCost
  const totalPLPct = totalCost > 0 ? (totalPL / totalCost * 100) : 0

  // Dividend projection from analysis results
  const annualDividends = result?.positions.reduce((sum, p) => {
    if (p.dividend_yield && p.dividend_yield > 0 && p.market_value) {
      return sum + (p.market_value * p.dividend_yield / 100)
    }
    return sum
  }, 0) ?? 0

  const dividendPositions = result?.positions.filter(p => p.dividend_yield && p.dividend_yield > 0) ?? []
  const macroWarningsByTicker = useMemo<Record<string, MacroExposureWarning[]>>(() => {
    const out: Record<string, MacroExposureWarning[]> = {}
    const marketEntries = Object.entries(macroStressData?.markets ?? {})
    if (!marketEntries.length || !positions.length) return out

    const tickersInPortfolio = new Set(positions.map((pos) => pos.ticker.toUpperCase()))
    for (const [marketId, market] of marketEntries) {
      const score = market.stress_score ?? 0
      if (score < 70) continue

      const pushWarning = (ticker: string, side: 'beneficiary' | 'loser', marketData: MacroStressMarket) => {
        const clean = ticker.toUpperCase()
        if (!tickersInPortfolio.has(clean)) return
        if (!out[clean]) out[clean] = []
        out[clean].push({
          marketId,
          marketLabel: marketData.label,
          score,
          regime: marketData.regime,
          side,
        })
      }

      for (const ticker of market.equity_exposure?.beneficiaries ?? []) pushWarning(ticker, 'beneficiary', market)
      for (const ticker of market.equity_exposure?.losers ?? []) pushWarning(ticker, 'loser', market)
    }
    return out
  }, [macroStressData, positions])

  const macroWarningEntries = useMemo(
    () => Object.entries(macroWarningsByTicker).sort((a, b) => a[0].localeCompare(b[0])),
    [macroWarningsByTicker],
  )

  if (loadingDb) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-6 select-none">
        {/* Animated tickers */}
        <div className="flex gap-2 items-end h-10">
          {['ABT','BSX','MA','INTU','ADP'].map((t, i) => (
            <div key={t} className="flex flex-col items-center gap-1">
              <div
                className="w-8 rounded-sm bg-primary/70"
                style={{
                  height: `${20 + Math.sin(i * 1.3) * 14 + 14}px`,
                  animation: `portfolioBar 1.1s ease-in-out ${i * 0.15}s infinite alternate`,
                }}
              />
              <span className="text-[0.5rem] font-mono text-muted-foreground/40">{t}</span>
            </div>
          ))}
        </div>
        <style>{`
          @keyframes portfolioBar {
            0%   { transform: scaleY(0.4); opacity: 0.4; }
            100% { transform: scaleY(1);   opacity: 1;   }
          }
        `}</style>
        <div className="text-center space-y-1">
          <p className="text-sm font-semibold text-foreground/80">Cargando tu cartera…</p>
          <p className="text-xs text-muted-foreground/50">Conectando con la nube</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="gradient-title text-2xl font-extrabold flex items-center gap-2">
          <Wallet size={22} className="text-primary" />
          Mi Cartera Personal
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Tus posiciones se guardan en la nube. El análisis IA se actualiza en cada visita.
        </p>
      </div>

      {/* Summary (after analysis) */}
      {result && (
        <div className="glass rounded-2xl p-5 space-y-4">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div className="flex gap-6 flex-wrap">
              <div className="animate-fade-in-up text-center sm:text-left" style={{ animationDelay: '0ms' }}>
                <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-0.5">Valor total</div>
                <div className="text-4xl font-black tabular-nums text-foreground">
                  ${result.total_value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </div>
              </div>
              <div className="animate-fade-in-up text-center sm:text-left" style={{ animationDelay: '60ms' }}>
                <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-0.5">P&L total</div>
                <div className={`text-2xl font-bold tabular-nums flex items-center gap-1 ${totalPL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {totalPL >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                  {totalPL >= 0 ? '+' : ''}${totalPL.toFixed(0)}
                  <span className="text-sm font-semibold ml-1">({totalPLPct >= 0 ? '+' : ''}{totalPLPct.toFixed(2)}%)</span>
                </div>
              </div>
              <div className="animate-fade-in-up text-center sm:text-left" style={{ animationDelay: '120ms' }}>
                <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-0.5">Posiciones</div>
                <div className="text-2xl font-bold text-foreground">{positions.length}</div>
              </div>
              {annualDividends > 0 && (
                <div className="animate-fade-in-up text-center sm:text-left" style={{ animationDelay: '180ms' }}>
                  <div className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-0.5">Dividendos / año</div>
                  <div className="text-2xl font-bold tabular-nums text-emerald-400">
                    ~${annualDividends.toFixed(0)}
                  </div>
                </div>
              )}
            </div>
            <div className="flex flex-col items-end gap-1.5">
              <button
                onClick={() => { invalidateCache(); analyze() }}
                disabled={analyzing}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/10 border border-primary/25 text-primary text-sm font-semibold hover:bg-primary/20 transition-colors disabled:opacity-50"
              >
                <RefreshCw size={13} className={analyzing ? 'animate-spin' : ''} />
                {analyzing ? 'Analizando...' : 'Re-analizar'}
              </button>
              {cacheAge !== null && (
                <span className="text-[0.58rem] text-muted-foreground/40">
                  {cacheAge === 0 ? 'Actualizado ahora' : cacheAge < 60_000 ? 'Hace <1 min' : cacheAge < 3_600_000 ? `Hace ${Math.round(cacheAge / 60_000)}min` : `Hace ${Math.round(cacheAge / 3_600_000)}h`}
                  {' · '}cache activo
                </span>
              )}
            </div>
          </div>

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

          {/* Risk & Position Sizing overview */}
          {result.risk_metrics && (
            <div className="pt-3 border-t border-border/30">
              <div className="text-[0.62rem] font-bold uppercase tracking-widest text-muted-foreground/50 mb-2">
                Risk Management · Position Sizing (Kelly)
              </div>
              <div className="flex gap-4 flex-wrap text-[0.72rem] mb-2">
                <span className="text-muted-foreground">
                  Riesgo total cartera{' '}
                  <strong className={result.risk_metrics.total_risk_pct > 10 ? 'text-red-400' : result.risk_metrics.total_risk_pct > 5 ? 'text-amber-400' : 'text-emerald-400'}>
                    {result.risk_metrics.total_risk_pct.toFixed(1)}%
                  </strong>
                  <span className="text-muted-foreground/50 ml-1">(${result.risk_metrics.total_risk_amount.toFixed(0)} en riesgo)</span>
                </span>
                <span className="text-muted-foreground">
                  Kelly base <strong className="text-foreground">{result.risk_metrics.kelly_base_pct.toFixed(1)}%</strong>
                </span>
                <span className="text-muted-foreground">
                  Win rate <strong className="text-foreground">{result.risk_metrics.win_rate_used.toFixed(0)}%</strong>
                </span>
              </div>
              {result.risk_metrics.oversized_positions.length > 0 && (
                <div className="flex items-start gap-2 p-2 rounded-lg bg-red-500/8 border border-red-500/15 text-[0.72rem]">
                  <AlertTriangle size={11} className="text-red-400 mt-0.5 shrink-0" />
                  <span className="text-red-300/80">
                    Posiciones sobreexpuestas (peso actual &gt; 1.5× Kelly óptimo):{' '}
                    <strong>{result.risk_metrics.oversized_positions.join(', ')}</strong>
                    {' '}— considera reducir o abrir hedge
                  </span>
                </div>
              )}
              {/* Per-position sizing bars */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-2">
                {result.positions.map(p => {
                  const actual = p.portfolio_pct
                  const optimal = p.optimal_size_pct ?? 0
                  const maxBar = Math.max(actual, optimal, 1)
                  const isOver = actual > optimal * 1.5
                  const isUnder = actual < optimal * 0.5 && optimal > 0
                  return (
                    <div key={p.ticker} className="p-2 rounded-lg bg-muted/10 border border-border/20">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono font-bold text-[0.68rem] text-foreground">{p.ticker}</span>
                        <span className={`text-[0.6rem] font-bold ${isOver ? 'text-red-400' : isUnder ? 'text-blue-400' : 'text-emerald-400'}`}>
                          {isOver ? 'SOBRE' : isUnder ? 'INFRA' : 'OK'}
                        </span>
                      </div>
                      <div className="relative h-2 rounded-full bg-muted/30 overflow-hidden">
                        <div className="absolute inset-y-0 left-0 rounded-full bg-primary/50" style={{ width: `${(optimal / maxBar) * 100}%` }} />
                        <div className={`absolute inset-y-0 left-0 rounded-full ${isOver ? 'bg-red-400/60' : 'bg-emerald-400/60'}`} style={{ width: `${(actual / maxBar) * 100}%`, height: '50%', top: '25%' }} />
                      </div>
                      <div className="flex justify-between mt-0.5 text-[0.58rem] text-muted-foreground/60">
                        <span>Actual {actual.toFixed(1)}%</span>
                        <span>Kelly {optimal.toFixed(1)}%</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Analyst revisions — target price changes over time */}
          {(() => {
            const revisions = revisionsData?.revisions ?? []
            if (revisions.length === 0 || result.positions.length === 0) return null
            const byTicker = new Map<string, AnalystRevision>()
            for (const r of revisions) byTicker.set(r.ticker.toUpperCase(), r)
            const portfolioRevs = result.positions
              .map(p => ({ pos: p, rev: byTicker.get(p.ticker.toUpperCase()) }))
              .filter((x): x is { pos: typeof x.pos; rev: AnalystRevision } => x.rev != null)
              .sort((a, b) => {
                const ac = a.rev.target_change_7d_pct ?? a.rev.target_change_30d_pct ?? 0
                const bc = b.rev.target_change_7d_pct ?? b.rev.target_change_30d_pct ?? 0
                return Math.abs(bc) - Math.abs(ac)
              })
            if (portfolioRevs.length === 0) return null
            const hasHistory = portfolioRevs.some(x => (x.rev.snapshots ?? 0) > 1)
            return (
              <div className="pt-3 border-t border-border/30">
                <div className="flex items-baseline justify-between mb-2">
                  <div className="text-[0.62rem] font-bold uppercase tracking-widest text-muted-foreground/50">
                    Revisiones de analistas
                  </div>
                  {!hasHistory && (
                    <div className="text-[0.58rem] text-muted-foreground/50 italic">
                      Empezando a trackear — los deltas se poblarán en días
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {portfolioRevs.map(({ pos, rev }) => {
                    const target = rev.target_mean
                    const currentPrice = pos.current_price
                    const upsidePct = target != null && currentPrice ? ((target - currentPrice) / currentPrice) * 100 : null
                    return (
                      <div key={pos.ticker} className="p-2.5 rounded-lg bg-muted/10 border border-border/20 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-[0.72rem] text-foreground">{pos.ticker}</span>
                          <AnalystRevisionBadge
                            targetChange7dPct={rev.target_change_7d_pct}
                            upgradeDays14d={rev.upgrade_days_14d}
                            downgradeDays14d={rev.downgrade_days_14d}
                          />
                        </div>
                        <div className="flex items-center justify-between text-[0.62rem]">
                          <span className="text-muted-foreground/70">Target medio</span>
                          <span className="font-semibold text-foreground tabular-nums">
                            {target != null ? `$${target.toFixed(0)}` : '—'}
                            {upsidePct != null && (
                              <span className={`ml-1 ${upsidePct > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                {upsidePct > 0 ? '+' : ''}{upsidePct.toFixed(0)}%
                              </span>
                            )}
                          </span>
                        </div>
                        {rev.target_change_30d_pct != null && (
                          <div className="flex items-center justify-between text-[0.58rem] text-muted-foreground/60">
                            <span>30d</span>
                            <span className={rev.target_change_30d_pct > 0 ? 'text-emerald-400/80' : rev.target_change_30d_pct < 0 ? 'text-red-400/80' : ''}>
                              {rev.target_change_30d_pct > 0 ? '+' : ''}{rev.target_change_30d_pct.toFixed(1)}%
                            </span>
                          </div>
                        )}
                        {rev.analyst_count != null && (
                          <div className="flex items-center justify-between text-[0.58rem] text-muted-foreground/60">
                            <span>Cobertura</span>
                            <span>{rev.analyst_count} analistas</span>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })()}

          {/* Dividend breakdown */}
          {dividendPositions.length > 0 && (
            <div className="pt-3 border-t border-border/30">
              <div className="text-[0.62rem] font-bold uppercase tracking-widest text-muted-foreground/50 mb-2">
                Proyección dividendos anuales
              </div>
              <div className="flex flex-wrap gap-2">
                {dividendPositions.map(p => (
                  <div key={p.ticker} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-500/8 border border-emerald-500/15 text-[0.72rem]">
                    <span className="font-mono font-bold text-emerald-400">{p.ticker}</span>
                    <span className="text-muted-foreground">{p.dividend_yield?.toFixed(2)}%</span>
                    <span className="text-emerald-400 font-semibold">
                      ~${((p.market_value * (p.dividend_yield ?? 0)) / 100).toFixed(0)}/año
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Add form */}
      <AddForm onAdd={addPosition} saving={saving} />

      {/* Refresh status banner — feedback al editar posiciones */}
      {refreshState.status !== 'idle' && (
        <div className={
          refreshState.status === 'running' ? 'flex items-center gap-2 p-3 rounded-xl bg-primary/10 border border-primary/20 text-primary text-sm animate-fade-in-up' :
          refreshState.status === 'ok'      ? 'flex items-center gap-2 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm animate-fade-in-up' :
                                              'flex items-center gap-2 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm animate-fade-in-up'
        }>
          {refreshState.status === 'running'
            ? <Loader2 size={14} className="animate-spin" />
            : refreshState.status === 'ok' ? <Check size={14} /> : <AlertTriangle size={14} />}
          {refreshState.message}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertTriangle size={14} />
          {error}
        </div>
      )}

      {/* Empty state */}
      {positions.length === 0 && (
        <div className="glass rounded-2xl p-12 text-center animate-fade-in-up">
          <Wallet size={40} className="mx-auto text-muted-foreground/30 mb-4" />
          <p className="text-foreground font-semibold mb-1">Sin posiciones todavía</p>
          <p className="text-sm text-muted-foreground">Añade tus posiciones arriba y el análisis IA se generará automáticamente.</p>
        </div>
      )}

      {/* Positions */}
      {positions.length > 0 && (
        <div className="space-y-4">
          {!analyzed && !analyzing && (
            <button
              onClick={() => analyze()}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-colors"
            >
              <RefreshCw size={14} />
              Analizar cartera con IA
            </button>
          )}

          {analyzing && (() => {
            const stockTickers = positions.filter(p => p.asset_type !== 'covered_call').map(p => p.ticker)
            const steps = [
              'Consultando precios en tiempo real…',
              'Calculando P&L y sizing Kelly…',
              'Evaluando fundamentales VALUE…',
              'Analizando riesgo de cartera…',
              'Generando análisis con IA…',
            ]
            return (
              <div className="glass rounded-2xl p-8 space-y-6 animate-fade-in-up">
                {/* Ticker parade */}
                <div className="flex flex-wrap gap-2 justify-center">
                  {stockTickers.map((t, i) => (
                    <span
                      key={t}
                      className="font-mono font-bold text-xs px-2.5 py-1 rounded-lg border border-primary/20 text-primary/70 bg-primary/5"
                      style={{ animation: `fadeInUp 0.4s ease-out ${i * 0.08}s both` }}
                    >
                      {t}
                    </span>
                  ))}
                </div>
                {/* Steps */}
                <div className="space-y-2.5 max-w-xs mx-auto">
                  {steps.map((step, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2.5"
                      style={{ animation: `fadeInUp 0.4s ease-out ${0.3 + i * 0.25}s both` }}
                    >
                      <div className="w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0"
                        style={{ animation: `pulse 1.4s ${i * 0.25}s infinite` }} />
                      <span className="text-xs text-muted-foreground/60">{step}</span>
                    </div>
                  ))}
                </div>
                <p className="text-center text-[0.65rem] text-muted-foreground/30">
                  ~20-40s · solo en la primera visita del día
                </p>
              </div>
            )
          })()}

          {!analyzing && (() => {
            const stockPositions = positions.filter(p => p.asset_type !== 'covered_call')
            const posWithAlerts = stockPositions.filter(p =>
              cerebro.exitMap[p.ticker] || cerebro.trapMap[p.ticker] || cerebro.divMap[p.ticker]
            )
            const criticalCount = stockPositions.filter(p =>
              cerebro.exitMap[p.ticker]?.severity === 'HIGH' || cerebro.trapMap[p.ticker]?.severity === 'HIGH'
            ).length
            return (
              <>
                {macroWarningEntries.length > 0 && (
                  <div className="flex items-start gap-3 rounded-xl border border-orange-500/25 bg-orange-500/8 p-4">
                    <AlertTriangle size={16} className="mt-0.5 shrink-0 text-orange-300" />
                    <div>
                      <p className="text-sm font-bold text-orange-300">
                        Macro Stress detecta exposición en {macroWarningEntries.length} posición{macroWarningEntries.length > 1 ? 'es' : ''}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {macroWarningEntries
                          .map(([ticker, warnings]) => `${ticker} → ${warnings.map(w => `${w.marketLabel} ${w.score.toFixed(0)}`).join(', ')}`)
                          .join(' · ')}
                      </p>
                    </div>
                  </div>
                )}

                {posWithAlerts.length > 0 && (
                  <div className={`flex items-start gap-3 p-4 rounded-xl border ${criticalCount > 0 ? 'border-red-500/30 bg-red-500/8' : 'border-amber-500/25 bg-amber-500/6'}`}>
                    <Brain size={16} className={criticalCount > 0 ? 'text-red-400 mt-0.5 shrink-0' : 'text-amber-400 mt-0.5 shrink-0'} />
                    <div>
                      <p className={`text-sm font-bold ${criticalCount > 0 ? 'text-red-400' : 'text-amber-400'}`}>
                        Cerebro IA detectó alertas en {posWithAlerts.length} de {positions.length} posiciones
                        {criticalCount > 0 && ` — ${criticalCount} crítica${criticalCount > 1 ? 's' : ''}`}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {posWithAlerts.map(p => p.ticker).join(', ')} · Ver detalles en cada posición
                      </p>
                    </div>
                  </div>
                )}
                {(() => {
                  // Map ticker → covered_call position so we can embed it in the stock card
                  const ccByTicker = new Map<string, Position>()
                  for (const p of positions) {
                    if (p.asset_type === 'covered_call') ccByTicker.set(p.ticker, p)
                  }
                  const visiblePositions = positions.filter(p => p.asset_type !== 'covered_call')
                  return (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                      {visiblePositions.map((pos, index) => (
                        <div key={pos.id} className="animate-fade-in-up h-full" style={{ animationDelay: `${index * 80}ms` }}>
                          <PositionCard
                            pos={pos}
                            userId={user!.id}
                            result={result?.positions.find(r => r.ticker === pos.ticker)}
                            onRemove={() => removePosition(pos.id)}
                            onEdit={updatePosition}
                            cerebro={cerebro}
                            confluence={confluence[pos.ticker] ?? null}
                            macroWarnings={macroWarningsByTicker[pos.ticker] ?? []}
                            priceAlert={priceAlertMap[pos.ticker.toUpperCase()]}
                            coveredCall={ccByTicker.get(pos.ticker)}
                          />
                        </div>
                      ))}
                    </div>
                  )
                })()}
              </>
            )
          })()}
        </div>
      )}
    </div>
  )
}
