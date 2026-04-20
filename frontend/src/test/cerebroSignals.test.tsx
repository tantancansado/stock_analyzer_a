import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = {
  fetchCerebroValueTraps: vi.fn(),
  fetchCerebroSmartMoney: vi.fn(),
  fetchCerebroExitSignals: vi.fn(),
  fetchCerebroDividendSafety: vi.fn(),
  fetchCerebroPiotroski: vi.fn(),
  fetchCerebroShortSqueeze: vi.fn(),
  fetchCerebroQualityDecay: vi.fn(),
  fetchCerebroSectorRV: vi.fn(),
  fetchCerebroEntrySignals: vi.fn(),
}

vi.mock('@/api/client', () => mocks)

async function loadModule() {
  vi.resetModules()
  return import('@/hooks/useCerebroSignals')
}

describe('useCerebroSignals', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.fetchCerebroValueTraps.mockResolvedValue({ data: { traps: [{ ticker: 'AAPL', severity: 'HIGH', trap_score: 90, flags: ['debt'] }] } })
    mocks.fetchCerebroSmartMoney.mockResolvedValue({ data: { signals: [{ ticker: 'AAPL', n_hedge_funds: 4, n_insiders: 2, convergence_score: 88 }] } })
    mocks.fetchCerebroExitSignals.mockResolvedValue({ data: { exits: [{ ticker: 'MSFT', severity: 'LOW', reasons: ['weakness'] }] } })
    mocks.fetchCerebroDividendSafety.mockResolvedValue({ data: { dividends: [{ ticker: 'T', rating: 'WATCH', safety_score: 55, div_yield: 6.4 }] } })
    mocks.fetchCerebroPiotroski.mockResolvedValue({ data: { candidates: [{ ticker: 'SAP', trend: 'IMPROVING', piotroski_current: 8, delta: 1, signal: 'STRONG' }] } })
    mocks.fetchCerebroShortSqueeze.mockResolvedValue({ data: { setups: [{ ticker: 'GME', severity: 'HIGH', squeeze_score: 91, short_pct_float: 20, flags: ['float'] }] } })
    mocks.fetchCerebroQualityDecay.mockResolvedValue({ data: { decays: [{ ticker: 'INTC', severity: 'MEDIUM', decay_score: 60, flags: ['margin'] }] } })
    mocks.fetchCerebroSectorRV.mockResolvedValue({ data: { standouts: [{ ticker: 'AAPL', label: 'BEST_IN_SECTOR', fcf_yield_pct: 4.2, fcf_rank: 1, fcf_rank_of: 10, sector: 'Tech' }] } })
    mocks.fetchCerebroEntrySignals.mockResolvedValue({ data: { signals: [{ ticker: 'AAPL', signal: 'BUY', entry_score: 77 }] } })
  })

  it('aggregates the cerebro maps from the fetched endpoints', async () => {
    const { useCerebroSignals } = await loadModule()
    const { result } = renderHook(() => useCerebroSignals())

    await waitFor(() => {
      expect(result.current.trapMap.AAPL).toBeDefined()
    })

    expect(result.current.trapMap.AAPL.trap_score).toBe(90)
    expect(result.current.smMap.AAPL.convergence_score).toBe(88)
    expect(result.current.exitMap.MSFT.severity).toBe('LOW')
    expect(result.current.divMap.T.rating).toBe('WATCH')
    expect(result.current.piotrMap.SAP.piotroski_current).toBe(8)
    expect(result.current.squeezeMap.GME.squeeze_score).toBe(91)
    expect(result.current.sectorMap.AAPL.label).toBe('BEST_IN_SECTOR')
    expect(result.current.entryMap.AAPL.signal).toBe('BUY')
  })

  it('keeps only qualifying dividend and entry signals', async () => {
    mocks.fetchCerebroDividendSafety.mockResolvedValue({
      data: { dividends: [{ ticker: 'SAFE', rating: 'SAFE', safety_score: 99, div_yield: 2.1 }] },
    })
    mocks.fetchCerebroEntrySignals.mockResolvedValue({
      data: { signals: [{ ticker: 'WAIT', signal: 'MONITOR', entry_score: 40 }] },
    })

    const { useCerebroSignals } = await loadModule()
    const { result } = renderHook(() => useCerebroSignals())

    await waitFor(() => {
      expect(result.current.trapMap.AAPL).toBeDefined()
    })

    expect(result.current.divMap.SAFE).toBeUndefined()
    expect(result.current.entryMap.WAIT).toBeUndefined()
  })
})
