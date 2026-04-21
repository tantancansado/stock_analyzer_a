import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  targetChange7dPct?: number | null
  upgradeDays14d?: number | null
  downgradeDays14d?: number | null
  className?: string
  compact?: boolean
}

export default function AnalystRevisionBadge({
  targetChange7dPct,
  upgradeDays14d,
  downgradeDays14d,
  className,
  compact = false,
}: Props) {
  if (targetChange7dPct == null || Number.isNaN(targetChange7dPct)) return null
  const abs = Math.abs(targetChange7dPct)
  if (abs < 0.5) {
    if (compact) return null
    return (
      <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[0.6rem] font-medium bg-muted/20 text-muted-foreground border border-border/30', className)} title="Targets estables últimos 7 días">
        <Minus size={10} /> 0.0%
      </span>
    )
  }
  const up = targetChange7dPct > 0
  const strong = abs >= 3
  const colorClasses = up
    ? strong
      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25'
      : 'bg-emerald-500/10 text-emerald-400/80 border-emerald-500/15'
    : strong
      ? 'bg-red-500/15 text-red-400 border-red-500/25'
      : 'bg-red-500/10 text-red-400/80 border-red-500/15'
  const Icon = up ? TrendingUp : TrendingDown
  const tooltip = `Target medio ${up ? '+' : ''}${targetChange7dPct.toFixed(1)}% en 7 días${
    upgradeDays14d != null ? ` · ${upgradeDays14d} días de subida (14d)` : ''
  }${downgradeDays14d != null && downgradeDays14d > 0 ? ` · ${downgradeDays14d} de bajada` : ''}`
  return (
    <span
      className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[0.6rem] font-bold border', colorClasses, className)}
      title={tooltip}
    >
      <Icon size={10} />
      {up ? '+' : ''}{targetChange7dPct.toFixed(1)}%
    </span>
  )
}
