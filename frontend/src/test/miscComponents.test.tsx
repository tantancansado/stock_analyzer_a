import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Loading, { ErrorState } from '@/components/Loading'
import ScrollToTop from '@/components/ScrollToTop'
import WatchlistButton from '@/components/WatchlistButton'

const useWatchlistMock = vi.fn()
const useToastMock = vi.fn()

vi.mock('@/hooks/useWatchlist', () => ({
  useWatchlist: () => useWatchlistMock(),
}))

vi.mock('@/components/Toast', () => ({
  useToast: () => useToastMock(),
}))

describe('misc components', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useWatchlistMock.mockReturnValue({
      has: vi.fn(() => false),
      toggle: vi.fn(),
    })
    useToastMock.mockReturnValue({
      toast: vi.fn(),
    })
    window.scrollTo = vi.fn()
    Object.defineProperty(window, 'scrollY', { value: 0, writable: true })
  })

  it('renders the loading skeleton shell', () => {
    const { container } = render(<Loading />)
    expect(container.querySelectorAll('.glass').length).toBeGreaterThan(0)
    expect(container.querySelectorAll('table').length).toBe(1)
  })

  it('renders a connection-specific error state', () => {
    render(<ErrorState message="Network Error" />)
    expect(screen.getByText('No se puede conectar con la API')).toBeInTheDocument()
    expect(screen.getByText(/Ejecuta python3 ticker_api.py/)).toBeInTheDocument()
  })

  it('renders a generic error state', () => {
    render(<ErrorState message="Algo fue mal" />)
    expect(screen.getByText('Error al cargar datos')).toBeInTheDocument()
    expect(screen.getByText('Algo fue mal')).toBeInTheDocument()
  })

  it('shows the scroll button after scrolling and scrolls to the top on click', async () => {
    const user = userEvent.setup()
    render(<ScrollToTop />)

    Object.defineProperty(window, 'scrollY', { value: 400, writable: true })
    fireEvent.scroll(window)

    const button = screen.getByRole('button', { name: 'Volver arriba' })
    expect(button.className).toContain('opacity-100')

    await user.click(button)
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' })
  })

  it('toggles the watchlist and shows a success toast when inactive', async () => {
    const user = userEvent.setup()
    const toggle = vi.fn()
    const toast = vi.fn()
    useWatchlistMock.mockReturnValue({ has: vi.fn(() => false), toggle })
    useToastMock.mockReturnValue({ toast })

    render(<WatchlistButton ticker="AAPL" />)

    await user.click(screen.getByRole('button'))

    expect(toggle).toHaveBeenCalledWith({ ticker: 'AAPL' })
    expect(toast).toHaveBeenCalledWith('AAPL añadido a watchlist', 'success')
  })

  it('shows an info toast when removing an active watchlist entry', async () => {
    const user = userEvent.setup()
    const toggle = vi.fn()
    const toast = vi.fn()
    useWatchlistMock.mockReturnValue({ has: vi.fn(() => true), toggle })
    useToastMock.mockReturnValue({ toast })

    render(<WatchlistButton ticker="AAPL" />)

    await user.click(screen.getByRole('button'))

    expect(toast).toHaveBeenCalledWith('AAPL eliminado', 'info')
  })
})
