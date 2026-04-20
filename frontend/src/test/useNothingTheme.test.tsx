import { renderHook, act } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useNothingTheme } from '@/hooks/useNothingTheme'

describe('useNothingTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.body.removeAttribute('data-nothing-theme')
  })

  it('starts disabled by default', () => {
    const { result } = renderHook(() => useNothingTheme())

    expect(result.current.enabled).toBe(false)
    expect(document.body.hasAttribute('data-nothing-theme')).toBe(false)
    expect(localStorage.getItem('sa-nothing-theme')).toBe('false')
  })

  it('loads the enabled state from localStorage', () => {
    localStorage.setItem('sa-nothing-theme', 'true')

    const { result } = renderHook(() => useNothingTheme())

    expect(result.current.enabled).toBe(true)
    expect(document.body.getAttribute('data-nothing-theme')).toBe('true')
  })

  it('toggles the Nothing theme state and persists it', () => {
    const { result } = renderHook(() => useNothingTheme())

    act(() => {
      result.current.toggle()
    })

    expect(result.current.enabled).toBe(true)
    expect(document.body.getAttribute('data-nothing-theme')).toBe('true')
    expect(localStorage.getItem('sa-nothing-theme')).toBe('true')

    act(() => {
      result.current.toggle()
    })

    expect(result.current.enabled).toBe(false)
    expect(document.body.hasAttribute('data-nothing-theme')).toBe(false)
    expect(localStorage.getItem('sa-nothing-theme')).toBe('false')
  })
})
