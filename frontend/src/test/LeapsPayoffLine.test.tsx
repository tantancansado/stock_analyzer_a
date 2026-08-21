import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import LeapsPayoffLine from '@/components/LeapsPayoffLine'

// ICE real del 20-ago-2026: spot 158.39, strike 115, breakeven 168.30
const ICE = { strike: 115, spot: 158.39, breakeven: 168.3, target: 185.93 }
// UBER real: spot 78.63 por DEBAJO del breakeven 87.35 — aún no empata
const UBER = { strike: 60, spot: 78.63, breakeven: 87.35, target: 101.5 }

describe('LeapsPayoffLine', () => {
  it('no dibuja nada sin los tres puntos obligatorios', () => {
    const { container } = render(<LeapsPayoffLine strike={0} spot={100} breakeven={110} />)
    expect(container.firstChild).toBeNull()
  })

  it('dice "colchón ganado" cuando el precio ya superó el break-even', () => {
    render(<LeapsPayoffLine strike={115} spot={175} breakeven={168.3} target={185.93} />)
    expect(screen.getByText(/de colchón ya ganado/)).toBeInTheDocument()
  })

  it('ICE real: spot todavía por debajo del break-even', () => {
    render(<LeapsPayoffLine {...ICE} />)
    expect(screen.getByText(/necesita \+6\.3% para empatar/)).toBeInTheDocument()
  })

  it('dice "necesita" cuando el precio aún no llega al break-even', () => {
    render(<LeapsPayoffLine {...UBER} />)
    expect(screen.getByText(/necesita \+11\.1% para empatar/)).toBeInTheDocument()
  })

  it('el target es opcional: sin dato no rompe ni lo dibuja', () => {
    render(<LeapsPayoffLine strike={115} spot={158.39} breakeven={168.3} />)
    expect(screen.queryByText('Target')).not.toBeInTheDocument()
    expect(screen.getByText('Empate')).toBeInTheDocument()
  })

  it('muestra los cuatro valores en la leyenda', () => {
    render(<LeapsPayoffLine {...ICE} />)
    expect(screen.getByText('115')).toBeInTheDocument()
    expect(screen.getByText('158,39')).toBeInTheDocument()
    expect(screen.getByText('168,3')).toBeInTheDocument()
    expect(screen.getByText('185,93')).toBeInTheDocument()
  })
})
