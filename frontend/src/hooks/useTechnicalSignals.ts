import { useState, useEffect } from 'react'
import type { TechnicalSignal, TechnicalSummary } from '../api/client'
import { subscribeToTechnicalData, getTechnicalCache } from './useTechnicalData'

export function useTechnicalSignals(ticker: string) {
  const initial = getTechnicalCache()
  const [data, setData] = useState(initial)
  const [loading, setLoading] = useState(!initial)
  useEffect(() => {
    const current = getTechnicalCache()
    if (current) { setData(current); setLoading(false); return }
    const unsub = subscribeToTechnicalData(d => { setData(d); setLoading(false) })
    return unsub
  }, [])

  const tickerSignals: TechnicalSignal[] = data?.signals?.filter(s => s.ticker === ticker) ?? []
  const tickerSummary: TechnicalSummary | null = data?.summary?.find(s => s.ticker === ticker) ?? null

  return { signals: tickerSignals, summary: tickerSummary, loading }
}
