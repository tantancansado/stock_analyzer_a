import { useState, useEffect } from 'react'
import type { TechnicalSummary } from '../api/client'
import { subscribeToTechnicalData, getTechnicalCache } from './useTechnicalData'

function buildMap(summary: TechnicalSummary[] | undefined): Record<string, TechnicalSummary> {
  const m: Record<string, TechnicalSummary> = {}
  for (const row of (summary ?? [])) m[row.ticker] = row
  return m
}

export function useTechnicalSummaryMap(): Record<string, TechnicalSummary> {
  const initial = getTechnicalCache()
  const [map, setMap] = useState<Record<string, TechnicalSummary>>(
    initial ? buildMap(initial.summary) : {}
  )

  useEffect(() => {
    const current = getTechnicalCache()
    if (current) { setMap(buildMap(current.summary)); return }
    const unsub = subscribeToTechnicalData(d => setMap(buildMap(d.summary)))
    return unsub
  }, [])

  return map
}
