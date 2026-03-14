import { fetchTechnicalSignals } from '../api/client'
import type { TechnicalSignal, TechnicalSummary } from '../api/client'

export type TechnicalData = { signals: TechnicalSignal[]; summary: TechnicalSummary[] }

let cache: TechnicalData | null = null
let promise: Promise<void> | null = null
const listeners: Array<(d: TechnicalData) => void> = []

export function subscribeToTechnicalData(cb: (d: TechnicalData) => void): () => void {
  // Already loaded — call back async so it doesn't fire during render
  if (cache !== null) {
    const d = cache
    setTimeout(() => cb(d), 0)
    return () => {}
  }
  listeners.push(cb)
  if (promise === null) {
    promise = fetchTechnicalSignals()
      .then(d => {
        cache = d
        const fns = listeners.splice(0)
        for (const fn of fns) fn(d)
      })
      .catch(() => {
        promise = null
        listeners.splice(0)
      })
  }
  return () => {
    const idx = listeners.indexOf(cb)
    if (idx !== -1) listeners.splice(idx, 1)
  }
}

export function getTechnicalCache(): TechnicalData | null {
  return cache
}
