import { CheckCircle2, Eye, PauseCircle, ShieldAlert, SlidersHorizontal } from 'lucide-react'
import type { ValueOpportunity } from '@/api/client'
import { Card, CardContent } from '@/components/ui/card'
import TickerLogo from './TickerLogo'
import { cn } from '@/lib/utils'
import type { ValueDecision } from '@/lib/valueDecision'

export function ValueDecisionBadge({ decision, className }: { decision: ValueDecision; className?: string }) {
  const Icon =
    decision.kind === 'ready' ? CheckCircle2 :
    decision.kind === 'watch' ? Eye :
    decision.kind === 'avoid' ? ShieldAlert :
    PauseCircle

  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[0.68rem] font-bold', decision.badgeClass, className)}>
      <Icon size={12} strokeWidth={1.8} />
      {decision.label}
    </span>
  )
}

export function ValueModeToggle({
  clearMode,
  onChange,
}: {
  clearMode: boolean
  onChange: (enabled: boolean) => void
}) {
  return (
    <button
      type="button"
      aria-pressed={clearMode}
      onClick={() => onChange(!clearMode)}
      className={cn(
        'inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors',
        clearMode
          ? 'border-primary/40 bg-primary/10 text-primary'
          : 'border-border/50 text-muted-foreground hover:border-border/80 hover:text-foreground'
      )}
      title={clearMode ? 'Cambiar a vista avanzada' : 'Cambiar a vista clara'}
    >
      <SlidersHorizontal size={13} strokeWidth={1.8} />
      {clearMode ? 'Vista clara' : 'Vista avanzada'}
    </button>
  )
}

export function ValueClarityPanel({
  rows,
  getDecision,
  currencyFor,
  onSelect,
  onRecommended,
  onExpert,
}: {
  rows: ValueOpportunity[]
  getDecision: (row: ValueOpportunity) => ValueDecision
  currencyFor: (row: ValueOpportunity) => string
  onSelect: (row: ValueOpportunity) => void
  onRecommended: () => void
  onExpert: () => void
}) {
  const evaluated = rows.map(row => ({ row, decision: getDecision(row) }))
  const ready = evaluated.filter(item => item.decision.kind === 'ready')
  const watch = evaluated.filter(item => item.decision.kind === 'watch')
  const avoid = evaluated.filter(item => item.decision.kind === 'avoid')
  const lead = ready[0] ?? watch[0] ?? evaluated[0]

  return (
    <Card className="liquid-glass mb-5 overflow-clip">
      <CardContent className="p-0">
        <div className="grid gap-0 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="p-5 md:p-6">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-[0.14em] text-primary">
                Vista clara
              </span>
              <span className="text-xs text-muted-foreground">
                La lógica técnica sigue detrás; aquí ves la conclusión.
              </span>
            </div>

            {lead ? (
              <button
                type="button"
                onClick={() => onSelect(lead.row)}
                className={cn('w-full rounded-xl border p-4 text-left transition-colors hover:border-primary/30', lead.decision.panelClass)}
              >
                <div className="flex items-start gap-3">
                  <TickerLogo ticker={lead.row.ticker} size="md" className="mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-bold text-foreground">{lead.row.ticker}</span>
                      <ValueDecisionBadge decision={lead.decision} />
                    </div>
                    <p className="text-sm font-semibold text-foreground">{lead.decision.headline}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{lead.decision.detail}</p>
                    <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                      {lead.row.analyst_upside_pct != null && (
                        <span>Potencial: <strong className={lead.row.analyst_upside_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}>{lead.row.analyst_upside_pct >= 0 ? '+' : ''}{lead.row.analyst_upside_pct.toFixed(0)}%</strong></span>
                      )}
                      {lead.row.current_price != null && <span>Precio: <strong className="text-foreground">{currencyFor(lead.row)}{lead.row.current_price.toFixed(2)}</strong></span>}
                      {lead.row.company_name && <span className="min-w-0 truncate">{lead.row.company_name}</span>}
                    </div>
                  </div>
                </div>
              </button>
            ) : (
              <div className="rounded-xl border border-border/30 bg-muted/10 p-4 text-sm text-muted-foreground">
                No hay ideas visibles con los filtros actuales.
              </div>
            )}
          </div>

          <div className="border-t border-border/20 p-5 lg:border-l lg:border-t-0">
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-emerald-500/15 bg-emerald-500/5 p-3">
                <div className="text-2xl font-extrabold tabular-nums text-emerald-400">{ready.length}</div>
                <div className="text-[0.65rem] font-semibold text-muted-foreground">para revisar</div>
              </div>
              <div className="rounded-lg border border-sky-500/15 bg-sky-500/5 p-3">
                <div className="text-2xl font-extrabold tabular-nums text-sky-400">{watch.length}</div>
                <div className="text-[0.65rem] font-semibold text-muted-foreground">en vigilancia</div>
              </div>
              <div className="rounded-lg border border-red-500/15 bg-red-500/5 p-3">
                <div className="text-2xl font-extrabold tabular-nums text-red-400">{avoid.length}</div>
                <div className="text-[0.65rem] font-semibold text-muted-foreground">mejor evitar</div>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" onClick={onRecommended} className="filter-btn active">
                Vista recomendada
              </button>
              <button type="button" onClick={onExpert} className="filter-btn">
                Filtros técnicos
              </button>
            </div>

            <p className="mt-3 text-[0.72rem] leading-relaxed text-muted-foreground">
              El ranking conserva tus modelos: calidad, precio, riesgo, alertas y señales. La diferencia es que la pantalla habla en decisiones.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
