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

/**
 * 10-nov-2026: en las fichas de BRO y PGR la Conclusión y los Riesgos salían
 * con los asteriscos a la vista («**ESPERAR.**»), la tesis de PGR abría con un
 * «# TESIS DE INVERSIÓN» y cada título de sección quedaba vacío, con su texto
 * en una tarjeta suelta debajo. Es el formato que escribe la IA.
 */
describe('ThesisBody con el formato de la IA', () => {
  const tesis = [
    '# TESIS DE INVERSIÓN: BROWN & BROWN (BRO)',
    '',
    '**Resumen**',
    '',
    'Distribuidor de seguros que cotiza a -2,29σ de su PER histórico.',
    '',
    '**Riesgos**',
    '',
    '1. **Crecimiento comprado**: el orgánico apenas llega al 1,2 %.',
    '',
    '**Conclusión**',
    '',
    '**COMPRAR.** Está en Prioridad y nuestra valoración le ve recorrido.',
  ].join('\n')

  it('no enseña asteriscos ni almohadillas', () => {
    const { container } = render(<ThesisBody text={tesis} />)
    expect(container.textContent).not.toMatch(/\*\*|#/)
  })

  it('la negrita se pinta como negrita', () => {
    render(<ThesisBody text={tesis} />)
    expect(screen.getByText('COMPRAR.').tagName).toBe('STRONG')
  })

  it('cada sección lleva su texto dentro', () => {
    const { container } = render(<ThesisBody text={tesis} />)
    const conclusion = [...container.querySelectorAll('.rounded-xl')]
      .find(el => el.textContent?.startsWith('Conclusión'))
    expect(conclusion?.textContent).toContain('nuestra valoración le ve recorrido')
  })
})
