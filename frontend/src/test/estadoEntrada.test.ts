import { describe, expect, it } from 'vitest'
import { ordenaPorEntrada, ORDEN_ENTRADA } from '@/lib/estadoEntrada'

type Fila = { t: string; entry_readiness?: 'ENTRADA' | 'VIGILAR' | 'ESPERAR' | null; opportunity_score: number }

describe('ordenaPorEntrada', () => {
  it('lo que se puede comprar hoy va antes que un ESPERAR con más score', () => {
    const lista: Fila[] = [
      { t: 'MCD', entry_readiness: 'ESPERAR', opportunity_score: 84 },
      { t: 'MA', entry_readiness: 'VIGILAR', opportunity_score: 70 },
      { t: 'XX', entry_readiness: 'ENTRADA', opportunity_score: 55 },
    ]
    expect(ordenaPorEntrada(lista).map(f => f.t)).toEqual(['XX', 'MA', 'MCD'])
  })

  it('a igual estado manda el score', () => {
    const lista: Fila[] = [
      { t: 'A', entry_readiness: 'VIGILAR', opportunity_score: 60 },
      { t: 'B', entry_readiness: 'VIGILAR', opportunity_score: 80 },
    ]
    expect(ordenaPorEntrada(lista).map(f => f.t)).toEqual(['B', 'A'])
  })

  it('sin estado no se promociona: va al final', () => {
    const lista: Fila[] = [
      { t: 'V', entry_readiness: null, opportunity_score: 90 },
      { t: 'MCD', entry_readiness: 'ESPERAR', opportunity_score: 50 },
    ]
    expect(ordenaPorEntrada(lista).map(f => f.t)).toEqual(['MCD', 'V'])
  })

  it('no muta la lista original', () => {
    const lista: Fila[] = [
      { t: 'A', entry_readiness: 'ESPERAR', opportunity_score: 1 },
      { t: 'B', entry_readiness: 'ENTRADA', opportunity_score: 1 },
    ]
    ordenaPorEntrada(lista)
    expect(lista.map(f => f.t)).toEqual(['A', 'B'])
  })

  it('el orden es el mismo que el de Value', () => {
    expect(ORDEN_ENTRADA.ENTRADA).toBeLessThan(ORDEN_ENTRADA.VIGILAR)
    expect(ORDEN_ENTRADA.VIGILAR).toBeLessThan(ORDEN_ENTRADA.ESPERAR)
  })
})
