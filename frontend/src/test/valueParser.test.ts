/**
 * Tests para el parseo de VALUE CSVs.
 *
 * Invariantes críticas:
 * 1. Toda columna declarada como number|null en ValueOpportunity debe estar en VALUE_NUMERIC
 *    — si falta, llega como string y .toFixed() / comparaciones numéricas rompen en runtime.
 * 2. parseValueRows convierte correctamente los campos numéricos desde el CSV.
 * 3. Los campos booleanos se parsean como boolean, no string.
 * 4. Campos ausentes o vacíos no crashan.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      interceptors: { request: { use: vi.fn() } },
    })),
  },
}))

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
      refreshSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}))

// Todos los campos de ValueOpportunity tipados como number | null | undefined.
// Si añades un campo numérico a la interfaz, añádelo aquí también —
// este array es el contrato que garantiza que VALUE_NUMERIC lo cubre.
const NUMERIC_FIELDS_IN_INTERFACE = [
  'current_price',
  'value_score',
  'conviction_score',
  'conviction_positives',
  'conviction_red_flags',
  'target_price_analyst',
  'target_price_analyst_high',
  'target_price_analyst_low',
  'analyst_upside_pct',
  'analyst_count',
  'fcf_yield_pct',
  'risk_reward_ratio',
  'dividend_yield_pct',
  'days_to_earnings',
  'entry_price',
  'stop_loss',
  'target_price',
  'proximity_to_52w_high',
  'piotroski_score',
  'ebit_ev_yield',
  'roic_greenblatt',
  'peg_ratio',
  'roe_pct',
  'profit_margin_pct',
  'revenue_growth_pct',
  'pe_forward',
  'pe_trailing',
  'market_cap',
  'payout_ratio_pct',
  'dividend_rate',
  'five_yr_avg_dividend_yield_pct',
  'shares_change_pct',
  'interest_coverage',
  'analyst_revision_momentum',
  'fundamental_score',
  'earnings_quality_score',
  'growth_acceleration_score',
  'relative_strength_score',
  'financial_health_score',
  'catalyst_timing_score',
  'rs_line_score',
  'rs_line_percentile',
  'eps_growth_yoy',
  'eps_accel_quarters',
  'rev_growth_yoy',
  'rev_accel_quarters',
  'fifty_two_week_high',
  'trend_template_score',
  'target_price_dcf',
  'target_price_dcf_upside_pct',
  'target_price_pe',
  'target_price_pe_upside_pct',
  'fcf_per_share',
  'short_percent_float',
  'short_ratio',
  'market_cape',
  'pct_from_52w_high',
  'oe_ai_adjustment',
  'target_change_7d_pct',
  'target_change_30d_pct',
  'upgrade_days_14d',
  'downgrade_days_14d',
  'target_revision_bonus',
  'piotroski_bonus',
  'fcf_bonus',
  'dividend_bonus',
  'buyback_bonus',
  'revision_bonus',
  'rr_bonus',
  'sector_bonus',
  'insider_bonus',
  'institutional_bonus',
  'options_bonus',
  'mr_bonus',
  'hf_bonus',
  'days_in_list',
  'profitability_penalty',
  'cerebro_score_adj',
  'hedge_fund_count',
  'hv_30d',
  'atm_iv',
  'iv_ratio',
  'iv_premium_pts',
  'ml_win_probability',
  'ml_score',
] as const

const MINIMAL_CSV = `ticker,value_score,ml_score,ml_win_probability,analyst_upside_pct,fcf_yield_pct,buyback_active,earnings_warning,company_name,conviction_grade
AAPL,75.5,86.3,0.72,23.5,4.2,True,False,Apple Inc.,B
MSFT,68.0,50.0,0.45,18.0,3.1,False,True,Microsoft Corp.,A
NEWCO,55.0,,,,False,False,New Company,`

async function loadClient() {
  vi.resetModules()
  return import('@/api/client')
}

describe('VALUE_NUMERIC coverage', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('incluye todos los campos numéricos de ValueOpportunity', async () => {
    const { VALUE_NUMERIC } = await loadClient()
    const missing = NUMERIC_FIELDS_IN_INTERFACE.filter(f => !VALUE_NUMERIC.has(f))
    expect(missing).toEqual([])
  })

  it('incluye ml_score (regresión: llegaba como string → .toFixed() crashaba)', async () => {
    const { VALUE_NUMERIC } = await loadClient()
    expect(VALUE_NUMERIC.has('ml_score')).toBe(true)
  })

  it('incluye ml_win_probability', async () => {
    const { VALUE_NUMERIC } = await loadClient()
    expect(VALUE_NUMERIC.has('ml_win_probability')).toBe(true)
  })
})

describe('parseValueRows — tipos', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('parsea el número correcto de filas', async () => {
    const { parseValueRows } = await loadClient()
    expect(parseValueRows(MINIMAL_CSV)).toHaveLength(3)
  })

  it('value_score llega como number', async () => {
    const { parseValueRows } = await loadClient()
    const rows = parseValueRows(MINIMAL_CSV)
    expect(typeof rows[0].value_score).toBe('number')
    expect(rows[0].value_score).toBe(75.5)
  })

  it('ml_score llega como number y admite .toFixed() sin crash (regresión)', async () => {
    const { parseValueRows } = await loadClient()
    const rows = parseValueRows(MINIMAL_CSV)
    expect(typeof rows[0].ml_score).toBe('number')
    expect(rows[0].ml_score).toBe(86.3)
    expect(() => rows[0].ml_score!.toFixed(0)).not.toThrow()
    expect(rows[0].ml_score!.toFixed(0)).toBe('86')
  })

  it('ml_win_probability llega como number', async () => {
    const { parseValueRows } = await loadClient()
    const rows = parseValueRows(MINIMAL_CSV)
    expect(typeof rows[0].ml_win_probability).toBe('number')
    expect(rows[0].ml_win_probability).toBeCloseTo(0.72)
  })

  it('ml_score = 50.0 llega como number (no string)', async () => {
    const { parseValueRows } = await loadClient()
    const rows = parseValueRows(MINIMAL_CSV)
    expect(typeof rows[1].ml_score).toBe('number')
    expect(rows[1].ml_score).toBe(50)
  })

  it('campo numérico vacío llega como null', async () => {
    const { parseValueRows } = await loadClient()
    const rows = parseValueRows(MINIMAL_CSV)
    expect(rows[2].ml_score).toBeNull()
    expect(rows[2].ml_win_probability).toBeNull()
    expect(rows[2].analyst_upside_pct).toBeNull()
  })

  it('buyback_active llega como boolean', async () => {
    const { parseValueRows } = await loadClient()
    const rows = parseValueRows(MINIMAL_CSV)
    expect(rows[0].buyback_active).toBe(true)
    expect(typeof rows[0].buyback_active).toBe('boolean')
  })

  it('earnings_warning True/False llega como boolean', async () => {
    const { parseValueRows } = await loadClient()
    const rows = parseValueRows(MINIMAL_CSV)
    expect(rows[0].earnings_warning).toBe(false)
    expect(rows[1].earnings_warning).toBe(true)
  })

  it('conviction_grade vacío llega como undefined (no string vacío)', async () => {
    const { parseValueRows } = await loadClient()
    const rows = parseValueRows(MINIMAL_CSV)
    expect(rows[2].conviction_grade).toBeUndefined()
  })
})

// Regresión: antes fetchValueOpportunities priorizaba value_conviction.csv
// (solo grade≥B) y perdía los tickers nuevos del día que aún no tenían grade.

describe('parseValueRows — tickers sin conviction_grade', () => {
  beforeEach(() => { vi.clearAllMocks() })

  const CSV_MIXED = `ticker,value_score,company_name,conviction_grade
CLPBY,69.8,Coloplast AS,B
DSGX,56.4,Descartes Systems,
CDNS,56.4,Cadence Design,
ICE,56.0,Intercontinental Exchange,
OTIS,55.1,Otis Worldwide,`

  it('devuelve todos los tickers incluyendo los sin grade (regresión)', async () => {
    const { parseValueRows } = await loadClient()
    const rows = parseValueRows(CSV_MIXED)
    expect(rows).toHaveLength(5)
    const tickers = rows.map(r => r.ticker)
    expect(tickers).toContain('DSGX')
    expect(tickers).toContain('CDNS')
    expect(tickers).toContain('ICE')
    expect(tickers).toContain('OTIS')
  })

  it('los tickers sin grade tienen conviction_grade undefined', async () => {
    const { parseValueRows } = await loadClient()
    const rows = parseValueRows(CSV_MIXED)
    const dsgx = rows.find(r => r.ticker === 'DSGX')!
    expect(dsgx.conviction_grade).toBeUndefined()
  })

  it('el ticker con grade B lo conserva', async () => {
    const { parseValueRows } = await loadClient()
    const rows = parseValueRows(CSV_MIXED)
    const clpby = rows.find(r => r.ticker === 'CLPBY')!
    expect(clpby.conviction_grade).toBe('B')
  })
})
