import { describe, expect, it } from 'vitest'
import { mejoresYPeores } from '@/pages/SignalStats'
import type { TimeseriesRow } from '@/api/client'

/**
 * Con pocos períodos que cualifican, «mejores» y «peores» se solapaban: el
 * mismo mes salía puntuado arriba y abajo en la misma pantalla.
 *
 * Caso real visto el 24-sep-2026 en /signal-stats, pestaña Mes: con 4 períodos
 * que llegaban al mínimo de 5 señales, "mar 2026" y "feb 2026" aparecían a la
 * vez en "Mejores períodos" (3º y 2º) y en "Peores períodos" (2º y 3º).
 */

function fila(label: string, win_rate: number, signals = 30): TimeseriesRow {
  return {
    label, signals, horizonte: '90d', horizonte_2: '180d',
    win_rate, win_rate_2: null, avg_return: 1, avg_return_2: null,
  }
}

describe('mejoresYPeores', () => {
  it('el caso real: 4 períodos no repiten ninguno entre las dos listas', () => {
    const rows = [
      fila('may 2026', 83.3, 6),
      fila('feb 2026', 63.5, 74),
      fila('mar 2026', 56.6, 1293),
      fila('abr 2026', 37.2, 148),
    ]
    const { best, worst } = mejoresYPeores(rows)
    const enLasDos = best.map(r => r.label).filter(l => worst.some(w => w.label === l))
    expect(enLasDos).toEqual([])
    expect(best.map(r => r.label)).toEqual(['may 2026', 'feb 2026', 'mar 2026'])
    // Solo queda "abr 2026" tras quitar el solape — la lista sale más corta,
    // no repetida.
    expect(worst.map(r => r.label)).toEqual(['abr 2026'])
  })

  it('con muchos períodos, mejores y peores van llenos y sin solape', () => {
    const rows = [90, 80, 70, 60, 50, 40, 30, 20].map((wr, i) => fila(`p${i}`, wr))
    const { best, worst } = mejoresYPeores(rows)
    expect(best).toHaveLength(3)
    expect(worst).toHaveLength(3)
    const enLasDos = best.map(r => r.label).filter(l => worst.some(w => w.label === l))
    expect(enLasDos).toEqual([])
  })

  it('menos de 2 períodos cualificados no devuelve nada', () => {
    const { best, worst } = mejoresYPeores([fila('único', 50, 10)])
    expect(best).toEqual([])
    expect(worst).toEqual([])
  })

  it('un período con menos de 5 señales no cualifica para el ranking', () => {
    const rows = [fila('a', 90, 4), fila('b', 10, 4)]
    expect(mejoresYPeores(rows).best).toEqual([])
  })

  it('un win_rate nulo (horizonte sin datos todavía) no cualifica', () => {
    const rows = [
      fila('a', 90), fila('b', 80),
      { ...fila('c', 0), win_rate: null },
    ]
    const { best } = mejoresYPeores(rows)
    expect(best.map(r => r.label)).not.toContain('c')
  })
})
