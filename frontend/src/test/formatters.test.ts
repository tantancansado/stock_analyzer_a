import { describe, expect, it } from 'vitest'
import { fmt, fmtDate, fmtM, fmtPct } from '@/lib/formatters'

describe('formatters', () => {
  it('formats generic values with prefix, suffix, and decimals', () => {
    expect(fmt(12.3456, '$', 'x', 2)).toBe('$12.35x')
    expect(fmt(12.3456, '', '%', 1)).toBe('12.3%')
  })

  it('returns an em dash for nullish generic values', () => {
    expect(fmt(null)).toBe('—')
    expect(fmt(undefined)).toBe('—')
  })

  it('formats millions, billions, and negative dollar values', () => {
    expect(fmtM(1_250_000_000)).toBe('$1.3B')
    expect(fmtM(450_000_000)).toBe('$450M')
    expect(fmtM(-999)).toBe('-$999')
  })

  it('returns an em dash for nullish money values', () => {
    expect(fmtM(null)).toBe('—')
    expect(fmtM(undefined)).toBe('—')
  })

  it('formats percentages with configurable decimals', () => {
    expect(fmtPct(12.345)).toBe('12.3%')
    expect(fmtPct(12.345, 2)).toBe('12.35%')
  })

  it('returns an em dash for nullish percentage values', () => {
    expect(fmtPct(null)).toBe('—')
    expect(fmtPct(undefined)).toBe('—')
  })

  it('formats ISO dates for es-ES locale and handles empty values', () => {
    expect(fmtDate('2026-04-15')).toBe('15/04/2026')
    expect(fmtDate('')).toBe('—')
    expect(fmtDate(null)).toBe('—')
    expect(fmtDate(undefined)).toBe('—')
  })
})
