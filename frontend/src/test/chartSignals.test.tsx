import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchChartSignalsMock = vi.fn()

vi.mock('@/api/client', () => ({
  fetchChartSignals: () => fetchChartSignalsMock(),
}))

async function loadModule() {
  vi.resetModules()
  return import('@/hooks/useChartSignals')
}

describe('useChartSignals', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchChartSignalsMock.mockResolvedValue({
      AAPL: {
        ticker: 'AAPL',
        entry_quality: 'ideal',
        trend_direction: 'uptrend',
        above_200ma: true,
        above_150ma: true,
        base_forming: true,
        base_type: 'cup',
        base_weeks: 7,
        volume_dryup_visible: true,
        volume_breakout: true,
        extended_from_base: false,
        distribution_signs: false,
        risk_level: 'low',
        confidence: 'high',
        entry_rationale: 'Strong setup',
        notes: null,
        analyzed_at: '2026-04-18',
        model: 'test',
      },
    })
  })

  it('loads and exposes cached chart signals', async () => {
    const { useChartSignals } = await loadModule()
    const { result } = renderHook(() => useChartSignals())

    await waitFor(() => {
      expect(result.current.AAPL).toBeDefined()
    })

    expect(result.current.AAPL.entry_quality).toBe('ideal')
    expect(fetchChartSignalsMock).toHaveBeenCalledTimes(1)
  })

  it('reuses the module cache for later hook mounts', async () => {
    const { useChartSignals } = await loadModule()
    const first = renderHook(() => useChartSignals())

    await waitFor(() => {
      expect(first.result.current.AAPL).toBeDefined()
    })

    const second = renderHook(() => useChartSignals())
    expect(second.result.current.AAPL).toBeDefined()
    expect(fetchChartSignalsMock).toHaveBeenCalledTimes(1)
  })
})
