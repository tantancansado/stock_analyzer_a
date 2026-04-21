import { useState } from 'react'
import { CheckCircle2, Clock, XCircle, HelpCircle } from 'lucide-react'
import type { EntryVerdict } from '../api/client'
import { cn } from '@/lib/utils'

interface Props {
  verdict: EntryVerdict | null | undefined
  compact?: boolean
  className?: string
}

const VERDICT_META = {
  ENTRY:   { label: 'ENTRA',  icon: CheckCircle2, bg: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/20' },
  WAIT:    { label: 'ESPERA', icon: Clock,        bg: 'bg-amber-500/15 text-amber-300 border-amber-500/30 hover:bg-amber-500/20' },
  AVOID:   { label: 'EVITA',  icon: XCircle,      bg: 'bg-red-500/15 text-red-300 border-red-500/30 hover:bg-red-500/20' },
  NEUTRAL: { label: '—',       icon: HelpCircle,   bg: 'bg-muted/20 text-muted-foreground border-border/30 hover:bg-muted/30' },
} as const

export default function EntryVerdictBadge({ verdict, compact = false, className }: Readonly<Props>) {
  const [open, setOpen] = useState(false)

  if (!verdict) {
    if (compact) return null
    return (
      <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[0.58rem] font-bold border bg-muted/10 text-muted-foreground/60 border-border/20', className)}>
        <HelpCircle size={10} /> ?
      </span>
    )
  }

  const meta = VERDICT_META[verdict.verdict] ?? VERDICT_META.NEUTRAL
  const Icon = meta.icon
  const reasons = (verdict.reasons || '').split(' · ').filter(Boolean)
  const blockers = (verdict.blockers || '').split(' · ').filter(Boolean)

  const tooltipText = [
    reasons.length > 0 ? `✓ ${reasons.join(' · ')}` : null,
    blockers.length > 0 ? `✗ ${blockers.join(' · ')}` : null,
    verdict.trigger ? `→ ${verdict.trigger}` : null,
  ].filter(Boolean).join('\n')

  return (
    <div className={cn('relative inline-block', className)}>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(o => !o) }}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className={cn(
          'inline-flex items-center gap-1 px-1.5 py-0.5 rounded border font-bold transition-colors cursor-pointer',
          compact ? 'text-[0.58rem]' : 'text-[0.65rem]',
          meta.bg
        )}
        title={tooltipText}
      >
        <Icon size={compact ? 10 : 12} strokeWidth={2.2} />
        {meta.label}
        {verdict.confidence != null && !compact && (
          <span className="opacity-60 tabular-nums">{verdict.confidence}</span>
        )}
      </button>

      {open && (
        <div className="absolute z-50 top-full left-0 mt-1 w-72 rounded-lg border border-border shadow-xl p-3 text-xs space-y-2" style={{ backgroundColor: 'hsl(var(--background))' }}>
          <div className="flex items-center gap-2 pb-1.5 border-b border-border/30">
            <Icon size={14} className={meta.bg.split(' ').find(c => c.startsWith('text-')) ?? 'text-foreground'} />
            <span className="font-bold">{meta.label}</span>
            {verdict.confidence != null && (
              <span className="text-[0.58rem] text-muted-foreground/70 tabular-nums ml-auto">conf {verdict.confidence}</span>
            )}
            {verdict.source === 'ai' && (
              <span className="text-[0.55rem] px-1.5 py-0.5 rounded border border-primary/30 bg-primary/10 text-primary font-bold">IA</span>
            )}
          </div>
          {reasons.length > 0 && (
            <div>
              <div className="text-[0.55rem] uppercase tracking-widest text-emerald-400/70 font-bold mb-1">A favor</div>
              <ul className="space-y-0.5">
                {reasons.map(r => <li key={r} className="text-foreground/85 text-[0.7rem]">· {r}</li>)}
              </ul>
            </div>
          )}
          {blockers.length > 0 && (
            <div>
              <div className="text-[0.55rem] uppercase tracking-widest text-red-400/70 font-bold mb-1">En contra</div>
              <ul className="space-y-0.5">
                {blockers.map(b => <li key={b} className="text-foreground/85 text-[0.7rem]">· {b}</li>)}
              </ul>
            </div>
          )}
          {verdict.trigger && (
            <div className="pt-1.5 border-t border-border/30">
              <div className="text-[0.55rem] uppercase tracking-widest text-primary/80 font-bold mb-1">Trigger</div>
              <p className="text-[0.7rem] text-foreground/85 leading-snug">{verdict.trigger}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
