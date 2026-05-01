import { describe, it, expect, vi } from 'vitest'
import { getValueDecision } from '@/lib/valueDecision'
import type { ValueDecision } from '@/lib/valueDecision'

// The module under test has no external dependencies — no axios or supabase mocks needed.
vi.mock('axios', () => ({ default: { create: vi.fn(() => ({ get: vi.fn(), post: vi.fn(), interceptors: { request: { use: vi.fn() } } })) } }))
vi.mock('@/lib/supabase', () => ({ supabase: { auth: { onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })), refreshSession: vi.fn() } } }))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Minimal valid ValueOpportunity row — passes all quality gates. */
function makeRow(overrides: Partial<Parameters<typeof getValueDecision>[0]['row']> = {}) {
  return {
    ticker: 'TEST',
    company_name: 'Test Inc',
    current_price: 100,
    value_score: 70,
    conviction_grade: 'A',
    analyst_upside_pct: 20,
    risk_reward_ratio: 2.0,
    days_to_earnings: 30,
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// AVOID — EXIT signal
// ---------------------------------------------------------------------------

describe('getValueDecision — EXIT signal', () => {
  it('returns avoid when hasExit flag is true', () => {
    const result = getValueDecision({ row: makeRow(), hasExit: true })
    expect(result.kind).toBe('avoid')
    expect(result.label).toBe('Evitar')
    expect(result.headline).toContain('señal de salida')
  })

  it('returns avoid when row.cerebro_signal is EXIT', () => {
    const result = getValueDecision({ row: makeRow({ cerebro_signal: 'EXIT' }) })
    expect(result.kind).toBe('avoid')
    expect(result.headline).toContain('señal de salida')
  })

  it('EXIT takes priority over TRAP when both are set', () => {
    const result = getValueDecision({ row: makeRow({ cerebro_signal: 'TRAP' }), hasExit: true })
    expect(result.headline).toContain('señal de salida')
  })

  it('EXIT takes priority over nearEarnings', () => {
    const result = getValueDecision({ row: makeRow({ days_to_earnings: 1 }), hasExit: true })
    expect(result.kind).toBe('avoid')
    expect(result.headline).toContain('señal de salida')
  })

  it('EXIT takes priority over bad upside', () => {
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: -5 }), hasExit: true })
    expect(result.kind).toBe('avoid')
    expect(result.headline).toContain('señal de salida')
  })

  it('EXIT badge and panel classes are red', () => {
    const result = getValueDecision({ row: makeRow(), hasExit: true })
    expect(result.badgeClass).toContain('red')
    expect(result.panelClass).toContain('red')
  })
})

// ---------------------------------------------------------------------------
// AVOID — TRAP signal
// ---------------------------------------------------------------------------

describe('getValueDecision — TRAP signal', () => {
  it('returns avoid when hasTrap flag is true', () => {
    const result = getValueDecision({ row: makeRow(), hasTrap: true })
    expect(result.kind).toBe('avoid')
    expect(result.label).toBe('Evitar')
    expect(result.headline).toContain('trampa')
  })

  it('returns avoid when row.cerebro_signal is TRAP', () => {
    const result = getValueDecision({ row: makeRow({ cerebro_signal: 'TRAP' }) })
    expect(result.kind).toBe('avoid')
    expect(result.headline).toContain('trampa')
  })

  it('TRAP takes priority over bad upside', () => {
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: -10 }), hasTrap: true })
    expect(result.headline).toContain('trampa')
  })

  it('TRAP takes priority over nearEarnings', () => {
    const result = getValueDecision({ row: makeRow({ days_to_earnings: 0 }), hasTrap: true })
    expect(result.headline).toContain('trampa')
  })

  it('TRAP badge and panel classes are red', () => {
    const result = getValueDecision({ row: makeRow(), hasTrap: true })
    expect(result.badgeClass).toContain('red')
    expect(result.panelClass).toContain('red')
  })
})

// ---------------------------------------------------------------------------
// AVOID — bad upside (analyst_upside_pct < 0)
// ---------------------------------------------------------------------------

describe('getValueDecision — bad upside', () => {
  it('returns avoid when analyst_upside_pct is negative', () => {
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: -1 }) })
    expect(result.kind).toBe('avoid')
    expect(result.headline).toContain('potencial')
  })

  it('returns avoid for upside exactly 0 — boundary: 0 is not negative', () => {
    // regression: 0 is NOT < 0 so hasBadUpside is false — should NOT be avoid
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: 0 }) })
    // upside=0 → hasBadUpside=false, hasGoodUpside=false (0 < 10) → isReady=false → watch/wait
    expect(result.kind).not.toBe('avoid')
  })

  it('bad upside takes priority over nearEarnings', () => {
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: -5, days_to_earnings: 3 }) })
    expect(result.kind).toBe('avoid')
    expect(result.headline).toContain('potencial')
  })

  it('avoid: bad upside badge and panel classes are red', () => {
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: -0.01 }) })
    expect(result.badgeClass).toContain('red')
    expect(result.panelClass).toContain('red')
  })
})

// ---------------------------------------------------------------------------
// WAIT — near earnings
// ---------------------------------------------------------------------------

describe('getValueDecision — near earnings', () => {
  it('returns wait when days_to_earnings is exactly 7', () => {
    const result = getValueDecision({ row: makeRow({ days_to_earnings: 7 }) })
    expect(result.kind).toBe('wait')
    expect(result.label).toBe('Esperar')
    expect(result.headline).toContain('Resultados')
  })

  it('returns wait when days_to_earnings is 0', () => {
    const result = getValueDecision({ row: makeRow({ days_to_earnings: 0 }) })
    expect(result.kind).toBe('wait')
  })

  it('returns wait when days_to_earnings is 1', () => {
    const result = getValueDecision({ row: makeRow({ days_to_earnings: 1 }) })
    expect(result.kind).toBe('wait')
    expect(result.headline).toContain('Resultados')
  })

  it('does NOT trigger nearEarnings when days_to_earnings is 8', () => {
    // regression: 8 > 7 should not be "near earnings"
    const result = getValueDecision({ row: makeRow({ days_to_earnings: 8 }) })
    expect(result.kind).not.toBe('wait')
  })

  it('does NOT trigger nearEarnings when days_to_earnings is null', () => {
    const result = getValueDecision({ row: makeRow({ days_to_earnings: undefined }) })
    // No nearEarnings — should evaluate normally (ready with our good defaults)
    expect(result.kind).toBe('ready')
  })

  it('near earnings badge and panel classes are amber', () => {
    const result = getValueDecision({ row: makeRow({ days_to_earnings: 5 }) })
    expect(result.badgeClass).toContain('amber')
    expect(result.panelClass).toContain('amber')
  })
})

// ---------------------------------------------------------------------------
// READY — isReady path
// ---------------------------------------------------------------------------

describe('getValueDecision — ready (isReady path)', () => {
  it('returns ready for a fully qualifying row', () => {
    const result = getValueDecision({ row: makeRow() })
    expect(result.kind).toBe('ready')
    expect(result.label).toBe('Listo para revisar')
  })

  it('returns ready with grade B', () => {
    const result = getValueDecision({ row: makeRow({ conviction_grade: 'B' }) })
    expect(result.kind).toBe('ready')
  })

  it('returns ready with grade EXCELLENT', () => {
    const result = getValueDecision({ row: makeRow({ conviction_grade: 'EXCELLENT' }) })
    expect(result.kind).toBe('ready')
  })

  it('returns ready with grade STRONG', () => {
    const result = getValueDecision({ row: makeRow({ conviction_grade: 'STRONG' }) })
    expect(result.kind).toBe('ready')
  })

  it('grade matching is case-insensitive', () => {
    const result = getValueDecision({ row: makeRow({ conviction_grade: 'a' }) })
    expect(result.kind).toBe('ready')
  })

  it('score exactly 65 qualifies as ready', () => {
    const result = getValueDecision({ row: makeRow({ value_score: 65 }) })
    expect(result.kind).toBe('ready')
  })

  it('score 64 does NOT qualify as isReady', () => {
    // regression: 64 < 65 boundary — falls through to watch since grade A
    const result = getValueDecision({ row: makeRow({ value_score: 64 }) })
    expect(result.kind).not.toBe('ready')
  })

  it('returns ready when upside is null (no analyst coverage)', () => {
    // upside null → hasGoodUpside=true (null treated as unknown/ok)
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: undefined }) })
    expect(result.kind).toBe('ready')
  })

  it('returns ready when upside is exactly 10 (boundary)', () => {
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: 10 }) })
    expect(result.kind).toBe('ready')
  })

  it('upside 9 blocks isReady (< 10 threshold)', () => {
    // regression: upside 9 → hasGoodUpside=false → isReady=false → falls to watch (grade A)
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: 9 }) })
    expect(result.kind).not.toBe('ready')
  })

  it('returns ready when risk_reward_ratio is null', () => {
    // null rr → hasEnoughReward=true
    const result = getValueDecision({ row: makeRow({ risk_reward_ratio: undefined }) })
    expect(result.kind).toBe('ready')
  })

  it('returns ready when risk_reward_ratio is exactly 1.5', () => {
    const result = getValueDecision({ row: makeRow({ risk_reward_ratio: 1.5 }) })
    expect(result.kind).toBe('ready')
  })

  it('risk_reward_ratio 1.4 blocks isReady', () => {
    // regression: 1.4 < 1.5 → hasEnoughReward=false → isReady=false → watch (grade A)
    const result = getValueDecision({ row: makeRow({ risk_reward_ratio: 1.4 }) })
    expect(result.kind).not.toBe('ready')
  })

  it('ready badge class contains emerald', () => {
    const result = getValueDecision({ row: makeRow() })
    expect(result.badgeClass).toContain('emerald')
    expect(result.panelClass).toContain('emerald')
  })

  it('grade C (not in GOOD_GRADES) blocks isReady even with high score', () => {
    const result = getValueDecision({ row: makeRow({ conviction_grade: 'C', value_score: 90 }) })
    // Not ready; with score 90 ≥ 60 → watch
    expect(result.kind).toBe('watch')
  })

  it('missing grade blocks isReady', () => {
    const result = getValueDecision({ row: makeRow({ conviction_grade: undefined, value_score: 90 }) })
    // Empty string after toUpperCase — not in GOOD_GRADES → not isReady → watch (score ≥ 60)
    expect(result.kind).toBe('watch')
  })

  it('null value_score defaults to 0 and fails isReady', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: undefined as unknown as number, conviction_grade: 'A' }),
    })
    // score defaults to 0 → not ≥ 65 → not isReady; grade A → watch
    expect(result.kind).toBe('watch')
  })
})

// ---------------------------------------------------------------------------
// READY — hasEntry secondary path
// ---------------------------------------------------------------------------

describe('getValueDecision — ready via hasEntry', () => {
  it('returns ready when hasEntry=true, score≥60, good upside', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 60, conviction_grade: 'C', analyst_upside_pct: 15 }),
      hasEntry: true,
    })
    expect(result.kind).toBe('ready')
  })

  it('hasEntry with score exactly 60 qualifies (boundary)', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 60, conviction_grade: 'D' }),
      hasEntry: true,
    })
    expect(result.kind).toBe('ready')
  })

  it('hasEntry with score 59 does NOT qualify for ready (falls to watch)', () => {
    // regression: 59 < 60 → not ready via hasEntry path; but hasEntry=true → watch
    const result = getValueDecision({
      row: makeRow({ value_score: 59, conviction_grade: 'D' }),
      hasEntry: true,
    })
    expect(result.kind).toBe('watch')
  })

  it('hasEntry + score≥60 + bad upside does NOT qualify for ready', () => {
    // regression: upside 5 → hasGoodUpside=false → entry path blocked
    const result = getValueDecision({
      row: makeRow({ value_score: 65, conviction_grade: 'C', analyst_upside_pct: 5 }),
      hasEntry: true,
    })
    // Not ready (hasGoodUpside=false); grade C, score 65 ≥ 60, hasEntry → watch
    expect(result.kind).toBe('watch')
  })

  it('hasEntry with upside null (good upside) qualifies for ready', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 62, conviction_grade: 'D', analyst_upside_pct: undefined }),
      hasEntry: true,
    })
    expect(result.kind).toBe('ready')
  })
})

// ---------------------------------------------------------------------------
// WATCH
// ---------------------------------------------------------------------------

describe('getValueDecision — watch', () => {
  it('returns watch when score is exactly 60 with bad grade and no flags', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 60, conviction_grade: 'C', risk_reward_ratio: 1.4 }),
    })
    // isReady blocked by rr < 1.5; score ≥ 60 → watch
    expect(result.kind).toBe('watch')
  })

  it('returns watch when grade is A but score < 65 (fails isReady)', () => {
    const result = getValueDecision({ row: makeRow({ value_score: 50, conviction_grade: 'A' }) })
    expect(result.kind).toBe('watch')
  })

  it('returns watch when hasSmartMoney is true and score < 60 and bad grade', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 30, conviction_grade: 'D' }),
      hasSmartMoney: true,
    })
    expect(result.kind).toBe('watch')
  })

  it('returns watch when hasSqueeze is true and score < 60 and bad grade', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 20, conviction_grade: 'F' }),
      hasSqueeze: true,
    })
    expect(result.kind).toBe('watch')
  })

  it('returns watch when hasEntry is true (score < 60)', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 45, conviction_grade: 'D' }),
      hasEntry: true,
    })
    expect(result.kind).toBe('watch')
  })

  it('watch badge class contains sky', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 60, conviction_grade: 'C', risk_reward_ratio: 1.0 }),
    })
    expect(result.badgeClass).toContain('sky')
    expect(result.panelClass).toContain('sky')
  })

  it('watch label is Vigilar', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 60, conviction_grade: 'C', risk_reward_ratio: 1.0 }),
    })
    expect(result.label).toBe('Vigilar')
  })
})

// ---------------------------------------------------------------------------
// WAIT (default — no signal)
// ---------------------------------------------------------------------------

describe('getValueDecision — wait (default)', () => {
  it('returns wait when score is low, grade is bad, and no flags are set', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 30, conviction_grade: 'D' }),
    })
    expect(result.kind).toBe('wait')
    expect(result.label).toBe('Esperar')
    expect(result.headline).toContain('señal')
  })

  it('wait badge class does NOT contain red/amber/sky/emerald', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 10, conviction_grade: 'F' }),
    })
    expect(result.badgeClass).not.toMatch(/red|amber|sky|emerald/)
  })

  it('score 59 and no grade and no flags defaults to wait', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: 59, conviction_grade: undefined }),
    })
    expect(result.kind).toBe('wait')
  })
})

// ---------------------------------------------------------------------------
// Priority ordering — compound scenarios
// ---------------------------------------------------------------------------

describe('getValueDecision — priority ordering', () => {
  it('EXIT > TRAP > bad upside > nearEarnings > isReady', () => {
    // A "perfect" row except it has all warning flags set
    const result = getValueDecision({
      row: makeRow({ analyst_upside_pct: -5, days_to_earnings: 3, cerebro_signal: 'TRAP' }),
      hasExit: true,
    })
    expect(result.kind).toBe('avoid')
    expect(result.headline).toContain('señal de salida')
  })

  it('TRAP wins over bad upside', () => {
    const result = getValueDecision({
      row: makeRow({ analyst_upside_pct: -5, cerebro_signal: 'TRAP' }),
    })
    expect(result.headline).toContain('trampa')
  })

  it('bad upside wins over nearEarnings', () => {
    const result = getValueDecision({
      row: makeRow({ analyst_upside_pct: -10, days_to_earnings: 2 }),
    })
    expect(result.headline).toContain('potencial')
  })

  it('nearEarnings wins over isReady', () => {
    // Even a score=80 A-grade stock should wait if earnings in 5 days
    const result = getValueDecision({
      row: makeRow({ value_score: 80, conviction_grade: 'A', days_to_earnings: 5 }),
    })
    expect(result.kind).toBe('wait')
    expect(result.headline).toContain('Resultados')
  })
})

// ---------------------------------------------------------------------------
// Edge cases — boundary values and null-safety
// ---------------------------------------------------------------------------

describe('getValueDecision — edge cases', () => {
  it('upside between 0 and 10 (exclusive) is NOT bad but IS not good', () => {
    // regression: upside=5 → hasBadUpside=false (not < 0), hasGoodUpside=false (not ≥ 10)
    // → isReady=false; grade A, score 70 ≥ 60 → watch
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: 5 }) })
    expect(result.kind).toBe('watch')
  })

  it('upside exactly 10 is "good" (boundary inclusive)', () => {
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: 10 }) })
    expect(result.kind).toBe('ready')
  })

  it('upside -0.001 is considered bad (just below zero)', () => {
    const result = getValueDecision({ row: makeRow({ analyst_upside_pct: -0.001 }) })
    expect(result.kind).toBe('avoid')
  })

  it('days_to_earnings exactly 7 triggers nearEarnings (boundary inclusive)', () => {
    const result = getValueDecision({ row: makeRow({ days_to_earnings: 7 }) })
    expect(result.kind).toBe('wait')
  })

  it('days_to_earnings 8 does NOT trigger nearEarnings', () => {
    const result = getValueDecision({ row: makeRow({ days_to_earnings: 8 }) })
    expect(result.kind).toBe('ready')
  })

  it('rr exactly 1.5 qualifies as enough reward (boundary inclusive)', () => {
    const result = getValueDecision({ row: makeRow({ risk_reward_ratio: 1.5 }) })
    expect(result.kind).toBe('ready')
  })

  it('rr 1.49 does not qualify (blocks isReady, falls to watch)', () => {
    const result = getValueDecision({ row: makeRow({ risk_reward_ratio: 1.49 }) })
    expect(result.kind).toBe('watch')
  })

  it('value_score defaults to 0 when undefined/null', () => {
    const result = getValueDecision({
      row: makeRow({ value_score: null as unknown as number }),
    })
    // score 0 → not ≥ 60 for watch either; grade A is in GOOD_GRADES → watch
    expect(result.kind).toBe('watch')
  })

  it('all optional flags default to false (no extra watch/ready boost)', () => {
    const result = getValueDecision({ row: makeRow({ value_score: 30, conviction_grade: 'D' }) })
    // Explicitly no flags passed → should be wait
    expect(result.kind).toBe('wait')
  })

  it('cerebro_signal value other than EXIT/TRAP has no special effect', () => {
    const result = getValueDecision({ row: makeRow({ cerebro_signal: 'BUY' }) })
    // Normal evaluation — good row → ready
    expect(result.kind).toBe('ready')
  })

  it('returns a complete ValueDecision shape for every kind', () => {
    const cases: Array<Parameters<typeof getValueDecision>[0]> = [
      { row: makeRow(), hasExit: true },                           // avoid
      { row: makeRow(), hasTrap: true },                           // avoid
      { row: makeRow({ analyst_upside_pct: -1 }) },                // avoid
      { row: makeRow({ days_to_earnings: 3 }) },                   // wait
      { row: makeRow() },                                          // ready
      { row: makeRow({ value_score: 60, conviction_grade: 'C', risk_reward_ratio: 1.4 }) }, // watch
      { row: makeRow({ value_score: 20, conviction_grade: 'F' }) }, // wait (default)
    ]

    for (const input of cases) {
      const result = getValueDecision(input)
      expect(result).toHaveProperty('kind')
      expect(result).toHaveProperty('label')
      expect(result).toHaveProperty('headline')
      expect(result).toHaveProperty('detail')
      expect(result).toHaveProperty('badgeClass')
      expect(result).toHaveProperty('panelClass')
      expect(['ready', 'watch', 'wait', 'avoid']).toContain(result.kind)
    }
  })
})
