import { useState, useEffect } from 'react'
import { fetchChartSignals, type ChartSignal } from '../api/client'

let cache: Record<string, ChartSignal> | null = null
let promise: Promise<Record<string, ChartSignal>> | null = null

export function useChartSignals(): Record<string, ChartSignal> {
  const [signals, setSignals] = useState<Record<string, ChartSignal>>(cache ?? {})

  useEffect(() => {
    if (cache) { setSignals(cache); return }
    if (!promise) promise = fetchChartSignals().then(d => { cache = d; return d }).catch((e: unknown) => {
      promise = null
      // Devolver {} sin decir nada convierte «no pude cargarlo» en «no hay
      // ninguna señal», que se pinta idéntico. Al menos queda rastro.
      console.error('[chart-signals] carga fallida', e)
      return {} as Record<string, ChartSignal>
    })
    promise.then(d => setSignals(d))
  }, [])

  return signals
}
