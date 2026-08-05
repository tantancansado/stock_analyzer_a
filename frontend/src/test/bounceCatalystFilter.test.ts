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

type CatalystFlags = Record<string, { motivo: string }>

/** Misma condición que BounceTrader.tsx / BroadBounceView.tsx. */
function pasaFiltroCatalizador(s: Setup, flags: CatalystFlags): boolean {
  return !flags[s.ticker.toUpperCase()]
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
