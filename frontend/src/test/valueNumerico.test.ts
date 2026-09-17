/**
 * El tipo decía `number`, el dato era texto, y la página se caía entera.
 *
 * 17-sep-2026, en el móvil: «e.rr_operativo.toFixed is not a function». El CSV
 * llega como texto y `parseValueRows` convierte a número SOLO los campos que
 * están en `VALUE_NUMERIC`, una lista que se mantiene a mano. `rr_operativo` se
 * añadió al backend y a la interfaz, pero no a esa lista: llegaba como cadena,
 * el guardia `!= null` daba true —una cadena no es null— y `.toFixed` no existe
 * en un string. Pantalla de error, no un número mal puesto.
 *
 * Había diez campos así, no uno: los cinco de soportes, ai_confidence,
 * ml_confidence, ml_win_prob y magic_formula_rank. Ninguno daba síntoma hasta
 * que alguien abría la página que lo pintaba.
 */
import { readFileSync } from 'fs'
import { join } from 'path'

import { describe, expect, it } from 'vitest'

import { VALUE_NUMERIC, parseValueRows } from '../api/client'

const fuente = readFileSync(join(__dirname, '..', 'api', 'client.ts'), 'utf-8')

describe('VALUE_NUMERIC contra la interfaz', () => {
  it('todo campo declarado number se convierte a número', () => {
    const i = fuente.indexOf('interface ValueOpportunity')
    const cuerpo = fuente.slice(i, fuente.indexOf('\n}', i))
    const declarados = [...cuerpo.matchAll(/^\s*(\w+)\??:\s*number(?:\s*\|\s*null)?\s*$/gm)]
      .map(m => m[1])
    expect(declarados.length).toBeGreaterThan(50)   // el regex sigue encontrando campos

    const sinConvertir = declarados.filter(c => !VALUE_NUMERIC.has(c))
    expect(sinConvertir, `declarados number pero no convertidos: ${sinConvertir.join(', ')}`)
      .toEqual([])
  })
})

describe('parseValueRows', () => {
  it('convierte de verdad, no deja la cadena', () => {
    const [fila] = parseValueRows('ticker,rr_operativo,soporte_nivel\nBR,2.4,158.3\n')
    expect(typeof fila.rr_operativo).toBe('number')
    expect(fila.rr_operativo).toBe(2.4)
    expect(typeof fila.soporte_nivel).toBe('number')
  })

  it('una celda vacía es null, no la cadena vacía', () => {
    // Este es el caso exacto del fallo: `'' != null` es true, y `''.toFixed`
    // no existe. Tiene que llegar como null para que el guardia funcione.
    const [fila] = parseValueRows('ticker,rr_operativo\nBR,\n')
    expect(fila.rr_operativo).toBeNull()
  })

  it('un texto que no es número es null, no NaN', () => {
    const [fila] = parseValueRows('ticker,rr_operativo\nBR,n/d\n')
    expect(fila.rr_operativo).toBeNull()
  })

  it('el número sobrevive a toFixed, que es lo que rompía', () => {
    const [fila] = parseValueRows('ticker,rr_operativo\nBR,2.44\n')
    expect(fila.rr_operativo!.toFixed(1)).toBe('2.4')
  })
})
