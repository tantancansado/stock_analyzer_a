import { describe, expect, it } from 'vitest'

import { lecturaIndice } from '@/pages/MacroRadar'

// 12-nov-2026: «yo no quiero datos técnicos, quiero que la IA interprete esos datos
// técnicos y los traduzca a lenguaje humano». Una frase por índice, sin RSI ni MACD.
describe('lectura de un índice en lenguaje normal', () => {
  it('el S&P de la captura del 12-nov', () => {
    const t = lecturaIndice({ name: 'S&P 500', ytd_pct: 12.1, weinstein_stage: 2, speed_63d: -2.1, pct_from_52w_high: -2.5 })
    expect(t).toBe('S&P 500: +12,1 % en el año; sigue al alza; a un 2,5 % de su máximo.')
  })

  it('al alza pero cayendo en tres meses lo dice', () => {
    const t = lecturaIndice({ name: 'Nasdaq 100', ytd_pct: 13, weinstein_stage: 2, speed_63d: -5.6, pct_from_52w_high: -9.1 })
    expect(t).toContain('sigue al alza, aunque en tres meses ha bajado un 5,6 %')
  })

  it('no lleva jerga técnica', () => {
    const t = lecturaIndice({ name: 'Russell 2000', ytd_pct: -3, weinstein_stage: 4, speed_63d: -8, pct_from_52w_high: -15 })
    expect(t).not.toMatch(/RSI|MACD|MA\d|Stage|Weinstein|Minervini/)
    expect(t).toContain('tendencia bajista')
  })
})
