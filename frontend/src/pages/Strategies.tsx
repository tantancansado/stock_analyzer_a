import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Brain, TrendingUp, TrendingDown, Pause, Activity, AlertTriangle, Calendar, Target, Shield } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import Loading, { ErrorState } from '../components/Loading'
import TickerLogo from '../components/TickerLogo'
import { Card, CardContent } from '@/components/ui/card'
import EmptyState from '../components/EmptyState'
import { fetchPortfolioStrategies, type PortfolioStrategy, type StrategyAction } from '../api/client'

const ACTION_META: Record<StrategyAction, { label: string; bg: string; icon: typeof Brain }> = {
  HOLD:  { label: 'Mantener',         bg: 'border-sky-500/30 bg-sky-500/10 text-sky-300',         icon: Pause },
  TRIM:  { label: 'Recoger parcial',  bg: 'border-amber-500/30 bg-amber-500/10 text-amber-300',   icon: TrendingDown },
  ADD:   { label: 'Añadir',           bg: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300', icon: TrendingUp },
  EXIT:  { label: 'Salir',            bg: 'border-red-500/30 bg-red-500/10 text-red-300',         icon: AlertTriangle },
  WATCH: { label: 'Vigilar',          bg: 'border-muted-foreground/30 bg-muted/15 text-muted-foreground', icon: Activity },
}

function ActionBadge({ action }: { action: StrategyAction }) {
  const meta = ACTION_META[action] ?? ACTION_META.HOLD
  const Icon = meta.icon
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[0.7rem] font-bold uppercase tracking-wider ${meta.bg}`}>
      <Icon size={12} strokeWidth={2} />
      {meta.label}
    </span>
  )
}

function StrategyCard({ s }: { s: PortfolioStrategy }) {
  const plClass = (s.pl_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'
  const distToTrim = s.trim_at_price ? ((s.trim_at_price - s.current_price) / s.current_price * 100) : null
  const distToAdd  = s.add_at_price  ? ((s.current_price - s.add_at_price)  / s.current_price * 100) : null
  const distToStop = ((s.stop_loss_price - s.current_price) / s.current_price * 100)

  return (
    <Card className="liquid-glass overflow-clip">
      <CardContent className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
          <div className="flex items-center gap-3 min-w-0">
            <TickerLogo ticker={s.ticker} size="md" className="shrink-0" />
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <Link
                  to={`/search?q=${s.ticker}`}
                  className="font-mono font-extrabold text-lg text-primary hover:underline"
                >
                  {s.ticker}
                </Link>
                <ActionBadge action={s.current_action} />
                {s._stale_strategy && (
                  <span
                    className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-300/90 px-2 py-0.5 text-[0.62rem] font-bold uppercase tracking-wider"
                    title={s._stale_reason || 'Plan del día anterior — IA sin presupuesto hoy'}
                  >
                    <AlertTriangle size={10} strokeWidth={2.5} />
                    Plan ayer
                  </span>
                )}
              </div>
              <div className="text-[0.72rem] text-muted-foreground/70 mt-0.5">
                {s.shares} acc · avg ${s.avg_price.toFixed(2)} · actual <b className="text-foreground">${s.current_price.toFixed(2)}</b>
              </div>
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className={`text-base font-bold tabular-nums ${plClass}`}>
              {(s.pl_pct ?? 0) >= 0 ? '+' : ''}{(s.pl_pct ?? 0).toFixed(1)}%
            </div>
            <div className="text-[0.6rem] uppercase tracking-wider text-muted-foreground/50 mt-0.5">P&L abierto</div>
          </div>
        </div>

        {/* Action reason */}
        {s.action_reason && (
          <div className="mb-4 rounded-lg border border-border/30 bg-muted/10 px-3 py-2.5">
            <p className="text-sm leading-relaxed text-foreground">{s.action_reason}</p>
          </div>
        )}

        {/* Levels grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 mb-4">
          {s.trim_at_price && s.trim_pct ? (
            <div className="rounded-lg border border-amber-500/25 bg-amber-500/5 px-3 py-2.5">
              <div className="flex items-center gap-1.5 text-[0.62rem] font-bold uppercase tracking-wider text-amber-400/80 mb-1">
                <TrendingDown size={11} /> Vender {s.trim_pct.toFixed(0)}%
              </div>
              <div className="text-base font-bold tabular-nums text-amber-300">${s.trim_at_price.toFixed(2)}</div>
              {distToTrim !== null && (
                <div className="text-[0.65rem] text-muted-foreground/60 mt-0.5">
                  {distToTrim >= 0 ? '+' : ''}{distToTrim.toFixed(1)}% desde aquí
                </div>
              )}
              {s.trim_reason && (
                <div className="mt-1.5 text-[0.7rem] leading-snug text-muted-foreground">{s.trim_reason}</div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-border/20 bg-muted/5 px-3 py-2.5 opacity-50">
              <div className="text-[0.62rem] font-bold uppercase tracking-wider text-muted-foreground/50">Sin nivel de venta</div>
            </div>
          )}

          {s.add_at_price && s.add_pct ? (
            <div className="rounded-lg border border-emerald-500/25 bg-emerald-500/5 px-3 py-2.5">
              <div className="flex items-center gap-1.5 text-[0.62rem] font-bold uppercase tracking-wider text-emerald-400/80 mb-1">
                <TrendingUp size={11} /> Comprar +{s.add_pct.toFixed(0)}%
              </div>
              <div className="text-base font-bold tabular-nums text-emerald-300">${s.add_at_price.toFixed(2)}</div>
              {distToAdd !== null && (
                <div className="text-[0.65rem] text-muted-foreground/60 mt-0.5">
                  -{Math.abs(distToAdd).toFixed(1)}% desde aquí
                </div>
              )}
              {s.add_reason && (
                <div className="mt-1.5 text-[0.7rem] leading-snug text-muted-foreground">{s.add_reason}</div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-border/20 bg-muted/5 px-3 py-2.5 opacity-50">
              <div className="text-[0.62rem] font-bold uppercase tracking-wider text-muted-foreground/50">Sin nivel de recompra</div>
            </div>
          )}

          <div className="rounded-lg border border-red-500/25 bg-red-500/5 px-3 py-2.5">
            <div className="flex items-center gap-1.5 text-[0.62rem] font-bold uppercase tracking-wider text-red-400/80 mb-1">
              <Shield size={11} /> Stop loss
            </div>
            <div className="text-base font-bold tabular-nums text-red-300">${s.stop_loss_price.toFixed(2)}</div>
            <div className="text-[0.65rem] text-muted-foreground/60 mt-0.5">
              {distToStop.toFixed(1)}% desde aquí
            </div>
          </div>
        </div>

        {/* Triggers */}
        {(s.triggers_sell.length > 0 || s.triggers_buy.length > 0) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
            {s.triggers_sell.length > 0 && (
              <div>
                <div className="text-[0.62rem] font-bold uppercase tracking-wider text-amber-400/70 mb-1.5">Triggers de salida</div>
                <ul className="space-y-1">
                  {s.triggers_sell.slice(0, 3).map((t, i) => (
                    <li key={i} className="flex gap-1.5 text-[0.78rem] leading-snug text-muted-foreground">
                      <span className="text-amber-400/60 shrink-0">•</span>
                      <span>{t}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {s.triggers_buy.length > 0 && (
              <div>
                <div className="text-[0.62rem] font-bold uppercase tracking-wider text-emerald-400/70 mb-1.5">Triggers de compra</div>
                <ul className="space-y-1">
                  {s.triggers_buy.slice(0, 3).map((t, i) => (
                    <li key={i} className="flex gap-1.5 text-[0.78rem] leading-snug text-muted-foreground">
                      <span className="text-emerald-400/60 shrink-0">•</span>
                      <span>{t}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Thesis + next check */}
        {s.thesis_short && (
          <div className="mb-3 text-[0.78rem] leading-relaxed text-muted-foreground italic">
            “{s.thesis_short}”
          </div>
        )}

        <div className="flex items-center justify-between flex-wrap gap-2 pt-3 border-t border-border/20">
          <div className="flex items-center gap-1.5 text-[0.72rem] text-muted-foreground">
            <Calendar size={11} />
            Próximo check: <b className="text-foreground tabular-nums">{s.next_check_date}</b>
            {s.next_check_reason && <span className="text-muted-foreground/60">— {s.next_check_reason}</span>}
          </div>
          <div className="flex items-center gap-1.5 text-[0.65rem]">
            <Target size={10} className="text-muted-foreground/50" />
            <span className="text-muted-foreground/60">Confianza</span>
            <b className="text-foreground tabular-nums">{s.confidence}%</b>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function Strategies() {
  const { data, loading, error } = useApi(() => fetchPortfolioStrategies(), [])

  const strategies = useMemo(() => {
    const map = data?.strategies ?? {}
    return Object.values(map)
  }, [data])

  const counts = useMemo(() => {
    const c: Record<StrategyAction, number> = { HOLD: 0, TRIM: 0, ADD: 0, EXIT: 0, WATCH: 0 }
    for (const s of strategies) c[s.current_action] = (c[s.current_action] ?? 0) + 1
    return c
  }, [strategies])

  if (loading) return <Loading />
  if (error) return <ErrorState message={error} />

  if (strategies.length === 0) {
    return (
      <Card className="glass">
        <CardContent className="p-0">
          <EmptyState
            icon="🧠"
            title="No hay estrategias generadas todavía"
            subtitle="Añade posiciones reales (con coste medio y acciones) en Mis Posiciones. El agente IA generará un plan diario por cada una en el próximo run del pipeline."
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <div className="mb-5 flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-extrabold tracking-tight gradient-title flex items-center gap-2 mb-1">
            <Brain size={20} className="text-purple-400" />
            Estrategias IA
          </h2>
          <p className="text-sm text-muted-foreground">
            Plan personalizado por posición — trim/add levels, triggers y fechas concretas. Generado a diario.
            {data?.scan_date && <span className="text-muted-foreground/40"> · Scan {data.scan_date}</span>}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(['ADD', 'TRIM', 'HOLD', 'WATCH', 'EXIT'] as StrategyAction[]).map(action => {
            const n = counts[action]
            if (!n) return null
            const meta = ACTION_META[action]
            return (
              <div key={action} className={`text-[0.7rem] font-bold px-3 py-1.5 rounded-full border ${meta.bg}`}>
                {n} {meta.label}
              </div>
            )
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {strategies
          .sort((a, b) => {
            // Orden: ADD/TRIM/EXIT primero (acción hoy), HOLD/WATCH al final
            const order: Record<StrategyAction, number> = { EXIT: 0, ADD: 1, TRIM: 2, WATCH: 3, HOLD: 4 }
            return order[a.current_action] - order[b.current_action]
          })
          .map(s => <StrategyCard key={s.ticker} s={s} />)
        }
      </div>
    </>
  )
}
