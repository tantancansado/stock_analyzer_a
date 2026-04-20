import { beforeEach, describe, expect, it, vi } from 'vitest'

const axiosGet = vi.fn()
const axiosPost = vi.fn()
const requestUse = vi.fn()
const onAuthStateChange = vi.fn()
const refreshSession = vi.fn()

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: axiosGet,
      post: axiosPost,
      interceptors: {
        request: {
          use: requestUse,
        },
      },
    })),
  },
}))

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      onAuthStateChange,
      refreshSession,
    },
  },
}))

async function loadClient() {
  vi.resetModules()
  return import('@/api/client')
}

describe('api/client module', () => {
  beforeEach(() => {
    vi.unstubAllEnvs()
    vi.clearAllMocks()

    onAuthStateChange.mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } })
    refreshSession.mockResolvedValue({ data: { session: null } })

    vi.stubGlobal('fetch', vi.fn())
    vi.stubGlobal('open', vi.fn())
    window.open = vi.fn()
  })

  it('returns the dev CSV url when VITE_CSV_BASE is not set', async () => {
    const { getCsvUrl } = await loadClient()

    expect(getCsvUrl('fundamental')).toBe('/api/download/fundamental')
    expect(getCsvUrl('unknown-dataset')).toBe('')
  })

  it('returns the production CSV url when VITE_CSV_BASE is set', async () => {
    vi.stubEnv('VITE_CSV_BASE', 'https://static.example.com')
    const { getCsvUrl } = await loadClient()

    expect(getCsvUrl('value-us')).toBe('https://static.example.com/value_opportunities.csv')
  })

  it('opens CSV downloads through the local API in development', async () => {
    const { downloadCsv } = await loadClient()

    downloadCsv('fundamental')

    expect(window.open).toHaveBeenCalledWith('/api/download/fundamental', '_blank')
  })

  it('opens CSV downloads through the static base in production', async () => {
    vi.stubEnv('VITE_CSV_BASE', 'https://static.example.com')
    const { downloadCsv } = await loadClient()

    downloadCsv('fundamental-eu')

    expect(window.open).toHaveBeenCalledWith(
      'https://static.example.com/european_fundamental_scores.csv',
      '_blank',
    )
  })

  it('builds a ticker-sector map from development CSV endpoints', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/download/fundamental-eu')) {
        return Promise.resolve(new Response('ticker,sector\nSAP.DE,Enterprise Software'))
      }
      if (url.endsWith('/api/download/fundamental')) {
        return Promise.resolve(new Response('ticker,sector\nAAPL,Tech\nMSFT,Software'))
      }
      return Promise.resolve(new Response('', { status: 404 }))
    })

    const { fetchTickerSectorMap } = await loadClient()
    const result = await fetchTickerSectorMap()

    expect(result).toEqual({
      AAPL: 'Tech',
      MSFT: 'Software',
      'SAP.DE': 'Enterprise Software',
    })
  })

  it('parses technical signals CSVs from the static base', async () => {
    vi.stubEnv('VITE_CSV_BASE', 'https://static.example.com')
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/technical_signals.csv')) {
        return Promise.resolve(
          new Response(
            'ticker,company_name,source,signal_name,direction,timeframe,triggered_date,days_ago,description,strength\nAAPL,Apple,scanner,Breakout,BULLISH,DAILY,2026-04-10,3,Fresh breakout,87',
          ),
        )
      }
      if (url.endsWith('/technical_signals_summary.csv')) {
        return Promise.resolve(
          new Response(
            'ticker,company_name,source,sector,bullish_count,bearish_count,net_signals,net_score,bias,top_bullish_signal,top_bearish_signal,most_recent_signal,generated_at\nAAPL,Apple,scanner,Technology,4,1,3,88,BULLISH,Breakout,None,Breakout,2026-04-10T08:00:00Z',
          ),
        )
      }
      return Promise.resolve(new Response('', { status: 404 }))
    })

    const { fetchTechnicalSignals } = await loadClient()
    const result = await fetchTechnicalSignals()

    expect(result.signals[0]).toMatchObject({
      ticker: 'AAPL',
      days_ago: 3,
      strength: 87,
    })
    expect(result.summary[0]).toMatchObject({
      ticker: 'AAPL',
      bullish_count: 4,
      net_score: 88,
    })
  })

  it('returns local API technical signals in development', async () => {
    axiosGet.mockResolvedValue({
      data: {
        signals: [{ ticker: 'AAPL', days_ago: 1, strength: 70 }],
        summary: [{ ticker: 'AAPL', bullish_count: 2, bearish_count: 0, net_signals: 2, net_score: 50 }],
      },
    })

    const { fetchTechnicalSignals } = await loadClient()
    const result = await fetchTechnicalSignals()

    expect(axiosGet).toHaveBeenCalledWith('/api/technical-signals')
    expect(result.signals).toHaveLength(1)
    expect(result.summary).toHaveLength(1)
  })

  it('returns empty prices when no tickers are requested', async () => {
    const { fetchPortfolioPrices } = await loadClient()

    await expect(fetchPortfolioPrices([])).resolves.toEqual({})
    expect(axiosPost).not.toHaveBeenCalled()
  })

  it('returns API portfolio prices when the request succeeds', async () => {
    axiosPost.mockResolvedValue({ data: { prices: { AAPL: 190.5, MSFT: 420.1 } } })

    const { fetchPortfolioPrices } = await loadClient()
    const result = await fetchPortfolioPrices(['AAPL', 'MSFT'])

    expect(axiosPost).toHaveBeenCalledWith('/api/portfolio-prices', { tickers: ['AAPL', 'MSFT'] })
    expect(result).toEqual({ AAPL: 190.5, MSFT: 420.1 })
  })

  it('returns empty prices when the portfolio price request fails', async () => {
    axiosPost.mockRejectedValue(new Error('boom'))

    const { fetchPortfolioPrices } = await loadClient()

    await expect(fetchPortfolioPrices(['AAPL'])).resolves.toEqual({})
  })
})
