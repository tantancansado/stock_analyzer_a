import { useState, useCallback } from 'react'

const KEY = 'sa-watchlist-v1'

export interface WatchlistEntry {
  ticker: string
  company_name?: string
  sector?: string
  added_at: string
  value_score?: number
  conviction_grade?: string
  analyst_upside_pct?: number
  fcf_yield_pct?: number
  current_price?: number
  note?: string
}

function load(): WatchlistEntry[] {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as WatchlistEntry[]) : []
  } catch {
    return []
  }
}

function save(entries: WatchlistEntry[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(entries))
  } catch {
    // storage quota exceeded — fail silently
  }
}

export function useWatchlist() {
  const [entries, setEntries] = useState<WatchlistEntry[]>(load)

  const add = useCallback((entry: Omit<WatchlistEntry, 'added_at'>) => {
    setEntries(prev => {
      if (prev.some(e => e.ticker === entry.ticker)) return prev
      const next = [{ ...entry, added_at: new Date().toISOString() }, ...prev]
      save(next)
      return next
    })
  }, [])

  const remove = useCallback((ticker: string) => {
    setEntries(prev => {
      const next = prev.filter(e => e.ticker !== ticker)
      save(next)
      return next
    })
  }, [])

  const toggle = useCallback((entry: Omit<WatchlistEntry, 'added_at'>) => {
    setEntries(prev => {
      const exists = prev.some(e => e.ticker === entry.ticker)
      const next = exists
        ? prev.filter(e => e.ticker !== entry.ticker)
        : [{ ...entry, added_at: new Date().toISOString() }, ...prev]
      save(next)
      return next
    })
  }, [])

  const has = useCallback((ticker: string) => entries.some(e => e.ticker === ticker), [entries])

  const updateNote = useCallback((ticker: string, note: string) => {
    setEntries(prev => {
      const next = prev.map(e => e.ticker === ticker ? { ...e, note } : e)
      save(next)
      return next
    })
  }, [])

  return { entries, add, remove, toggle, has, updateNote }
}
