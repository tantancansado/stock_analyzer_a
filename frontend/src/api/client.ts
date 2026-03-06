import axios from 'axios'
import { supabase } from '@/lib/supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
})

// Attach Supabase JWT to every request
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
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
  total_qty?: number
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
  top_performers?: Array<Record<string, unknown>>
  worst_performers?: Array<Record<string, unknown>>
  recent_signals?: Array<Record<string, unknown>>
  avg_max_drawdown?: number
  score_correlation?: number
}

export interface MarketRegime {
  us: Record<string, unknown>
  eu: Record<string, unknown>
}

export const fetchValueOpportunities = () =>
  api.get<{ data: ValueOpportunity[]; count: number; source: string }>('/api/value-opportunities')

export const fetchEUValueOpportunities = () =>
  api.get<{ data: ValueOpportunity[]; count: number; source: string }>('/api/eu-value-opportunities')

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

const GLOBAL_NUMERIC = new Set([
  'current_price','value_score','conviction_score','conviction_positives','conviction_red_flags',
  'market_cape','target_price_analyst','analyst_upside_pct','analyst_count',
  'fcf_yield_pct','risk_reward_ratio','dividend_yield_pct','roe_pct',
  'pe_forward','pe_trailing','profit_margin_pct','revenue_growth_pct','pct_from_52w_high',
])

export const fetchGlobalValueOpportunities = async (): Promise<{
  data: { data: ValueOpportunity[]; count: number; source: string }
}> => {
  const csvBase = import.meta.env.VITE_CSV_BASE as string | undefined
  if (csvBase) {
    // Production: read CSV directly from GitHub Pages (always up-to-date)
    const url = `${csvBase}/global_value_opportunities.csv`
    const res = await fetch(url)
    if (!res.ok) throw new Error(`CSV fetch failed: ${res.status}`)
    const text = await res.text()
    const rawRows = parseCsvRows(text)
    const data = rawRows.map(row => {
      const obj: Record<string, unknown> = {}
      for (const [k, v] of Object.entries(row)) {
        if (GLOBAL_NUMERIC.has(k)) obj[k] = v === '' ? null : Number(v)
        else if (k === 'buyback_active') obj[k] = v.toLowerCase() === 'true'
        else obj[k] = v === '' ? undefined : v
      }
      return obj as unknown as ValueOpportunity
    })
    return { data: { data, count: data.length, source: 'github-pages' } }
  }
  // Development: Railway API reads local docs/ folder
  const res = await api.get<{ data: ValueOpportunity[]; count: number; source: string }>('/api/global-value')
  return { data: res.data }
}

export const fetchMomentumOpportunities = () =>
  api.get<{ data: MomentumOpportunity[]; count: number; source: string }>('/api/momentum-opportunities')

export const fetchSectorRotation = () =>
  api.get<SectorRotationData>('/api/sector-rotation')

export const fetchOptionsFlow = () =>
  api.get('/api/options-flow')

export const fetchMeanReversion = () =>
  api.get('/api/mean-reversion')

export const fetchRecurringInsiders = () =>
  api.get<{ data: InsiderData[]; count: number; source: string }>('/api/recurring-insiders')

export const fetchPortfolioTracker = () =>
  api.get<PortfolioSummary>('/api/portfolio-tracker')

export const fetchMarketRegime = () =>
  api.get<MarketRegime>('/api/market-regime')

export const fetchMacroRadar = () =>
  api.get('/api/macro-radar')

export const fetchMacroRadarHistory = () =>
  api.get<{ history: Array<{ date: string; composite_score: number; composite_pct: number; regime: string; regime_color: string }> }>('/api/macro-radar/history')

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
}

export const fetchEarningsCalendar = () =>
  api.get<{ earnings: EarningsEntry[]; total: number; as_of: string }>('/api/earnings-calendar')

export const fetchBacktest = () =>
  api.get('/api/backtest')

export const fetchThesis = (ticker: string) =>
  api.get<{ ticker: string; thesis: string | null }>(`/api/theses/${ticker}`)

export const analyzeTicker = (ticker: string) =>
  api.get(`/api/analyze/${ticker}`)

export interface SearchResult {
  ticker: string
  company_name: string
  sector?: string
}

export const searchTickers = (q: string) =>
  api.get<{ results: SearchResult[] }>(`/api/search?q=${encodeURIComponent(q)}`)

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

export default api
