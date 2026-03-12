import { useState, useEffect } from 'react'
import type { TechnicalSignal, TechnicalSummary } from '../api/client'
import { fetchTechnicalSignals } from '../api/client'

// Module-level cache so the CSV is only fetched once per session
let cache: { signals: TechnicalSignal[]; summary: TechnicalSummary[] } | null = null
let promise: Promise<void> | null = null

export function useTechnicalSignals(ticker: string) {
  const [data, setData] = useState(cache)
  const [loading, setLoading] = useState(!cache)

  useEffect(() => {
    if (cache) { setData(cache); setLoading(false); return }
    if (!promise) {
      promise = fetchTechnicalSignals()
        .then(d => { cache = d })
        .catch(() => { cache = { signals: [], summary: [] } })
    }
    promise.then(() => { setData(cache); setLoading(false) })
  }, [])

  const tickerSignals = data?.signals.filter(s => s.ticker === ticker) ?? []
  const tickerSummary = data?.summary.find(s => s.ticker === ticker) ?? null

  return { signals: tickerSignals, summary: tickerSummary, loading }
}
