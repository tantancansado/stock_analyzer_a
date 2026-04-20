import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import EmptyState from '@/components/EmptyState'
import OwnedBadge from '@/components/OwnedBadge'
import GradeBadge from '@/components/GradeBadge'
import ScoreBar from '@/components/ScoreBar'
import ScoreRing from '@/components/ScoreRing'

const usePersonalPortfolioMock = vi.fn()

vi.mock('@/context/PersonalPortfolioContext', () => ({
  usePersonalPortfolio: () => usePersonalPortfolioMock(),
}))

describe('simple components', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    usePersonalPortfolioMock.mockReturnValue({
      getPosition: vi.fn(() => undefined),
    })
    let calls = 0
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
      calls += 1
      cb(calls * 16)
      return calls
    })
    vi.stubGlobal('cancelAnimationFrame', vi.fn())
  })

  it('renders EmptyState with subtitle and action', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(
      <EmptyState
        icon="*"
        title="Nada por aqui"
        subtitle="Sin resultados"
        action={{ label: 'Recargar', onClick }}
      />,
    )

    expect(screen.getByText('Nada por aqui')).toBeInTheDocument()
    expect(screen.getByText('Sin resultados')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Recargar' }))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('renders OwnedBadge when the ticker is in the portfolio', () => {
    usePersonalPortfolioMock.mockReturnValue({
      getPosition: vi.fn(() => ({ shares: 5, avg_price: 120, currency: 'USD' })),
    })

    render(<OwnedBadge ticker="AAPL" showShares />)

    expect(screen.getByText('5 acc')).toBeInTheDocument()
  })

  it('renders a placeholder when GradeBadge has no grade', () => {
    render(<GradeBadge />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('renders the grade and tooltip when GradeBadge has data', () => {
    render(<GradeBadge grade="A" score={88} />)

    const badge = screen.getByText('A')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveAttribute('title')
  })

  it('renders a placeholder when ScoreBar has no score', () => {
    render(<ScoreBar score={null} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('renders the formatted score in ScoreBar', () => {
    render(<ScoreBar score={72.34} />)
    expect(screen.getByText('72.3')).toBeInTheDocument()
  })

  it('renders ScoreRing label and aria text', () => {
    render(<ScoreRing score={81.2} size="sm" />)
    expect(screen.getByRole('img', { name: 'Score 81' })).toBeInTheDocument()
    expect(screen.getByText('81')).toBeInTheDocument()
  })

  it('hides the ScoreRing label when showLabel is false', () => {
    render(<ScoreRing score={55} showLabel={false} />)
    expect(screen.getByRole('img', { name: 'Score 55' })).toBeInTheDocument()
    expect(screen.queryByText('55')).not.toBeInTheDocument()
  })
})
