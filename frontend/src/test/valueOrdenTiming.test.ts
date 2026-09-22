import { describe, expect, it } from 'vitest'

import { ORDEN_TIMING, comparaPorTiming } from '@/pages/ValueUS'

type Idea = { ticker: string; entry_readiness?: string; value_score?: number }

const ordenar = (ideas: Idea[]) =>
  [...ideas]
    .sort((a, b) => comparaPorTiming(a as never, b as never))
    .map(i => i.ticker)

describe('orden por defecto de Value US', () => {
  // Datos reales del 22-sep-2026, incluido EQIX: ENTRADA con score 30,9, el
  // más bajo de la lista. Es el caso que motiva el desempate por score.
  const reales: Idea[] = [
    { ticker: 'EQIX', entry_readiness: 'ENTRADA', value_score: 30.9 },
    { ticker: 'VRSN', entry_readiness: 'VIGILAR', value_score: 61.0 },
    { ticker: 'THC', entry_readiness: 'ENTRADA', value_score: 58.9 },
    { ticker: 'ODFL', entry_readiness: 'ESPERAR', value_score: 68.0 },
    { ticker: 'KO', entry_readiness: 'ENTRADA', value_score: 52.1 },
  ]

  it('pone arriba lo que se puede comprar hoy', () => {
    expect(ordenar(reales).slice(0, 3)).toEqual(['THC', 'KO', 'EQIX'])
  })

  it('un ESPERAR con buen score no adelanta a un ENTRADA', () => {
    // ODFL puntúa 68 y aun así va detrás: por definición sigue cayendo.
    const pos = ordenar(reales)
    expect(pos.indexOf('ODFL')).toBeGreaterThan(pos.indexOf('EQIX'))
  })

  it('dentro del mismo timing manda el score', () => {
    // Que un ENTRADA flojo no encabece la pantalla.
    const pos = ordenar(reales)
    expect(pos.indexOf('THC')).toBeLessThan(pos.indexOf('EQIX'))
  })

  it('sin timing no se promociona: va al final', () => {
    const conHuecos: Idea[] = [
      { ticker: 'SINDATO', value_score: 99 },
      { ticker: 'ESPERA', entry_readiness: 'ESPERAR', value_score: 10 },
    ]
    expect(ordenar(conHuecos)).toEqual(['ESPERA', 'SINDATO'])
  })

  it('el orden de accionabilidad es entrada, vigilar, esperar', () => {
    expect(ORDEN_TIMING.ENTRADA).toBeLessThan(ORDEN_TIMING.VIGILAR)
    expect(ORDEN_TIMING.VIGILAR).toBeLessThan(ORDEN_TIMING.ESPERAR)
  })

  it('invertir la dirección invierte los grupos', () => {
    const asc = [...reales]
      .sort((a, b) => comparaPorTiming(a as never, b as never, 'asc'))
      .map(i => i.ticker)
    expect(asc[0]).toBe('ODFL')
  })
})
