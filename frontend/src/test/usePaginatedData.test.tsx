import { renderHook, act } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePaginatedData } from '@/hooks/usePaginatedData'

describe('usePaginatedData', () => {
  beforeEach(() => {
    window.scrollTo = vi.fn()
  })

  it('returns the first page by default', () => {
    const data = [1, 2, 3, 4, 5]
    const { result } = renderHook(() => usePaginatedData(data, 2))

    expect(result.current.page).toBe(1)
    expect(result.current.totalPages).toBe(3)
    expect(result.current.paged).toEqual([1, 2])
  })

  it('updates the page and scrolls to the top', () => {
    const data = [1, 2, 3, 4, 5]
    const { result } = renderHook(() => usePaginatedData(data, 2))

    act(() => {
      result.current.setPage(2)
    })

    expect(result.current.page).toBe(2)
    expect(result.current.paged).toEqual([3, 4])
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' })
  })

  it('resets to page 1 when resetPage is called', () => {
    const data = [1, 2, 3, 4, 5]
    const { result } = renderHook(() => usePaginatedData(data, 2))

    act(() => {
      result.current.setPage(3)
      result.current.resetPage()
    })

    expect(result.current.page).toBe(1)
    expect(result.current.paged).toEqual([1, 2])
  })

  it('resets to page 1 when the data reference changes', () => {
    const initial = [1, 2, 3, 4]
    const next = [10, 20, 30]
    const { result, rerender } = renderHook(
      ({ data }) => usePaginatedData(data, 2),
      { initialProps: { data: initial } },
    )

    act(() => {
      result.current.setPage(2)
    })
    expect(result.current.page).toBe(2)

    rerender({ data: next })

    expect(result.current.page).toBe(1)
    expect(result.current.paged).toEqual([10, 20])
  })

  it('always reports at least one page for empty data', () => {
    const { result } = renderHook(() => usePaginatedData([], 10))

    expect(result.current.totalPages).toBe(1)
    expect(result.current.paged).toEqual([])
  })
})
