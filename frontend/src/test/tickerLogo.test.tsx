import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { fireEvent } from '@testing-library/dom'
import TickerLogo from '../components/TickerLogo'

describe('TickerLogo', () => {
  it('intenta cargar el logo YA en el primer render', () => {
    // El bug que motivó el test: los candidatos se calculaban en un useEffect
    // y se guardaban en un useRef. Un ref no provoca re-render, y el
    // setCandidateIdx(0) que lo acompañaba no cambiaba el valor, así que React
    // salía por su bail-out. El primer render veía la lista vacía, caía a las
    // iniciales y no volvía a renderizar jamás.
    //
    // Medido en producción antes del arreglo: 114 fichas con iniciales y CERO
    // peticiones de logo. Ni una fallida — el mecanismo entero estaba muerto.
    const { container } = render(<TickerLogo ticker="AAPL" />)
    const img = container.querySelector('img')
    expect(img).not.toBeNull()
    expect(img?.getAttribute('src')).toBeTruthy()
  })

  it('cae a las iniciales cuando se agotan los candidatos', () => {
    const { container } = render(<TickerLogo ticker="ZZZZ" />)
    let img = container.querySelector('img')
    // se fuerza el fallo de todas las fuentes
    let vueltas = 0
    while (img && vueltas < 5) {
      fireEvent.error(img)
      img = container.querySelector('img')
      vueltas++
    }
    expect(container.querySelector('img')).toBeNull()
    expect(screen.getByText('ZZ')).toBeInTheDocument()
  })

  it('trata un 1×1 servido con 200 como candidato fallido', () => {
    // Algunos CDN devuelven un píxel transparente en vez de un 404.
    const { container } = render(<TickerLogo ticker="MSFT" />)
    const img = container.querySelector('img') as HTMLImageElement
    Object.defineProperty(img, 'naturalWidth', { value: 1, configurable: true })
    Object.defineProperty(img, 'naturalHeight', { value: 1, configurable: true })
    const antes = img.getAttribute('src')
    fireEvent.load(img)
    const despues = container.querySelector('img')?.getAttribute('src') ?? null
    expect(despues).not.toBe(antes)   // pasó al siguiente candidato, o a iniciales
  })

  it('al cambiar de ticker vuelve al primer candidato', () => {
    const { container, rerender } = render(<TickerLogo ticker="AAPL" />)
    const primera = container.querySelector('img')!
    fireEvent.error(primera)          // AAPL avanza de candidato
    rerender(<TickerLogo ticker="V" />)
    const img = container.querySelector('img')
    // V empieza de cero: tiene que haber <img>, no heredar el índice agotado
    expect(img).not.toBeNull()
    expect(img?.getAttribute('src')).toContain('V')
  })

  it('sin ticker no revienta', () => {
    const { container } = render(<TickerLogo ticker="" />)
    expect(container.querySelector('img')).toBeNull()
    expect(screen.getByText('?')).toBeInTheDocument()
  })
})
