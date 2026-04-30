import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { X, AlertTriangle, Zap, TrendingUp, TrendingDown, Loader2 } from 'lucide-react'
import { fetchEarningsThesis } from '../api/client'
import type { EarningsThesis, EarningsThesisVerdict } from '../api/client'
import TickerLogo from './TickerLogo'

interface Props {
  ticker: string
  onClose: () => void
}

interface VerdictStyle {
  label: string
  bg: string
  text: string
  border: string
}

const VERDICT_MAP: Record<EarningsThesisVerdict, VerdictStyle> = {
  EXIT_BEFORE:  { label: 'Salir antes',        bg: 'bg-red-500/15',     text: 'text-red-400',     border: 'border-red-500/40' },
  REDUCE:       { label: 'Reducir posición',   bg: 'bg-orange-500/15',  text: 'text-orange-400',  border: 'border-orange-500/40' },
  HOLD:         { label: 'Mantener',           bg: 'bg-blue-500/15',    text: 'text-blue-400',    border: 'border-blue-500/40' },
  HOLD_THROUGH: { label: 'Mantener en earnings', bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/40' },
  ADD_AFTER:    { label: 'Añadir post-earnings', bg: 'bg-cyan-500/15',   text: 'text-cyan-400',    border: 'border-cyan-500/40' },
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex flex-col gap-0.5 px-3 py-2 rounded-lg bg-muted/20 border border-border/20 min-w-[70px]">
      <span className="text-[0.5rem] font-bold uppercase tracking-widest text-muted-foreground/50 leading-none">{label}</span>
      <span className={`text-sm font-bold tabular-nums leading-tight ${color ?? 'text-foreground/80'}`}>{value}</span>
    </div>
  )
}

export default function EarningsThesisModal({ ticker, onClose }: Props) {
  const [thesis, setThesis] = useState<EarningsThesis | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setNotFound(false)
    fetchEarningsThesis(ticker)
      .then(t => {
        if (!alive) return
        if (!t) { setNotFound(true); setThesis(null) }
        else setThesis(t)
      })
      .catch(() => { if (alive) setNotFound(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [ticker])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  const verdictStyle = thesis ? VERDICT_MAP[thesis.verdict] ?? VERDICT_MAP.HOLD : null

  return createPortal(
    <>
      <div
        className="fixed inset-0 z-[500] bg-black/70 backdrop-blur-md animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className="fixed z-[500] bottom-0 left-0 right-0 sm:inset-0 sm:flex sm:items-center sm:justify-center sm:p-4"
        role="dialog"
        aria-modal="true"
      >
        <div className="liquid-glass relative w-full sm:max-w-2xl rounded-t-2xl sm:rounded-2xl flex flex-col max-h-[92dvh] sm:max-h-[88dvh] modal-enter">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-primary/60 via-primary to-purple-500/50 z-10" />

          <div className="sm:hidden flex justify-center pt-3 pb-1 flex-shrink-0">
            <div className="w-10 h-1 rounded-full bg-muted-foreground/25" />
          </div>

          <div className="flex items-start justify-between gap-3 px-5 pt-4 pb-3 flex-shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <TickerLogo ticker={ticker} size="md" />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-extrabold text-primary text-xl tracking-tight">{ticker}</span>
                  <span className="text-[0.6rem] font-bold uppercase tracking-widest text-primary/70 px-1.5 py-0.5 rounded bg-primary/10 border border-primary/20">
                    Tesis IA
                  </span>
                </div>
                {thesis?.company_name && (
                  <p className="text-xs text-foreground/60 truncate">{thesis.company_name}</p>
                )}
                {thesis?.sector && (
                  <p className="text-[0.65rem] text-muted-foreground/40">{thesis.sector}</p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground/60 hover:bg-red-500/15 hover:text-red-400 transition-colors"
              title="Cerrar (Esc)"
            >
              <X size={16} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto min-h-0 border-t border-border/30 px-5 py-4 space-y-5">
            {loading && (
              <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
                <Loader2 size={14} className="animate-spin" /> Cargando tesis IA...
              </div>
            )}

            {!loading && notFound && (
              <div className="text-center py-10 space-y-2">
                <AlertTriangle size={20} className="text-muted-foreground/40 mx-auto" />
                <p className="text-sm text-muted-foreground">
                  Aún no hay tesis generada para <span className="font-mono font-bold text-foreground/70">{ticker}</span>.
                </p>
                <p className="text-[0.65rem] text-muted-foreground/50">
                  La tesis se genera cada noche para posiciones con earnings en ≤14 días.
                </p>
              </div>
            )}

            {!loading && thesis && verdictStyle && (
              <>
                {/* Verdict banner */}
                <div className={`flex items-center justify-between gap-3 px-4 py-3 rounded-xl border ${verdictStyle.bg} ${verdictStyle.border}`}>
                  <div>
                    <div className="text-[0.55rem] font-bold uppercase tracking-widest text-muted-foreground/60">Recomendación</div>
                    <div className={`text-lg font-extrabold ${verdictStyle.text}`}>{verdictStyle.label}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[0.55rem] font-bold uppercase tracking-widest text-muted-foreground/60">Confianza</div>
                    <div className={`text-lg font-extrabold tabular-nums ${verdictStyle.text}`}>{thesis.confidence}</div>
                  </div>
                </div>

                {/* Sentiment tone badge */}
                {thesis.sentiment_tone && (
                  <div className="flex items-center gap-2">
                    <span className="text-[0.55rem] font-bold uppercase tracking-widest text-muted-foreground/50">Tono</span>
                    <span className={`text-[0.65rem] font-bold px-2 py-0.5 rounded-full border ${
                      thesis.sentiment_tone === 'BULLISH'
                        ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                        : thesis.sentiment_tone === 'BEARISH'
                        ? 'bg-red-500/15 text-red-400 border-red-500/30'
                        : 'bg-muted/20 text-muted-foreground border-border/30'
                    }`}>
                      {thesis.sentiment_tone === 'BULLISH' ? '▲ Optimista' : thesis.sentiment_tone === 'BEARISH' ? '▼ Defensivo' : '— Neutro'}
                    </span>
                    <span className="text-[0.6rem] text-muted-foreground/40">basado en noticias recientes + historial</span>
                  </div>
                )}

                {/* Implied move big number */}
                <div className="flex items-center gap-3 flex-wrap">
                  <div className="flex-1 min-w-[160px] px-4 py-3 rounded-xl bg-primary/5 border border-primary/20">
                    <div className="text-[0.55rem] font-bold uppercase tracking-widest text-primary/60">Implied Move</div>
                    <div className="text-3xl font-extrabold tabular-nums text-primary leading-tight">
                      {thesis.implied_move_pct != null ? `±${thesis.implied_move_pct.toFixed(1)}%` : 'N/A'}
                    </div>
                    <div className="text-[0.62rem] text-muted-foreground/60">
                      Earnings en {thesis.days_to_earnings}d · {thesis.earnings_date}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {thesis.expected_eps != null && (
                      <Stat label="EPS est." value={thesis.expected_eps.toFixed(2)} color="text-foreground" />
                    )}
                    {thesis.expected_revenue_millions != null && (
                      <Stat label="Rev est.($M)" value={thesis.expected_revenue_millions.toLocaleString(undefined, { maximumFractionDigits: 0 })} color="text-foreground" />
                    )}
                    {thesis.beat_rate_last_4q != null && (
                      <Stat
                        label="Beat 4Q"
                        value={`${(thesis.beat_rate_last_4q * 100).toFixed(0)}%`}
                        color={thesis.beat_rate_last_4q >= 0.75 ? 'text-emerald-400' : thesis.beat_rate_last_4q >= 0.5 ? 'text-amber-400' : 'text-red-400'}
                      />
                    )}
                    {thesis.unrealized_pct != null && (
                      <Stat
                        label="P&L"
                        value={`${thesis.unrealized_pct >= 0 ? '+' : ''}${thesis.unrealized_pct.toFixed(1)}%`}
                        color={thesis.unrealized_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}
                      />
                    )}
                  </div>
                </div>

                {/* Thesis summary */}
                {thesis.thesis_summary && (
                  <div>
                    <h4 className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">Resumen</h4>
                    <p className="text-sm text-foreground/85 leading-relaxed whitespace-pre-line">
                      {thesis.thesis_summary}
                    </p>
                  </div>
                )}

                {/* Catalysts */}
                {thesis.key_catalysts?.length > 0 && (
                  <div>
                    <h4 className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1.5">
                      <Zap size={11} className="text-emerald-400" />
                      Catalizadores
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {thesis.key_catalysts.map((c, i) => (
                        <span key={i} className="text-[0.68rem] px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-400/90">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Risks */}
                {thesis.key_risks?.length > 0 && (
                  <div>
                    <h4 className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1.5">
                      <AlertTriangle size={11} className="text-red-400" />
                      Riesgos
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {thesis.key_risks.map((r, i) => (
                        <span key={i} className="text-[0.68rem] px-2.5 py-1 rounded-lg bg-red-500/10 border border-red-500/25 text-red-400/90">
                          {r}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Earnings history */}
                {thesis.earnings_history && thesis.earnings_history.length > 0 && (
                  <div>
                    <h4 className="text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground mb-2">Histórico últimos 4Q</h4>
                    <div className="space-y-1">
                      {thesis.earnings_history.map((h, i) => (
                        <div key={i} className="flex items-center gap-2 text-[0.7rem] py-1 px-2 rounded-md bg-muted/15">
                          <span className="tabular-nums text-muted-foreground/60 w-20">{h.period}</span>
                          <span className="text-foreground/60">est {h.eps_estimate ?? '—'}</span>
                          <span className="text-foreground/80">act {h.eps_actual ?? '—'}</span>
                          {h.surprise_pct != null && (
                            <span className={`tabular-nums ml-auto font-semibold flex items-center gap-0.5 ${h.surprise_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {h.surprise_pct >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                              {h.surprise_pct >= 0 ? '+' : ''}{h.surprise_pct.toFixed(1)}%
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </>,
    document.body
  )
}
