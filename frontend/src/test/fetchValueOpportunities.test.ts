import { beforeEach, describe, expect, it, vi } from 'vitest'

// ── Module-level mocks (hoisted before any import) ────────────────────────────

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
      interceptors: { request: { use: requestUse } },
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

// ── Helpers ───────────────────────────────────────────────────────────────────

const FILTERED_CSV = [
  'ticker,company_name,current_price,value_score',
  'AAPL,Apple Inc,190,85',
  'MSFT,Microsoft Corp,420,78',
  'GOOG,Alphabet Inc,175,72',
].join('\n')

const CONVICTION_CSV = [
  'ticker,conviction_grade,conviction_score,conviction_reasons,conviction_positives,conviction_red_flags',
  'AAPL,A,92,Strong FCF,3,0',
  'MSFT,B+,81,Solid moat,2,1',
].join('\n')

const FALLBACK_CSV = [
  'ticker,company_name,current_price,value_score',
  'AAPL,Apple Inc,188,80',
  'TSLA,Tesla Inc,200,60',
].join('\n')

function makeOkResponse(body: string) {
  return Promise.resolve(new Response(body, { status: 200 }))
}

function makeErrorResponse(status = 404) {
  return Promise.resolve(new Response('', { status }))
}

async function loadClient() {
  vi.resetModules()
  return import('@/api/client')
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('fetchValueOpportunities', () => {
  beforeEach(() => {
    vi.unstubAllEnvs()
    vi.clearAllMocks()

    onAuthStateChange.mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } })
    refreshSession.mockResolvedValue({ data: { session: null } })

    vi.stubGlobal('fetch', vi.fn())
    vi.stubGlobal('open', vi.fn())
    window.open = vi.fn()
  })

  // ── 1. Filtered CSV loads all tickers ──────────────────────────────────────

  it('returns all tickers from value_opportunities_filtered.csv', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('value_opportunities_filtered.csv')) return makeOkResponse(FILTERED_CSV)
      if (url.endsWith('value_conviction.csv')) return makeOkResponse(CONVICTION_CSV)
      return makeErrorResponse()
    })

    const { fetchValueOpportunities } = await loadClient()
    const result = await fetchValueOpportunities()

    expect(result.data.data).toHaveLength(3)
    expect(result.data.data.map((r) => r.ticker)).toEqual(['AAPL', 'MSFT', 'GOOG'])
  })

  // ── 2. Conviction grades merged for matching tickers ──────────────────────

  it('merges conviction grades from value_conviction.csv for matching tickers', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('value_opportunities_filtered.csv')) return makeOkResponse(FILTERED_CSV)
      if (url.endsWith('value_conviction.csv')) return makeOkResponse(CONVICTION_CSV)
      return makeErrorResponse()
    })

    const { fetchValueOpportunities } = await loadClient()
    const result = await fetchValueOpportunities()

    const aapl = result.data.data.find((r) => r.ticker === 'AAPL')
    const msft = result.data.data.find((r) => r.ticker === 'MSFT')

    expect(aapl?.conviction_grade).toBe('A')
    expect(aapl?.conviction_score).toBe(92)
    expect(msft?.conviction_grade).toBe('B+')
    expect(msft?.conviction_score).toBe(81)
  })

  // ── 3. Tickers NOT in conviction.csv keep original data unchanged ──────────

  it('keeps original data for tickers absent from conviction.csv', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('value_opportunities_filtered.csv')) return makeOkResponse(FILTERED_CSV)
      if (url.endsWith('value_conviction.csv')) return makeOkResponse(CONVICTION_CSV)
      return makeErrorResponse()
    })

    const { fetchValueOpportunities } = await loadClient()
    const result = await fetchValueOpportunities()

    const goog = result.data.data.find((r) => r.ticker === 'GOOG')
    expect(goog).toBeDefined()
    expect(goog?.value_score).toBe(72)
    // No conviction grade was in the conviction CSV for GOOG — fields absent in CSV come through as undefined
    expect(goog?.conviction_grade).toBeUndefined()
    expect(goog?.conviction_score).toBeUndefined()
  })

  // ── 4. conviction.csv fetch failure → all tickers still returned ───────────

  it('returns all tickers even when conviction.csv fetch fails (no crash)', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('value_opportunities_filtered.csv')) return makeOkResponse(FILTERED_CSV)
      if (url.endsWith('value_conviction.csv')) return makeErrorResponse(500)
      return makeErrorResponse()
    })

    const { fetchValueOpportunities } = await loadClient()
    const result = await fetchValueOpportunities()

    // All 3 tickers returned despite conviction fetch failure
    expect(result.data.data).toHaveLength(3)
    expect(result.data.data.map((r) => r.ticker)).toEqual(['AAPL', 'MSFT', 'GOOG'])
  })

  it('returns all tickers even when conviction.csv fetch throws a network error', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('value_opportunities_filtered.csv')) return makeOkResponse(FILTERED_CSV)
      if (url.endsWith('value_conviction.csv')) return Promise.reject(new Error('network error'))
      return makeErrorResponse()
    })

    const { fetchValueOpportunities } = await loadClient()
    const result = await fetchValueOpportunities()

    expect(result.data.data).toHaveLength(3)
  })

  // ── 5. filtered.csv failure → falls back to value_opportunities.csv ────────

  it('falls back to value_opportunities.csv when filtered.csv fails', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('value_opportunities_filtered.csv')) return makeErrorResponse(404)
      if (url.endsWith('value_opportunities.csv')) return makeOkResponse(FALLBACK_CSV)
      if (url.endsWith('value_conviction.csv')) return makeErrorResponse(404)
      return makeErrorResponse()
    })

    const { fetchValueOpportunities } = await loadClient()
    const result = await fetchValueOpportunities()

    expect(result.data.data).toHaveLength(2)
    expect(result.data.data.map((r) => r.ticker)).toEqual(['AAPL', 'TSLA'])
    expect(result.data.source).toBe('github-pages')
  })

  it('falls back to value_opportunities.csv when filtered.csv throws', async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('value_opportunities_filtered.csv'))
        return Promise.reject(new Error('network down'))
      if (url.endsWith('value_opportunities.csv')) return makeOkResponse(FALLBACK_CSV)
      if (url.endsWith('value_conviction.csv')) return makeErrorResponse(404)
      return makeErrorResponse()
    })

    const { fetchValueOpportunities } = await loadClient()
    const result = await fetchValueOpportunities()

    expect(result.data.data).toHaveLength(2)
    expect(result.data.data.map((r) => r.ticker)).toEqual(['AAPL', 'TSLA'])
  })

  // ── 6. Both CSVs fail → falls through to Railway API ──────────────────────

  it('falls through to the Railway API when both CSVs are unavailable', async () => {
    vi.mocked(fetch).mockImplementation(() => makeErrorResponse(503))

    axiosGet.mockResolvedValue({
      data: {
        data: [{ ticker: 'IBM', company_name: 'IBM Corp', current_price: 150, value_score: 65 }],
        count: 1,
        source: 'api',
      },
    })

    const { fetchValueOpportunities } = await loadClient()
    const result = await fetchValueOpportunities()

    expect(result.data.data[0].ticker).toBe('IBM')
    expect(result.data.source).toBe('api')
  })
})
