import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { supabase } from '@/lib/supabase'
import { useAuth } from './AuthContext'

interface OwnedPosition {
  id: string
  ticker: string
  shares: number
  avg_price: number
  currency: 'USD' | 'EUR'
}

interface PersonalPortfolioCtx {
  positions: OwnedPosition[]
  isOwned: (ticker: string) => boolean
  getPosition: (ticker: string) => OwnedPosition | undefined
  loading: boolean
}

const Ctx = createContext<PersonalPortfolioCtx>({
  positions: [],
  isOwned: () => false,
  getPosition: () => undefined,
  loading: false,
})

export function PersonalPortfolioProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [positions, setPositions] = useState<OwnedPosition[]>([])
  const [loading, setLoading]     = useState(false)

  useEffect(() => {
    if (!user) { setPositions([]); return }
    setLoading(true)
    supabase
      .from('personal_portfolio_positions')
      .select('id, ticker, shares, avg_price, currency')
      .eq('user_id', user.id)
      .then(({ data }) => {
        setPositions((data ?? []) as OwnedPosition[])
        setLoading(false)
      })
  }, [user])

  const isOwned     = (ticker: string) => positions.some(p => p.ticker === ticker.toUpperCase())
  const getPosition = (ticker: string) => positions.find(p => p.ticker === ticker.toUpperCase())

  return (
    <Ctx.Provider value={{ positions, isOwned, getPosition, loading }}>
      {children}
    </Ctx.Provider>
  )
}

export const usePersonalPortfolio = () => useContext(Ctx)
