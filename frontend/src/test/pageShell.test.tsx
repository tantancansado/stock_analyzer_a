import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import PageShell from '../components/PageShell'

describe('PageShell', () => {
  it('pinta la cabecera mientras carga', () => {
    // El motivo de que exista: 26 páginas hacían `if (error) return
    // <ErrorState/>` ANTES de su cabecera, así que al caerse la API te
    // quedabas con un mensaje de error sin saber en qué sección estabas.
    render(<PageShell title="Recurring Insiders" subtitle="Convicción directiva" loading />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Recurring Insiders')
  })

  it('pinta la cabecera también cuando la API falla', () => {
    render(<PageShell title="Recurring Insiders" error="No se puede conectar con la API" />)
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Recurring Insiders')
    expect(screen.getByText(/No se puede conectar/)).toBeInTheDocument()
  })

  it('no repite el título en el esqueleto de carga', () => {
    // Loading trae su propio esqueleto de título y subtítulo. Bajo una
    // cabecera ya pintada se veía como un segundo título fantasma.
    const { container } = render(<PageShell title="Mi cartera" loading />)
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
    // el primer bloque tras la cabecera son las tarjetas, no dos barras sueltas
    const esqueletos = container.querySelectorAll('[class*="h-8"][class*="w-52"]')
    expect(esqueletos).toHaveLength(0)
  })

  it('el error manda sobre el contenido', () => {
    render(
      <PageShell title="X" error="boom">
        <p>contenido que no debe verse</p>
      </PageShell>,
    )
    expect(screen.queryByText('contenido que no debe verse')).not.toBeInTheDocument()
  })

  it('sin loading ni error, enseña el contenido', () => {
    render(
      <PageShell title="X">
        <p>la tabla</p>
      </PageShell>,
    )
    expect(screen.getByText('la tabla')).toBeInTheDocument()
  })

  it('el banner va por delante de la cabecera', () => {
    const { container } = render(
      <PageShell title="Insiders" banner={<div data-testid="banner">obsoleto</div>}>
        <p>x</p>
      </PageShell>,
    )
    const orden = [...container.querySelectorAll('[data-testid=banner], h1')]
    expect(orden[0]).toHaveAttribute('data-testid', 'banner')
  })
})
