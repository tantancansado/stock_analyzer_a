import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ThesisBody from '@/components/ThesisBody'

/**
 * Reproducción del crash de producción del 14-sep-2026: al abrir la tesis de
 * una idea de Value salía "n.replace is not a function".
 *
 * Las tres páginas que enseñan tesis hacían
 *     thesis_narrative || overview || JSON.stringify(t)
 * y `overview` es un DICCIONARIO de métricas (score, precio, sector), sin una
 * sola frase dentro. Al faltar la narrativa, ese objeto —truthy— pasaba el
 * guardia `!text` y `.replace()` explotaba, tumbando la pantalla entera.
 *
 * Arreglado en el origen (fetchThesis normaliza a string|null), pero un
 * componente de presentación tampoco debe poder tumbar la página por recibir
 * algo raro.
 */
describe('ThesisBody', () => {
  it('pinta una tesis normal', () => {
    render(<ThesisBody text="Broadridge combina un ROE excepcional con márgenes sólidos." />)
    expect(screen.getByText(/ROE excepcional/)).toBeInTheDocument()
  })

  it('un objeto no revienta: se trata como sin tesis', () => {
    const basura = { score: 81.7, sector: 'Technology' } as unknown as string
    render(<ThesisBody text={basura} />)
    expect(screen.getByText('Sin tesis disponible')).toBeInTheDocument()
  })

  it.each([42, null, undefined, [] as unknown])('tampoco %s', (v) => {
    render(<ThesisBody text={v as unknown as string} />)
    expect(screen.getByText('Sin tesis disponible')).toBeInTheDocument()
  })

  it('los estados de carga se enseñan tal cual', () => {
    render(<ThesisBody text="Cargando tesis..." />)
    expect(screen.getByText('Cargando tesis...')).toBeInTheDocument()
  })
})
