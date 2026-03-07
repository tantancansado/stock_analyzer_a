import { useEffect } from 'react'
import { X, TrendingUp, AlertTriangle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import GradeBadge from './GradeBadge'
import ThesisBody from './ThesisBody'
import type { ValueOpportunity } from '../api/client'

// ── Conviction panel ──────────────────────────────────────────────────────────

function ConvictionPanel({ row }: { row: ValueOpportunity }) {
  const reasons = row.conviction_reasons
    ? row.conviction_reasons.split(' | ').filter(Boolean)
    : []
  const pos   = row.conviction_positives ?? 0
  const flags = row.conviction_red_flags ?? 0
  const score = row.conviction_score
  const grade = row.conviction_grade

  if (!reasons.length && score == null) return null

  return (
    <div className="mt-5 pt-5 border-t border-border/40">
      <div className="flex items-center gap-2.5 mb-3 flex-wrap">
        <span className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">Conviction Filter</span>
        {grade && score != null && (
          <span className={`text-xs font-bold px-2 py-0.5 rounded ${grade === 'A' || grade === 'A+' ? 'bg-emerald-500/20 text-emerald-400' : grade === 'B' ? 'bg-blue-500/20 text-blue-400' : 'bg-amber-500/20 text-amber-400'}`}>
            {grade} — {score.toFixed(0)} pts
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

// ── Metric chip ───────────────────────────────────────────────────────────────

function Chip({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5 px-3 py-2 rounded-lg bg-white/4 border border-border/30 min-w-[64px]">
      <span className="text-[0.55rem] font-bold uppercase tracking-widest text-muted-foreground/60">{label}</span>
      <span className={`text-sm font-bold tabular-nums ${color ?? 'text-foreground'}`}>{value}</span>
    </div>
  )
}

// ── Main modal ────────────────────────────────────────────────────────────────

interface Props {
  row: ValueOpportunity
  thesisText: string
  onClose: () => void
  currency?: string
}

export default function ThesisModal({ row, thesisText, onClose, currency = '$' }: Props) {
  // ESC key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  // Prevent body scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  const upside    = row.analyst_upside_pct
  const rr        = row.risk_reward_ratio
  const fcf       = row.fcf_yield_pct
  const earn      = row.days_to_earnings
  const price     = row.current_price

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/65 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal — bottom sheet on mobile, centered card on sm+ */}
      <div
        className="fixed z-50 bottom-0 left-0 right-0 sm:inset-0 sm:flex sm:items-center sm:justify-center sm:p-6"
        role="dialog"
        aria-modal="true"
      >
        <div className="relative w-full sm:max-w-2xl bg-[hsl(var(--card))] border border-border/60 shadow-2xl rounded-t-2xl sm:rounded-2xl flex flex-col max-h-[92dvh] sm:max-h-[88dvh] modal-enter">
          {/* Handle (mobile) */}
          <div className="sm:hidden flex justify-center pt-3 pb-1 flex-shrink-0">
            <div className="w-10 h-1 rounded-full bg-muted-foreground/25" />
          </div>

          {/* Header */}
          <div className="flex items-start justify-between gap-4 px-5 pt-3 pb-4 border-b border-border/50 flex-shrink-0">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="font-mono font-extrabold text-primary text-xl tracking-tight">{row.ticker}</span>
                <GradeBadge grade={row.conviction_grade} score={row.conviction_score} />
                {row.earnings_warning && (
                  <Badge variant="yellow" className="text-[0.62rem] gap-1">
                    <AlertTriangle size={10} strokeWidth={2} /> Earnings
                  </Badge>
                )}
                {row.proximity_to_52w_high != null && row.proximity_to_52w_high > -5 && (
                  <Badge variant="green" className="text-[0.6rem]">52w High</Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground truncate">{row.company_name}</p>
              {row.sector && <p className="text-[0.7rem] text-muted-foreground/50 mt-0.5">{row.sector}</p>}
            </div>
            <div className="flex items-start gap-3 shrink-0">
              {price != null && (
                <div className="text-right">
                  <div className="text-xl font-extrabold tabular-nums">{currency}{price.toFixed(2)}</div>
                  {upside != null && (
                    <div className={`text-xs font-semibold tabular-nums flex items-center gap-1 justify-end ${upside >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      <TrendingUp size={11} />
                      {upside >= 0 ? '+' : ''}{upside.toFixed(1)}%
                    </div>
                  )}
                </div>
              )}
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted/40 hover:text-foreground transition-colors flex-shrink-0"
                aria-label="Cerrar"
              >
                <X size={16} strokeWidth={2} />
              </button>
            </div>
          </div>

          {/* Metrics strip */}
          <div className="flex gap-2 px-5 py-3 overflow-x-auto border-b border-border/30 flex-shrink-0 scrollbar-hide">
            <Chip label="Score" value={row.value_score.toFixed(0)} color="text-primary" />
            {row.piotroski_score != null && (
              <Chip
                label="F-Score"
                value={`${row.piotroski_score}/9`}
                color={row.piotroski_score >= 8 ? 'text-emerald-400' : row.piotroski_score <= 2 ? 'text-red-400' : 'text-amber-400'}
              />
            )}
            {row.magic_formula_rank != null && (
              <Chip label="MF Rank" value={`#${row.magic_formula_rank}`} color="text-purple-400" />
            )}
            {row.peg_ratio != null && (
              <Chip
                label="PEG"
                value={row.peg_ratio.toFixed(2)}
                color={row.peg_ratio < 1 ? 'text-emerald-400' : row.peg_ratio < 2 ? 'text-amber-400' : 'text-red-400'}
              />
            )}
            {rr != null && (
              <Chip
                label="R:R"
                value={rr.toFixed(1)}
                color={rr >= 2 ? 'text-emerald-400' : rr >= 1 ? 'text-amber-400' : 'text-red-400'}
              />
            )}
            {fcf != null && (
              <Chip
                label="FCF%"
                value={`${fcf.toFixed(1)}%`}
                color={fcf >= 5 ? 'text-emerald-400' : fcf >= 3 ? 'text-amber-400' : fcf < 0 ? 'text-red-400' : ''}
              />
            )}
            {row.roic_greenblatt != null && (
              <Chip
                label="ROIC"
                value={`${row.roic_greenblatt.toFixed(0)}%`}
                color={row.roic_greenblatt >= 20 ? 'text-emerald-400' : row.roic_greenblatt >= 10 ? 'text-amber-400' : ''}
              />
            )}
            {row.dividend_yield_pct != null && row.dividend_yield_pct > 0 && (
              <Chip label="Div" value={`${row.dividend_yield_pct.toFixed(1)}%`} color="text-emerald-400" />
            )}
            {row.buyback_active && (
              <Chip label="Buyback" value="Activo" color="text-emerald-400" />
            )}
            {earn != null && (
              <Chip
                label="Earnings"
                value={`${earn}d`}
                color={earn <= 7 ? 'text-red-400' : earn <= 21 ? 'text-amber-400' : 'text-emerald-400'}
              />
            )}
            {row.target_price_analyst != null && (
              <Chip label="Target" value={`${currency}${row.target_price_analyst.toFixed(0)}`} />
            )}
            {row.analyst_count != null && (
              <Chip label="Analistas" value={String(row.analyst_count)} />
            )}
          </div>

          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto px-5 py-4 min-h-0">
            {/* Entry/exit prices */}
            {(row.entry_price != null || row.stop_loss != null || row.target_price != null) && (
              <div className="flex gap-3 mb-5 flex-wrap">
                {row.entry_price != null && (
                  <div className="flex-1 min-w-[80px] px-3 py-2.5 rounded-lg bg-primary/8 border border-primary/20">
                    <div className="text-[0.58rem] font-bold uppercase tracking-widest text-primary/60 mb-1">Entrada</div>
                    <div className="font-bold text-sm tabular-nums text-primary">{currency}{row.entry_price.toFixed(2)}</div>
                  </div>
                )}
                {row.stop_loss != null && (
                  <div className="flex-1 min-w-[80px] px-3 py-2.5 rounded-lg bg-red-500/8 border border-red-500/20">
                    <div className="text-[0.58rem] font-bold uppercase tracking-widest text-red-400/60 mb-1">Stop Loss</div>
                    <div className="font-bold text-sm tabular-nums text-red-400">{currency}{row.stop_loss.toFixed(2)}</div>
                  </div>
                )}
                {row.target_price != null && (
                  <div className="flex-1 min-w-[80px] px-3 py-2.5 rounded-lg bg-emerald-500/8 border border-emerald-500/20">
                    <div className="text-[0.58rem] font-bold uppercase tracking-widest text-emerald-400/60 mb-1">Objetivo</div>
                    <div className="font-bold text-sm tabular-nums text-emerald-400">{currency}{row.target_price.toFixed(2)}</div>
                  </div>
                )}
              </div>
            )}

            {/* Thesis */}
            <ThesisBody text={thesisText} />

            {/* Conviction */}
            <ConvictionPanel row={row} />
          </div>
        </div>
      </div>
    </>
  )
}
