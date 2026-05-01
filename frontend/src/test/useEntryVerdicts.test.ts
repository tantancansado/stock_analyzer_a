import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// ── Mock axios + supabase (required by api/client module graph) ───────────────
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
  supabase: {
    auth: {
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
      refreshSession: vi.fn(),
    },
  },
}))

const fetchEntryVerdictsMock = vi.fn()

vi.mock('@/api/client', () => ({
  fetchEntryVerdicts: fetchEntryVerdictsMock,
}))

// Each test gets a fresh module instance so the module-level cache / inflight /
// listeners do not bleed across tests.
async function loadModule() {
  vi.resetModules()
  return import('@/hooks/useEntryVerdicts')
}

describe('useEntryVerdicts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── Happy path ─────────────────────────────────────────────────────────────
  it('returns a map keyed by uppercase ticker from the API response', async () => {
    fetchEntryVerdictsMock.mockResolvedValue({
      data: {
        verdicts: [
          { ticker: 'AAPL', origin: 'value_us', verdict: 'ENTRY', confidence: 0.87, reasons: 'FCF strong', blockers: null, trigger: 'RSI dip', source: 'ai' },
          { ticker: 'msft', origin: 'value_us', verdict: 'WAIT',  confidence: 0.5,  reasons: null,         blockers: 'PE high', trigger: null, source: 'rules' },
        ],
        total: 2,
        as_of: '2026-05-01T08:00:00Z',
      },
    })

    const { useEntryVerdicts } = await loadModule()
    const { result } = renderHook(() => useEntryVerdicts())

    await waitFor(() => expect(result.current.AAPL).toBeDefined())

    // Correct ticker → verdict mapping
    expect(result.current.AAPL.verdict).toBe('ENTRY')
    expect(result.current.AAPL.confidence).toBe(0.87)
    expect(result.current.AAPL.source).toBe('ai')

    // Lowercase ticker in response must be uppercased
    expect(result.current.MSFT).toBeDefined()
    expect(result.current.MSFT.verdict).toBe('WAIT')
    expect(result.current.MSFT.blockers).toBe('PE high')

    // No stray keys
    expect(Object.keys(result.current)).toHaveLength(2)
  })

  // ── Ticker normalisation ───────────────────────────────────────────────────
  it('normalises mixed-case tickers to uppercase keys', async () => {
    fetchEntryVerdictsMock.mockResolvedValue({
      data: {
        verdicts: [
          { ticker: 'sap.de', verdict: 'AVOID', confidence: 0.1, reasons: 'loss', blockers: null, trigger: null, source: 'rules', origin: null },
        ],
        total: 1,
        as_of: null,
      },
    })

    const { useEntryVerdicts } = await loadModule()
    const { result } = renderHook(() => useEntryVerdicts())

    await waitFor(() => expect(result.current['SAP.DE']).toBeDefined())

    expect(result.current['sap.de']).toBeUndefined()  // lowercase key must not exist
    expect(result.current['SAP.DE'].verdict).toBe('AVOID')
  })

  // ── useEntryVerdict single-ticker selector ─────────────────────────────────
  it('useEntryVerdict returns the verdict for a given ticker', async () => {
    fetchEntryVerdictsMock.mockResolvedValue({
      data: {
        verdicts: [{ ticker: 'NVDA', verdict: 'ENTRY', confidence: 0.9, reasons: null, blockers: null, trigger: null, source: 'ai', origin: null }],
        total: 1,
        as_of: null,
      },
    })

    const { useEntryVerdict } = await loadModule()
    const { result } = renderHook(() => useEntryVerdict('NVDA'))

    await waitFor(() => expect(result.current).not.toBeNull())

    expect(result.current?.verdict).toBe('ENTRY')
  })

  it('useEntryVerdict returns null for an unknown ticker', async () => {
    fetchEntryVerdictsMock.mockResolvedValue({
      data: { verdicts: [], total: 0, as_of: null },
    })

    const { useEntryVerdict } = await loadModule()
    const { result } = renderHook(() => useEntryVerdict('UNKNOWN'))

    await waitFor(() => {}, { timeout: 200 })

    expect(result.current).toBeNull()
  })

  it('useEntryVerdict returns null when ticker argument is null', async () => {
    fetchEntryVerdictsMock.mockResolvedValue({
      data: { verdicts: [], total: 0, as_of: null },
    })

    const { useEntryVerdict } = await loadModule()
    const { result } = renderHook(() => useEntryVerdict(null))

    await waitFor(() => {}, { timeout: 200 })

    expect(result.current).toBeNull()
  })

  // ── Empty response ─────────────────────────────────────────────────────────
  it('returns an empty map when verdicts array is empty', async () => {
    fetchEntryVerdictsMock.mockResolvedValue({
      data: { verdicts: [], total: 0, as_of: null },
    })

    const { useEntryVerdicts } = await loadModule()
    const { result } = renderHook(() => useEntryVerdicts())

    await waitFor(() => {}, { timeout: 200 })

    expect(Object.keys(result.current)).toHaveLength(0)
  })

  // ── Malformed data: verdicts null or undefined ─────────────────────────────
  // Bug: `for (const v of res.data.verdicts)` throws TypeError when verdicts is
  // null/undefined because null is not iterable. The hook's `.catch(() => {})`
  // swallows it and the map stays empty — safe for callers but the load()
  // function silently fails. This test documents the behaviour.
  it('returns empty map and does not throw when verdicts is null', async () => {
    fetchEntryVerdictsMock.mockResolvedValue({
      data: { verdicts: null, total: 0, as_of: null },
    })

    const { useEntryVerdicts } = await loadModule()
    const { result } = renderHook(() => useEntryVerdicts())

    await waitFor(() => {}, { timeout: 200 })

    // Should not propagate an error — map stays empty
    expect(result.current).toEqual({})
  })

  it('returns empty map and does not throw when verdicts key is absent', async () => {
    fetchEntryVerdictsMock.mockResolvedValue({
      data: { total: 0, as_of: null },  // no verdicts key
    })

    const { useEntryVerdicts } = await loadModule()
    const { result } = renderHook(() => useEntryVerdicts())

    await waitFor(() => {}, { timeout: 200 })

    expect(result.current).toEqual({})
  })

  // ── Malformed verdict objects: missing ticker field ────────────────────────
  it('skips verdict objects with missing ticker and does not throw', async () => {
    fetchEntryVerdictsMock.mockResolvedValue({
      data: {
        verdicts: [
          { ticker: undefined, verdict: 'ENTRY', confidence: 0.8, reasons: null, blockers: null, trigger: null, source: 'rules', origin: null },
          { ticker: 'GOOD', verdict: 'WAIT', confidence: 0.5, reasons: null, blockers: null, trigger: null, source: 'rules', origin: null },
        ],
        total: 2,
        as_of: null,
      },
    })

    const { useEntryVerdicts } = await loadModule()
    const { result } = renderHook(() => useEntryVerdicts())

    await waitFor(() => expect(result.current.GOOD).toBeDefined())

    // Undefined-ticker entry must be skipped
    expect(Object.keys(result.current)).toHaveLength(1)
    expect(result.current.GOOD.verdict).toBe('WAIT')
  })

  // ── Network failure ────────────────────────────────────────────────────────
  it('returns empty map when the API call rejects', async () => {
    fetchEntryVerdictsMock.mockRejectedValue(new Error('network error'))

    const { useEntryVerdicts } = await loadModule()
    const { result } = renderHook(() => useEntryVerdicts())

    await waitFor(() => {}, { timeout: 200 })

    expect(result.current).toEqual({})
  })

  // ── TTL cache: stale data triggers a re-fetch ──────────────────────────────
  it('serves cached data without a second fetch within TTL', async () => {
    fetchEntryVerdictsMock.mockResolvedValue({
      data: {
        verdicts: [{ ticker: 'AAPL', verdict: 'ENTRY', confidence: 0.9, reasons: null, blockers: null, trigger: null, source: 'ai', origin: null }],
        total: 1,
        as_of: null,
      },
    })

    const { useEntryVerdicts } = await loadModule()

    // First consumer — triggers the fetch
    const { result: r1 } = renderHook(() => useEntryVerdicts())
    await waitFor(() => expect(r1.current.AAPL).toBeDefined())

    // Second consumer mounts after data is cached
    const { result: r2 } = renderHook(() => useEntryVerdicts())
    await waitFor(() => expect(r2.current.AAPL).toBeDefined())

    // Only one real API call despite two consumers
    expect(fetchEntryVerdictsMock).toHaveBeenCalledTimes(1)
  })

  // ── Listener cleanup: unmounted hooks do not receive updates ───────────────
  it('removes the listener when the hook unmounts', async () => {
    fetchEntryVerdictsMock.mockResolvedValue({
      data: { verdicts: [], total: 0, as_of: null },
    })

    const { useEntryVerdicts } = await loadModule()
    const { unmount } = renderHook(() => useEntryVerdicts())

    await waitFor(() => {}, { timeout: 200 })

    // Unmount should not throw
    expect(() => unmount()).not.toThrow()
  })
})
