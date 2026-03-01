/**
 * Lightweight CSS-only tooltip — no extra deps.
 * Renders a small "?" badge; hover reveals the explanation panel.
 *
 * Usage:
 *   <InfoTooltip text="Kelly Criterion: fracción óptima del portfolio…" />
 *
 * Props:
 *   text      — tooltip body (string or JSX)
 *   side      — where the panel opens: 'top' (default) | 'bottom'
 *   align     — horizontal anchor: 'center' (default) | 'left' | 'right'
 *   iconCls   — extra classes for the "?" badge
 *   width     — Tailwind width class for the panel (default 'w-60')
 */
import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface InfoTooltipProps {
  text: ReactNode
  side?: 'top' | 'bottom'
  align?: 'center' | 'left' | 'right'
  iconCls?: string
  width?: string
}

export default function InfoTooltip({
  text,
  side = 'top',
  align = 'center',
  iconCls,
  width = 'w-60',
}: InfoTooltipProps) {
  const panelVertical =
    side === 'top'
      ? 'bottom-full mb-1.5'
      : 'top-full mt-1.5'

  const panelHorizontal =
    align === 'left'
      ? 'left-0'
      : align === 'right'
        ? 'right-0'
        : 'left-1/2 -translate-x-1/2'

  return (
    <span className="group relative inline-flex items-center align-middle ml-1">
      {/* "?" badge */}
      <span
        className={cn(
          'inline-flex h-3.5 w-3.5 cursor-help select-none items-center justify-center rounded-full',
          'bg-muted-foreground/20 text-[0.55rem] font-bold text-muted-foreground',
          'transition-colors group-hover:bg-primary/20 group-hover:text-primary',
          iconCls,
        )}
      >
        ?
      </span>

      {/* Tooltip panel */}
      <span
        className={cn(
          'pointer-events-none absolute z-50',
          panelVertical,
          panelHorizontal,
          width,
          'rounded-md border border-border bg-popover px-2.5 py-2',
          'text-[0.7rem] leading-relaxed text-popover-foreground shadow-lg',
          'opacity-0 group-hover:opacity-100 transition-opacity duration-150',
          'whitespace-normal text-left',
        )}
      >
        {text}
      </span>
    </span>
  )
}
