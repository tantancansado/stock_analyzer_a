import axios from 'axios'
import { supabase } from '@/lib/supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

// Cache session token — onAuthStateChange fires INITIAL_SESSION immediately
// on setup, so no separate getSession() call needed. Interceptor stays sync.
let _cachedToken: string | null = null
let _tokenExpiresAt: number | null = null
supabase.auth.onAuthStateChange((_event, session) => {
  _cachedToken = session?.access_token ?? null
  if (session?.access_token) {
    try {
      const payload = JSON.parse(atob(session.access_token.split('.')[1]))
      _tokenExpiresAt = payload.exp ? payload.exp * 1000 : null
    } catch { _tokenExpiresAt = null }
  } else {
    _tokenExpiresAt = null
  }
})

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
})

// Attach Supabase JWT to every request; refresh proactively if expiring soon
apiClient.interceptors.request.use(async (config) => {
  // Fallback: if onAuthStateChange hasn't fired yet, fetch session directly
  if (!_cachedToken) {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      _cachedToken = session?.access_token ?? null
      if (session?.access_token) {
        const payload = JSON.parse(atob(session.access_token.split('.')[1]))
        _tokenExpiresAt = payload.exp ? payload.exp * 1000 : null
      }
    } catch { /* ignore */ }
  }
  // Proactive refresh if token expires in less than 2 minutes
  if (_cachedToken && _tokenExpiresAt && Date.now() > _tokenExpiresAt - 120_000) {
    try {
      const { data: { session } } = await supabase.auth.refreshSession()
      _cachedToken = session?.access_token ?? null
      if (session?.access_token) {
        const payload = JSON.parse(atob(session.access_token.split('.')[1]))
        _tokenExpiresAt = payload.exp ? payload.exp * 1000 : null
      }
    } catch { /* keep old token */ }
  }
  if (_cachedToken) {
    config.headers.Authorization = `Bearer ${_cachedToken}`
  }
  return config
})

export interface ValueOpportunity {
  ticker: string
  company_name: string
  current_price: number
  value_score: number
  conviction_grade?: string
  conviction_score?: number
  conviction_reasons?: string
  conviction_positives?: number
  conviction_red_flags?: number
  sector?: string
  target_price_analyst?: number
  analyst_upside_pct?: number
  analyst_count?: number
  fcf_yield_pct?: number
  risk_reward_ratio?: number
  dividend_yield_pct?: number
  buyback_active?: boolean
  days_to_earnings?: number
  earnings_warning?: boolean
  market?: string
  entry_price?: number
  stop_loss?: number
  target_price?: number
  thesis?: string
  proximity_to_52w_high?: number
  // Fundamental growth signals
  eps_accelerating?: boolean | null
  eps_accel_quarters?: number | null
  rev_accelerating?: boolean | null
  short_squeeze_potential?: boolean | null
  earnings_catalyst?: boolean | null
  // Piotroski F-Score (Proven: +13.4% annual alpha)
  piotroski_score?: number
  piotroski_label?: string
  // Magic Formula (Greenblatt) + PEG (Lynch)
  ebit_ev_yield?: number
  roic_greenblatt?: number
  magic_formula_rank?: number
  peg_ratio?: number
  // Hedge Fund 13F consensus
  hedge_fund_count?: number
  hedge_fund_names?: string
  // Health/earnings metrics (from global CSV)
  roe_pct?: number
  profit_margin_pct?: number
  revenue_growth_pct?: number
  pe_forward?: number
  pe_trailing?: number
  // Cerebro IA synthesized signal (written by cerebro.py → read by super_score_integrator)
  cerebro_signal?: string
  cerebro_score_adj?: number
  // AI quality filter reasoning (ai_quality_filter.py via Groq)
  ai_reasoning?: string | null
  ai_verdict?: string | null
  ai_confidence?: number | null
  // Owner Earnings AI validator (owner_earnings_validator.py)
  oe_ai_adjustment?: number | null
  oe_ai_verdict?: string | null
  // Analyst revisions (analyst_revisions_tracker.py)
  target_change_7d_pct?: number | null
  target_change_30d_pct?: number | null
  upgrade_days_14d?: number | null
  downgrade_days_14d?: number | null
  target_revision_bonus?: number | null
  // ML Scorer (ml_scorer.py → docs/ml_scores.csv)
  ml_score?: number | null
  ml_win_prob?: number | null
  ml_confidence?: number | null
  // ML Win Predictor (ml_win_predictor.py → docs/ml_win_probability.json)
  ml_win_probability?: number | null
  ml_win_label?: string | null
  // IV vs Realized Volatility (options pricing signal)
  hv_30d?: number | null
  atm_iv?: number | null
  iv_ratio?: number | null
  iv_premium_pts?: number | null
  // Score breakdown bonuses (from super_score_integrator.py)
  piotroski_bonus?: number | null
  fcf_bonus?: number | null
  dividend_bonus?: number | null
  buyback_bonus?: number | null
  revision_bonus?: number | null
  rr_bonus?: number | null
  sector_bonus?: number | null
  insider_bonus?: number | null
  institutional_bonus?: number | null
  options_bonus?: number | null
  mr_bonus?: number | null
  hf_bonus?: number | null
  days_in_list?: number | null
  profitability_penalty?: number | null
}

export interface MomentumOpportunity {
  ticker: string
  company_name: string
  current_price: number
  momentum_score: number
  vcp_score?: number
  proximity_to_52w_high?: number
  trend_template_score?: number
  target_price_analyst?: number
  analyst_upside_pct?: number
}

export interface InsiderData {
  ticker: string
  company_name?: string
  company?: string          // US CSV field name
  purchase_count: number
  unique_insiders: number
  days_span: number
  first_purchase?: string
  last_purchase: string
  total_qty?: number        // US field
  total_shares?: number     // EU field
  confidence_score: number
  confidence_label?: string // EU field
  market?: string
}

export interface OptionsFlowItem {
  ticker: string
  company_name?: string
  sentiment: string
  flow_score: number
  quality: string
  current_price?: number
  total_premium?: number
  put_call_ratio?: number
  unusual_calls?: number
  unusual_puts?: number
  sentiment_emoji?: string
}

export interface MeanReversionItem {
  ticker: string
  company_name?: string
  strategy: string
  quality: string
  reversion_score: number
  current_price?: number
  entry_zone?: string
  target?: number
  stop_loss?: number
  rsi?: number
  drawdown_pct?: number
  risk_reward?: number
  support_level?: number
  resistance_level?: number
  distance_to_support_pct?: number
  volume_ratio?: number
  detected_date?: string
  ai_confirmation?: 'YES' | 'CAUTION' | 'NO' | null
  ai_confidence?: number | null
  ai_reason?: string | null
  historical_win_rate?: number | null
}

export interface SectorRotationData {
  results: Array<{
    sector: string
    status: string
    velocity: number
    relative_strength: number
  }>
  alerts: Array<{
    type: string
    sector: string
    message: string
  }>
  opportunities: Array<Record<string, unknown>>
  timestamp?: string
}

export interface PortfolioSummary {
  total_signals?: number
  unique_tickers?: number
  date_range?: string
  active_signals?: number
  completed_signals?: number
  overall?: {
    '7d': { count: number; win_rate: number; avg_return: number }
    '14d': { count: number; win_rate: number; avg_return: number }
    '30d': { count: number; win_rate: number; avg_return: number }
  }
  value_strategy?: StrategyStats
  eu_value_strategy?: StrategyStats
  top_performers?: Array<Record<string, unknown>>
  worst_performers?: Array<Record<string, unknown>>
  recent_signals?: Array<Record<string, unknown>>
  avg_max_drawdown?: number
  score_correlation?: number
  alpha?: {
    '30d': AlphaStat
    '14d': AlphaStat
    '7d':  AlphaStat
  }
}

export interface StrategyPeriodStats {
  count?: number
  win_rate?: number | null
  avg_return?: number | null
  median_return?: number | null
  best?: number | null
  worst?: number | null
  basis?: string
}

export interface StrategyStats {
  count?: number
  '7d'?: StrategyPeriodStats
  '14d'?: StrategyPeriodStats
  '30d'?: StrategyPeriodStats
}

export interface AlphaStat {
  count: number
  avg_alpha: number | null
  avg_signal_return: number | null
  avg_benchmark_return: number | null
  positive_alpha_rate: number | null
  best_alpha: number | null
  worst_alpha: number | null
}

export interface MarketRegime {
  us: Record<string, unknown>
  eu: Record<string, unknown>
}

export const fetchValueOpportunities = async (): Promise<{
  data: { data: ValueOpportunity[]; count: number; source: string }
}> => {
  // Load filtered (all daily tickers) + enrich conviction grades from conviction.csv.
  // Conviction.csv can mix US/EU ADRs and filters to grade≥B, missing new tickers —
  // so we use filtered as the source of truth and patch grades where available.
  for (const filename of ['value_opportunities_filtered.csv', 'value_opportunities.csv']) {
    try {
      const base = await fetchValueCsv(filename)
      if (base.data.length === 0) continue
      // Try to enrich with conviction grades (best-effort)
      try {
        const conv = await fetchValueCsv('value_conviction.csv')
        const gradeMap = new Map(conv.data.map(r => [r.ticker, r]))
        base.data = base.data.map(r => {
          const c = gradeMap.get(r.ticker)
          if (!c) return r
          return {
            ...r,
            conviction_grade: c.conviction_grade ?? r.conviction_grade,
            conviction_score: c.conviction_score ?? r.conviction_score,
            conviction_reasons: c.conviction_reasons ?? r.conviction_reasons,
            conviction_positives: c.conviction_positives ?? r.conviction_positives,
            conviction_red_flags: c.conviction_red_flags ?? r.conviction_red_flags,
          }
        })
      } catch { /* conviction enrichment failed — show tickers without grades */ }
      return { data: base }
    } catch { /* try next */ }
  }
  const res = await apiClient.get<{ data: ValueOpportunity[]; count: number; source: string }>('/api/value-opportunities')
  return { data: res.data }
}

const STATIC_DATA_BASE = (import.meta.env.VITE_CSV_BASE as string | undefined) || 'https://tantancansado.github.io/stock_analyzer_a'

/**
 * Fetcher unificado para endpoints con dualidad estático/API.
 *
 * En producción (VITE_CSV_BASE definido) lee el JSON directamente de
 * GitHub Pages — siempre fresco, no depende del deploy de Railway.
 * En dev (sin VITE_CSV_BASE) cae al API Flask local.
 *
 * Reemplaza el patrón repetido 14 veces:
 *   const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined
 *   if (csvBase) {
 *     const url = `${csvBase}/foo.json`
 *     const res = await apiClient.get(url, { transformResponse: [...] })
 *     return { data: res.data }
 *   }
 *   return apiClient.get('/api/foo')
 *
 * @param staticFile  nombre del archivo en docs/ (p.ej. "portfolio_news.json")
 * @param apiPath     path del endpoint Flask (p.ej. "/api/portfolio-news")
 */
export async function fetchStaticOrApi<T>(staticFile: string, apiPath: string): Promise<{ data: T }> {
  const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined
  if (csvBase) {
    const url = `${csvBase}/${staticFile}`
    const res = await apiClient.get<T>(url, {
      transformResponse: [(d) => typeof d === 'string' ? JSON.parse(d) : d],
    })
    return { data: res.data }
  }
  const res = await apiClient.get<T>(apiPath)
  return { data: res.data }
}

// Simple quoted-CSV parser (handles commas inside "..." fields)
function parseCsvRows(text: string): Record<string, string>[] {
  const lines = text.trim().split('\n')
  if (lines.length < 2) return []
  const splitRow = (line: string): string[] => {
    const out: string[] = []
    let cur = '', inQ = false
    for (let i = 0; i < line.length; i++) {
      const ch = line[i]
      if (ch === '"') { if (inQ && line[i + 1] === '"') { cur += '"'; i++ } else inQ = !inQ }
      else if (ch === ',' && !inQ) { out.push(cur); cur = '' }
      else cur += ch
    }
    out.push(cur)
    return out
  }
  const headers = splitRow(lines[0])
  return lines.slice(1).filter(l => l.trim()).map(line => {
    const vals = splitRow(line)
    const obj: Record<string, string> = {}
    headers.forEach((h, i) => { obj[h.trim()] = vals[i] ?? '' })
    return obj
  })
}

export const VALUE_NUMERIC = new Set([
  'current_price','value_score','conviction_score','conviction_positives','conviction_red_flags',
  'target_price_analyst','target_price_analyst_high','target_price_analyst_low','analyst_upside_pct',
  'analyst_count','fcf_yield_pct','risk_reward_ratio','dividend_yield_pct','days_to_earnings',
  'entry_price','stop_loss','target_price','proximity_to_52w_high','piotroski_score',
  'ebit_ev_yield','roic_greenblatt','peg_ratio','roe_pct','profit_margin_pct',
  'revenue_growth_pct','pe_forward','pe_trailing','market_cap','payout_ratio_pct',
  'dividend_rate','five_yr_avg_dividend_yield_pct','shares_change_pct','interest_coverage',
  'analyst_revision_momentum','fundamental_score','earnings_quality_score','growth_acceleration_score',
  'relative_strength_score','financial_health_score','catalyst_timing_score','rs_line_score',
  'rs_line_percentile','eps_growth_yoy','eps_accel_quarters','rev_growth_yoy','rev_accel_quarters',
  'fifty_two_week_high','trend_template_score','target_price_dcf','target_price_dcf_upside_pct',
  'target_price_pe','target_price_pe_upside_pct','fcf_per_share','short_percent_float',
  'short_ratio','market_cape','pct_from_52w_high','oe_ai_adjustment',
  'target_change_7d_pct','target_change_30d_pct','upgrade_days_14d','downgrade_days_14d','target_revision_bonus',
  'piotroski_bonus','fcf_bonus','dividend_bonus','buyback_bonus','revision_bonus',
  'rr_bonus','sector_bonus','insider_bonus','institutional_bonus','options_bonus',
  'mr_bonus','hf_bonus','days_in_list','profitability_penalty',
  'cerebro_score_adj','hedge_fund_count',
  'hv_30d','atm_iv','iv_ratio','iv_premium_pts',
  'ml_win_probability','ml_score',
])

const VALUE_BOOLEAN = new Set([
  'buyback_active','earnings_warning','earnings_catalyst','trend_template_pass',
  'eps_accelerating','rev_accelerating','rs_line_at_new_high','short_squeeze_potential',
])

export function parseValueRows(text: string): ValueOpportunity[] {
  return parseCsvRows(text).map(row => {
    const obj: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(row)) {
      if (VALUE_NUMERIC.has(k)) {
        const n = v === '' ? null : Number(v)
        obj[k] = (n !== null && Number.isNaN(n)) ? null : n
      } else if (VALUE_BOOLEAN.has(k)) {
        obj[k] = v.toLowerCase() === 'true'
      } else {
        obj[k] = v === '' ? undefined : v
      }
    }
    return obj as unknown as ValueOpportunity
  })
}

async function fetchValueCsv(filename: string): Promise<{ data: ValueOpportunity[]; count: number; source: string }> {
  const res = await fetch(`${STATIC_DATA_BASE}/${filename}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`CSV fetch failed: ${res.status}`)
  const data = parseValueRows(await res.text())
  return { data, count: data.length, source: 'github-pages' }
}

export const fetchEUValueOpportunities = async (): Promise<{
  data: { data: ValueOpportunity[]; count: number; source: string }
}> => {
  // Try conviction file first (has grades for all curated EU tickers), then raw scanner output
  for (const filename of ['european_value_conviction.csv', 'european_value_opportunities.csv']) {
    try {
      const data = await fetchValueCsv(filename)
      if (data.data.length > 0) return { data }
    } catch { /* try next */ }
  }
  const res = await apiClient.get<{ data: ValueOpportunity[]; count: number; source: string }>('/api/eu-value-opportunities')
  return { data: res.data }
}

export const fetchGlobalValueOpportunities = async (): Promise<{
  data: { data: ValueOpportunity[]; count: number; source: string }
}> => {
  try {
    const data = await fetchValueCsv('global_value_opportunities.csv')
    return { data }
  } catch {
    const res = await apiClient.get<{ data: ValueOpportunity[]; count: number; source: string }>('/api/global-value')
    return { data: res.data }
  }
}

const MOMENTUM_NUMERIC = new Set([
  'current_price','momentum_score','vcp_score','proximity_to_52w_high',
  'trend_template_score','target_price_analyst','analyst_upside_pct',
])

export const fetchMomentumOpportunities = async (): Promise<{
  data: { data: MomentumOpportunity[]; count: number; source: string }
}> => {
  for (const filename of ['momentum_opportunities_filtered.csv', 'momentum_opportunities.csv']) {
    try {
      const res = await fetch(`${STATIC_DATA_BASE}/${filename}`, { cache: 'no-store' })
      if (res.ok) {
        const text = await res.text()
        const rows = parseCsvRows(text)
        if (rows.length > 0) {
          const data = rows.map(r => {
            const obj: Record<string, unknown> = {}
            for (const [k, v] of Object.entries(r)) {
              if (MOMENTUM_NUMERIC.has(k)) {
                const n = v === '' ? null : Number(v)
                obj[k] = (n !== null && Number.isNaN(n)) ? null : n
              } else {
                obj[k] = v === '' ? undefined : v
              }
            }
            return obj as unknown as MomentumOpportunity
          })
          return { data: { data, count: data.length, source: 'github-pages' } }
        }
      }
    } catch { /* try next */ }
  }
  const res = await apiClient.get<{ data: MomentumOpportunity[]; count: number; source: string }>('/api/momentum-opportunities')
  return { data: res.data }
}

export interface PortfolioNewsItem {
  id: string
  ticker: string
  title: string
  source: string
  pub_date: string
  time_ago: string
  url: string
  importance: 'ALTA' | 'MEDIA' | 'BAJA'
}

export interface PortfolioNewsData {
  scan_date: string | null
  scan_time: string | null
  tickers: string[]
  count: number
  alta_count: number
  media_count: number
  new_alerts: number
  items: PortfolioNewsItem[]
}

// Portfolio news is updated every 6h — read from GitHub Pages directly (always fresh)
export const fetchPortfolioNews = () =>
  fetchStaticOrApi<PortfolioNewsData>('portfolio_news.json', '/api/portfolio-news')

export const fetchSectorRotation = () =>
  apiClient.get<SectorRotationData>('/api/sector-rotation')

export const fetchOptionsFlow = () =>
  apiClient.get('/api/options-flow')

export const fetchUnusualFlow = () =>
  fetchStaticOrApi<unknown>('unusual_flow.json', '/api/unusual-flow')

export const fetchMeanReversion = () =>
  fetchStaticOrApi<{ opportunities?: unknown[]; scan_date?: string }>(
    'mean_reversion_opportunities.json',
    '/api/mean-reversion'
  )

export interface BounceBroadSetup {
  ticker: string
  price: number
  target: number
  stop: number
  target_pct: number
  stop_pct: number
  rr: number
  rsi2: number
  rsi14: number
  atr_pct: number
  vol_ratio: number
  dist_support: number
  drawdown_20d: number
  sma20_distance: number
  above_sma200: boolean
  horizon_days: string
  setup_type: string
}

export interface BounceBroadResponse {
  scan_date: string
  generated_at: string
  universe_size: number
  universe: string
  count: number
  criteria: Record<string, unknown>
  setups: BounceBroadSetup[]
}

export const fetchBounceBroad = () =>
  fetchStaticOrApi<BounceBroadResponse>('bounce_setups_broad.json', '/api/bounce-broad')

// ── Portfolio Strategies (per-position trim/add plan via Groq) ─────────────────

export type StrategyAction = 'HOLD' | 'TRIM' | 'ADD' | 'EXIT' | 'WATCH'

export interface PortfolioStrategy {
  ticker: string
  company?: string
  current_price: number
  avg_price: number
  shares: number
  pl_pct: number | null
  current_action: StrategyAction
  action_reason: string
  trim_at_price: number | null
  trim_pct: number | null
  trim_reason: string | null
  add_at_price: number | null
  add_pct: number | null
  add_reason: string | null
  stop_loss_price: number
  triggers_sell: string[]
  triggers_buy: string[]
  next_check_date: string
  next_check_reason: string
  thesis_short: string
  confidence: number
  signals?: Record<string, unknown>
  _stale_strategy?: boolean
  _stale_reason?: string
}

export interface PortfolioStrategiesResponse {
  generated_at: string
  scan_date: string
  count: number
  strategies: Record<string, PortfolioStrategy>
}

export const fetchPortfolioStrategies = () =>
  fetchStaticOrApi<PortfolioStrategiesResponse>(
    'portfolio_strategies.json',
    '/api/portfolio-strategies',
  )

// ── Refresh on-demand (POST) — recomputa todos los artifacts del user ──────
export interface PortfolioRefreshResponse {
  user_id: string
  count_positions: number
  elapsed_seconds: number
  summary: {
    portfolio_strategies?: { count?: number; generated_at?: string; error?: string }
    earnings_theses?: { status?: string; error?: string }
    earnings_options?: { status?: string; error?: string }
  }
}

/**
 * Recomputa los artifacts del user (strategies, earnings theses, earnings
 * options) en función de las posiciones actuales en Supabase.
 *
 * Tarda 30-90s. Idempotente. Usa Groq (puede caer en rate-limit fuera del
 * pipeline diario; en ese caso preserva la última versión válida).
 *
 * Uso típico: tras editar/añadir/quitar una posición, llamar a esta función
 * para que la pestaña Estrategias refleje la cartera nueva sin esperar al
 * pipeline diario.
 */
export const refreshUserArtifacts = async (): Promise<PortfolioRefreshResponse> => {
  const res = await apiClient.post<PortfolioRefreshResponse>('/api/portfolio/refresh')
  return res.data
}

export const fetchOwnerEarningsBatch = (targetReturn = 15) =>
  fetchStaticOrApi<unknown>(
    'owner_earnings_batch.json',
    `/api/owner-earnings-batch?target_return=${targetReturn / 100}`,
  )

export const fetchRecurringInsiders = () =>
  apiClient.get<{ data: InsiderData[]; count: number; source: string }>('/api/recurring-insiders')

export const fetchPortfolioTracker = () =>
  apiClient.get<PortfolioSummary>('/api/portfolio-tracker')

export const fetchPortfolioSignals = () =>
  apiClient.get<{ data: Record<string, unknown>[] }>('/api/portfolio-tracker/signals')

export interface CalibrationBucket {
  range: string
  count: number
  win_rate_14d: number
  avg_return_14d: number
  median_return_14d: number
}
export interface CalibrationRegime {
  regime: string
  count: number
  win_rate_14d: number
  avg_return_14d: number
  median_return_14d: number
}
export interface CalibrationSector {
  sector: string
  count: number
  win_rate_14d: number
  avg_return_14d: number
  median_return_14d: number
}
export interface CalibrationData {
  score_buckets: CalibrationBucket[]
  regime_analysis: CalibrationRegime[]
  sector_calibration: CalibrationSector[]
  fcf_yield_buckets: CalibrationBucket[]
  total_completed: number
  generated_at: string
}
export const fetchCalibration = () =>
  apiClient.get<CalibrationData>('/api/portfolio-tracker/calibration')

export interface TimeseriesRow {
  label: string
  signals: number
  win_rate_14d: number | null
  win_rate_30d: number | null
  avg_return_14d: number | null
  avg_return_30d: number | null
  value_us?: number
  value_eu?: number
  momentum?: number
}
export interface StrategyRow {
  strategy: string
  signals: number
  win_rate_14d: number | null
  win_rate_30d: number | null
  avg_return_14d: number | null
  avg_return_30d: number | null
  avg_drawdown: number
}
export interface TimeseriesData {
  by_week: TimeseriesRow[]
  by_month: TimeseriesRow[]
  by_quarter: TimeseriesRow[]
  by_weekday: TimeseriesRow[]
  by_strategy: StrategyRow[]
  total_completed: number
  date_range: { from: string; to: string }
}
export const fetchTimeseries = () =>
  apiClient.get<TimeseriesData>('/api/portfolio-tracker/timeseries')

export interface BreadthData {
  total: number
  trend_pass?: number; trend_pass_pct?: number
  rs_at_high?: number; rs_at_high_pct?: number
  positive_upside?: number; positive_upside_pct?: number
  earnings_warnings?: number
}
export const fetchMarketBreadth = () =>
  apiClient.get<{ us: BreadthData; eu: BreadthData }>('/api/market-breadth')

// ── Cerebro AI agent ─────────────────────────────────────────────────────────
export interface CerebroTier {
  label: string
  win_rate_7d: number
  avg_return_7d: number
  n: number
  vs_baseline_wr: number
  vs_baseline_ret: number
}
export interface CerebroInsights {
  generated_at: string
  total_analyzed: number
  baseline_win_rate_7d: number
  baseline_avg_return_7d: number
  score_tiers: CerebroTier[]
  market_regimes: CerebroTier[]
  sectors: CerebroTier[]
  fcf_tiers: CerebroTier[]
  best_combos: CerebroTier[]
  period_stats: Record<string, { win_rate: number | null; avg_return: number; n: number }>
  narrative: string | null
}
export interface CerebroSignal {
  ticker: string
  company_name: string
  sector: string
  strategies: string[]
  strategy_count: number
  convergence_score: number
  value_score: number | null
  conviction_grade: string
  analyst_upside_pct: number | null
  fcf_yield_pct: number | null
  current_price: number | null
  analysis: string | null
}
export interface CerebroAlert {
  ticker: string
  type: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  title: string
  message: string
  date: string
  data?: Record<string, unknown>
}
export interface CerebroCalibration {
  generated_at: string
  recommendations: Array<{ type: string; factor: string; insight: string; n: number }>
  narrative: string | null
  total_recommendations: number
}

export interface EntrySignal {
  ticker: string
  company_name: string
  region: string
  sector: string
  value_score: number
  conviction_grade: string
  current_price: number | null
  analyst_upside_pct: number | null
  fcf_yield_pct: number | null
  risk_reward_ratio: number | null
  days_in_value: number
  streak_days: number
  entry_score: number
  signal: 'STRONG_BUY' | 'BUY' | 'MONITOR' | 'WAIT'
  signals_fired: string[]
  signals_pts: Array<{ name: string; pts: number }>
  signals_missing: string[]
  rsi: number | null
  earnings_warning: boolean
  days_to_earnings: number | null
}

export const fetchCerebroInsights    = () => apiClient.get<CerebroInsights>('/api/cerebro/insights')
export const fetchCerebroConvergence = () => apiClient.get<{ generated_at: string; total_convergences: number; triple_or_more: number; convergences: CerebroSignal[] }>('/api/cerebro/convergence')
export const fetchCerebroAlerts      = () => apiClient.get<{ generated_at: string; total: number; high_count: number; alerts: CerebroAlert[] }>('/api/cerebro/alerts')
export const fetchCerebroCalibration = () => apiClient.get<CerebroCalibration>('/api/cerebro/calibration')
export const fetchCerebroEntrySignals = () => apiClient.get<{ generated_at: string; total: number; strong_buy: number; buy: number; monitor: number; wait: number; narrative: string | null; signals: EntrySignal[] }>('/api/cerebro/entry-signals')

export interface ExitSignal {
  ticker: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  entry_score: number
  current_score: number | null
  signal_date: string | null
  reasons: string[]
}
export const fetchCerebroExitSignals = () => apiClient.get<{ generated_at: string; total: number; high_count: number; narrative: string | null; exits: ExitSignal[] }>('/api/cerebro/exit-signals')

export interface ValueTrap {
  ticker: string
  company_name: string
  severity: 'HIGH' | 'MEDIUM'
  trap_score: number
  value_score: number
  flags: string[]
  piotroski: number | null
  fcf_yield_pct: number | null
  fundamental_score: number | null
}
export const fetchCerebroValueTraps = () => apiClient.get<{ generated_at: string; total: number; high_count: number; narrative: string | null; traps: ValueTrap[] }>('/api/cerebro/value-traps')

export interface SmartMoneySignal {
  ticker: string
  company_name: string
  sector: string
  value_score: number | null
  n_hedge_funds: number
  hedge_funds: string[]
  n_insiders: number
  insider_purchases: number
  convergence_score: number
  in_value: boolean
}
export const fetchCerebroSmartMoney = () => apiClient.get<{ generated_at: string; total: number; narrative: string | null; signals: SmartMoneySignal[] }>('/api/cerebro/smart-money')

export interface InsiderCluster {
  sector: string
  ticker_count: number
  tickers: string[]
  total_purchases: number
  total_insiders: number
  cluster_score: number
  signal: 'STRONG' | 'MODERATE'
}
export const fetchCerebroInsiderClusters = () => apiClient.get<{ generated_at: string; total: number; narrative: string | null; clusters: InsiderCluster[] }>('/api/cerebro/insider-clusters')

export interface DividendSafety {
  ticker: string
  company_name: string
  div_yield: number
  payout_ratio: number | null
  fcf_yield_pct: number | null
  interest_coverage: number | null
  safety_score: number
  rating: 'AT_RISK' | 'WATCH' | 'SAFE'
  risk_flags: string[]
  value_score: number
}
export const fetchCerebroDividendSafety = () => apiClient.get<{ generated_at: string; total: number; at_risk: number; narrative: string | null; dividends: DividendSafety[] }>('/api/cerebro/dividend-safety')

export interface PiotroskiCandidate {
  ticker: string
  company_name: string
  piotroski_current: number
  piotroski_prev: number | null
  delta: number
  trend: 'IMPROVING' | 'SLIGHT_UP' | 'STABLE' | 'SLIGHT_DOWN' | 'DETERIORATING'
  signal: 'STRONG' | 'NEUTRAL' | 'WEAK'
  value_score: number
}
export const fetchCerebroPiotroski = () => apiClient.get<{ generated_at: string; total: number; improving: number; narrative: string | null; candidates: PiotroskiCandidate[] }>('/api/cerebro/piotroski')

export interface StressRisk {
  type: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  message: string
  detail: Record<string, unknown>
}
export const fetchCerebroStressTest = () => apiClient.get<{ generated_at: string; total_positions: number; risks: StressRisk[]; narrative: string | null; sector_breakdown: Array<{ sector: string; count: number; pct: number }>; region_breakdown: Record<string, number> }>('/api/cerebro/stress-test')

export interface CerebroBriefing {
  generated_at: string
  regime: string
  narrative: string
  sections: {
    regime: string
    strong_buy_count: number
    buy_count: number
    top_entries: [string, number][]
    top_convergences: [string, number][]
    high_alerts: [string, string][]
    traps_warning: [string, number][]
    exit_warnings: [string, string][]
    smart_money: [string, number][]
    macro_stress: Array<{ market: string; score: number; regime: string; exposed: string[] }>
  }
}
export const fetchCerebroBriefing = () => apiClient.get<CerebroBriefing>('/api/cerebro/briefing')

export interface ShortSqueezeSetup {
  ticker: string
  company_name: string
  sector: string
  severity: 'HIGH' | 'MEDIUM'
  squeeze_score: number
  short_pct_float: number
  piotroski: number | null
  value_score: number
  insider_buying: boolean
  hf_present: boolean
  flags: string[]
}
export const fetchCerebroShortSqueeze = () => apiClient.get<{ generated_at: string; total: number; high_count: number; narrative: string | null; setups: ShortSqueezeSetup[] }>('/api/cerebro/short-squeeze')

export interface QualityDecay {
  ticker: string
  company_name: string
  severity: 'HIGH' | 'MEDIUM'
  decay_score: number
  value_score: number
  snapshot_date: string
  roe_prev: number | null
  roe_curr: number | null
  margin_prev: number | null
  margin_curr: number | null
  fcf_prev: number | null
  fcf_curr: number | null
  flags: string[]
}
export const fetchCerebroQualityDecay = () => apiClient.get<{ generated_at: string; total: number; high_count: number; narrative: string | null; decays: QualityDecay[] }>('/api/cerebro/quality-decay')

export interface SectorStandout {
  ticker: string
  company_name: string
  sector: string
  label: 'BEST_IN_SECTOR' | 'PRICEY_VS_PEERS'
  fcf_yield_pct: number
  fcf_rank: number
  fcf_rank_of: number
  value_score: number
  analyst_upside_pct: number | null
  sector_avg_fcf: number | null
  peers_in_sector: number
}
export interface SectorSummary {
  sector: string
  count: number
  avg_value_score: number
  avg_fcf_yield: number | null
  rerate_potential: boolean
  tickers: string[]
}
export const fetchCerebroSectorRV = () => apiClient.get<{ generated_at: string; total: number; rerate_sectors: number; narrative: string | null; standouts: SectorStandout[]; sector_summary: SectorSummary[] }>('/api/cerebro/sector-rv')

// ── Thesis Drift ──────────────────────────────────────────────────────────────
export interface ThesisDrift {
  ticker: string
  company_name: string
  sector: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  drift_score: number
  days_tracked: number
  baseline_date: string
  value_score_now: number
  value_score_prev: number
  drift_flags: string[]
  improvements: string[]
}
export const fetchCerebroThesisDrift = () =>
  apiClient.get<{ generated_at: string; total: number; high_count: number; drifts: ThesisDrift[] }>('/api/cerebro/thesis-drift')

export interface OptionsQualitySignal {
  ticker: string
  company_name: string
  tier: 'TIER1' | 'TIER2' | 'TIER3'
  quality_score: number
  signal_type: string
  premium_usd: number
  volume: number
  oi: number
  vol_oi_ratio: number
  flags: string[]
}
export const fetchCerebroOptionsQuality = () =>
  apiClient.get<{ generated_at: string; tier1: number; tier2: number; tier3: number; noise_filtered: number; actionable: OptionsQualitySignal[] }>('/api/cerebro/options-quality')

export interface EarningsRevision {
  ticker: string
  company_name: string
  direction: 'STRONG_UP' | 'UP' | 'DOWN' | 'STRONG_DOWN'
  eps_prev: number
  eps_curr: number
  eps_chg_pct: number
  rev_chg_pct: number
  analysts_delta: number
  score_adj: number
  flags: string[]
}
export const fetchCerebroEarningsRevisions = () =>
  apiClient.get<{ generated_at: string; total: number; upgrades: number; downgrades: number; revisions: EarningsRevision[]; note?: string }>('/api/cerebro/earnings-revisions')

// ── Cerebro Daily Action Plan ─────────────────────────────────────────────────
export interface MacroPlay {
  instrument: string
  direction?: string
  thesis: string
  historical: string
  risk: string
  timeframe: string
  score: number
  eu_alternative?: {
    ticker: string | null
    name: string
    exchange: string | null
    available: string
  }
}

export interface DailyPlanAction {
  prioridad: number
  accion: string
  instrumento: string
  razon: string
  catalizador: string
  size_hint: string
  invalidacion: string
}

export interface DailyPlanEvitar {
  ticker: string
  razon: string
}

export interface AgendaEvent {
  fecha: string
  evento: string
  impacto: 'ALTO' | 'MEDIO' | 'BAJO'
  accion_sugerida?: string
}

export interface ValueEnEntorno {
  ticker: string
  score: number
  sector: string
  fcf_yield_pct?: number
  grade?: string
}

export interface DailyPlan {
  generated_at: string
  macro_regime: string
  composite_score: number
  sesgo: string
  confianza: number
  situacion: string
  narrativa: string
  acciones_inmediatas: DailyPlanAction[]
  macro_plays: MacroPlay[]
  macro_plays_commentary?: string
  value_en_entorno: ValueEnEntorno[]
  value_en_entorno_razon?: string
  evitar: DailyPlanEvitar[]
  agenda_semana: AgendaEvent[]
  frase_del_dia?: string
  mensaje_telegram?: string
  ai_powered: boolean
}

export async function fetchCerebroDailyPlan() {
  return apiClient.get<DailyPlan>('/api/cerebro/daily-plan')
}

export interface LivePrice {
  symbol: string
  label: string
  kind: string
  current: number | null
  prev_close: number | null
  change_pct: number | null
}

export interface LivePricesData {
  prices: Record<string, LivePrice>
  market_open: boolean
  fetched_at: string
}

export async function fetchLivePrices() {
  return apiClient.get<LivePricesData>('/api/live-prices')
}

export const fetchMarketRegime = () =>
  apiClient.get<MarketRegime>('/api/market-regime')

export const fetchMacroRadar = () =>
  apiClient.get('/api/macro-radar')

export const fetchMacroCountries = () =>
  apiClient.get('/api/macro-countries')

export const fetchMacroRadarHistory = () =>
  apiClient.get<{ history: Array<{ date: string; composite_score: number; composite_pct: number; regime: string; regime_color: string }> }>('/api/macro-radar/history')

export interface MacroStressSignal {
  label: string
  weight: number
  direction?: string
  value: number | null
  percentile: number | null
  z: number | null
  score: number | null
  contribution: number | null
  history_ready: boolean
  meta?: Record<string, unknown>
}

export interface MacroStressAnalogue {
  date: string
  name: string
  event?: string | null
  score: number
  similarity: number
  shared_signals: string[]
  forward_30d_return: number | null
  forward_60d_return: number | null
  forward_90d_return: number | null
}

export interface MacroStressChartPoint {
  date: string
  price: number
  stress_score: number | null
}

export interface MacroStressMarket {
  market_id: string
  label: string
  category?: string
  primary_ticker?: string
  stress_score: number | null
  band: 'green' | 'amber' | 'red' | 'unknown' | string
  regime: string
  signals_used?: number
  coverage_pct?: number
  narrative?: string
  history_ready?: boolean
  history_note?: string
  top_contributors?: Array<{ key: string; label: string; score: number | null; contribution: number | null }>
  signals: Record<string, MacroStressSignal>
  chart_series?: MacroStressChartPoint[]
  equity_exposure?: { beneficiaries?: string[]; losers?: string[] }
  historical_analogues?: MacroStressAnalogue[]
}

export interface MacroStressResponse {
  generated_at: string
  framework?: string
  summary?: {
    markets_total: number
    markets_red: number
    top_market?: string | null
    top_stress_score?: number | null
  }
  markets: Record<string, MacroStressMarket>
}

export const fetchMacroStress = () =>
  apiClient.get<MacroStressResponse>('/api/macro-stress')

export interface PipelineStatus {
  last_run: string    // ISO UTC e.g. "2026-04-03T07:45:00Z"
  run_date: string    // YYYY-MM-DD
  status: string
  run_id?: string
}

export interface ModuleHealth {
  status: 'ok' | 'stale' | 'missing' | 'empty'
  date: string | null
  days_ago?: number
  rows?: number
}

export interface PipelineHealth {
  generated_at: string        // ISO UTC
  pipeline_date: string       // YYYY-MM-DD
  ok_count: number
  total: number
  modules: Record<string, ModuleHealth>
}

const _csvBase = () => (import.meta.env.VITE_CSV_BASE as string | undefined) || ''

export const fetchPipelineStatus = async (): Promise<PipelineStatus | null> => {
  try {
    const res = await fetch(`${_csvBase()}/pipeline_status.json`, { cache: 'no-store' })
    if (!res.ok) return null
    return await res.json() as PipelineStatus
  } catch {
    return null
  }
}

export const fetchPipelineHealth = async (): Promise<PipelineHealth | null> => {
  try {
    const res = await fetch(`${_csvBase()}/pipeline_health.json`, { cache: 'no-store' })
    if (!res.ok) return null
    return await res.json() as PipelineHealth
  } catch {
    return null
  }
}

export const fetchDailyBriefing = () =>
  apiClient.get<{ narrative: string | null; date: string | null; macro_regime?: string; picks_count?: number; top_picks?: unknown[] }>('/api/daily-briefing')

export const fetchInsidersInsight = () =>
  apiClient.get<{ narrative: string | null; date: string | null; total_tickers?: number }>('/api/insiders-insight')

export const fetchValueEUInsight = () =>
  apiClient.get<{ narrative: string | null; date: string | null; macro_regime?: string; picks_count?: number }>('/api/value-eu-insight')

export const fetchPortfolioInsight = () =>
  apiClient.get<{ narrative: string | null; date: string | null; total_signals?: number; win_rate_7d?: number }>('/api/portfolio-insight')

export const analyzeTickerAI = (ticker: string) =>
  apiClient.get<{ ticker: string; narrative: string | null; date?: string; error?: string }>(`/api/analyze-ai/${ticker}`)

export interface EarningsEntry {
  ticker: string
  company: string
  sector: string
  earnings_date: string
  days_to_earnings: number | null
  earnings_warning: boolean
  earnings_catalyst: boolean
  fundamental_score: number | null
  current_price: number | null
  analyst_upside_pct: number | null
  analyst_count?: number | null
  analyst_recommendation?: string | null
  analyst_revision_momentum?: number | null
  earnings_quality_score?: number | null
  eps_growth_yoy?: number | null
  eps_accelerating?: boolean | null
  consensus_eps?: number | null
  consensus_revenue_millions?: number | null
  beat_rate_last_4q?: number | null
  avg_surprise_pct_last_4q?: number | null
  history_quarters?: number | null
  beat_probability?: number | null
  beat_confidence?: number | null
  beat_drivers?: string[]
  implied_move_pct?: number | null
  is_portfolio?: boolean
  portfolio_only_fetch?: boolean
}

export const fetchEarningsCalendar = () =>
  apiClient.get<{ earnings: EarningsEntry[]; total: number; as_of: string }>('/api/earnings-calendar')

export interface AnalystRevision {
  ticker: string
  target_mean: number | null
  reco_mean: number | null
  analyst_count: number | null
  snapshots: number | null
  target_change_1d_pct: number | null
  target_change_7d_pct: number | null
  target_change_30d_pct: number | null
  reco_change_1d: number | null
  reco_change_7d: number | null
  reco_change_30d: number | null
  analyst_count_change_1d: number | null
  analyst_count_change_7d: number | null
  analyst_count_change_30d: number | null
  upgrade_days_14d: number | null
  downgrade_days_14d: number | null
}

export const fetchAnalystRevisions = () =>
  apiClient.get<{ revisions: AnalystRevision[]; total: number; as_of: string | null }>('/api/analyst-revisions')

export interface AnalystRevisionHistory {
  date: string
  target_mean: number | null
  reco_mean: number | null
  analyst_count: number | null
}

export const fetchAnalystRevisionsTicker = (ticker: string) =>
  apiClient.get<{ ticker: string; history: AnalystRevisionHistory[]; latest: AnalystRevision | null }>(`/api/analyst-revisions/${ticker}`)

// ── Entry Verdicts ───────────────────────────────────────────────────────
export type EntryVerdictKind = 'ENTRY' | 'WAIT' | 'AVOID' | 'NEUTRAL'

export interface EntryVerdict {
  ticker: string
  origin: string | null
  verdict: EntryVerdictKind
  confidence: number | null
  reasons: string | null
  blockers: string | null
  trigger: string | null
  source: 'rules' | 'ai' | null
}

export const fetchEntryVerdicts = () =>
  apiClient.get<{ verdicts: EntryVerdict[]; total: number; as_of: string | null }>('/api/entry-verdicts')

export const fetchEntryVerdictTicker = (ticker: string) =>
  apiClient.get<EntryVerdict & { ticker: string }>(`/api/entry-verdicts/${ticker}`)

export type EarningsThesisVerdict = 'HOLD' | 'REDUCE' | 'EXIT_BEFORE' | 'ADD_AFTER' | 'HOLD_THROUGH'

export interface EarningsThesis {
  ticker: string
  company_name?: string | null
  sector?: string | null
  earnings_date: string
  days_to_earnings: number
  current_price: number | null
  fifty_two_week_high?: number | null
  fifty_two_week_low?: number | null
  avg_price?: number | null
  shares?: number | null
  unrealized_pct?: number | null
  verdict: EarningsThesisVerdict
  sentiment_tone?: 'BULLISH' | 'NEUTRAL' | 'BEARISH' | null
  recent_headlines?: string[]
  implied_move_pct: number | null
  expected_eps: number | null
  expected_revenue_millions: number | null
  beat_rate_last_4q: number | null
  key_risks: string[]
  key_catalysts: string[]
  thesis_summary: string
  confidence: number
  earnings_history?: Array<{
    period: string
    eps_estimate: number | null
    eps_actual: number | null
    surprise_pct: number | null
    beat: boolean | null
  }>
}

export const fetchEarningsThesis = async (ticker: string): Promise<EarningsThesis | null> => {
  const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined
  if (csvBase) {
    try {
      const res = await fetch(`${csvBase}/earnings_theses.json`, { cache: 'no-store' })
      if (res.ok) {
        const data = await res.json() as { theses?: Record<string, EarningsThesis> }
        const t = data?.theses?.[ticker.toUpperCase()] ?? null
        if (t) return t
      }
    } catch { /* fall through to API */ }
  }
  try {
    const res = await apiClient.get<{ ticker: string; thesis: EarningsThesis }>(`/api/earnings-thesis/${ticker.toUpperCase()}`)
    return res.data?.thesis ?? null
  } catch {
    return null
  }
}

export interface EconEvent {
  date: string
  event: string
  type: 'FED' | 'CPI' | 'PCE' | 'JOBS' | 'EARNINGS'
  impact: 'HIGH' | 'MEDIUM'
  description: string
}

export const fetchEconomicCalendar = () =>
  apiClient.get<{ events: EconEvent[]; total: number }>('/api/economic-calendar')

export interface CatalystEvent {
  id: string
  category: 'MACRO' | 'EARNINGS' | 'FDA' | 'OPTIONS_EXPIRY' | 'DIVIDEND'
  type: string
  date: string
  days_away: number
  title: string
  description: string
  impact: 'HIGH' | 'MEDIUM' | 'LOW'
  direction_bias: 'BULLISH' | 'BEARISH' | 'VOLATILE' | 'UNKNOWN'
  avg_move_pct: number | null
  affected_tickers: string[]
  bullish_sectors: string[]
  bearish_sectors: string[]
  source: string
  ticker: string | null
  company: string | null
  sector?: string
  current_price?: number | null
  market_cap?: number | null
  eps_estimate?: number | null
  earnings_history?: {
    beat_count: number
    miss_count: number
    total_quarters: number
    avg_surprise_pct: number
    beat_rate: number
    last_quarters: Array<{ date: string; eps_est: number; eps_act: number; surprise_pct: number; beat: boolean }>
  }
  earnings_warning?: boolean
  dividend_yield?: number
  dividend_rate?: number
  url?: string
}

export interface CatalystData {
  generated_at: string
  scan_date: string
  horizon_days: number
  total_events: number
  by_category: Record<string, number>
  events: CatalystEvent[]
}

export const fetchCatalysts = () =>
  apiClient.get<CatalystData>('/api/catalysts')

export interface DividendTrapEntry {
  ticker: string
  company: string
  sector: string
  current_price: number | null
  dividend_yield: number | null
  payout_ratio: number | null
  fcf_yield: number | null
  fundamental_score: number | null
  trap_score: number
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW'
  reasons: string[]
}

export interface DividendTrapsData {
  date: string
  total_scanned: number
  traps_high: number
  traps_medium: number
  safe_count: number
  traps: DividendTrapEntry[]
  safe_dividends: DividendTrapEntry[]
}

export const fetchDividendTraps = () =>
  apiClient.get<DividendTrapsData>('/api/dividend-traps')

export interface DividendCalendarEvent {
  ticker: string
  company: string
  sector: string
  ex_dividend_date: string
  payment_date: string | null
  days_to_exdiv: number
  dividend_per_share: number | null
  current_price: number | null
  capture_yield_pct: number | null
  dividend_yield_annual: number | null
  fundamental_score: number | null
  value_score: number | null
  conviction_grade: string
  ai_verdict: string
  ai_confidence: string
  source: 'value_filtered'
}

export interface DividendCalendarData {
  events: DividendCalendarEvent[]
  total: number
  tickers_scanned: number
  as_of: string
}

export const fetchDividendCalendar = () =>
  apiClient.get<DividendCalendarData>('/api/dividend-calendar')

export interface CorrelationData {
  tickers: string[]
  matrix: Record<string, number>[]
  days: number
  as_of: string
}

export const fetchCorrelationMatrix = () =>
  apiClient.get<CorrelationData>('/api/correlation-matrix')

// Theses are served as a static JSON from GitHub Pages (always fresh from pipeline)
let _thesesCache: Record<string, unknown> | null = null
let _thesesCachePromise: Promise<Record<string, unknown>> | null = null

const _loadTheses = (): Promise<Record<string, unknown>> => {
  if (_thesesCache) return Promise.resolve(_thesesCache)
  if (_thesesCachePromise) return _thesesCachePromise
  const csvBase = (import.meta.env.VITE_CSV_BASE as string | undefined) || ''
  _thesesCachePromise = fetch(`${csvBase}/theses.json`, { cache: 'default' })
    .then(r => r.ok ? r.json() : {})
    .then(data => { _thesesCache = data; _thesesCachePromise = null; return data })
    .catch(() => { _thesesCachePromise = null; return {} })
  return _thesesCachePromise
}

export const fetchThesis = async (ticker: string): Promise<{ data: { ticker: string; thesis: unknown } }> => {
  const data = await _loadTheses()
  const thesis = data[`${ticker}__value`] ?? data[`${ticker}__momentum`] ?? data[ticker] ?? null
  return { data: { ticker, thesis } }
}

export const analyzeTicker = (ticker: string) =>
  apiClient.get(`/api/analyze/${ticker}`)

export interface SearchResult {
  ticker: string
  company_name: string
  sector?: string
}

export const searchTickers = (q: string) =>
  apiClient.get<{ results: SearchResult[] }>(`/api/search?q=${encodeURIComponent(q)}`)

// CSV filenames by dataset key
const CSV_FILES: Record<string, string> = {
  'value-us':       'value_opportunities.csv',
  'value-eu':       'european_value_opportunities.csv',
  'value-global':   'global_value_opportunities.csv',
  'value-us-full':  'value_conviction.csv',
  'value-eu-full':  'european_value_conviction.csv',
  'mean-reversion': 'mean_reversion_opportunities.csv',
  'insiders':       'recurring_insiders.csv',
  'insiders-eu':    'eu_recurring_insiders.csv',
  'options-flow':   'options_flow.csv',
  'momentum':       'momentum_opportunities.csv',
  'fundamental':    'fundamental_scores.csv',
  'fundamental-eu': 'european_fundamental_scores.csv',
  'micro-cap':      'micro_cap_opportunities.csv',
  'commodities':    'commodity_opportunities.csv',
}

export const downloadCsv = (dataset: string) => {
  const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined
  const filename = CSV_FILES[dataset]
  if (!filename) return

  if (csvBase) {
    // Production: CSVs are served directly from GitHub Pages (always up-to-date)
    window.open(`${csvBase}/${filename}`, '_blank')
  } else {
    // Development: route through Vite proxy → local Flask API
    window.open(`/api/download/${dataset}`, '_blank')
  }
}

export const getCsvUrl = (dataset: string): string => {
  const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined
  const filename = CSV_FILES[dataset]
  if (!filename) return ''
  if (csvBase) return `${csvBase}/${filename}`
  return `/api/download/${dataset}`
}

// Reverse lookup: filename → CSV_FILES key (for dev API download endpoint)
const CSV_KEY_BY_FILE: Record<string, string> = Object.fromEntries(
  Object.entries(CSV_FILES).map(([k, v]) => [v, k])
)

/** Fetch ticker→sector mapping from fundamental_scores CSVs (broad coverage) */
export const fetchTickerSectorMap = async (): Promise<Record<string, string>> => {
  const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined
  const map: Record<string, string> = {}

  const fetchCsv = async (filename: string) => {
    try {
      const key = CSV_KEY_BY_FILE[filename] ?? filename.replace('.csv', '')
      const url = csvBase ? `${csvBase}/${filename}` : `/api/download/${key}`
      const res = await fetch(url)
      if (!res.ok) return
      const rows = parseCsvRows(await res.text())
      for (const row of rows) {
        const ticker = (row.ticker || '').trim()
        const sector = (row.sector || '').trim()
        if (ticker && sector) map[ticker] = sector
      }
    } catch { /* ignore */ }
  }

  await Promise.all([
    fetchCsv('fundamental_scores.csv'),
    fetchCsv('european_fundamental_scores.csv'),
  ])
  return map
}

export interface ScoreHistoryPoint { date: string; score: number; grade: string | null }
export const fetchScoreHistory = (ticker: string) =>
  apiClient.get<{ ticker: string; history: ScoreHistoryPoint[]; points: number }>(`/api/score-history/${ticker}`)

export interface PricePoint { date: string; close: number }
export const fetchPriceHistory = (ticker: string) =>
  apiClient.get<{ ticker: string; prices: PricePoint[] }>(`/api/price-history/${ticker}`)

export default apiClient

export interface TechnicalSignal {
  ticker: string
  company_name: string
  source: string
  signal_name: string
  direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  timeframe: 'DAILY' | 'WEEKLY'
  triggered_date: string
  days_ago: number
  description: string
  strength: number
}

export interface TechnicalSummary {
  ticker: string
  company_name: string
  source: string
  sector: string
  bullish_count: number
  bearish_count: number
  net_signals: number
  net_score: number
  bias: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  top_bullish_signal: string
  top_bearish_signal: string
  most_recent_signal: string
  generated_at: string
}

const TECH_SUMMARY_NUMERIC = new Set(['bullish_count','bearish_count','net_signals','net_score'])

export const fetchTechnicalSignals = async (): Promise<{ signals: TechnicalSignal[]; summary: TechnicalSummary[] }> => {
  const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined

  // Development: use local API endpoint
  if (!csvBase) {
    const res = await apiClient.get<{ signals: TechnicalSignal[]; summary: TechnicalSummary[] }>('/api/technical-signals')
    return res.data
  }

  // Production: read CSVs directly from GitHub Pages
  const [resSig, resSum] = await Promise.all([
    fetch(`${csvBase}/technical_signals.csv`),
    fetch(`${csvBase}/technical_signals_summary.csv`)
  ])
  if (!resSig.ok || !resSum.ok) throw new Error('Technical signals CSV not available yet')
  const [textSig, textSum] = await Promise.all([resSig.text(), resSum.text()])

  const signals = parseCsvRows(textSig).map(row => {
    const obj: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(row)) {
      if (k === 'days_ago' || k === 'strength') obj[k] = v === '' ? 0 : Number(v)
      else obj[k] = v === '' ? '' : v
    }
    return obj as unknown as TechnicalSignal
  })
  const summary = parseCsvRows(textSum).map(row => {
    const obj: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(row)) {
      if (TECH_SUMMARY_NUMERIC.has(k)) obj[k] = v === '' ? 0 : Number(v)
      else obj[k] = v === '' ? '' : v
    }
    return obj as unknown as TechnicalSummary
  })
  return { signals, summary }
}

export interface ChartSignal {
  ticker: string
  entry_quality: 'ideal' | 'acceptable' | 'wait' | 'avoid'
  trend_direction: 'uptrend' | 'downtrend' | 'sideways'
  above_200ma: boolean
  above_150ma: boolean
  base_forming: boolean
  base_type: string
  base_weeks: number | null
  volume_dryup_visible: boolean
  volume_breakout: boolean
  extended_from_base: boolean
  distribution_signs: boolean
  risk_level: 'low' | 'medium' | 'high'
  confidence: 'high' | 'medium' | 'low'
  entry_rationale: string | null
  notes: string | null
  analyzed_at: string
  model: string
  error?: string
}

export const fetchChartSignals = async (): Promise<Record<string, ChartSignal>> => {
  const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined
  if (csvBase) {
    const res = await apiClient.get<{ signals: Record<string, ChartSignal> }>(
      `${csvBase}/chart_signals.json`,
      { transformResponse: [(d) => typeof d === 'string' ? JSON.parse(d) : d] }
    )
    return res.data?.signals ?? {}
  }
  const res = await apiClient.get<{ signals: Record<string, ChartSignal> }>('/api/chart-signals')
  return res.data?.signals ?? {}
}

export interface PreferredStock {
  ticker: string
  name: string
  issuer: string
  sector: string
  par_value: number
  stated_div_pct: number
  annual_div: number
  price: number | null
  pct_from_par: number | null
  week52_high: number | null
  week52_low: number | null
  pct_from_high: number | null
  current_yield: number | null
  risk_tier: string
  value_rating: string
  recommendation: string
  currency: string
  generated_at: string
}

export async function fetchPreferredStocks(): Promise<PreferredStock[]> {
  const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined
  if (csvBase) {
    const url = `${csvBase}/preferred_stocks.csv`
    const res = await apiClient.get<string>(url, { transformResponse: [(d) => d] })
    return parseCsvRows(res.data).map(row => ({
      ticker:         row.ticker ?? '',
      name:           row.name ?? '',
      issuer:         row.issuer ?? '',
      sector:         row.sector ?? '',
      par_value:      row.par_value ? parseFloat(row.par_value) : 25,
      stated_div_pct: row.stated_div_pct ? parseFloat(row.stated_div_pct) : 0,
      annual_div:     row.annual_div ? parseFloat(row.annual_div) : 0,
      price:          row.price ? parseFloat(row.price) : null,
      pct_from_par:   row.pct_from_par ? parseFloat(row.pct_from_par) : null,
      week52_high:    row.week52_high ? parseFloat(row.week52_high) : null,
      week52_low:     row.week52_low ? parseFloat(row.week52_low) : null,
      pct_from_high:  row.pct_from_high ? parseFloat(row.pct_from_high) : null,
      current_yield:  row.current_yield ? parseFloat(row.current_yield) : null,
      risk_tier:      row.risk_tier ?? '',
      value_rating:   row.value_rating ?? '',
      recommendation: row.recommendation ?? '',
      currency:       row.currency ?? 'USD',
      generated_at:   row.generated_at ?? '',
    }))
  }
  const res = await apiClient.get<{ data: PreferredStock[] }>('/api/preferred-stocks')
  return res.data.data ?? []
}

export async function fetchPortfolioPrices(tickers: string[]): Promise<Record<string, number>> {
  if (!tickers.length) return {}
  try {
    const res = await apiClient.post<{ prices: Record<string, number> }>('/api/portfolio-prices', { tickers })
    return res.data.prices ?? {}
  } catch {
    return {}
  }
}

export interface BondOpportunity {
  ticker: string
  name: string
  short_name: string
  bond_type: string
  currency: string
  price: number | null
  week52_high: number | null
  week52_low: number | null
  pct_from_high: number | null
  yield_pct: number | null
  sec_yield_pct: number | null
  hist_avg_yield_pct: number | null
  yield_vs_avg_pct: number | null
  duration_years: number | null
  modified_duration: number | null
  expense_ratio_pct: number | null
  value_rating: string
  recommendation: string
  generated_at: string
}

export async function fetchBonds(): Promise<BondOpportunity[]> {
  const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined
  if (csvBase) {
    const url = `${csvBase}/bonds_opportunities.csv`
    const res = await apiClient.get<string>(url, { transformResponse: [(d) => d] })
    return parseCsvRows(res.data).map(row => ({
      ticker:              row.ticker ?? '',
      name:                row.name ?? '',
      short_name:          row.short_name ?? '',
      bond_type:           row.bond_type ?? '',
      currency:            row.currency ?? 'USD',
      price:               row.price ? parseFloat(row.price) : null,
      week52_high:         row.week52_high ? parseFloat(row.week52_high) : null,
      week52_low:          row.week52_low ? parseFloat(row.week52_low) : null,
      pct_from_high:       row.pct_from_high ? parseFloat(row.pct_from_high) : null,
      yield_pct:           row.yield_pct ? parseFloat(row.yield_pct) : null,
      sec_yield_pct:       row.sec_yield_pct ? parseFloat(row.sec_yield_pct) : null,
      hist_avg_yield_pct:  row.hist_avg_yield_pct ? parseFloat(row.hist_avg_yield_pct) : null,
      yield_vs_avg_pct:    row.yield_vs_avg_pct ? parseFloat(row.yield_vs_avg_pct) : null,
      duration_years:      row.duration_years ? parseFloat(row.duration_years) : null,
      modified_duration:   row.modified_duration ? parseFloat(row.modified_duration) : null,
      expense_ratio_pct:   row.expense_ratio_pct ? parseFloat(row.expense_ratio_pct) : null,
      value_rating:        row.value_rating ?? '',
      recommendation:      row.recommendation ?? '',
      generated_at:        row.generated_at ?? '',
    }))
  }
  const res = await apiClient.get<{ data: BondOpportunity[] }>('/api/bonds')
  return res.data.data ?? []
}

export interface CommodityOpportunity {
  ticker: string
  name: string
  short_name: string
  commodity_type: string
  sector: string
  currency: string
  ibkr_ireland: boolean
  price: number | null
  week52_high: number | null
  week52_low: number | null
  pct_from_high: number | null
  pct_from_low: number | null
  range_position: number | null
  avg_2y_price: number | null
  pct_vs_2y_avg: number | null
  vol_ratio: number | null
  change_1d: number | null
  dist_yield_pct: number | null
  expense_ratio_pct: number | null
  momentum_signal: string
  seasonality: string
  value_rating: string
  recommendation: string
  cycle_driver: string
  cycle_bullish: string
  cycle_bearish: string
  generated_at: string
}

export async function fetchCommodities(): Promise<CommodityOpportunity[]> {
  try {
    const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined
    if (!csvBase) throw new Error('no csvBase')
    const url = `${csvBase}/commodity_opportunities.csv`
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const text = await res.text()
    const lines = text.trim().split('\n')
    if (lines.length < 2) return []
    const headers = lines[0].split(',')
    return lines.slice(1).map(line => {
      const vals = line.split(',')
      const row: Record<string, string> = {}
      headers.forEach((h, i) => { row[h.trim()] = (vals[i] ?? '').trim() })
      return {
        ticker:           row.ticker ?? '',
        name:             row.name ?? '',
        short_name:       row.short_name ?? '',
        commodity_type:   row.commodity_type ?? '',
        sector:           row.sector ?? '',
        currency:         row.currency ?? '',
        ibkr_ireland:     row.ibkr_ireland === 'True',
        price:            row.price ? parseFloat(row.price) : null,
        week52_high:      row.week52_high ? parseFloat(row.week52_high) : null,
        week52_low:       row.week52_low ? parseFloat(row.week52_low) : null,
        pct_from_high:    row.pct_from_high ? parseFloat(row.pct_from_high) : null,
        pct_from_low:     row.pct_from_low ? parseFloat(row.pct_from_low) : null,
        range_position:   row.range_position ? parseFloat(row.range_position) : null,
        avg_2y_price:     row.avg_2y_price ? parseFloat(row.avg_2y_price) : null,
        pct_vs_2y_avg:    row.pct_vs_2y_avg ? parseFloat(row.pct_vs_2y_avg) : null,
        vol_ratio:        row.vol_ratio ? parseFloat(row.vol_ratio) : null,
        change_1d:        row.change_1d ? parseFloat(row.change_1d) : null,
        dist_yield_pct:   row.dist_yield_pct ? parseFloat(row.dist_yield_pct) : null,
        expense_ratio_pct: row.expense_ratio_pct ? parseFloat(row.expense_ratio_pct) : null,
        momentum_signal:  row.momentum_signal ?? '',
        seasonality:      row.seasonality ?? '',
        value_rating:     row.value_rating ?? '',
        recommendation:   row.recommendation ?? '',
        cycle_driver:     row.cycle_driver ?? '',
        cycle_bullish:    row.cycle_bullish ?? '',
        cycle_bearish:    row.cycle_bearish ?? '',
        generated_at:     row.generated_at ?? '',
      }
    })
  } catch {
    try {
      const res = await apiClient.get<{ data: CommodityOpportunity[] }>('/api/commodities')
      return res.data.data ?? []
    } catch {
      return []
    }
  }
}

export interface MlWinPrediction {
  probability: number
  percentile: number
  label: 'ALTA' | 'MEDIA' | 'BAJA'
}

export interface MlWinProbabilityData {
  generated_at: string
  market_regime: string
  model_auc: number
  base_win_rate: number
  predictions: Record<string, MlWinPrediction>
}

export interface ContrarianPick {
  ticker: string
  company_name: string
  sector: string | null
  current_price: number | null
  drawdown_from_52w: number
  analyst_upside_pct: number | null
  analyst_count: number | null
  piotroski_score: number | null
  roe_pct: number | null
  fcf_yield_pct: number | null
  profit_margin_pct: number | null
  debt_to_equity: number | null
  verdict: 'CONTRARIAN_BUY' | 'WATCH' | 'AVOID'
  confidence: number
  drop_reason: string
  is_circumstantial: boolean
  recovery_thesis: string
  key_risks: string
}

export interface ContrarianData {
  generated_at: string
  count: number
  contrarian_buys: number
  picks: ContrarianPick[]
}

export type PortfolioAlertType = 'STOP_TRIGGERED' | 'TARGET_REACHED' | 'NEAR_TARGET'

export interface PortfolioAlert {
  type: PortfolioAlertType
  ticker: string
  current: number
  entry: number
  target: number | null
  pct_change: number
  pct_to_target: number | null
}

export interface PortfolioAlertsData {
  generated_at: string
  alerts: PortfolioAlert[]
  counts: {
    stop_triggered: number
    target_reached: number
    near_target: number
  }
}

export async function fetchPortfolioAlerts(): Promise<PortfolioAlertsData | null> {
  try {
    const url = `${STATIC_DATA_BASE}/portfolio_alerts.json`
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json() as PortfolioAlertsData
  } catch {
    try {
      const res = await apiClient.get<PortfolioAlertsData>('/api/portfolio-price-alerts')
      return res.data
    } catch {
      return null
    }
  }
}

export type ScoreAlertType = 'NEW_ENTRY' | 'EXITED' | 'SCORE_UP' | 'SCORE_DOWN'

export interface ScoreAlert {
  type: ScoreAlertType
  ticker: string
  company_name: string
  sector: string
  score_today: number | null
  score_prev: number | null
  delta: number | null
  grade: string
}

export interface ScoreAlertsData {
  generated_at: string
  alerts: ScoreAlert[]
  counts: {
    new_entries: number
    exited: number
    score_up: number
    score_down: number
  }
}

export async function fetchScoreAlerts(): Promise<ScoreAlertsData | null> {
  try {
    const url = `${STATIC_DATA_BASE}/score_alerts.json`
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json() as ScoreAlertsData
  } catch {
    try {
      const res = await apiClient.get<ScoreAlertsData>('/api/score-alerts')
      return res.data
    } catch {
      return null
    }
  }
}

export async function fetchContrarianPicks(): Promise<ContrarianData | null> {
  try {
    // Try static GitHub Pages first (always fresh), fallback to Railway API
    const url = `${STATIC_DATA_BASE}/contrarian_picks.json`
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json() as ContrarianData
  } catch {
    try {
      const res = await apiClient.get<ContrarianData>('/api/contrarian-picks')
      return res.data
    } catch {
      return null
    }
  }
}

export async function fetchMlWinProbability(): Promise<MlWinProbabilityData | null> {
  try {
    const url = `${STATIC_DATA_BASE}/ml_win_probability.json`
    const res = await apiClient.get<MlWinProbabilityData>(url, {
      transformResponse: [(d) => typeof d === 'string' ? JSON.parse(d) : d],
    })
    return res.data
  } catch {
    return null
  }
}

// ── LEAPS (deep-ITM long-dated calls como sustituto apalancado de acciones) ───
export interface LeapsContract {
  expiry: string
  dte: number
  t_years: number
  strike: number
  bid: number
  ask: number
  mid: number
  cost_per_contract: number
  iv_pct: number
  open_interest: number
  volume: number
  spread_pct: number
  contract_score: number
  target_return_pct: number
  delta: number | null
  intrinsic: number
  extrinsic: number
  extrinsic_pct: number | null
  annual_carry_pct: number | null
  leverage: number | null
  breakeven: number
  breakeven_move_pct: number | null
}

export interface LeapsProfitAtTarget {
  target_price: number
  stock_return_pct: number
  option_return_pct: number
  leverage_realized: number | null
}

export interface LeapsExitPlan {
  take_profit?: string
  roll?: string
  thesis_break?: string
}

export type LeapsSituation = 'CAIDA_CIRCUNSTANCIAL' | 'CALIDAD_RAZONABLE' | 'DIP_GANADOR' | 'DETERIORO'

export interface LeapsVerdict {
  verdict: 'OPORTUNIDAD' | 'RAZONABLE' | 'EVITAR'
  reason: string
}

export interface LeapsOpportunity {
  ticker: string
  company_name: string
  sector?: string | null
  spot: number
  quality_score: number | null
  timing_score: number
  analyst_upside_pct: number | null
  conviction_grade?: string | null
  opportunity_score: number
  situation?: LeapsSituation
  pct_from_52w_high?: number | null
  ytd_pct?: number | null
  forward_pe?: number | null
  recommended_contract: LeapsContract
  alternative_contracts?: LeapsContract[]
  profit_at_target?: LeapsProfitAtTarget | null
  in_value_list: boolean
  ai_narrative?: string
  situation_verdict?: LeapsVerdict
  exit_plan?: LeapsExitPlan
  generated_at?: string
  risk_free_rate_pct?: number
  error?: string
}

export interface LeapsData {
  generated_at: string
  risk_free_rate_pct: number
  universe_size: number
  analyzed: number
  methodology: {
    delta_band: [number, number]
    min_dte: number
    max_carry_pct: number
    note: string
  }
  opportunities: LeapsOpportunity[]
}

export async function fetchLeaps(): Promise<LeapsData | null> {
  // El ranking precalculado vive en GitHub Pages (output del pipeline diario).
  // Railway solo tiene el snapshot del último deploy → quedaría desactualizado.
  try {
    const res = await fetch(`${STATIC_DATA_BASE}/leaps_opportunities.json`, { cache: 'no-store' })
    if (!res.ok) return null
    return await res.json() as LeapsData
  } catch {
    return null
  }
}

export async function fetchLeapsTicker(ticker: string): Promise<LeapsOpportunity> {
  const res = await apiClient.get<LeapsOpportunity>(`/api/leaps/${encodeURIComponent(ticker)}`)
  return res.data
}
