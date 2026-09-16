/**
 * bounce_alerts.py descarta un setup del aviso de Telegram si detecta un
 * catalizador negativo grave reciente (bounce_catalyst_check.py). Hasta el
 * 5-ago-2026 ese veredicto se calculaba y se tiraba: la app (BounceTrader.tsx,
 * BroadBounceView.tsx) seguía enseñando el mismo setup sin el aviso que sí
 * llegó por Telegram.
 *
 * Estos tests replican la lógica de filtrado por bounce_catalyst_flags.json.
 */
import { describe, it, expect } from 'vitest'

interface Setup {
  ticker: string
}

type CatalystFlags = Record<string, { motivo: string; veredicto?: 'PELIGRO' | 'LIMPIO' }>

/** Misma lógica que BroadBounceView.tsx: TRES estados, no dos.
 *
 * Antes solo se guardaban los PELIGRO, así que «sin flag» quería decir a la vez
 * «comprobado y limpio» y «nunca comprobado» — y los caminos por los que no se
 * comprueba son reales: el paso de alertas sale antes si todos los setups ya se
 * avisaron hace poco, devuelve vacío si no hay saldo, y lleva
 * `continue-on-error` en el workflow. */
function estadoVeto(t: string, flags: CatalystFlags): 'PELIGRO' | 'LIMPIO' | 'SIN_COMPROBAR' {
  const f = flags[t.toUpperCase()]
  if (!f) return 'SIN_COMPROBAR'
  // Los flags escritos antes del 16-sep-2026 no llevan `veredicto` y solo
  // registraban peligros: se siguen leyendo como tales.
  return f.veredicto ?? 'PELIGRO'
}

function pasaFiltroCatalizador(s: Setup, flags: CatalystFlags): boolean {
  return estadoVeto(s.ticker, flags) !== 'PELIGRO'
}

function filtrar(setups: Setup[], flags: CatalystFlags): Setup[] {
  return setups.filter(s => pasaFiltroCatalizador(s, flags))
}

const SETUPS: Setup[] = [
  { ticker: 'ABC' },
  { ticker: 'XYZ' },
  { ticker: 'DEF' },
]

describe('filtro de catalizador negativo en rebotes', () => {
  it('sin flags no excluye nada', () => {
    expect(filtrar(SETUPS, {}).map(s => s.ticker)).toEqual(['ABC', 'XYZ', 'DEF'])
  })

  it('un ticker flaggeado se excluye', () => {
    const flags = { XYZ: { motivo: 'Profit warning' } }
    expect(filtrar(SETUPS, flags).map(s => s.ticker)).toEqual(['ABC', 'DEF'])
  })

  it('la comparación es insensible a mayúsculas del ticker de origen', () => {
    const flags = { XYZ: { motivo: 'Profit warning' } }
    const setups: Setup[] = [{ ticker: 'xyz' }]
    expect(filtrar(setups, flags)).toEqual([])
  })

  it('varios tickers flaggeados se excluyen todos', () => {
    const flags = { ABC: { motivo: 'a' }, DEF: { motivo: 'b' } }
    expect(filtrar(SETUPS, flags).map(s => s.ticker)).toEqual(['XYZ'])
  })
})

describe('los tres estados del veto', () => {
  it('sin flag es SIN_COMPROBAR, no LIMPIO', () => {
    expect(estadoVeto('ABC', {})).toBe('SIN_COMPROBAR')
  })

  it('un LIMPIO registrado se distingue de no haber mirado', () => {
    const flags: CatalystFlags = { ABC: { motivo: '', veredicto: 'LIMPIO' } }
    expect(estadoVeto('ABC', flags)).toBe('LIMPIO')
    expect(estadoVeto('OTRO', flags)).toBe('SIN_COMPROBAR')
  })

  it('un LIMPIO se enseña igual que uno sin comprobar, pero el estado difiere', () => {
    // Los dos pasan el filtro; lo que cambia es que uno se puede anunciar como
    // verificado y el otro no.
    const flags: CatalystFlags = { ABC: { motivo: '', veredicto: 'LIMPIO' } }
    expect(filtrar(SETUPS, flags).map(s => s.ticker)).toEqual(['ABC', 'XYZ', 'DEF'])
    expect(estadoVeto('ABC', flags)).not.toBe(estadoVeto('XYZ', flags))
  })

  it('un flag antiguo sin `veredicto` se sigue leyendo como PELIGRO', () => {
    // Compatibilidad: cuando solo se guardaban los descartados, la mera
    // presencia del flag ERA el peligro. Leerlo como limpio los resucitaría.
    const flags: CatalystFlags = { XYZ: { motivo: 'Profit warning el lunes' } }
    expect(estadoVeto('XYZ', flags)).toBe('PELIGRO')
    expect(filtrar(SETUPS, flags).map(s => s.ticker)).toEqual(['ABC', 'DEF'])
  })
})
