/**
 * El dato de si la lista bate al índice estaba en cualquier sitio menos donde
 * se decide la compra.
 *
 * `summary.json` traía el alfa bien calculado desde siempre, y la página de
 * Cartera lo pintaba. Value US —la lista que el usuario mira para comprar— no.
 * Ahí se veía «61,5% de aciertos, +3,15% de media», que suena bien, sin decir
 * que el índice hizo +5,27% en el mismo periodo.
 */
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import RendimientoReal from '../components/RendimientoReal'

vi.mock('../api/client', async () => {
  const real = await vi.importActual<typeof import('../api/client')>('../api/client')
  return { ...real, fetchPortfolioTracker: vi.fn() }
})
const { fetchPortfolioTracker } = await import('../api/client')

const stat = (o: Record<string, unknown>) => ({
  count: 39, avg_alpha: -2.12, avg_signal_return: 3.15, avg_benchmark_return: 5.27,
  positive_alpha_rate: 35.9, best_alpha: 19.8, worst_alpha: -38.9, ...o,
})

describe('RendimientoReal', () => {
  it('enseña el alfa aunque sea malo', async () => {
    vi.mocked(fetchPortfolioTracker).mockResolvedValue({ data: { alpha_us: { '90d': stat({}) } } } as never)
    render(<RendimientoReal />)
    await waitFor(() => expect(screen.getByText(/-2\.12%/)).toBeInTheDocument())
    expect(screen.getByText(/5\.3%/)).toBeInTheDocument()   // el índice, para comparar
    expect(screen.getByText(/n=39/)).toBeInTheDocument()    // nunca un % sin su n
  })

  it('con menos de cinco señales no pinta nada', async () => {
    vi.mocked(fetchPortfolioTracker).mockResolvedValue({ data: { alpha_us: { '90d': stat({ count: 4 }) } } } as never)
    const { container } = render(<RendimientoReal />)
    await new Promise(r => setTimeout(r, 10))
    expect(container.textContent).toBe('')
  })

  it('sin tracker no rompe la página', async () => {
    vi.mocked(fetchPortfolioTracker).mockRejectedValue(new Error('caído'))
    const { container } = render(<RendimientoReal />)
    await new Promise(r => setTimeout(r, 10))
    expect(container.textContent).toBe('')
  })
})
