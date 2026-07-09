import { describe, it, expect } from 'vitest'
import { getTickerDecision, type OeModelInput } from '@/lib/tickerDecision'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Modelo OE sano: buy 100, cotizando a 120 (por encima → espera). */
function makeOe(overrides: Partial<OeModelInput> = {}): OeModelInput {
  return {
    current_price: 120,
    buy_price: 100,
    exit_price: 180,
    exit_year: 2030,
    safety_margin_pct: -20,
    target_return_pct: 15,
    ntm_fcf_yield_pct: 4.2,
    historical_fcf_per_share: { '2021': 3, '2022': 3.5, '2023': 4, '2024': 4.4, '2025': 5 },
    red_flags: [],
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// SIN MODELO
// ---------------------------------------------------------------------------

describe('getTickerDecision — sin modelo', () => {
  it('sin entrada OE devuelve sin_modelo', () => {
    const d = getTickerDecision({ oe: null })
    expect(d.kind).toBe('sin_modelo')
    expect(d.buyPrice).toBeNull()
  })

  it('con OE pero sin buy_price devuelve sin_modelo', () => {
    const d = getTickerDecision({ oe: makeOe({ buy_price: null }) })
    expect(d.kind).toBe('sin_modelo')
  })
})

// ---------------------------------------------------------------------------
// DATOS NO FIABLES (casos HESAY / ASAZY)
// ---------------------------------------------------------------------------

describe('getTickerDecision — calidad de datos', () => {
  it('histórico de FCF vacío → no_fiable (caso HESAY)', () => {
    const d = getTickerDecision({ oe: makeOe({ historical_fcf_per_share: {} }) })
    expect(d.kind).toBe('no_fiable')
    expect(d.dataFlags[0]).toContain('Histórico de FCF')
  })

  it('FCF yield implausible → no_fiable (caso ASAZY)', () => {
    const d = getTickerDecision({ oe: makeOe({ ntm_fcf_yield_pct: 43.9 }) })
    expect(d.kind).toBe('no_fiable')
    expect(d.dataFlags[0]).toContain('implausible')
  })

  it('red flag high del pipeline → no_fiable con su mensaje', () => {
    const d = getTickerDecision({
      oe: makeOe({ red_flags: [{ code: 'X', severity: 'high', msg: 'FCF negativo 3 años' }] }),
    })
    expect(d.kind).toBe('no_fiable')
    expect(d.dataFlags).toContain('FCF negativo 3 años')
  })

  it('validador IA marca datos no RELIABLE → no_fiable', () => {
    const d = getTickerDecision({ oe: makeOe(), oeAi: { data_quality: 'UNRELIABLE' } })
    expect(d.kind).toBe('no_fiable')
  })

  it('red flag medium NO bloquea — va a blockers, no a dataFlags', () => {
    const d = getTickerDecision({
      oe: makeOe({ red_flags: [{ code: 'X', severity: 'medium', msg: 'FCF cayó el último año' }] }),
    })
    expect(d.kind).toBe('espera')
    expect(d.blockers).toContain('FCF cayó el último año')
  })
})

// ---------------------------------------------------------------------------
// ESPERA A $X — el caso MA/V: buena empresa, precio por encima del objetivo
// ---------------------------------------------------------------------------

describe('getTickerDecision — espera', () => {
  it('precio por encima del buy_price → espera con el precio en el label', () => {
    const d = getTickerDecision({ oe: makeOe() })
    expect(d.kind).toBe('espera')
    expect(d.label).toBe('ESPERA A $100')
    expect(d.headline).toContain('20%')
  })

  it('usa el precio live si difiere del snapshot del batch', () => {
    // Snapshot decía 120, pero live está a 95 → en zona de compra
    const d = getTickerDecision({ oe: makeOe(), currentPrice: 95 })
    expect(d.kind).toBe('compra')
    expect(d.safetyMarginPct).toBeCloseTo(5, 0)
  })

  it('IA AVOID con precio por encima → sigue siendo espera (el problema es el precio)', () => {
    const d = getTickerDecision({ oe: makeOe(), oeAi: { data_quality: 'RELIABLE', thesis_verdict: 'AVOID', confidence: 80 } })
    expect(d.kind).toBe('espera')
    expect(d.blockers.some(b => b.includes('sobrevaloración'))).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// COMPRA
// ---------------------------------------------------------------------------

describe('getTickerDecision — compra', () => {
  it('precio en zona de compra con datos fiables → compra', () => {
    const d = getTickerDecision({
      oe: makeOe({ current_price: 92, safety_margin_pct: 8 }),
      oeAi: { data_quality: 'RELIABLE', thesis_verdict: 'BUY', confidence: 85 },
    })
    expect(d.kind).toBe('compra')
    expect(d.reasons.some(r => r.includes('Margen de seguridad'))).toBe(true)
    expect(d.reasons.some(r => r.includes('validador IA'))).toBe(true)
  })

  it('earnings próximos no cambian el veredicto pero aparecen como bloqueo', () => {
    const d = getTickerDecision({ oe: makeOe({ current_price: 92 }), daysToEarnings: 3 })
    expect(d.kind).toBe('compra')
    expect(d.blockers.some(b => b.includes('Earnings en 3 días'))).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// EVITA
// ---------------------------------------------------------------------------

describe('getTickerDecision — evita', () => {
  it('upside de consenso ≥30% → evita (hard reject value trap), aunque OE diga compra', () => {
    const d = getTickerDecision({ oe: makeOe({ current_price: 92 }), analystUpsidePct: 45 })
    expect(d.kind).toBe('evita')
    expect(d.blockers.some(b => b.includes('value trap'))).toBe(true)
  })

  it('IA AVOID con precio YA en zona de compra → evita (el problema no es el precio)', () => {
    const d = getTickerDecision({
      oe: makeOe({ current_price: 92 }),
      oeAi: { data_quality: 'RELIABLE', thesis_verdict: 'AVOID', confidence: 75 },
    })
    expect(d.kind).toBe('evita')
    expect(d.blockers.some(b => b.includes('rechaza la tesis'))).toBe(true)
  })

  it('upside en zona dorada [10,25) es razón, no bloqueo', () => {
    const d = getTickerDecision({ oe: makeOe(), analystUpsidePct: 18 })
    expect(d.kind).toBe('espera')
    expect(d.reasons.some(r => r.includes('zona dorada'))).toBe(true)
  })

  it('upside negativo del consenso es bloqueo pero el veredicto lo decide OE', () => {
    const d = getTickerDecision({ oe: makeOe(), analystUpsidePct: -5 })
    expect(d.kind).toBe('espera')
    expect(d.blockers.some(b => b.includes('consenso'))).toBe(true)
  })
})
