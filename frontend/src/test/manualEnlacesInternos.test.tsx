import { describe, it, expect, vi, beforeAll } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import Manual from '@/pages/Manual'

function Ruta() {
  const l = useLocation()
  return <div data-testid="ruta">{l.pathname}</div>
}

beforeAll(() => {
  // jsdom no trae ninguno de los dos
  Element.prototype.scrollIntoView = vi.fn()
  globalThis.IntersectionObserver = class {
    observe() {} disconnect() {} unobserve() {} takeRecords() { return [] }
  } as unknown as typeof IntersectionObserver
})

describe('los enlaces internos del manual no sacan del manual', () => {
  it('el índice baja a la sección sin cambiar de página', () => {
    render(
      <MemoryRouter initialEntries={['/manual']}>
        <Routes><Route path="/manual" element={<><Manual /><Ruta /></>} /></Routes>
      </MemoryRouter>,
    )
    const enlace = document.querySelector('a[href="#filosofia"]') as HTMLAnchorElement
    expect(enlace).toBeTruthy()
    fireEvent.click(enlace)
    expect(screen.getByTestId('ruta').textContent).toBe('/manual')
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled()
  })

  it('ninguna sección enlaza a una página que ya no existe', () => {
    render(<MemoryRouter><Manual /></MemoryRouter>)
    const rotas = Array.from(document.querySelectorAll('a[href]'))
      .map(a => a.getAttribute('href') ?? '')
      .filter(h => h.includes('/search'))
    expect(rotas).toEqual([])
  })
})
