import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMeanReversionMock = vi.fn()
const fetchUnusualFlowMock = vi.fn()

vi.mock('@/api/client', () => ({
  fetchMeanReversion: () => fetchMeanReversionMock(),
  fetchUnusualFlow: () => fetchUnusualFlowMock(),
}))

async function loadModule() {
  vi.resetModules()
  return import('@/hooks/usePortfolioConfluence')
}

describe('usePortfolioConfluence', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('european_value_opportunities_filtered.csv')) {
        return Promise.resolve(new Response('ticker\nSAP.DE\n'))
      }
      if (url.includes('value_opportunities_filtered.csv')) {
        return Promise.resolve(new Response('ticker\nAAPL\n'))
      }
      return Promise.resolve(new Response('', { status: 404 }))
    }))

    fetchMeanReversionMock.mockResolvedValue({
      data: {
        opportunities: [
          {
            ticker: 'AAPL',
            strategy: 'Oversold Bounce',
            rsi: 25,
            bounce_confidence: 55,
            dark_pool_signal: 'ACCUMULATION',
            current_price: 180,
            risk_reward: 2,
          },
        ],
      },
    })

    fetchUnusualFlowMock.mockResolvedValue({
      data: {
        results: [
          {
            ticker: 'AAPL',
            signal: 'BULLISH',
            flow_interpretation: 'STANDARD',
            total_premium: 100000,
          },
          {
            ticker: 'SAP.DE',
            signal: 'NEUTRAL',
            flow_interpretation: 'PUT_COVERING',
            total_premium: 26000,
          },
        ],
      },
    })
  })

  it('builds the confluence map from bounce, value, and flow sources', async () => {
    const { usePortfolioConfluence } = await loadModule()
    const { result } = renderHook(() => usePortfolioConfluence())

    await waitFor(() => {
      expect(result.current.AAPL).toBeDefined()
    })

    expect(result.current.AAPL).toEqual({
      bounce: true,
      value: true,
      flow: 'BULLISH',
    })
    expect(result.current['SAP.DE']).toEqual({
      bounce: false,
      value: true,
      flow: 'PUT_COVERING',
    })
  })

  it('reuses the session cache across hook mounts', async () => {
    const { usePortfolioConfluence } = await loadModule()
    const first = renderHook(() => usePortfolioConfluence())

    await waitFor(() => {
      expect(first.result.current.AAPL).toBeDefined()
    })

    const second = renderHook(() => usePortfolioConfluence())
    expect(second.result.current.AAPL.value).toBe(true)
    expect(fetchMeanReversionMock).toHaveBeenCalledTimes(1)
    expect(fetchUnusualFlowMock).toHaveBeenCalledTimes(1)
  })
})
