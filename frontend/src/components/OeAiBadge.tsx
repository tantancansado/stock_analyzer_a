interface Props {
  verdict?: string | null
  adjustment?: number | null
  compact?: boolean
}

function styleFor(verdict: string): { cls: string; icon: string } {
  const v = verdict.toUpperCase()
  if (v.startsWith('UNRELIABLE')) {
    return { cls: 'bg-muted/30 text-muted-foreground border-border/40', icon: '⚠' }
  }
  if (v.startsWith('RELIABLE/BUY')) {
    return { cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', icon: '✓' }
  }
  if (v.startsWith('RELIABLE/AVOID')) {
    return { cls: 'bg-red-500/15 text-red-400 border-red-500/30', icon: '✗' }
  }
  if (v.includes('/AVOID')) {
    return { cls: 'bg-red-500/10 text-red-400/80 border-red-500/20', icon: '✗' }
  }
  if (v.includes('/BUY')) {
    return { cls: 'bg-emerald-500/10 text-emerald-400/80 border-emerald-500/20', icon: '✓' }
  }
  return { cls: 'bg-muted/20 text-muted-foreground/80 border-border/30', icon: '·' }
}

export default function OeAiBadge({ verdict, adjustment, compact }: Props) {
  if (!verdict) return <span className="text-muted-foreground/30 text-xs">—</span>
  const { cls, icon } = styleFor(verdict)
  const adjTxt = adjustment != null && adjustment !== 0
    ? (adjustment > 0 ? `+${adjustment}` : `${adjustment}`)
    : '0'
  return (
    <span
      className={`inline-flex items-center gap-1 text-[0.6rem] font-bold px-1.5 py-0.5 rounded border tracking-wide ${cls}`}
      title={`Owner Earnings AI: ${verdict}`}
    >
      <span>{icon}</span>
      {compact ? null : <span className="tabular-nums">{adjTxt}</span>}
    </span>
  )
}
