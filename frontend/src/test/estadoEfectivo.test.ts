import { describe, it, expect } from 'vitest'
import { estadoEfectivo } from '@/lib/estadoEntrada'

describe('un solo estado de entrada por fila', () => {
  it('en suelo pero con veredicto de esperar (resultados en 3 días) no es «Entra»', () => {
    // CNI, 27-oct-2026: filtro «Entra» con etiqueta «ESPERA» en la misma fila
    expect(estadoEfectivo('ENTRADA', 'WAIT')).toBe('VIGILAR')
  })
  it('en suelo y sin nada en contra sí es «Entra»', () => {
    expect(estadoEfectivo('ENTRADA', 'ENTRY')).toBe('ENTRADA')
    expect(estadoEfectivo('ENTRADA', undefined)).toBe('ENTRADA')
  })
  it('evitar siempre manda', () => {
    expect(estadoEfectivo('ENTRADA', 'AVOID')).toBe('ESPERAR')
    expect(estadoEfectivo('VIGILAR', 'AVOID')).toBe('ESPERAR')
  })
  it('vigilar y esperar no cambian con un WAIT', () => {
    expect(estadoEfectivo('VIGILAR', 'WAIT')).toBe('VIGILAR')
    expect(estadoEfectivo('ESPERAR', 'WAIT')).toBe('ESPERAR')
  })
  it('sin estado técnico no se inventa uno', () => {
    expect(estadoEfectivo(null, 'WAIT')).toBeNull()
  })
})
