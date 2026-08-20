import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ValuationBar from '@/components/ValuationBar'

/**
 * Datos reales del CSV del 20-ago-2026. Se usan tal cual porque los casos
 * interesantes (un DCF roto, dos objetivos fuera por el mismo lado) salieron
 * de mirar la lista, no de imaginarlos.
 */
const MCO = {   // consenso y DCF por ENCIMA del máximo del año
  precio: 497.03, pctDesdeMax: -8.5, pctDesdeMin: 24.4,
  objetivoAnalista: 560.48, objetivoDcf: 631.57, objetivoPe: 483,
}
const MSFT = {  // DCF a 94 con la acción a 484: el modelo está roto
  precio: 484.31, pctDesdeMax: -11.98, pctDesdeMin: 38.69,
  objetivoAnalista: 569.56, objetivoDcf: 94.49, objetivoPe: 538.8,
}

describe('ValuationBar', () => {
  it('no dibuja nada sin el rango de 52 semanas', () => {
    // Sin dato no se inventa un rango: la barra sencillamente no aparece.
    const { container } = render(
      <ValuationBar precio={100} pctDesdeMax={null} pctDesdeMin={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('no dibuja nada sin precio', () => {
    const { container } = render(
      <ValuationBar precio={0} pctDesdeMax={-10} pctDesdeMin={20} />)
    expect(container.firstChild).toBeNull()
  })

  it('sitúa el precio dentro del rango del año, no dentro de los objetivos', () => {
    // La posición se calcula SOLO con mínimo y máximo de 52s. Es lo que hace
    // que dos tarjetas seguidas sean comparables entre sí.
    render(<ValuationBar {...MCO} />)
    // 497,03 con rango 399,6-543,3 → 68%
    expect(screen.getByText('68% del rango 52s')).toBeInTheDocument()
  })

  it('un objetivo roto no descoloca la escala', () => {
    // El DCF de MSFT (94,49) está un 80% por debajo del precio. Si entrara en
    // la escala, comprimiría el rango real (349-550) hasta hacerlo ilegible.
    render(<ValuationBar {...MSFT} />)
    expect(screen.getByText('67% del rango 52s')).toBeInTheDocument()
    // y el valor sigue siendo visible en la leyenda, no se esconde
    expect(screen.getByText('94,49')).toBeInTheDocument()
    expect(screen.getByText('-80%')).toBeInTheDocument()
  })

  it('marca como fuera de rango lo que se sale del año', () => {
    const { container } = render(<ValuationBar {...MSFT} />)
    const fuera = container.querySelectorAll('[title*="fuera del rango"]')
    // consenso 569,56 (> 550) por arriba y DCF 94,49 (< 349) por abajo
    expect(fuera.length).toBe(2)
  })

  it('escalona dos objetivos clavados en el mismo borde', () => {
    // MCO tiene consenso 560 y DCF 631, los dos por encima del máximo: sin
    // escalonar quedaban en la misma coordenada y solo se veía una flecha.
    const { container } = render(<ValuationBar {...MCO} />)
    const fuera = Array.from(container.querySelectorAll<HTMLElement>('[title*="fuera del rango"]'))
    expect(fuera.length).toBe(2)
    const margenes = fuera.map(el => el.style.marginLeft)
    expect(new Set(margenes).size).toBe(2)
  })

  it('omite el objetivo que no tiene dato', () => {
    render(<ValuationBar precio={100} pctDesdeMax={-20} pctDesdeMin={30}
      objetivoAnalista={120} objetivoDcf={null} objetivoPe={undefined} />)
    expect(screen.getByText('Consenso')).toBeInTheDocument()
    expect(screen.queryByText('DCF')).not.toBeInTheDocument()
    expect(screen.queryByText('P/E')).not.toBeInTheDocument()
  })

  it('en modo compacto solo deja la pista', () => {
    render(<ValuationBar {...MCO} compacta />)
    expect(screen.queryByText(/del rango 52s/)).not.toBeInTheDocument()
    expect(screen.queryByText('Consenso')).not.toBeInTheDocument()
  })
})
