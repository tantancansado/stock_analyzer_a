import { renderHook, act } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { useKeyboardNav } from '@/hooks/useKeyboardNav'

describe('useKeyboardNav', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('moves focus down and up within bounds', () => {
    const { result } = renderHook(() => useKeyboardNav(['A', 'B', 'C']))

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }))
    })
    expect(result.current.focused).toBe(0)

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'j' }))
    })
    expect(result.current.focused).toBe(1)

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k' }))
    })
    expect(result.current.focused).toBe(0)
  })

  it('does not move past the first or last item', () => {
    const { result } = renderHook(() => useKeyboardNav(['A', 'B']))

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp' }))
    })
    expect(result.current.focused).toBe(0)

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }))
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }))
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }))
    })
    expect(result.current.focused).toBe(1)
  })

  it('calls onEnter with the focused item', () => {
    const onEnter = vi.fn()
    const { result } = renderHook(() => useKeyboardNav(['A', 'B'], { onEnter }))

    act(() => {
      result.current.setFocused(1)
    })

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    })

    expect(onEnter).toHaveBeenCalledWith('B', 1)
  })

  it('resets focus and calls onEscape', () => {
    const onEscape = vi.fn()
    const { result } = renderHook(() => useKeyboardNav(['A', 'B'], { onEscape }))

    act(() => {
      result.current.setFocused(1)
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    })

    expect(result.current.focused).toBe(-1)
    expect(onEscape).toHaveBeenCalledOnce()
  })

  it('ignores key navigation while typing in an input', () => {
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()

    const { result } = renderHook(() => useKeyboardNav(['A', 'B']))

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }))
    })

    expect(result.current.focused).toBe(-1)
  })

  it('scrolls the focused row into view after moving', () => {
    vi.useFakeTimers()
    const row = document.createElement('div')
    row.setAttribute('data-row-idx', '0')
    row.scrollIntoView = vi.fn()
    document.body.appendChild(row)

    renderHook(() => useKeyboardNav(['A', 'B']))

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }))
    })
    act(() => {
      vi.runAllTimers()
    })

    expect(row.scrollIntoView).toHaveBeenCalledWith({ block: 'nearest', behavior: 'smooth' })
  })

  it('does not bind keyboard handlers when disabled', () => {
    const { result } = renderHook(() => useKeyboardNav(['A', 'B'], { disabled: true }))

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }))
    })

    expect(result.current.focused).toBe(-1)
  })
})
