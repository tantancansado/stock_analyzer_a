import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import EmptyState from '../components/EmptyState'

describe('EmptyState', () => {
  it('muestra icono, título y subtítulo', () => {
    render(<EmptyState icon="📂" title="Sin resultados" subtitle="Prueba a quitar filtros" />)
    expect(screen.getByText('Sin resultados')).toBeInTheDocument()
    expect(screen.getByText('Prueba a quitar filtros')).toBeInTheDocument()
    expect(screen.getByText('📂')).toBeInTheDocument()
  })

  it('la acción es opcional y se puede pulsar', async () => {
    const onClick = vi.fn()
    render(<EmptyState icon="📂" title="Vacío" action={{ label: 'Reintentar', onClick }} />)
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(onClick).toHaveBeenCalledOnce()
  })

  describe('variante compacta', () => {
    // Para huecos DENTRO de una tabla o una tarjeta. Sin ella, estos vacíos
    // se escribían a mano con ocho combinaciones distintas de padding y
    // color, porque el EmptyState normal (py-16, icono 4xl) no cabía ahí.

    it('funciona sin icono', () => {
      const { container } = render(<EmptyState compact title="Sin datos" />)
      expect(screen.getByText('Sin datos')).toBeInTheDocument()
      // solo el <p> del título, ningún contenedor de icono
      expect(container.querySelectorAll('div')).toHaveLength(1)
    })

    it('ocupa bastante menos alto que la variante normal', () => {
      const { container: compacto } = render(<EmptyState compact title="x" />)
      const { container: normal } = render(<EmptyState icon="📂" title="x" />)
      expect(compacto.firstElementChild?.className).toContain('py-7')
      expect(normal.firstElementChild?.className).toContain('py-16')
    })

    it('encoge el icono en vez de quitarlo cuando se le pasa uno', () => {
      render(<EmptyState compact icon="📂" title="x" />)
      const icono = screen.getByText('📂')
      expect(icono.className).toContain('text-xl')
      expect(icono.className).not.toContain('text-4xl')
    })
  })
})
