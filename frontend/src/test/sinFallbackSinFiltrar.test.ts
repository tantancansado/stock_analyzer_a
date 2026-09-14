import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * El gate de calidad es fail-CLOSED: si Claude no verifica un pick, no se
 * publica. La pantalla era fail-OPEN: si no se publicó ninguno, caía al
 * fichero SIN filtrar y enseñaba el universo entero con el mismo aspecto.
 *
 * Los dos se anulaban. El 11-sep-2026 se agotó el presupuesto de Claude,
 * value_opportunities_filtered.csv quedó en 0 filas y la app estuvo tres días
 * enseñando 54 ideas sin verificar sin avisar de nada — mientras el aviso de
 * Telegram decía "0 filas".
 *
 * Criterio del usuario, literal: "0 señales antes que señales falsas".
 */

const CLIENT = readFileSync(join(__dirname, '..', 'api', 'client.ts'), 'utf-8')

/** Cuerpo de una función exportada, desde su nombre hasta el siguiente export. */
function cuerpoDe(nombre: string): string {
  const i = CLIENT.indexOf(`export const ${nombre}`)
  expect(i, `no se encontró ${nombre} en client.ts`).toBeGreaterThan(-1)
  const j = CLIENT.indexOf('\nexport ', i + 1)
  return CLIENT.slice(i, j === -1 ? undefined : j)
}

describe('las páginas filtradas no caen al fichero sin filtrar', () => {
  it('Value US solo lee value_opportunities_filtered.csv', () => {
    const cuerpo = cuerpoDe('fetchValueOpportunities')
    expect(cuerpo).toContain('value_opportunities_filtered.csv')
    // El sin-filtrar no tiene siquiera columna ai_verified: nada de lo que hay
    // ahí ha pasado por el gate.
    const sinFiltrar = cuerpo.match(/'value_opportunities\.csv'/g) ?? []
    expect(sinFiltrar, 'no debe leerse el CSV sin filtrar').toHaveLength(0)
  })

  it('Momentum solo lee momentum_opportunities_filtered.csv', () => {
    const cuerpo = cuerpoDe('fetchMomentumOpportunities')
    expect(cuerpo).toContain('momentum_opportunities_filtered.csv')
    const sinFiltrar = cuerpo.match(/'momentum_opportunities\.csv'/g) ?? []
    expect(sinFiltrar, 'no debe leerse el CSV sin filtrar').toHaveLength(0)
  })

  it('cero verificados es una respuesta, no un motivo para buscar en otro sitio', () => {
    // El fallback vivía en un bucle `for (const filename of [filtrado, sin_filtrar])`
    // con un `if (data.length === 0) continue`. Ese `continue` era el bug: trataba
    // "ninguno pasó el filtro" como "este fichero no sirve, prueba el siguiente".
    const cuerpo = cuerpoDe('fetchValueOpportunities')
    expect(cuerpo).not.toMatch(/length === 0\)\s*continue/)
  })
})
