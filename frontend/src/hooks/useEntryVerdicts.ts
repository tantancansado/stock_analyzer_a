import { useEffect, useState } from 'react'
import { fetchEntryVerdicts, type EntryVerdict } from '../api/client'

type VerdictMap = Record<string, EntryVerdict>

let cache: { map: VerdictMap; at: number } | null = null
let inflight: Promise<VerdictMap> | null = null
const listeners = new Set<(m: VerdictMap) => void>()
const TTL_MS = 5 * 60 * 1000

async function load(): Promise<VerdictMap> {
  if (cache && Date.now() - cache.at < TTL_MS) return cache.map
  if (inflight) return inflight
  inflight = (async () => {
    try {
      const res = await fetchEntryVerdicts()
      const map: VerdictMap = {}
      for (const v of res.data.verdicts) {
        if (v.ticker) map[v.ticker.toUpperCase()] = v
      }
      cache = { map, at: Date.now() }
      listeners.forEach(l => l(map))
      return map
    } finally {
      inflight = null
    }
  })()
  return inflight
}

export function useEntryVerdicts() {
  const [map, setMap] = useState<VerdictMap>(cache?.map ?? {})

  useEffect(() => {
    let alive = true
    load().then(m => { if (alive) setMap(m) }).catch(() => {})
    const listener = (m: VerdictMap) => { if (alive) setMap(m) }
    listeners.add(listener)
    return () => { alive = false; listeners.delete(listener) }
  }, [])

  return map
}

export function useEntryVerdict(ticker: string | null | undefined): EntryVerdict | null {
  const map = useEntryVerdicts()
  if (!ticker) return null
  return map[ticker.toUpperCase()] ?? null
}
