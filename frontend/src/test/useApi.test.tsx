import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useApi } from '@/hooks/useApi'

describe('useApi', () => {
  it('loads data successfully', async () => {
    const fetcher = vi.fn().mockResolvedValue({ data: { total: 3 } })

    const { result } = renderHook(() => useApi(fetcher, []))

    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toEqual({ total: 3 })
    expect(result.current.error).toBeNull()
    expect(fetcher).toHaveBeenCalledOnce()
  })

  it('stores a friendly fallback error when the fetcher has no message', async () => {
    const fetcher = vi.fn().mockRejectedValue({})

    const { result } = renderHook(() => useApi(fetcher, []))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toBeNull()
    expect(result.current.error).toBe('Error de conexión')
  })

  it('re-fetches when dependencies change', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ data: { total: 1 } })
      .mockResolvedValueOnce({ data: { total: 2 } })

    const { result, rerender } = renderHook(
      ({ dep }) => useApi(fetcher, [dep]),
      { initialProps: { dep: 'first' } },
    )

    await waitFor(() => {
      expect(result.current.data).toEqual({ total: 1 })
    })

    rerender({ dep: 'second' })

    await waitFor(() => {
      expect(result.current.data).toEqual({ total: 2 })
    })

    expect(fetcher).toHaveBeenCalledTimes(2)
  })
})
