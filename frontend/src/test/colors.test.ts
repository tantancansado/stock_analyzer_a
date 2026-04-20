import { describe, expect, it } from 'vitest'
import { gradeColor, signalColor, SIGNAL_COLORS, upsideColor } from '@/lib/colors'

describe('colors helpers', () => {
  it('returns colors for upside percentages', () => {
    expect(upsideColor(10)).toBe('text-emerald-400')
    expect(upsideColor(-5)).toBe('text-red-400')
    expect(upsideColor(null)).toBe('text-muted-foreground')
  })

  it('returns colors for conviction grades', () => {
    expect(gradeColor('A+')).toBe('text-emerald-400')
    expect(gradeColor('STRONG')).toBe('text-blue-400')
    expect(gradeColor('moderate')).toBe('text-amber-400')
    expect(gradeColor('weak')).toBe('text-red-400')
    expect(gradeColor(undefined)).toBe('text-muted-foreground')
  })

  it('returns colors for signal labels and exposes badge variants', () => {
    expect(signalColor('BUY')).toBe('text-emerald-400')
    expect(signalColor('watch')).toBe('text-amber-400')
    expect(signalColor('hold')).toBe('text-sky-400')
    expect(signalColor('overvalued')).toBe('text-red-400')
    expect(signalColor('other')).toBe('text-muted-foreground')
    expect(SIGNAL_COLORS.BUY).toContain('bg-emerald-500/15')
    expect(SIGNAL_COLORS.NO_DATA).toContain('text-muted-foreground')
  })
})
