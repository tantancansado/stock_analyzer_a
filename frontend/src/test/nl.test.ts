import { describe, expect, it } from 'vitest'
import {
  nlAlert,
  nlRegimen,
  nlRegimenTono,
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

    // Los dos hechos por separado: el -18% es desde máximos, no de 4 sesiones.
    expect(text).toContain('Caída del 18% desde máximos')
    expect(text).toContain('4 sesiones consecutivas a la baja')
    expect(text).not.toContain('18% en 4 sesiones')
    expect(text).toContain('sobreventa extrema')
    expect(text).toContain('VALUE 67pts')
    expect(text).toContain('Connors RSI2')
    expect(text).toContain('earnings en 4 días')
  })

  describe('nlRegimen', () => {
    // El detector trabaja con constantes tipo CONFIRMED_UPTREND. En el badge
    // de Value se pintaba tal cual: jerga interna, en inglés y con guiones
    // bajos, al lado del título.
    it('traduce los regímenes conocidos', () => {
      expect(nlRegimen('CONFIRMED_UPTREND')).toBe('Alcista confirmada')
      expect(nlRegimen('CORRECTION')).toBe('Corrección')
      expect(nlRegimen('BEAR')).toBe('Bajista')
    })

    it('devuelve vacío cuando el régimen es "no lo sé"', () => {
      // Un badge que diga "desconocido" ocupa el sitio de un aviso de verdad
      // sin informar de nada.
      for (const v of ['UNKNOWN', 'N/A', 'NONE', 'ERROR', '', null, undefined]) {
        expect(nlRegimen(v)).toBe('')
      }
    })

    it('un régimen nuevo sale legible, no en SNAKE_CASE', () => {
      expect(nlRegimen('SIDEWAYS_CHOP')).toBe('Sideways chop')
    })

    it('no distingue mayúsculas ni espacios sobrantes', () => {
      expect(nlRegimen('  confirmed_uptrend ')).toBe('Alcista confirmada')
    })

    it('el tono se decide sobre el valor CRUDO, no sobre la etiqueta', () => {
      // Al traducir, "Alcista confirmada" dejó de contener "UP" y el badge
      // salía en ámbar de advertencia con el mercado en tendencia alcista.
      expect(nlRegimenTono('CONFIRMED_UPTREND')).toBe('green')
      expect(nlRegimenTono('CORRECTION')).toBe('red')
      expect(nlRegimenTono('BEAR')).toBe('red')
      expect(nlRegimenTono('NEUTRAL')).toBe('yellow')
      expect(nlRegimenTono(nlRegimen('CONFIRMED_UPTREND'))).not.toBe('green')  // por eso hay que pasarle el crudo
    })
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
