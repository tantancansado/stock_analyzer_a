import { renderHook, act } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useCountUp } from '@/hooks/useCountUp'

describe('useCountUp', () => {
  beforeEach(() => {
    let frame = 0
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
      frame += 1
      const ts = frame === 1 ? 0 : 1000
      cb(ts)
      return frame
    })
    vi.stubGlobal('cancelAnimationFrame', vi.fn())
  })

  it('returns 0 when the target is nullish', () => {
    const { result } = renderHook(() => useCountUp(null))
    expect(result.current).toBe(0)
  })

  it('animates to the target value', () => {
    const { result } = renderHook(() => useCountUp(42, 650, 0))
    expect(result.current).toBe(42)
  })

  it('supports decimal precision', () => {
    const { result } = renderHook(() => useCountUp(12.345, 650, 2))
    expect(result.current).toBe(12.35)
  })
})
