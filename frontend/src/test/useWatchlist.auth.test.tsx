import { renderHook, act, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const upsertMock = vi.fn()
const selectMock = vi.fn()
const eqMock = vi.fn()
const orderMock = vi.fn()
const insertMock = vi.fn()
const deleteMock = vi.fn()
const matchMock = vi.fn()
const fromMock = vi.fn()

vi.mock('@/lib/supabase', () => ({
  supabase: {
    from: (...args: unknown[]) => fromMock(...args),
  },
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1' } }),
}))

async function loadHook() {
  vi.resetModules()
  return import('@/hooks/useWatchlist')
}

describe('useWatchlist with auth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()

    orderMock.mockResolvedValue({
      data: [{ ticker: 'AAPL', added_at: '2026-04-18T10:00:00.000Z' }],
      error: null,
    })
    eqMock.mockReturnValue({ order: orderMock })
    selectMock.mockReturnValue({ eq: eqMock })
    upsertMock.mockResolvedValue({ error: null })
    insertMock.mockResolvedValue({ error: null })
    matchMock.mockResolvedValue({ error: null })
    deleteMock.mockReturnValue({ match: matchMock })

    fromMock.mockImplementation(() => ({
      upsert: upsertMock,
      select: selectMock,
      insert: insertMock,
      delete: deleteMock,
    }))
  })

  it('migrates local entries to Supabase and merges remote data with local metadata', async () => {
    localStorage.setItem('sa-watchlist-v1', JSON.stringify([
      { ticker: 'AAPL', company_name: 'Apple', note: 'core', added_at: '2026-04-17T10:00:00.000Z' },
    ]))

    const { useWatchlist } = await loadHook()
    const { result } = renderHook(() => useWatchlist())

    await waitFor(() => {
      expect(result.current.entries[0]?.ticker).toBe('AAPL')
    })

    expect(upsertMock).toHaveBeenCalledWith([{ user_id: 'user-1', ticker: 'AAPL' }], { onConflict: 'user_id,ticker' })
    expect(selectMock).toHaveBeenCalledWith('ticker, added_at')
    expect(eqMock).toHaveBeenCalledWith('user_id', 'user-1')
    expect(orderMock).toHaveBeenCalledWith('added_at', { ascending: false })
    expect(result.current.entries[0].company_name).toBe('Apple')
    expect(result.current.entries[0].note).toBe('core')
  })

  it('inserts and deletes remote rows when adding and removing entries', async () => {
    const { useWatchlist } = await loadHook()
    const { result } = renderHook(() => useWatchlist())

    await waitFor(() => {
      expect(result.current.entries[0]?.ticker).toBe('AAPL')
    })

    act(() => {
      result.current.add({ ticker: 'MSFT' })
    })
    expect(insertMock).toHaveBeenCalledWith({ user_id: 'user-1', ticker: 'MSFT' })

    act(() => {
      result.current.remove('MSFT')
    })
    expect(deleteMock).toHaveBeenCalled()
    expect(matchMock).toHaveBeenCalledWith({ user_id: 'user-1', ticker: 'MSFT' })
  })

  it('syncs remote changes through toggle', async () => {
    const { useWatchlist } = await loadHook()
    const { result } = renderHook(() => useWatchlist())

    await waitFor(() => {
      expect(result.current.entries[0]?.ticker).toBe('AAPL')
    })

    act(() => {
      result.current.toggle({ ticker: 'NVDA' })
    })
    expect(insertMock).toHaveBeenCalledWith({ user_id: 'user-1', ticker: 'NVDA' })

    act(() => {
      result.current.toggle({ ticker: 'NVDA' })
    })
    expect(matchMock).toHaveBeenCalledWith({ user_id: 'user-1', ticker: 'NVDA' })
  })
})
