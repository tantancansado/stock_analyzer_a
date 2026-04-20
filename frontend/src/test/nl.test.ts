import { describe, expect, it } from 'vitest'
import {
  nlAlert,
  nlBounceConfidence,
  nlBounceSetup,
  nlGrade,
  nlInsiderActivity,
  nlMacroSignal,
  nlMarketRegime,
  nlOptionsSignal,
  nlPositionStatus,
  nlValuation,
  nlValueScore,
  scoreColor,
  plColor,
  pctLabel,
  currencyLabel,
} from '@/lib/nl'

describe('nl helpers', () => {
  it('describes value scores and grades', () => {
    expect(nlValueScore(82, 'a')).toContain('Grado A')
    expect(nlValueScore(35)).toContain('Puntuación baja')
    expect(nlGrade('excellent')).toContain('Alta convicción')
    expect(nlGrade('Z')).toBe('Grado Z')
  })

  it('builds bounce setup narratives with extras and earnings risk', () => {
    const text = nlBounceSetup({
      ticker: 'AAPL',
      drawdown_pct: -18,
      rsi: 22,
      rsi_tier: 'EXTREMO',
      value_score: 67,
      days_to_earnings: 4,
      earnings_warning: true,
      consecutive_down_days: 4,
      dark_pool_signal: 'ACCUMULATION',
      connors_signal: true,
      hammer_candle: true,
    })

    expect(text).toContain('4 sesiones consecutivas')
    expect(text).toContain('sobreventa extrema')
    expect(text).toContain('VALUE 67pts')
    expect(text).toContain('Connors RSI2')
    expect(text).toContain('earnings en 4 días')
  })

  it('describes bounce confidence buckets', () => {
    expect(nlBounceConfidence(80)).toContain('Muy alta')
    expect(nlBounceConfidence(50)).toContain('moderada')
    expect(nlBounceConfidence(10)).toContain('Señal débil')
  })

  it('describes portfolio position states and warnings', () => {
    const text = nlPositionStatus({
      pl_pct: -9,
      action: 'VENDER',
      cerebro_exit: true,
      cerebro_trap: true,
      cerebro_smart_money: true,
      days_to_earnings: 3,
      earnings_warning: true,
      optimal_size_pct: 4,
      portfolio_pct: 8,
    })

    expect(text).toContain('stop loss superado')
    expect(text).toContain('señal de salida activa')
    expect(text).toContain('trampa de dividendo')
    expect(text).toContain('Smart money activo')
    expect(text).toContain('earnings en 3 días')
    expect(text).toContain('sobreponderada')
  })

  it('describes valuation scenarios', () => {
    const text = nlValuation({
      ticker: 'AAPL',
      current_price: 100,
      intrinsic_value: 130,
      ev_fcf: 14,
      fcf_yield_pct: 8.2,
    })

    expect(text).toContain('descuento del 30%')
    expect(text).toContain('EV/FCF 14.0x')
    expect(text).toContain('FCF yield del 8.2%')
  })

  it('describes alert, regime, and macro messages', () => {
    expect(nlAlert({ type: 'exit_signal', ticker: 'aapl', severity: 'HIGH' })).toContain('AAPL')
    expect(nlMarketRegime('neutral')).toContain('Mercado lateral')
    expect(nlMarketRegime('custom', 20)).toContain('Régimen débil')
    expect(nlMacroSignal('INFLATION', 3.2)).toContain('3.2%')
    expect(nlMacroSignal('RATE_CUT')).toContain('Bajada de tipos')
  })

  it('describes options and insider activity', () => {
    expect(nlOptionsSignal({ signal: 'BULLISH', premium: 2_500_000 })).toContain('$2.5M')
    expect(nlOptionsSignal({ signal: 'X', interpretation: 'PUT_COVERING', premium: 50_000 })).toContain('Cobertura de puts')
    expect(nlInsiderActivity({ confidence: 85, transaction_type: 'BUY', value_usd: 2_000_000 })).toContain('$2.0M')
    expect(nlInsiderActivity({ confidence: 20, transaction_type: 'SELL' })).toContain('venta de directivos')
  })

  it('formats score colors and labels', () => {
    expect(scoreColor(75)).toBe('text-emerald-400')
    expect(scoreColor(10)).toBe('text-red-400')
    expect(plColor(4)).toBe('text-green-400')
    expect(plColor(-9)).toBe('text-red-400')
    expect(pctLabel(3.2)).toBe('+3.2%')
    expect(pctLabel(-3.2)).toBe('-3.2%')
    expect(currencyLabel(1_500_000)).toBe('$1.5M')
    expect(currencyLabel(2_500, 'EUR')).toBe('€3K')
  })
})
