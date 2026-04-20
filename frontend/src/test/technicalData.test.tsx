import { renderHook, waitFor, act } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  getTechnicalCache,
  resetTechnicalCache,
  subscribeToTechnicalData,
} from '@/hooks/useTechnicalData'
import { useTechnicalSignals } from '@/hooks/useTechnicalSignals'
import { useTechnicalSummaryMap } from '@/hooks/useTechnicalSummaryMap'

const fetchTechnicalSignalsMock = vi.fn()

vi.mock('@/api/client', () => ({
  fetchTechnicalSignals: () => fetchTechnicalSignalsMock(),
}))

const technicalPayload = {
  signals: [
    {
      ticker: 'AAPL',
      company_name: 'Apple',
      source: 'scanner',
      signal_name: 'Breakout',
      direction: 'BULLISH',
      timeframe: 'DAILY',
      triggered_date: '2026-04-18',
      days_ago: 1,
      description: 'Fresh breakout',
      strength: 82,
    },
    {
      ticker: 'MSFT',
      company_name: 'Microsoft',
      source: 'scanner',
      signal_name: 'Reclaim',
      direction: 'BULLISH',
      timeframe: 'WEEKLY',
      triggered_date: '2026-04-17',
      days_ago: 2,
      description: 'Reclaim',
      strength: 70,
    },
  ],
  summary: [
    {
      ticker: 'AAPL',
      company_name: 'Apple',
      source: 'scanner',
      sector: 'Technology',
      bullish_count: 2,
      bearish_count: 0,
      net_signals: 2,
      net_score: 50,
      bias: 'BULLISH',
      top_bullish_signal: 'Breakout',
      top_bearish_signal: 'None',
      most_recent_signal: 'Breakout',
      generated_at: '2026-04-18T08:00:00Z',
    },
  ],
}

describe('technical data cache and hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
    resetTechnicalCache()
    fetchTechnicalSignalsMock.mockResolvedValue(technicalPayload)
  })

  it('loads technical data once and caches it for subscribers', async () => {
    const callback = vi.fn()

    subscribeToTechnicalData(callback)

    await waitFor(() => {
      expect(callback).toHaveBeenCalledWith(technicalPayload)
    })

    expect(getTechnicalCache()).toEqual(technicalPayload)
    expect(fetchTechnicalSignalsMock).toHaveBeenCalledTimes(1)
  })

  it('serves cached data asynchronously to later subscribers', async () => {
    const first = vi.fn()
    subscribeToTechnicalData(first)

    await waitFor(() => {
      expect(first).toHaveBeenCalledWith(technicalPayload)
    })

    vi.useFakeTimers()
    const second = vi.fn()
    subscribeToTechnicalData(second)

    expect(second).not.toHaveBeenCalled()

    act(() => {
      vi.runAllTimers()
    })

    expect(second).toHaveBeenCalledWith(technicalPayload)
  })

  it('filters technical signals by ticker in the hook', async () => {
    const { result } = renderHook(() => useTechnicalSignals('AAPL'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.signals).toHaveLength(1)
    expect(result.current.signals[0].ticker).toBe('AAPL')
    expect(result.current.summary?.ticker).toBe('AAPL')
  })

  it('builds a summary map keyed by ticker', async () => {
    const { result } = renderHook(() => useTechnicalSummaryMap())

    await waitFor(() => {
      expect(result.current.AAPL).toBeDefined()
    })

    expect(result.current.AAPL.net_score).toBe(50)
  })

  it('stops retrying after a failed load', async () => {
    fetchTechnicalSignalsMock.mockRejectedValueOnce(new Error('network'))
    const callback = vi.fn()

    subscribeToTechnicalData(callback)

    await waitFor(() => {
      expect(fetchTechnicalSignalsMock).toHaveBeenCalledTimes(1)
    })

    subscribeToTechnicalData(vi.fn())

    expect(fetchTechnicalSignalsMock).toHaveBeenCalledTimes(1)
    expect(callback).not.toHaveBeenCalled()
  })
})
