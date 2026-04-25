import { useEffect, useState } from 'react'

type ValueExperienceMode = 'clear' | 'expert'

const STORAGE_KEY = 'stock-analyzer:value-experience-mode'

export function useValueExperienceMode() {
  const [mode, setModeState] = useState<ValueExperienceMode>(() => {
    if (typeof window === 'undefined') return 'clear'
    return window.localStorage.getItem(STORAGE_KEY) === 'expert' ? 'expert' : 'clear'
  })

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, mode)
  }, [mode])

  return {
    clearMode: mode === 'clear',
    mode,
    setClearMode: (enabled: boolean) => setModeState(enabled ? 'clear' : 'expert'),
  }
}
