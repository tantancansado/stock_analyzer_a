import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// ── Mock shape required by useCerebroSignals ─────────────────────────────────
const mocks = {
  fetchCerebroValueTraps:    vi.fn(),
  fetchCerebroSmartMoney:    vi.fn(),
  fetchCerebroExitSignals:   vi.fn(),
  fetchCerebroDividendSafety: vi.fn(),
  fetchCerebroPiotroski:     vi.fn(),
  fetchCerebroShortSqueeze:  vi.fn(),
  fetchCerebroQualityDecay:  vi.fn(),
  fetchCerebroSectorRV:      vi.fn(),
  fetchCerebroEntrySignals:  vi.fn(),
}

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      interceptors: { request: { use: vi.fn() } },
    })),
  },
}))

vi.mock('@/lib/supabase', () => ({
  supabase: { auth: { onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })), refreshSession: vi.fn() } },
}))

vi.mock('@/api/client', () => mocks)

// Re-import the module fresh each test so the module-level _cache / _promise
// are reset and do not bleed across tests.
async function loadHook() {
  vi.resetModules()
  // After resetModules the vi.mock() factory still applies but the module
  // instance is new, so _cache and _promise start as null again.
  return import('@/hooks/useCerebroSignals')
}

// Default happy-path data
function defaultMocks() {
  mocks.fetchCerebroValueTraps.mockResolvedValue({
    data: { traps: [{ ticker: 'AAPL', severity: 'HIGH', trap_score: 90, flags: ['debt'] }] },
  })
  mocks.fetchCerebroSmartMoney.mockResolvedValue({
    data: { signals: [{ ticker: 'MSFT', n_hedge_funds: 3, n_insiders: 1, convergence_score: 75 }] },
  })
  mocks.fetchCerebroExitSignals.mockResolvedValue({
    data: { exits: [{ ticker: 'T', severity: 'HIGH', reasons: ['weakness', 'distribution'] }] },
  })
  mocks.fetchCerebroDividendSafety.mockResolvedValue({
    data: { dividends: [{ ticker: 'VZ', rating: 'AT_RISK', safety_score: 40, div_yield: 7.1 }] },
  })
  mocks.fetchCerebroPiotroski.mockResolvedValue({
    data: { candidates: [{ ticker: 'SAP', trend: 'IMPROVING', piotroski_current: 8, delta: 1, signal: 'STRONG' }] },
  })
  mocks.fetchCerebroShortSqueeze.mockResolvedValue({
    data: { setups: [{ ticker: 'GME', severity: 'HIGH', squeeze_score: 88, short_pct_float: 22, flags: ['float'] }] },
  })
  mocks.fetchCerebroQualityDecay.mockResolvedValue({
    data: { decays: [{ ticker: 'INTC', severity: 'MEDIUM', decay_score: 61, flags: ['margin'] }] },
  })
  mocks.fetchCerebroSectorRV.mockResolvedValue({
    data: { standouts: [{ ticker: 'NVDA', label: 'BEST_IN_SECTOR', fcf_yield_pct: 5.1, fcf_rank: 1, fcf_rank_of: 12, sector: 'Semiconductors' }] },
  })
  mocks.fetchCerebroEntrySignals.mockResolvedValue({
    data: { signals: [{ ticker: 'GOOG', signal: 'STRONG_BUY', entry_score: 91 }] },
  })
}

describe('useCerebroSignals', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    defaultMocks()
  })

  // ── Happy path ─────────────────────────────────────────────────────────────
  it('populates all nine maps with the correct ticker keys', async () => {
    const { useCerebroSignals } = await loadHook()
    const { result } = renderHook(() => useCerebroSignals())

    await waitFor(() => expect(result.current.trapMap.AAPL).toBeDefined())

    expect(result.current.trapMap.AAPL).toEqual({ severity: 'HIGH', trap_score: 90, flags: ['debt'] })
    expect(result.current.smMap.MSFT).toEqual({ n_hedge_funds: 3, n_insiders: 1, convergence_score: 75 })
    expect(result.current.exitMap.T).toEqual({ severity: 'HIGH', reasons: ['weakness', 'distribution'] })
    expect(result.current.divMap.VZ).toEqual({ rating: 'AT_RISK', safety_score: 40, div_yield: 7.1 })
    expect(result.current.piotrMap.SAP).toEqual({ trend: 'IMPROVING', piotroski_current: 8, delta: 1 })
    expect(result.current.squeezeMap.GME).toEqual({ severity: 'HIGH', squeeze_score: 88, short_pct_float: 22, flags: ['float'] })
    expect(result.current.decayMap.INTC).toEqual({ severity: 'MEDIUM', decay_score: 61, flags: ['margin'] })
    expect(result.current.sectorMap.NVDA).toEqual({
      label: 'BEST_IN_SECTOR', fcf_yield_pct: 5.1, fcf_rank: 1, fcf_rank_of: 12, sector: 'Semiconductors',
    })
    expect(result.current.entryMap.GOOG).toEqual({ signal: 'STRONG_BUY', entry_score: 91 })
  })

  // ── Filtering: dividends ───────────────────────────────────────────────────
  it('excludes SAFE-rated dividends from divMap', async () => {
    mocks.fetchCerebroDividendSafety.mockResolvedValue({
      data: { dividends: [
        { ticker: 'SAFE_CO', rating: 'SAFE', safety_score: 99, div_yield: 2.0 },
        { ticker: 'WATCH_CO', rating: 'WATCH', safety_score: 65, div_yield: 3.5 },
      ]},
    })

    const { useCerebroSignals } = await loadHook()
    const { result } = renderHook(() => useCerebroSignals())

    await waitFor(() => expect(result.current.trapMap.AAPL).toBeDefined())

    expect(result.current.divMap.SAFE_CO).toBeUndefined()
    expect(result.current.divMap.WATCH_CO).toBeDefined()
  })

  // ── Filtering: piotroski ───────────────────────────────────────────────────
  it('only includes IMPROVING, SLIGHT_UP, and STRONG-signal candidates in piotrMap', async () => {
    mocks.fetchCerebroPiotroski.mockResolvedValue({
      data: { candidates: [
        { ticker: 'IMP',  trend: 'IMPROVING',  piotroski_current: 7, delta: 2, signal: 'STRONG' },
        { ticker: 'SUP',  trend: 'SLIGHT_UP',  piotroski_current: 5, delta: 1, signal: 'NEUTRAL' },
        { ticker: 'STR',  trend: 'STABLE',     piotroski_current: 6, delta: 0, signal: 'STRONG' },
        { ticker: 'DET',  trend: 'DETERIORATING', piotroski_current: 3, delta: -2, signal: 'WEAK' },
      ]},
    })

    const { useCerebroSignals } = await loadHook()
    const { result } = renderHook(() => useCerebroSignals())

    await waitFor(() => expect(result.current.trapMap.AAPL).toBeDefined())

    expect(result.current.piotrMap.IMP).toBeDefined()  // trend=IMPROVING
    expect(result.current.piotrMap.SUP).toBeDefined()  // trend=SLIGHT_UP
    expect(result.current.piotrMap.STR).toBeDefined()  // signal=STRONG (even trend=STABLE)
    expect(result.current.piotrMap.DET).toBeUndefined() // neither condition met
  })

  // ── Filtering: entry signals ───────────────────────────────────────────────
  it('only includes STRONG_BUY and BUY signals in entryMap', async () => {
    mocks.fetchCerebroEntrySignals.mockResolvedValue({
      data: { signals: [
        { ticker: 'SB',  signal: 'STRONG_BUY', entry_score: 90 },
        { ticker: 'B',   signal: 'BUY',         entry_score: 70 },
        { ticker: 'MON', signal: 'MONITOR',     entry_score: 50 },
        { ticker: 'W',   signal: 'WAIT',         entry_score: 30 },
      ]},
    })

    const { useCerebroSignals } = await loadHook()
    const { result } = renderHook(() => useCerebroSignals())

    await waitFor(() => expect(result.current.trapMap.AAPL).toBeDefined())

    expect(result.current.entryMap.SB).toBeDefined()
    expect(result.current.entryMap.B).toBeDefined()
    expect(result.current.entryMap.MON).toBeUndefined()
    expect(result.current.entryMap.W).toBeUndefined()
  })

  // ── Empty responses ────────────────────────────────────────────────────────
  it('returns all empty maps when every endpoint returns an empty array', async () => {
    mocks.fetchCerebroValueTraps.mockResolvedValue({ data: { traps: [] } })
    mocks.fetchCerebroSmartMoney.mockResolvedValue({ data: { signals: [] } })
    mocks.fetchCerebroExitSignals.mockResolvedValue({ data: { exits: [] } })
    mocks.fetchCerebroDividendSafety.mockResolvedValue({ data: { dividends: [] } })
    mocks.fetchCerebroPiotroski.mockResolvedValue({ data: { candidates: [] } })
    mocks.fetchCerebroShortSqueeze.mockResolvedValue({ data: { setups: [] } })
    mocks.fetchCerebroQualityDecay.mockResolvedValue({ data: { decays: [] } })
    mocks.fetchCerebroSectorRV.mockResolvedValue({ data: { standouts: [] } })
    mocks.fetchCerebroEntrySignals.mockResolvedValue({ data: { signals: [] } })

    const { useCerebroSignals } = await loadHook()
    const { result } = renderHook(() => useCerebroSignals())

    // Give the promise time to settle
    await waitFor(() => {}, { timeout: 200 })

    // All maps must be empty objects, not crash
    expect(Object.keys(result.current.trapMap)).toHaveLength(0)
    expect(Object.keys(result.current.smMap)).toHaveLength(0)
    expect(Object.keys(result.current.exitMap)).toHaveLength(0)
    expect(Object.keys(result.current.divMap)).toHaveLength(0)
    expect(Object.keys(result.current.piotrMap)).toHaveLength(0)
    expect(Object.keys(result.current.squeezeMap)).toHaveLength(0)
    expect(Object.keys(result.current.decayMap)).toHaveLength(0)
    expect(Object.keys(result.current.sectorMap)).toHaveLength(0)
    expect(Object.keys(result.current.entryMap)).toHaveLength(0)
  })

  // ── Partial failure: some endpoints reject ─────────────────────────────────
  it('populates available maps even when some endpoints reject', async () => {
    mocks.fetchCerebroValueTraps.mockRejectedValue(new Error('network'))
    mocks.fetchCerebroSmartMoney.mockRejectedValue(new Error('timeout'))
    // The rest keep the default happy-path mocks

    const { useCerebroSignals } = await loadHook()
    const { result } = renderHook(() => useCerebroSignals())

    await waitFor(() => expect(result.current.exitMap.T).toBeDefined())

    // Failed endpoints produce empty maps — no crash
    expect(result.current.trapMap).toEqual({})
    expect(result.current.smMap).toEqual({})
    // Successful endpoints are still populated
    expect(result.current.exitMap.T).toBeDefined()
    expect(result.current.squeezeMap.GME).toBeDefined()
    expect(result.current.entryMap.GOOG).toBeDefined()
  })

  // ── Malformed data: missing array keys ────────────────────────────────────
  it('does not throw when response arrays are null or undefined', async () => {
    mocks.fetchCerebroValueTraps.mockResolvedValue({ data: { traps: null } })
    mocks.fetchCerebroSmartMoney.mockResolvedValue({ data: {} })  // signals key absent
    mocks.fetchCerebroExitSignals.mockResolvedValue({ data: { exits: undefined } })
    mocks.fetchCerebroDividendSafety.mockResolvedValue({ data: { dividends: null } })
    mocks.fetchCerebroPiotroski.mockResolvedValue({ data: {} })
    mocks.fetchCerebroShortSqueeze.mockResolvedValue({ data: { setups: undefined } })
    mocks.fetchCerebroQualityDecay.mockResolvedValue({ data: { decays: null } })
    mocks.fetchCerebroSectorRV.mockResolvedValue({ data: {} })
    mocks.fetchCerebroEntrySignals.mockResolvedValue({ data: { signals: null } })

    const { useCerebroSignals } = await loadHook()
    // Should not throw
    const { result } = renderHook(() => useCerebroSignals())

    await waitFor(() => {}, { timeout: 200 })

    // All maps must remain empty objects
    expect(result.current.trapMap).toEqual({})
    expect(result.current.smMap).toEqual({})
  })

  // ── Multiple consumers share the same cache ────────────────────────────────
  it('makes only one set of network requests when multiple hook instances mount', async () => {
    const { useCerebroSignals } = await loadHook()

    renderHook(() => useCerebroSignals())
    renderHook(() => useCerebroSignals())
    renderHook(() => useCerebroSignals())

    await waitFor(() => {}, { timeout: 300 })

    // Each fetch function should be called exactly once despite 3 consumers
    expect(mocks.fetchCerebroValueTraps).toHaveBeenCalledTimes(1)
    expect(mocks.fetchCerebroEntrySignals).toHaveBeenCalledTimes(1)
  })
})
