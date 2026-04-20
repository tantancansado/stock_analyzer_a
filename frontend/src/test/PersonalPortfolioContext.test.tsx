import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PersonalPortfolioProvider, usePersonalPortfolio } from '@/context/PersonalPortfolioContext'

const useAuthMock = vi.fn()
const selectMock = vi.fn()
const eqMock = vi.fn()
const fromMock = vi.fn()

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}))

vi.mock('@/lib/supabase', () => ({
  supabase: {
    from: (...args: unknown[]) => fromMock(...args),
  },
}))

function Harness() {
  const { positions, isOwned, getPosition, loading } = usePersonalPortfolio()
  return (
    <div>
      <output data-testid="count">{positions.length}</output>
      <output data-testid="loading">{String(loading)}</output>
      <output data-testid="owned">{String(isOwned('aapl'))}</output>
      <output data-testid="shares">{String(getPosition('aapl')?.shares ?? '')}</output>
    </div>
  )
}

describe('PersonalPortfolioContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    eqMock.mockResolvedValue({ data: [] })
    selectMock.mockReturnValue({ eq: eqMock })
    fromMock.mockReturnValue({ select: selectMock })
  })

  it('resets to an empty portfolio when there is no user', () => {
    useAuthMock.mockReturnValue({ user: null })

    render(
      <PersonalPortfolioProvider>
        <Harness />
      </PersonalPortfolioProvider>,
    )

    expect(screen.getByTestId('count')).toHaveTextContent('0')
    expect(screen.getByTestId('owned')).toHaveTextContent('false')
    expect(fromMock).not.toHaveBeenCalled()
  })

  it('loads positions for the authenticated user and exposes helpers', async () => {
    useAuthMock.mockReturnValue({ user: { id: 'user-1' } })
    eqMock.mockResolvedValue({
      data: [
        { id: '1', ticker: 'AAPL', shares: 5, avg_price: 120, currency: 'USD' },
        { id: '2', ticker: 'SAP.DE', shares: 3, avg_price: 140, currency: 'EUR' },
      ],
    })

    render(
      <PersonalPortfolioProvider>
        <Harness />
      </PersonalPortfolioProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('count')).toHaveTextContent('2')
    })

    expect(fromMock).toHaveBeenCalledWith('personal_portfolio_positions')
    expect(selectMock).toHaveBeenCalledWith('id, ticker, shares, avg_price, currency')
    expect(eqMock).toHaveBeenCalledWith('user_id', 'user-1')
    expect(screen.getByTestId('owned')).toHaveTextContent('true')
    expect(screen.getByTestId('shares')).toHaveTextContent('5')
    expect(screen.getByTestId('loading')).toHaveTextContent('false')
  })
})
