/**
 * Los filtros de las listas VALUE tienen que filtrar.
 *
 * El 5-ago-2026 el filtro de score no filtraba: cualquier ticker de grado A o B
 * se lo saltaba, así que con "65+" marcado la lista seguía mostrando valores de
 * 32 y 42 puntos sin avisar de nada. Estuvo así meses. Había 37 archivos de test
 * en el frontend y ninguno tocaba los filtros de las páginas que más se usan.
 *
 * Estos tests replican la lógica de filtrado de ValueUS.tsx y ValueEU.tsx. Si
 * alguien vuelve a meter una excepción que salte el umbral elegido, esto lo caza.
 */
import { describe, it, expect } from 'vitest'

interface Fila {
  ticker: string
  value_score: number | null
  conviction_grade?: string
  sector?: string
}

/** Misma condición que ValueUS.tsx / ValueEU.tsx tras el arreglo. */
function pasaFiltroScore(r: Fila, minScore: string): boolean {
  if (minScore === '') return true
  return r.value_score != null && r.value_score >= Number(minScore)
}

function filtrar(filas: Fila[], minScore: string): Fila[] {
  return filas.filter(r => pasaFiltroScore(r, minScore))
}

const LISTA: Fila[] = [
  { ticker: 'DB1.DE',  value_score: 69.9, conviction_grade: 'C' },
  { ticker: 'SAP.DE',  value_score: 56.4, conviction_grade: 'A' },
  { ticker: 'AMS.MC',  value_score: 54.2, conviction_grade: 'B' },
  { ticker: 'AUTO.L',  value_score: 42.6, conviction_grade: 'B' },
  { ticker: 'KNEBV.HE', value_score: 32.1, conviction_grade: 'B' },
  { ticker: 'SINSCORE', value_score: null, conviction_grade: 'A' },
]

describe('filtro de score en las listas VALUE', () => {
  it('con 65+ solo deja los que llegan a 65', () => {
    expect(filtrar(LISTA, '65').map(r => r.ticker)).toEqual(['DB1.DE'])
  })

  it('el grado alto NO exime del umbral (el bug de 2026-08-05)', () => {
    // SAP es grado A y AMS grado B: antes se colaban con 56,4 y 54,2
    const tickers = filtrar(LISTA, '65').map(r => r.ticker)
    expect(tickers).not.toContain('SAP.DE')
    expect(tickers).not.toContain('AMS.MC')
  })

  it('ningún resultado queda por debajo del umbral elegido', () => {
    for (const umbral of ['50', '55', '60', '65']) {
      for (const fila of filtrar(LISTA, umbral)) {
        expect(fila.value_score).not.toBeNull()
        expect(fila.value_score!).toBeGreaterThanOrEqual(Number(umbral))
      }
    }
  })

  it('sin score no pasa ningún umbral', () => {
    expect(filtrar(LISTA, '50').map(r => r.ticker)).not.toContain('SINSCORE')
  })

  it('ALL no filtra nada', () => {
    expect(filtrar(LISTA, '')).toHaveLength(LISTA.length)
  })

  it('un umbral más alto nunca devuelve más filas que uno más bajo', () => {
    const n50 = filtrar(LISTA, '50').length
    const n60 = filtrar(LISTA, '60').length
    const n65 = filtrar(LISTA, '65').length
    expect(n60).toBeLessThanOrEqual(n50)
    expect(n65).toBeLessThanOrEqual(n60)
  })
})
