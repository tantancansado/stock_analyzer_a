import { useState, useEffect, useMemo } from 'react'
import { fetchBonds, type BondOpportunity } from '../api/client'
import Loading, { ErrorState } from '../components/Loading'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp, Calculator } from 'lucide-react'
import { cn } from '@/lib/utils'

const BOND_TYPE_LABELS: Record<string, string> = {
  T_Bill:    'T-Bill <1a',
  EUR_Cash:  'Cash EUR',
  Treasury:  'Tesoro EEUU',
  TIPS:      'TIPS (Inflación)',
  Aggregate: 'Agregado',
  IG_Corp:   'Corp IG',
  HY_Corp:   'Corp HY',
  EUR_Govt:  'Gob EUR',
  EUR_IG:    'Corp EUR IG',
  EM_Bond:   'Emergentes',
}

const TYPE_COLORS: Record<string, string> = {
  T_Bill:    'text-emerald-400 bg-emerald-500/10 border-emerald-500/25',
  EUR_Cash:  'text-teal-400 bg-teal-500/10 border-teal-500/25',
  Treasury:  'text-blue-400 bg-blue-500/10 border-blue-500/25',
  TIPS:      'text-yellow-400 bg-yellow-500/10 border-yellow-500/25',
  Aggregate: 'text-slate-400 bg-slate-500/10 border-slate-500/25',
  IG_Corp:   'text-cyan-400 bg-cyan-500/10 border-cyan-500/25',
  HY_Corp:   'text-orange-400 bg-orange-500/10 border-orange-500/25',
  EUR_Govt:  'text-purple-400 bg-purple-500/10 border-purple-500/25',
  EUR_IG:    'text-violet-400 bg-violet-500/10 border-violet-500/25',
  EM_Bond:   'text-pink-400 bg-pink-500/10 border-pink-500/25',
}

const RATING_CONFIG = {
  MUY_ATRACTIVO: { label: 'MUY ATRACTIVO', bg: 'bg-emerald-500/15 border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  ATRACTIVO:     { label: 'ATRACTIVO',     bg: 'bg-green-500/10 border-green-500/25',     text: 'text-green-400',   dot: 'bg-green-400'   },
  NEUTRAL:       { label: 'NEUTRAL',       bg: 'bg-slate-500/10 border-slate-500/25',     text: 'text-slate-400',   dot: 'bg-slate-400'   },
  CARO:          { label: 'CARO',          bg: 'bg-red-500/10 border-red-500/25',          text: 'text-red-400',     dot: 'bg-red-400'     },
  SIN_DATO:      { label: 'SIN DATO',      bg: 'bg-muted/20 border-muted/30',             text: 'text-muted-foreground', dot: 'bg-muted'  },
}

// ─── Yield calculator helpers ─────────────────────────────────────────────────

// Para ETFs de T-Bills y muy corto plazo el yield anual ya está normalizado.
// El rendimiento para un plazo X meses = capital × yield_anual × (meses/12)
// con reinversión mensual (interés compuesto mensual).
function calcReturn(capital: number, yieldAnnual: number, months: number) {
  const monthlyRate = yieldAnnual / 100 / 12
  const final = capital * Math.pow(1 + monthlyRate, months)
  const gain = final - capital
  const effectiveYield = (gain / capital) * 100   // rendimiento total del período
  return { final, gain, effectiveYield }
}

function fmtEur(n: number) {
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n)
}
function fmtUsd(n: number) {
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

const PRESET_MONTHS = [1, 3, 6, 12, 24, 36]

function YieldCalculator({ bonds }: { bonds: BondOpportunity[] }) {
  const [capital, setCapital] = useState(10000)
  const [months, setMonths] = useState(12)
  const [rawCapital, setRawCapital] = useState('10000')

  // Only show bonds with actual yield data, sorted by yield desc
  const calcBonds = useMemo(() =>
    bonds
      .filter(b => b.yield_pct != null && b.yield_pct > 0)
      .sort((a, b) => (b.yield_pct ?? 0) - (a.yield_pct ?? 0)),
    [bonds]
  )

  const topGainer = calcBonds[0]

  return (
    <Card className="glass border-primary/20">
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Calculator size={16} className="text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Calculadora de rendimiento</h2>
          <span className="text-xs text-muted-foreground ml-1">— ¿cuánto ganas si inviertes X durante Y meses?</span>
        </div>

        {/* Inputs */}
        <div className="flex flex-wrap gap-4 mb-5">
          {/* Capital */}
          <div>
            <label className="text-xs text-muted-foreground block mb-1.5">Capital a invertir ($)</label>
            <div className="flex items-center gap-1.5">
              <input
                type="text"
                inputMode="numeric"
                value={rawCapital}
                onChange={e => {
                  const raw = e.target.value.replace(/[^\d]/g, '')
                  setRawCapital(raw)
                  const n = parseInt(raw, 10)
                  if (!isNaN(n) && n > 0) setCapital(n)
                }}
                className="w-32 px-3 py-1.5 rounded-lg border border-border/50 bg-background/40 text-foreground text-sm font-mono focus:outline-none focus:border-primary/60"
              />
              {[1000, 5000, 10000, 50000, 100000].map(v => (
                <button
                  key={v}
                  onClick={() => { setCapital(v); setRawCapital(String(v)) }}
                  className={cn(
                    'text-[0.65rem] px-2 py-1 rounded border transition-all',
                    capital === v
                      ? 'bg-primary/20 border-primary/50 text-primary'
                      : 'border-border/30 text-muted-foreground hover:border-border/60 hover:text-foreground'
                  )}
                >
                  {v >= 1000 ? `${v / 1000}k` : v}
                </button>
              ))}
            </div>
          </div>

          {/* Plazo */}
          <div>
            <label className="text-xs text-muted-foreground block mb-1.5">Plazo</label>
            <div className="flex gap-1.5">
              {PRESET_MONTHS.map(m => (
                <button
                  key={m}
                  onClick={() => setMonths(m)}
                  className={cn(
                    'text-xs px-2.5 py-1.5 rounded-lg border transition-all font-medium',
                    months === m
                      ? 'bg-primary/20 border-primary/50 text-primary'
                      : 'border-border/40 text-muted-foreground hover:border-border/60 hover:text-foreground'
                  )}
                >
                  {m < 12 ? `${m}m` : `${m / 12}a`}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Top gainer highlight */}
        {topGainer && (() => {
          const { gain, effectiveYield } = calcReturn(capital, topGainer.yield_pct!, months)
          return (
            <div className="mb-4 px-3 py-2 rounded-lg bg-emerald-500/8 border border-emerald-500/20 text-xs text-emerald-400">
              Mejor rendimiento: <span className="font-bold">{topGainer.ticker}</span> — ganarías{' '}
              <span className="font-bold">{fmtUsd(gain)}</span> en {months < 12 ? `${months} meses` : months === 12 ? '1 año' : `${months / 12} años`}{' '}
              <span className="opacity-70">({effectiveYield.toFixed(2)}% del período)</span>
            </div>
          )
        })()}

        {/* Results table */}
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border/20 text-[0.65rem] text-muted-foreground/50 uppercase tracking-wider">
                <th className="pb-2 text-left pr-3">ETF</th>
                <th className="pb-2 text-left pr-3">Tipo</th>
                <th className="pb-2 text-right pr-3">Yield anual</th>
                <th className="pb-2 text-right pr-3">Ganancia</th>
                <th className="pb-2 text-right pr-3">Capital final</th>
                <th className="pb-2 text-right">Rend. período</th>
              </tr>
            </thead>
            <tbody>
              {calcBonds.map((b, i) => {
                const { final, gain, effectiveYield } = calcReturn(capital, b.yield_pct!, months)
                const ratingCfg = RATING_CONFIG[b.value_rating as keyof typeof RATING_CONFIG] ?? RATING_CONFIG.SIN_DATO
                const typeCls = TYPE_COLORS[b.bond_type] ?? 'text-slate-400'
                const isTop = i === 0
                return (
                  <tr
                    key={b.ticker}
                    className={cn(
                      'border-b border-border/10 transition-colors',
                      isTop ? 'bg-emerald-500/5' : 'hover:bg-white/[0.02]'
                    )}
                  >
                    <td className="py-2 pr-3">
                      <div className="flex items-center gap-1.5">
                        <div className={cn('w-1 h-1 rounded-full flex-shrink-0', ratingCfg.dot)} />
                        <span className="font-mono font-bold text-foreground">{b.ticker}</span>
                        {isTop && <span className="text-[0.6rem] text-emerald-400 font-medium">TOP</span>}
                      </div>
                    </td>
                    <td className="py-2 pr-3">
                      <span className={cn('text-[0.65rem] font-medium', typeCls.split(' ')[0])}>
                        {BOND_TYPE_LABELS[b.bond_type] ?? b.bond_type}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-right font-mono text-foreground/80">
                      {b.yield_pct!.toFixed(2)}%
                    </td>
                    <td className="py-2 pr-3 text-right font-mono font-semibold text-emerald-400">
                      +{b.currency === 'EUR' ? fmtEur(gain) : fmtUsd(gain)}
                    </td>
                    <td className="py-2 pr-3 text-right font-mono text-foreground/70">
                      {b.currency === 'EUR' ? fmtEur(final) : fmtUsd(final)}
                    </td>
                    <td className="py-2 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <div className="h-1 w-16 rounded-full bg-muted/20 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-emerald-500/60"
                            style={{ width: `${Math.min((effectiveYield / (calcBonds[0]?.yield_pct ?? 1)) * (months / 12) * 100, 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-foreground/60 w-12 text-right">{effectiveYield.toFixed(2)}%</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <p className="text-[0.62rem] text-muted-foreground/40 mt-3">
          Cálculo con reinversión mensual (interés compuesto). No incluye fiscalidad ni comisiones de broker. Los T-Bills y ETFs de ultracorto se pueden vender en cualquier momento — no hay penalización por liquidez anticipada.
        </p>
      </CardContent>
    </Card>
  )
}

// ─── Bond table row ───────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, dec = 2, suffix = '') {
  if (n == null) return '—'
  return `${n.toFixed(dec)}${suffix}`
}

function YieldVsAvg({ val }: { val: number | null | undefined }) {
  if (val == null) return <span className="text-muted-foreground">—</span>
  const color = val >= 0.3 ? 'text-emerald-400' : val >= 0 ? 'text-green-400' : val >= -0.3 ? 'text-yellow-400' : 'text-red-400'
  const Icon = val > 0 ? TrendingUp : val < 0 ? TrendingDown : Minus
  return (
    <span className={cn('flex items-center gap-1 font-mono text-xs', color)}>
      <Icon size={11} />
      {val > 0 ? '+' : ''}{val.toFixed(2)}%
    </span>
  )
}

function PctFromHigh({ val }: { val: number | null | undefined }) {
  if (val == null) return <span className="text-muted-foreground">—</span>
  const color = val <= -8 ? 'text-emerald-400' : val <= -3 ? 'text-yellow-400' : 'text-muted-foreground'
  return <span className={cn('font-mono text-xs', color)}>{val > 0 ? '+' : ''}{val.toFixed(1)}%</span>
}

function DurationBar({ years }: { years: number | null | undefined }) {
  if (years == null) return <span className="text-muted-foreground">—</span>
  const max = 20
  const pct = Math.min((years / max) * 100, 100)
  const color = years >= 15 ? '#ef4444' : years >= 8 ? '#f97316' : years >= 4 ? '#eab308' : '#10b981'
  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-16 rounded-full bg-muted/30 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono" style={{ color }}>{years < 1 ? `${(years * 12).toFixed(0)}m` : `${years}y`}</span>
    </div>
  )
}

function BondRow({ bond }: { bond: BondOpportunity }) {
  const [expanded, setExpanded] = useState(false)
  const ratingCfg = RATING_CONFIG[bond.value_rating as keyof typeof RATING_CONFIG] ?? RATING_CONFIG.SIN_DATO
  const typeCls = TYPE_COLORS[bond.bond_type] ?? 'text-slate-400 bg-slate-500/10 border-slate-500/25'

  return (
    <>
      <tr
        className="border-b border-border/20 hover:bg-white/[0.02] cursor-pointer transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <td className="px-3 py-2.5">
          <div className="flex items-center gap-2">
            <div className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', ratingCfg.dot)} />
            <div>
              <span className="font-mono font-bold text-sm text-primary">{bond.ticker}</span>
              <div className="text-[0.62rem] text-muted-foreground truncate max-w-[140px]">{bond.name}</div>
            </div>
          </div>
        </td>
        <td className="px-3 py-2.5">
          <Badge variant="outline" className={cn('text-[0.65rem] font-medium', typeCls)}>
            {BOND_TYPE_LABELS[bond.bond_type] ?? bond.bond_type}
          </Badge>
        </td>
        <td className="px-3 py-2.5 text-right">
          {bond.yield_pct != null ? (
            <span className={cn('font-mono font-bold text-sm', bond.yield_pct >= 5 ? 'text-emerald-400' : bond.yield_pct >= 3.5 ? 'text-green-400' : 'text-muted-foreground')}>
              {bond.yield_pct.toFixed(2)}%
            </span>
          ) : <span className="text-muted-foreground">—</span>}
        </td>
        <td className="px-3 py-2.5 text-right">
          <YieldVsAvg val={bond.yield_vs_avg_pct} />
        </td>
        <td className="px-3 py-2.5">
          <DurationBar years={bond.duration_years} />
        </td>
        <td className="px-3 py-2.5 text-right">
          <PctFromHigh val={bond.pct_from_high} />
        </td>
        <td className="px-3 py-2.5">
          <Badge variant="outline" className={cn('text-[0.65rem] font-semibold border', ratingCfg.bg, ratingCfg.text)}>
            {ratingCfg.label}
          </Badge>
        </td>
        <td className="px-3 py-2.5 text-right">
          {expanded ? <ChevronUp size={14} className="text-muted-foreground" /> : <ChevronDown size={14} className="text-muted-foreground" />}
        </td>
      </tr>

      {expanded && (
        <tr className="border-b border-border/20 bg-white/[0.015]">
          <td colSpan={8} className="px-4 py-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs mb-3">
              <div>
                <div className="text-muted-foreground/60 mb-0.5">Precio</div>
                <div className="font-mono font-semibold">{bond.currency === 'EUR' ? '€' : '$'}{fmt(bond.price)}</div>
              </div>
              <div>
                <div className="text-muted-foreground/60 mb-0.5">Máx 52s</div>
                <div className="font-mono">{bond.currency === 'EUR' ? '€' : '$'}{fmt(bond.week52_high)}</div>
              </div>
              <div>
                <div className="text-muted-foreground/60 mb-0.5">Mín 52s</div>
                <div className="font-mono">{bond.currency === 'EUR' ? '€' : '$'}{fmt(bond.week52_low)}</div>
              </div>
              <div>
                <div className="text-muted-foreground/60 mb-0.5">Yield histórico avg</div>
                <div className="font-mono">{fmt(bond.hist_avg_yield_pct)}%</div>
              </div>
              <div>
                <div className="text-muted-foreground/60 mb-0.5">SEC Yield (30d)</div>
                <div className="font-mono">{bond.sec_yield_pct != null ? `${bond.sec_yield_pct.toFixed(2)}%` : '—'}</div>
              </div>
              <div>
                <div className="text-muted-foreground/60 mb-0.5">Duración modificada</div>
                <div className="font-mono">{fmt(bond.modified_duration, 1)} años</div>
              </div>
              <div>
                <div className="text-muted-foreground/60 mb-0.5">Expense ratio</div>
                <div className="font-mono">{bond.expense_ratio_pct != null ? `${bond.expense_ratio_pct.toFixed(3)}%` : '—'}</div>
              </div>
              <div>
                <div className="text-muted-foreground/60 mb-0.5">Divisa</div>
                <div className="font-mono">{bond.currency}</div>
              </div>
            </div>
            <div className={cn('text-xs px-3 py-2 rounded-lg border', ratingCfg.bg, ratingCfg.text)}>
              {bond.recommendation}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

// ─── Filters ──────────────────────────────────────────────────────────────────

type FilterType = 'ALL' | 'T_Bill' | 'EUR_Cash' | 'Treasury' | 'IG_Corp' | 'HY_Corp' | 'TIPS' | 'EUR_Govt' | 'EUR_IG' | 'EM_Bond' | 'Aggregate'

const TYPE_FILTERS: { key: FilterType; label: string }[] = [
  { key: 'ALL',       label: 'Todos' },
  { key: 'T_Bill',    label: 'T-Bill <1a' },
  { key: 'EUR_Cash',  label: 'Cash EUR' },
  { key: 'Treasury',  label: 'Tesoro EEUU' },
  { key: 'TIPS',      label: 'TIPS' },
  { key: 'IG_Corp',   label: 'Corp IG' },
  { key: 'HY_Corp',   label: 'Corp HY' },
  { key: 'EUR_Govt',  label: 'EUR Gob' },
  { key: 'EUR_IG',    label: 'EUR Corp' },
  { key: 'EM_Bond',   label: 'Emergentes' },
  { key: 'Aggregate', label: 'Agregado' },
]

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Bonds() {
  const [bonds, setBonds] = useState<BondOpportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState<FilterType>('ALL')
  const [ratingFilter, setRatingFilter] = useState<'ALL' | 'ATRACTIVO' | 'NEUTRAL' | 'CARO'>('ALL')
  const [showCalc, setShowCalc] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchBonds()
      .then(data => setBonds(data))
      .catch(err => setError(err.message ?? 'Error de conexión'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    return bonds.filter(b => {
      if (typeFilter !== 'ALL' && b.bond_type !== typeFilter) return false
      if (ratingFilter === 'ATRACTIVO' && !['MUY_ATRACTIVO', 'ATRACTIVO'].includes(b.value_rating)) return false
      if (ratingFilter === 'NEUTRAL' && b.value_rating !== 'NEUTRAL') return false
      if (ratingFilter === 'CARO' && b.value_rating !== 'CARO') return false
      return true
    })
  }, [bonds, typeFilter, ratingFilter])

  const atractivos = bonds.filter(b => ['MUY_ATRACTIVO', 'ATRACTIVO'].includes(b.value_rating))
  const avgYield = bonds.length
    ? bonds.reduce((s, b) => s + (b.yield_pct ?? 0), 0) / bonds.filter(b => b.yield_pct != null).length
    : 0
  const generatedAt = bonds[0]?.generated_at

  if (loading) return <Loading />
  if (error) return <ErrorState message="No se pudo cargar datos de bonos" />

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Bonos &amp; Renta Fija</h1>
        <p className="text-sm text-muted-foreground mt-1">
          ETFs de renta fija con análisis VALUE — yield vs histórico, duración y dislocation de precio
          {generatedAt && <span className="ml-2 opacity-60">· {new Date(generatedAt).toLocaleDateString('es-ES')}</span>}
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="glass border-border/30">
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground mb-1">Bonos analizados</div>
            <div className="text-2xl font-bold text-foreground">{bonds.length}</div>
          </CardContent>
        </Card>
        <Card className="glass border-emerald-500/20">
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground mb-1">Atractivos</div>
            <div className="text-2xl font-bold text-emerald-400">{atractivos.length}</div>
          </CardContent>
        </Card>
        <Card className="glass border-border/30">
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground mb-1">Yield medio universo</div>
            <div className="text-2xl font-bold text-foreground">{avgYield > 0 ? `${avgYield.toFixed(2)}%` : '—'}</div>
          </CardContent>
        </Card>
        <Card className="glass border-border/30">
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground mb-1">Yield más alto</div>
            <div className="text-2xl font-bold text-foreground">
              {bonds.length ? `${Math.max(...bonds.map(b => b.yield_pct ?? 0)).toFixed(2)}%` : '—'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Calculator toggle + panel */}
      <div>
        <button
          onClick={() => setShowCalc(v => !v)}
          className="flex items-center gap-2 text-sm font-medium text-primary/80 hover:text-primary transition-colors mb-3"
        >
          <Calculator size={14} />
          Calculadora de rendimiento
          {showCalc ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>
        {showCalc && <YieldCalculator bonds={bonds} />}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {TYPE_FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setTypeFilter(f.key)}
            className={cn(
              'text-xs px-3 py-1.5 rounded-lg border transition-all font-medium',
              typeFilter === f.key
                ? 'bg-primary/20 border-primary/50 text-primary'
                : 'border-border/40 text-muted-foreground hover:border-border/60 hover:text-foreground'
            )}
          >
            {f.label}
          </button>
        ))}
        <div className="w-px bg-border/30 mx-1" />
        {(['ALL', 'ATRACTIVO', 'NEUTRAL', 'CARO'] as const).map(r => (
          <button
            key={r}
            onClick={() => setRatingFilter(r)}
            className={cn(
              'text-xs px-3 py-1.5 rounded-lg border transition-all font-medium',
              ratingFilter === r
                ? r === 'ATRACTIVO' ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
                  : r === 'CARO' ? 'bg-red-500/20 border-red-500/40 text-red-400'
                  : 'bg-primary/20 border-primary/50 text-primary'
                : 'border-border/40 text-muted-foreground hover:border-border/60 hover:text-foreground'
            )}
          >
            {r === 'ALL' ? 'Todos ratings' : r === 'ATRACTIVO' ? 'Atractivos' : r === 'NEUTRAL' ? 'Neutros' : 'Caros'}
          </button>
        ))}
      </div>

      {/* Table */}
      <Card className="glass border-border/30">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/30 text-[0.7rem] text-muted-foreground/60 uppercase tracking-wider">
                  <th className="px-3 py-2.5 text-left">ETF / Bono</th>
                  <th className="px-3 py-2.5 text-left">Tipo</th>
                  <th className="px-3 py-2.5 text-right">Yield</th>
                  <th className="px-3 py-2.5 text-right">vs Histórico</th>
                  <th className="px-3 py-2.5 text-left">Duración</th>
                  <th className="px-3 py-2.5 text-right">vs Máx 52s</th>
                  <th className="px-3 py-2.5 text-left">Rating VALUE</th>
                  <th className="px-3 py-2.5" />
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground text-sm">
                      No hay bonos con los filtros seleccionados
                    </td>
                  </tr>
                ) : (
                  filtered.map(bond => <BondRow key={bond.ticker} bond={bond} />)
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* How to read guide */}
      <Card className="glass border-border/20">
        <CardContent className="p-4 text-xs text-muted-foreground space-y-1.5">
          <div className="font-semibold text-foreground/70 mb-2">Cómo leer la tabla</div>
          <div><span className="text-emerald-400 font-medium">T-Bill / Cash EUR</span> — vencimiento &lt;1 año. Sin riesgo de precio, liquidez total. BIL/SGOV pagan ~4-5% anual — a 3 meses son ~1.1%, proporcional al tiempo invertido</div>
          <div><span className="text-blue-400 font-medium">Treasury 1-2 años</span> — SHY/VGSH: rendimiento competitivo, riesgo de tipos mínimo, mucho más seguro que largo plazo</div>
          <div><span className="text-emerald-400 font-medium">Yield vs Histórico positivo</span> — el ETF paga más que su media histórica → precio deprimido → oportunidad de entrada</div>
          <div><span className="text-yellow-400 font-medium">Duración larga (&gt;10y)</span> — sensibilidad alta a tipos. TLT puede subir 15-20% si tipos bajan, pero también caer igual si suben</div>
          <div><span className="text-orange-400 font-medium">Corp HY</span> — rendimiento alto pero riesgo de impago. Solo cuando los spreads son realmente amplios</div>
          <div><span className="text-purple-400 font-medium">EUR Govt/IG</span> — denominado en EUR, añade riesgo divisa vs USD pero diversifica geografía</div>
        </CardContent>
      </Card>
    </div>
  )
}
