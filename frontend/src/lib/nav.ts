import {
  Globe, TrendingUp, Users, Activity,
  ArrowLeftRight, PieChart, BarChart2, FlaskConical, Search, LayoutDashboard, Database,
  Ruler, Layers, Star, Radar, CalendarDays, AlertTriangle, Sparkles, Building2, Zap,
  DollarSign, Euro,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type NavSection  = { section: string }
export type NavLinkItem = { path: string; icon: LucideIcon; label: string; color: string; tag?: string; keywords?: string[] }
export type NavItem = NavSection | NavLinkItem

export const NAV: NavItem[] = [
  { path: '/dashboard',      icon: LayoutDashboard, label: 'Dashboard',           color: '#6366f1', keywords: ['inicio', 'home', 'resumen'] },
  { section: 'Estrategias' },
  { path: '/value',          icon: DollarSign,      label: 'Value',               color: '#10b981', tag: '🇺🇸', keywords: ['value', 'fundamental', 'us', 'acciones'] },
  { path: '/value-eu',       icon: Euro,            label: 'Value',               color: '#3b82f6', tag: '🇪🇺', keywords: ['value', 'europa', 'europeo'] },
  { path: '/value-global',   icon: Globe,           label: 'Value',               color: '#a855f7', tag: '🌍', keywords: ['value', 'global', 'mundial'] },
  { path: '/momentum',       icon: TrendingUp,      label: 'Momentum',            color: '#f97316', keywords: ['momentum', 'tendencia', 'minervini', 'vcp'] },
  { path: '/macro-radar',    icon: Radar,           label: 'Macro Radar',         color: '#e11d48', keywords: ['macro', 'radar', 'economía'] },
  { path: '/earnings',       icon: CalendarDays,    label: 'Earnings Calendar',   color: '#f59e0b', keywords: ['earnings', 'resultados', 'calendario', 'earnings date'] },
  { path: '/dividend-traps', icon: AlertTriangle,   label: 'Dividend Traps',      color: '#ef4444', keywords: ['dividendo', 'trampa', 'yield trap'] },
  { path: '/smart-portfolio', icon: Sparkles,       label: 'Smart Portfolio',     color: '#a855f7', keywords: ['portfolio', 'cartera', 'smart', 'builder'] },
  { path: '/hedge-funds',     icon: Building2,      label: 'Hedge Funds 13F',     color: '#f59e0b', keywords: ['hedge fund', '13f', 'buffett', 'ackman', 'klarman', 'sec', 'whales'] },
  { path: '/factor-status',   icon: Zap,            label: 'Factor Status',       color: '#6366f1', keywords: ['factor', 'value momentum quality insider smart money fama french aqr'] },
  { section: 'Señales' },
  { path: '/insiders',       icon: Users,           label: 'Insiders',            color: '#8b5cf6', keywords: ['insiders', 'directivos', 'compras'] },
  { path: '/options',        icon: Activity,        label: 'Options Flow',        color: '#ec4899', keywords: ['options', 'opciones', 'flujo', 'institucional'] },
  { path: '/mean-reversion', icon: ArrowLeftRight,  label: 'Mean Reversion',      color: '#14b8a6', keywords: ['mean reversion', 'rebote', 'soporte', 'oversold'] },
  { path: '/sectors',        icon: PieChart,        label: 'Rotación Sectorial',  color: '#6366f1', keywords: ['sector', 'rotacion', 'sectorial'] },
  { section: 'Rendimiento' },
  { path: '/portfolio',      icon: BarChart2,       label: 'Portfolio Tracker',   color: '#22c55e', keywords: ['portfolio', 'cartera', 'rendimiento', 'tracker'] },
  { path: '/backtest',       icon: FlaskConical,    label: 'Backtest',            color: '#a78bfa', keywords: ['backtest', 'historico', 'simulacion'] },
  { section: 'Análisis' },
  { path: '/industry-groups', icon: Layers,         label: 'Industry Groups',     color: '#0ea5e9', keywords: ['industry', 'grupos', 'industria', 'rs'] },
  { path: '/position-sizing', icon: Ruler,          label: 'Position Sizing',     color: '#f59e0b', keywords: ['position', 'tamaño', 'kelly', 'sizing'] },
  { section: 'Herramientas' },
  { path: '/watchlist',      icon: Star,            label: 'Watchlist',           color: '#f59e0b', keywords: ['watchlist', 'seguimiento', 'favoritos'] },
  { path: '/search',         icon: Search,          label: 'Buscar Ticker',       color: '#94a3b8', keywords: ['buscar', 'ticker', 'search', 'analisis'] },
  { path: '/datos',          icon: Database,        label: 'Datos & Historial',   color: '#64748b', keywords: ['datos', 'historial', 'csv', 'descarga'] },
]

export const NAV_LINKS = NAV.filter((item): item is NavLinkItem => 'path' in item)
